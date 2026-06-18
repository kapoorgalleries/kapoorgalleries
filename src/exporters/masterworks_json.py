"""Masterworks & museum-accessions feed for the website.

Reads ``data/raw/masterworks_and_museum_accessions.csv`` (the export of
the curator-maintained Sheet at Drive ID
``17jK96JKxAmH6rBGcgK_nzn-nFx_t7vliH0S70GzZh8M``) and produces
``data/masterworks.json`` — a showcase feed for the website's
``/masterworks`` (or ``/museum-accessions``) landing page.

These are works the gallery has placed in major museum collections;
they're a historical prestige showcase, not for sale.  Distinct from
``website_inventory.json`` (current inventory).
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


def _slug(text: str, max_len: int = 80) -> str:
    if not text:
        return ""
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s[:max_len].rstrip("-")


def _drive_id_from_url(url: str) -> str | None:
    """Extract the Drive file ID from a sharing URL like
    ``https://drive.google.com/file/d/<id>/view?...``."""
    if not url:
        return None
    m = re.search(r"/file/d/([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"id=([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else None


def _drive_image_url(file_id: str | None) -> str | None:
    """Build a usable thumbnail URL from a Drive file id.  Drive's
    ``/uc?id=`` endpoint serves the file directly when the doc is
    "anyone with link" shared — which is how the gallery has these
    files set up."""
    return f"https://drive.google.com/uc?export=view&id={file_id}" if file_id else None


def export_masterworks(
    *,
    source_csv: Path | str = "data/raw/masterworks_and_museum_accessions.csv",
    out_path: Path | str = "data/masterworks.json",
) -> tuple[Path, int]:
    """Build the masterworks/museum-accessions showcase feed.

    Returns (out_path, work_count).  Rows without a title are dropped.
    """
    src = Path(source_csv)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        # No source — emit an empty (but well-formed) feed so the
        # website always has something to load.
        out.write_text(json.dumps({
            "schema_version": 1,
            "count": 0,
            "facets": {"acquired_by": [], "tags": []},
            "works": [],
            "_note": f"source {src} not present; run kg-inv fetch-masterworks first",
        }, indent=2) + "\n")
        return out, 0

    works: list[dict] = []
    with src.open(newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh)):
            title = (row.get("Title") or "").strip()
            if not title:
                # The Sheet has many "continuation" rows (extra image
                # files for a single work — see Krishnanagar Clay
                # Figures 1, 2, 3, 4 in the snippet).  Skip these for
                # the headline feed; v2 can stitch them as alternates.
                continue

            file_id = _drive_id_from_url((row.get("File Location") or "").strip())

            doc: dict[str, Any] = {
                "id": f"mw-{i+1:03d}",
                "slug": _slug(title),
                "url_path": f"/masterworks/{_slug(title)}",
                "title": title,
                "origin": (row.get("Origin") or "").strip() or None,
                "date": (row.get("Date") or "").strip() or None,
                "medium": (row.get("Medium") or "").strip() or None,
                "dimensions_display": (row.get("Dimensions") or "").strip() or None,
                "acquired_by": (row.get("Acquired By") or "").strip() or None,
                "provenance": (row.get("Provenance") or "").strip() or None,
                "published_and_exhibited": (row.get("Published and Exhibited") or "").strip() or None,
                "label_copy": (row.get("Label Copy") or "").strip() or None,
                "museum_link": (row.get("Link") or "").strip() or None,
                "image": {
                    "drive_file_id": file_id,
                    "url": _drive_image_url(file_id),
                },
                "tags": _infer_tags(title, row),
            }
            works.append(doc)

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


_PERIOD_RE = re.compile(r"(\d{1,2}(?:st|nd|rd|th))\s+century", re.IGNORECASE)
_CIRCA_RE = re.compile(r"ca\.?\s*(\d{3,4})", re.IGNORECASE)


def _infer_tags(title: str, row: dict) -> list[str]:
    """Light tag inference based on Origin + Date + Title."""
    blob = " ".join(filter(None, [
        title, row.get("Origin") or "", row.get("Date") or "",
        row.get("Medium") or "",
    ])).lower()
    tags: list[str] = []
    # Period
    m = _PERIOD_RE.search(blob)
    if m:
        tags.append(f"{m.group(1).lower()}-century")
    m = _CIRCA_RE.search(blob)
    if m:
        year = int(m.group(1))
        c = (year + 99) // 100
        tags.append(f"{c}th-century")
    # Region / origin
    if re.search(r"\bpunjab|kangra|guler|bahu|jammu|basohli\b", blob):
        tags.append("punjab-hills")
    if re.search(r"\bmalwa|rajasthan|mewar|bundi|kotah\b", blob):
        tags.append("rajasthan")
    if re.search(r"\btibet|himalayan|nepal", blob):
        tags.append("himalayan")
    if re.search(r"\bbengal|kolkata|krishnanagar", blob):
        tags.append("bengal")
    if re.search(r"\bdeccan", blob):
        tags.append("deccan")
    if re.search(r"\bgandhara", blob):
        tags.append("gandhara")
    # Subject
    if re.search(r"\bkrishna|gopi|radha", blob):
        tags.append("krishna")
    if re.search(r"\brama|sita|lakshmana|ramayana", blob):
        tags.append("ramayana")
    if re.search(r"\bshiva|parvati|durga|kali", blob):
        tags.append("shiva")
    if re.search(r"\bbhagavata|krishna", blob):
        tags.append("bhagavata-purana")
    if re.search(r"\bbuddha|bodhisattva|maitreya|tara", blob):
        tags.append("buddhist")
    if re.search(r"\bjain", blob):
        tags.append("jain")
    return sorted(set(tags))


def _build_facets(works: list[dict]) -> dict:
    acq = Counter(w["acquired_by"] for w in works if w.get("acquired_by"))
    tag = Counter(t for w in works for t in (w.get("tags") or []))
    with_image = sum(1 for w in works if w.get("image", {}).get("url"))
    return {
        "acquired_by": [{"value": v, "count": n} for v, n in acq.most_common()],
        "tags": [{"value": v, "count": n} for v, n in tag.most_common()],
        "with_image": with_image,
        "without_image": len(works) - with_image,
    }
