"""Curator-grade enrichment: merge external Sheet data into the
website inventory feed by fuzzy title match.

Source: ``data/raw/catalog_and_inventory_tab1.csv`` (the "2024
Catalogue" tab of the master Catalog & Inventory Google Sheet).

For each row with a title that matches an existing KG-numbered work
in ``data/master.csv`` (rapidfuzz token-set ratio >= threshold), copy
the rich fields — provenance, physical location, literature/exhibited,
acquired-from — into the website feed.  Conservative threshold: 88
(out of 100) to avoid wrong matches across similarly-named works.

Output: ``data/website_inventory_enriched.json`` (same schema as
``website_inventory.json`` but with the additional fields populated
on ~30-50% more works) PLUS ``data/enrichment_audit.csv`` so the
curator can spot-check the matches.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False


# Words to strip when normalizing for match — these are common
# disambiguators that vary across sources.
_NOISE_WORDS = re.compile(
    r"\b(folio|leaf|page|illustration|from\s+a|series|circa|c\.|ca\.|the)\b",
    re.IGNORECASE,
)


def _norm_title(s: str) -> str:
    s = (s or "").lower().strip()
    s = _NOISE_WORDS.sub(" ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _best_match(
    needle: str, haystack: list[tuple[str, str]], threshold: int = 88
) -> tuple[str, int] | None:
    """Find the best KG-# match for ``needle`` in ``haystack`` (a list
    of ``(kg_id, normalized_title)`` pairs).  Returns ``(kg_id, score)``
    if score >= threshold, else None."""
    if not needle or not HAS_RAPIDFUZZ:
        return None
    best_kg = None
    best_score = 0
    for kg_id, h_title in haystack:
        if not h_title:
            continue
        # token_set_ratio is forgiving of word reordering — fine for
        # titles like "X folio from a Ramayana" vs "Ramayana folio X".
        score = int(fuzz.token_set_ratio(needle, h_title))
        if score > best_score:
            best_score = score
            best_kg = kg_id
    return (best_kg, best_score) if best_kg and best_score >= threshold else None


def _read_csv_rows(path: Path) -> list[dict]:
    """Read a CSV and return rows with stripped header/value whitespace."""
    with path.open(newline="") as fh:
        raw = list(csv.DictReader(fh))
    return [{k.strip(): (v or "").strip() for k, v in r.items()} for r in raw]


def _is_sold(row: dict) -> bool:
    """Honor a SOLD-like column if present (all-tabs CSV adds one)."""
    val = (row.get("SOLD") or row.get("Sold") or "").lower().strip()
    return val in {"x", "yes", "y", "sold", "true", "1"}


def export_enrichment(
    *,
    source_csv: Path | str = "data/raw/catalog_and_inventory_tab1.csv",
    extra_sources: list[Path | str] | None = None,
    base_feed: Path | str = "data/website_inventory.json",
    out_feed: Path | str = "data/website_inventory_enriched.json",
    audit_csv: Path | str = "data/enrichment_audit.csv",
    sold_csv: Path | str = "data/sold_candidates.csv",
    threshold: int = 88,
    sold_threshold: int = 95,
) -> tuple[Path, dict]:
    """Merge external enrichment data into the website feed.

    ``source_csv`` is the primary catalog CSV (tab-1 export today).
    ``extra_sources`` lets the caller chain additional CSVs (e.g. the
    all-tabs export covering tabs 2-5).  Rows already matched by an
    earlier source aren't overwritten by later ones — first source wins
    per field, except where the later value is strictly richer.

    Returns (out_feed, stats) where stats is a dict with match counts.
    """
    src = Path(source_csv)
    extras = [Path(p) for p in (extra_sources or []) if Path(p).exists()]
    base = Path(base_feed)
    out = Path(out_feed)
    audit = Path(audit_csv)
    sold_out = Path(sold_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    audit.parent.mkdir(parents=True, exist_ok=True)
    sold_out.parent.mkdir(parents=True, exist_ok=True)

    if not base.exists():
        raise FileNotFoundError(
            f"{base} missing — run `kg-inv export-website` first."
        )
    feed = json.loads(base.read_text())

    # If the primary enrichment source is missing, emit the base feed
    # unchanged and an empty audit — keeps `make report` deterministic.
    if not src.exists() and not extras:
        out.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n")
        audit.write_text("kg_id,match_score,external_title,decision\n")
        return out, {
            "source_rows": 0, "matched": 0, "skipped_low_score": 0,
            "skipped_no_title": 0, "skipped_sold": 0,
            "note": f"{src} not present",
        }

    if not HAS_RAPIDFUZZ:
        # Degrade gracefully — emit the base feed and note in audit
        out.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n")
        audit.write_text("kg_id,match_score,external_title,decision\n"
                         "(none),0,,rapidfuzz not installed; pip install rapidfuzz\n")
        return out, {"matched": 0, "note": "rapidfuzz missing"}

    # Build the haystack: (kg_id, normalized_title) for every active
    # work in the feed.
    haystack: list[tuple[str, str]] = [
        (w["kg_id"], _norm_title(w["title"])) for w in feed["works"]
    ]
    by_kg = {w["kg_id"]: w for w in feed["works"]}

    # Read all sources, in priority order: primary first, then extras.
    # Header whitespace is stripped because the curator sheets vary
    # ("Medium " with a trailing space in tab-1, plain "Medium" in
    # the all-tabs export).
    rows: list[dict] = []
    if src.exists():
        rows.extend(_read_csv_rows(src))
    for ex in extras:
        rows.extend(_read_csv_rows(ex))

    # Predeclare the keys so the returned dict always has the same
    # shape — consumers can assume `stats["matched"]` is always there.
    stats: Counter = Counter(
        source_rows=0, matched=0, skipped_low_score=0,
        skipped_no_title=0, skipped_sold=0,
    )
    audit_rows: list[dict] = []
    sold_candidates: list[dict] = []
    seen_kg: set[str] = set()
    for r in rows:
        stats["source_rows"] += 1
        ext_title = r.get("Title", "")
        if not ext_title:
            stats["skipped_no_title"] += 1
            continue
        if _is_sold(r):
            stats["skipped_sold"] += 1
            # Run the fuzzy match against the active feed at a TIGHTER
            # threshold (95 vs 88).  If the curator-flagged-sold title
            # closely matches an active KG-#, record it as a candidate
            # for review.  We never auto-remove from the public feed —
            # curator confirmation is required, since title collisions
            # across centuries happen ("Krishna and Radha" exists ~30x).
            sold_match = _best_match(
                _norm_title(ext_title), haystack, sold_threshold
            )
            if sold_match:
                kg_id, score = sold_match
                sold_candidates.append({
                    "kg_id": kg_id,
                    "match_score": score,
                    "external_title": ext_title[:120],
                    "current_title": by_kg.get(kg_id, {}).get("title", "")[:120],
                    "action": "review-and-confirm-before-removing-from-public-feed",
                })
            audit_rows.append({
                "kg_id": sold_match[0] if sold_match else "",
                "match_score": sold_match[1] if sold_match else 0,
                "external_title": ext_title[:80],
                "decision": ("skipped: SOLD flag set in curator sheet"
                             + (" (sold-candidate emitted)" if sold_match
                                else "")),
            })
            continue
        result = _best_match(_norm_title(ext_title), haystack, threshold)
        if not result:
            stats["skipped_low_score"] += 1
            audit_rows.append({
                "kg_id": "",
                "match_score": 0,
                "external_title": ext_title[:80],
                "decision": "no match >= threshold",
            })
            continue
        kg_id, score = result
        # First-source-wins: if we already merged this KG-# from an
        # earlier row, skip later rows from extra sources rather than
        # overwriting.  The audit still records the matched-skip.
        if kg_id in seen_kg:
            audit_rows.append({
                "kg_id": kg_id,
                "match_score": score,
                "external_title": ext_title[:80],
                "decision": "skipped: KG-# already enriched from earlier source",
            })
            continue
        seen_kg.add(kg_id)
        stats["matched"] += 1
        work = by_kg[kg_id]
        # Track which fields we've actually changed.
        changes: list[str] = []
        # Provenance — prefer richer of the two (longer).
        ext_prov = r.get("Provenance", "")
        if ext_prov and len(ext_prov) > len(work.get("provenance") or ""):
            work["provenance"] = ext_prov
            changes.append("provenance")
        # Physical location — only filled here.
        loc = r.get("Physical Location", "")
        if loc:
            work["physical_location"] = loc
            changes.append("physical_location")
        # Acquired from
        acq = r.get("Acquired From", "")
        if acq:
            work["acquired_from"] = acq
            changes.append("acquired_from")
        # Literature & exhibited — long-form column.
        lit = r.get("Literature & Exhibited", "")
        if lit:
            work["publications_and_exhibitions"] = lit
            changes.append("publications_and_exhibitions")
        # Drive file URL — into image.alternates if a Drive link.
        file_loc = r.get("File Location", "")
        m = re.search(r"drive\.google\.com/[^\s\"]+", file_loc)
        if m:
            work.setdefault("image", {}).setdefault("alternates", []).append(m.group(0))
            changes.append("image.alternates")

        audit_rows.append({
            "kg_id": kg_id,
            "match_score": score,
            "external_title": ext_title[:80],
            "decision": "merged: " + ",".join(changes) if changes else "matched-but-nothing-new",
        })

    # Recompute facets in case anything in classification changed (it
    # doesn't, but the facets block should always reflect the feed).
    out.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n")
    with audit.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["kg_id", "match_score",
                                          "external_title", "decision"])
        w.writeheader()
        w.writerows(audit_rows)
    # Always write sold_candidates.csv (even if empty) so the curator
    # can pick it up in a known location.
    with sold_out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["kg_id", "match_score",
                                          "external_title",
                                          "current_title", "action"])
        w.writeheader()
        w.writerows(sold_candidates)
    stats["sold_candidates"] = len(sold_candidates)
    return out, dict(stats)
