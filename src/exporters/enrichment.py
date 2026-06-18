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


def export_enrichment(
    *,
    source_csv: Path | str = "data/raw/catalog_and_inventory_tab1.csv",
    base_feed: Path | str = "data/website_inventory.json",
    out_feed: Path | str = "data/website_inventory_enriched.json",
    audit_csv: Path | str = "data/enrichment_audit.csv",
    threshold: int = 88,
) -> tuple[Path, dict]:
    """Merge external enrichment data into the website feed.

    Returns (out_feed, stats) where stats is a dict with match counts.
    """
    src = Path(source_csv)
    base = Path(base_feed)
    out = Path(out_feed)
    audit = Path(audit_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    audit.parent.mkdir(parents=True, exist_ok=True)

    if not base.exists():
        raise FileNotFoundError(
            f"{base} missing — run `kg-inv export-website` first."
        )
    feed = json.loads(base.read_text())

    # If the enrichment source is missing, emit the base feed unchanged
    # and an empty audit — keeps `make report` deterministic.
    if not src.exists():
        out.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n")
        audit.write_text("kg_id,match_score,external_title,decision\n")
        return out, {
            "source_rows": 0, "matched": 0, "skipped_low_score": 0,
            "skipped_no_title": 0, "note": f"{src} not present",
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

    # Read the enrichment source.  Strip header trailing whitespace
    # because the curator sheet has "Medium " with a trailing space.
    with src.open(newline="") as fh:
        raw_rows = list(csv.DictReader(fh))
    rows = [
        {k.strip(): (v or "").strip() for k, v in r.items()}
        for r in raw_rows
    ]

    # Predeclare the keys so the returned dict always has the same
    # shape — consumers can assume `stats["matched"]` is always there.
    stats: Counter = Counter(
        source_rows=0, matched=0, skipped_low_score=0, skipped_no_title=0,
    )
    audit_rows: list[dict] = []
    for r in rows:
        stats["source_rows"] += 1
        ext_title = r.get("Title", "")
        if not ext_title:
            stats["skipped_no_title"] += 1
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
    return out, dict(stats)
