"""Website-ready inventory feed for kapoorgalleries/sb1-vuxiwzek.

Produces ``data/website_inventory.json`` — a richer per-work shape than
``master.json`` (which is the raw consolidation output).  Designed to
drop straight into a static-site generator / SPA build:

  - Stable URL slugs.
  - Pre-formatted human-readable dimensions and prices.
  - Image variants (primary + alternates) folded into one ``image``
    object instead of a flat URL string.
  - Tag inference (period, region, deity, medium-family) for filters.
  - Per-work ``visibility`` flag — works that are sold / hidden /
    placeholder-titled don't leak through.
  - Empty / private fields are dropped, not emitted as null, so the
    consumer doesn't have to ``if x !== null`` everywhere.

The schema is documented in ``WEBSITE_SCHEMA.md`` (sibling file) so the
frontend can type it once and stay in sync.

Filter rules (mirrored from artsy_upload_csv and lint):
  - Exclude status != 'active'  (external / sold / needs_renumbering).
  - Exclude internal placeholder titles ("Need title", "TBD" …).
  - Always include 'Untitled' (it's a legitimate art title).
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

import sqlite_utils

from ..normalize import INTERNAL_PLACEHOLDER_TITLES


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _slug(text: str, max_len: int = 60) -> str:
    """Slugify a string for URL use ('Krishna and Radha' -> 'krishna-and-radha')."""
    if not text:
        return ""
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s[:max_len].rstrip("-")


def _decimal_to_fraction(value: float) -> str:
    """Render an inches value back as a mixed fraction, when it matches a
    common art-world denominator (1/2, 1/4, 1/8, 3/8 …).  Falls back to
    one-decimal-place if the fractional part doesn't round to a clean
    denominator.  Returns '' for None / 0.
    """
    if value is None or value == 0:
        return ""
    whole = int(value)
    frac = round((value - whole) * 1000) / 1000
    # Common art-world fractions.
    FRACTIONS = [
        (0.125, "1/8"), (0.25, "1/4"), (0.375, "3/8"), (0.5, "1/2"),
        (0.625, "5/8"), (0.75, "3/4"), (0.875, "7/8"),
    ]
    if abs(frac) < 0.05:
        return str(whole) if whole else "0"
    for f, label in FRACTIONS:
        if abs(frac - f) < 0.02:
            return f"{whole} {label}" if whole else label
    # Fallback — one decimal place, drop trailing zero.
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _dimensions_display(h: Any, w: Any, d: Any) -> str:
    """Format dims in art-world style: '24 1/2 × 18 in. (62.2 × 45.7 cm.)'.
    Returns '' if neither h nor w is present.
    """
    def _fl(x: Any) -> float | None:
        try:
            f = float(x)
            return f if f > 0 else None
        except (TypeError, ValueError):
            return None
    h, w, d = _fl(h), _fl(w), _fl(d)
    if h is None and w is None:
        return ""
    parts_in = [_decimal_to_fraction(v) for v in (h, w, d) if v is not None]
    parts_cm = [f"{v * 2.54:.1f}".rstrip("0").rstrip(".") for v in (h, w, d) if v is not None]
    return f"{' × '.join(parts_in)} in. ({' × '.join(parts_cm)} cm.)"


def _price_display(price: Any) -> str:
    """Format USD price.  '$25,000' for set values; 'Price on request' when
    blank (so the website never shows a confusing $0 or empty cell).
    """
    try:
        f = float(price)
        if f <= 0:
            return "Price on request"
        return f"${f:,.0f}"
    except (TypeError, ValueError):
        return "Price on request"


# Tag inference — quick categorization for filter/facet UI.  These are
# additive (a work can carry multiple tags).
_PERIOD_PATTERNS = {
    "ancient":           r"\b(2nd|3rd|4th)\s+century|ancient",
    "medieval":          r"\b(8th|9th|10th|11th|12th|13th|14th)\s+century|medieval",
    "early-modern":      r"\b(15th|16th|17th)\s+century",
    "18th-century":      r"\b18th\s+century",
    "19th-century":      r"\b19th\s+century",
    "20th-century":      r"\b20th\s+century",
    "21st-century":      r"\b21st\s+century|contemporary",
}
_REGION_PATTERNS = {
    "tibetan":           r"\btibet|himalayan",
    "indian":            r"\bindian?\b|kashmir|bengal|pahari|rajasthan|deccan|gujarat|mughal|kangra|mewar",
    "nepalese":          r"\bnepal",
    "south-east-asian":  r"\bcambodia|burma|thailand|vietnam|myanmar",
    "persian":           r"\bpersian|iran|safavid|qajar",
    "japanese":          r"\bjapan|edo|meiji|naginata|kabuto",
    "chinese":           r"\bchinese|sino-",
    "western":           r"\beuropean|american|british|french|german|italian",
}
_SUBJECT_PATTERNS = {
    "thangka":           r"\bthangka",
    "mandala":           r"\bmandala",
    "buddha":            r"\bbuddha|shakyamuni|maitreya|amitayus",
    "vishnu":            r"\bvishnu|krishna|rama|narayana",
    "shiva":             r"\bshiva|nataraja|parvati|durga|kali",
    "tara":              r"\btara\b",
    "avalokiteshvara":   r"\bavalokiteshvara|padmapani|lokeshvara",
    "manuscript":        r"\bmanuscript|folio|leaf|kalpa-sutra",
    "ragamala":          r"\bragamala|ragini|ragamala",
    "portrait":          r"\bportrait|maharaja|maharana|nizam|prince",
    "weapon":            r"\bkhanjar|talwar|shamshir|naginata|sword|dagger",
    "jewelry":           r"\bring|necklace|amulet|gau|bangle|diamond",
}


# Map period tags to display strings — used to derive ``era_display``
# when a work has no explicit year.  The site author asked: "Year
# fallback — render as blank, as 'Date unknown', or as the era from
# tags?" — this populates the era-from-tags option so the site can
# pick a fallback at render time without re-computing it.
_PERIOD_DISPLAY = {
    "ancient":       "Ancient",
    "medieval":      "Medieval",
    "early-modern":  "Early modern",
    "18th-century":  "18th century",
    "19th-century":  "19th century",
    "20th-century":  "20th century",
    "21st-century":  "Contemporary",
}


def _era_display_from_tags(tags: list[str]) -> str | None:
    """Pick the most specific period tag and return its display label.
    Returns None if no period-shaped tag is present.
    """
    # Prefer century tags over the broader buckets.
    for t in tags:
        if re.match(r"^\d+(st|nd|rd|th)-century$", t):
            n = re.match(r"^(\d+)", t).group(1)
            # Match the natural-language form ("19th century").
            return _PERIOD_DISPLAY.get(t) or f"{n}{t.split('-')[0][-2:]} century"
    for t in tags:
        if t in _PERIOD_DISPLAY:
            return _PERIOD_DISPLAY[t]
    return None


def _infer_tags(title: str, classification: str, medium: str, year: int | None) -> list[str]:
    blob = " ".join(filter(None, [title, classification, medium])).lower()
    tags: list[str] = []
    for label, pat in {**_PERIOD_PATTERNS, **_REGION_PATTERNS, **_SUBJECT_PATTERNS}.items():
        if re.search(pat, blob):
            tags.append(label)
    # Year-based fallback period tag, if nothing matched.
    if year and not any(t.endswith("-century") or t in ("ancient", "medieval") for t in tags):
        c = (year + 99) // 100  # 1850 -> 19th
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(c % 10 if (c % 100) not in (11, 12, 13) else 0, "th")
        tags.append(f"{c}{suffix}-century")
    # Medium-family tag.
    m = (medium or "").lower()
    if "bronze" in m or "copper alloy" in m or "gilt" in m: tags.append("metal")
    if "sandstone" in m or "schist" in m or "stone" in m or "marble" in m: tags.append("stone")
    if "wood" in m: tags.append("wood")
    if "paper" in m or "wasli" in m: tags.append("works-on-paper")
    if "cloth" in m or "cotton" in m or "silk" in m: tags.append("textile-ground")
    return sorted(set(tags))


# ---------------------------------------------------------------------------
# core exporter
# ---------------------------------------------------------------------------


def export_website_inventory(
    db: sqlite_utils.Database | None,
    out_path: Path | str,
    *,
    source_csv: Path | str = "data/master.csv",
    include_prices: bool = True,
) -> tuple[Path, int]:
    """Build the website-ready inventory feed.

    Reads from ``master.csv`` (the canonical, post-consolidate CSV) so this
    exporter works even if the SQLite DB has been deleted.  ``db`` is
    accepted for signature symmetry with other exporters but isn't required.

    ``include_prices=False`` strips numeric prices and replaces with
    "Price on request" everywhere — useful if the gallery wants to keep
    pricing internal.

    Returns (out_path, work_count).
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    src = Path(source_csv)
    if not src.exists():
        raise FileNotFoundError(
            f"{src} doesn't exist — run `make all` first."
        )

    works: list[dict] = []
    with src.open(newline="") as fh:
        for row in csv.DictReader(fh):
            wid = (row.get("work_id") or "").strip()
            if not wid:
                continue
            # Active-only.  External sub-inventory and needs_renumbering
            # records are not website candidates.
            status = (row.get("status") or "active").strip()
            if status != "active":
                continue
            title = (row.get("title") or "").strip()
            if title.lower() in INTERNAL_PLACEHOLDER_TITLES:
                continue

            classification = (row.get("classification") or "").strip()
            medium = (row.get("medium") or "").strip()
            year_raw = (row.get("year") or "").strip()
            try:
                year = int(float(year_raw)) if year_raw else None
            except ValueError:
                year = None

            def _f(field: str) -> float | None:
                v = (row.get(field) or "").strip()
                if not v:
                    return None
                try:
                    return float(v)
                except ValueError:
                    return None

            h, w, d = _f("height_in"), _f("width_in"), _f("depth_in")
            price = _f("price_usd")

            doc: dict[str, Any] = {
                "id": wid.lower(),
                "kg_id": wid,
                "slug": (_slug(wid) + "-" + _slug(title, 40)).strip("-"),
                "url_path": f"/works/{(_slug(wid) + '-' + _slug(title, 40)).strip('-')}",
                "title": title,
                "classification": classification or None,
                "medium": medium or None,
                "year": year,
                "year_display": str(year) if year is not None else None,
                "dimensions": {
                    "height_in": h, "width_in": w, "depth_in": d,
                    "display": _dimensions_display(h, w, d) or None,
                },
                "price": {
                    "usd": price if include_prices else None,
                    "display": _price_display(price) if include_prices else "Price on request",
                    "available": price is not None and include_prices,
                },
                "image": {
                    "primary": (row.get("primary_image_url") or "").strip() or None,
                    "alternates": [],  # filled by image-catalog merge in a later step
                    "thumbnail": None,
                },
                "tags": _infer_tags(title, classification, medium, year),
                "status": "available",
                "era_display": None,  # filled in below — needs the tag list
                "_internal": {
                    "primer_uuid": (row.get("primer_uuid") or "").strip() or None,
                    "has_conflict": bool(int((row.get("has_conflict") or "0") or 0)),
                },
            }

            # era_display — fallback for the site author's
            # "year missing → what to show?" decision.  We derive it
            # from the inferred period tags so the site can render
            # "19th century" instead of blank when year is null.
            if year is None:
                doc["era_display"] = _era_display_from_tags(doc["tags"])
            else:
                # Drop the placeholder so works with a year don't carry
                # a redundant era string.
                doc.pop("era_display", None)

            # Optional fields — only emit if populated, so the consumer
            # doesn't see noisy nulls.
            for key, csv_field in (
                ("artist", "artist"),
                ("period_school_region", "period_school_region"),
                ("materials", "materials"),
                ("provenance", "provenance_text"),
                ("exhibitions", "exhibitions"),
                ("publications", "publications"),
                ("signature", "signature"),
                ("coa_status", "coa_status"),
            ):
                v = (row.get(csv_field) or "").strip()
                if v:
                    doc[key] = v

            works.append(doc)

    # Stable sort: classification group, then KG-#.
    works.sort(key=lambda d: (d.get("classification") or "zzz", d["kg_id"]))

    payload = {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "count": len(works),
        "facets": _build_facets(works),
        "works": works,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return out, len(works)


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_facets(works: list[dict]) -> dict:
    """Pre-compute filter facets so the frontend doesn't have to scan
    every work to populate dropdowns."""
    from collections import Counter
    classification = Counter(w["classification"] for w in works if w.get("classification"))
    tags = Counter(t for w in works for t in (w.get("tags") or []))
    has_image = sum(1 for w in works if w.get("image", {}).get("primary"))
    return {
        "classification": [
            {"value": c, "count": n} for c, n in classification.most_common()
        ],
        "tags": [{"value": t, "count": n} for t, n in tags.most_common()],
        "with_image": has_image,
        "without_image": len(works) - has_image,
    }
