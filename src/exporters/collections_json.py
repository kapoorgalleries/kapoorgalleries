"""Collection-landing-page feed for the website.

Reads ``data/collections.yaml`` (curator-maintained) and the website
inventory feed (``data/website_inventory.json`` or the enriched variant)
and emits ``data/collections.json`` — a list of curated groupings, each
populated with the member works that satisfy the collection's tag
filter or explicit KG-# list.

Output shape (TypeScript-ish):

    type CollectionsFeed = {
      schema_version: 1;
      generated_at: string;
      count: number;                  // number of collections
      collections: Collection[];
    };

    type Collection = {
      slug:           string;
      title:          string;
      subtitle:       string | null;
      description:    string | null;
      source_catalog: string | null;
      url_path:       string;         // "/collections/<slug>"
      include_tags:   string[];
      member_count:   number;
      members:        Array<{
        id: string;                 // "kg-1023"
        kg_id: string;              // "KG-1023"
        title: string;
        url_path: string;
        thumbnail: string | null;
      }>;
    };

Designed to be a no-op when ``collections.yaml`` is missing — keeps
``make report`` deterministic for fresh checkouts.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-untyped]
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False


_SCHEMA_VERSION = 1

# Strip noise terms before fuzzy-matching seed titles against feed
# titles.  Same vocabulary as enrichment.py — catalog folder/file
# names use "Illustration to / Leaf from / Folio from" patterns that
# the inventory feed often omits.
_SEED_NOISE = re.compile(
    r"\b(folio|leaf|page|illustration|to a|to the|from a|from the|"
    r"series|circa|c\.|ca\.|the|of)\b",
    re.IGNORECASE,
)


def _norm_seed(s: Any) -> str:
    # Defensive: a curator can accidentally write an unquoted YAML
    # entry like `- Title: With a colon`, which PyYAML parses as a
    # dict.  Coerce non-strings to empty so they're emitted as
    # "no match" rows in the audit instead of crashing the pipeline.
    if not isinstance(s, str):
        return ""
    s = s.lower().strip()
    s = _SEED_NOISE.sub(" ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _empty_feed(note: str) -> dict:
    return {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": _now_utc(),
        "count": 0,
        "collections": [],
        "_note": note,
    }


def _member_summary(work: dict) -> dict:
    """Trim a full website-feed work down to the listing-row shape."""
    img = work.get("image") or {}
    return {
        "id": work["id"],
        "kg_id": work["kg_id"],
        "title": work["title"],
        "url_path": work["url_path"],
        "thumbnail": img.get("thumbnail") or img.get("primary"),
    }


def _best_seed_match(
    needle: str, haystack: list[tuple[str, str]], threshold: int,
) -> tuple[str, int] | None:
    """Best fuzzy match for a seed title against (kg_id, normalized_title)
    pairs.  Same family of token-set-ratio matching as enrichment.py.
    """
    if not needle or not HAS_RAPIDFUZZ:
        return None
    best_kg = None
    best_score = 0
    for kg_id, h_title in haystack:
        if not h_title:
            continue
        score = int(fuzz.token_set_ratio(needle, h_title))
        if score > best_score:
            best_score = score
            best_kg = kg_id
    return (best_kg, best_score) if best_kg and best_score >= threshold else None


def export_collections(
    *,
    config_yaml: Path | str = "data/collections.yaml",
    feed_path: Path | str = "data/website_inventory.json",
    out_path: Path | str = "data/collections.json",
    seed_audit_csv: Path | str = "data/collection_seed_audit.csv",
    seed_threshold: int = 90,
) -> tuple[Path, int]:
    """Build collections.json from the YAML config and the inventory feed.

    Returns (out_path, n_collections_with_members).  Collections whose
    membership resolves to zero works are still emitted (visible on the
    site as "coming soon") but excluded from the returned count.
    """
    cfg = Path(config_yaml)
    feed_p = Path(feed_path)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not cfg.exists():
        out.write_text(json.dumps(
            _empty_feed(f"{cfg} not present"),
            indent=2, ensure_ascii=False) + "\n")
        return out, 0
    if not HAS_YAML:
        out.write_text(json.dumps(
            _empty_feed("PyYAML not installed; pip install pyyaml"),
            indent=2, ensure_ascii=False) + "\n")
        return out, 0
    if not feed_p.exists():
        raise FileNotFoundError(
            f"{feed_p} missing — run `kg-inv export-website` first."
        )

    cfg_data: dict[str, Any] = yaml.safe_load(cfg.read_text()) or {}
    coll_specs: list[dict] = cfg_data.get("collections") or []
    feed = json.loads(feed_p.read_text())
    works: list[dict] = feed.get("works", [])

    # Pre-index works for fast tag and KG-# lookup.
    by_kg = {w["kg_id"]: w for w in works}
    # Haystack for seed-title fuzzy matching.
    haystack: list[tuple[str, str]] = [
        (w["kg_id"], _norm_seed(w["title"])) for w in works
    ]

    audit_rows: list[dict] = []
    collections_out: list[dict] = []
    n_with_members = 0
    for spec in coll_specs:
        slug = (spec.get("slug") or "").strip()
        if not slug:
            continue
        include_tags = set(spec.get("include_tags") or [])
        include_kg_ids = set(spec.get("include_kg_ids") or [])
        seed_titles: list[str] = spec.get("seed_titles") or []

        members: list[dict] = []
        seen: set[str] = set()

        # Tag-driven matches
        if include_tags:
            for w in works:
                tags = set(w.get("tags") or [])
                if tags & include_tags and w["kg_id"] not in seen:
                    members.append(_member_summary(w))
                    seen.add(w["kg_id"])

        # Explicit KG-# matches (curator override; can include works the
        # tag filter missed).
        for kg in include_kg_ids:
            w = by_kg.get(kg)
            if w and kg not in seen:
                members.append(_member_summary(w))
                seen.add(kg)

        # Seed-title fuzzy matches — for catalogs where membership is
        # known by title (curator extracted from a Drive folder of
        # lot-numbered PDFs) but the KG-#s haven't been mapped.
        for title in seed_titles:
            res = _best_seed_match(_norm_seed(title), haystack, seed_threshold)
            if not res:
                audit_rows.append({
                    "collection": slug,
                    "seed_title": title[:120],
                    "kg_id": "",
                    "match_score": 0,
                    "decision": "no match >= threshold",
                })
                continue
            kg, score = res
            audit_rows.append({
                "collection": slug,
                "seed_title": title[:120],
                "kg_id": kg,
                "match_score": score,
                "decision": ("added" if kg not in seen
                             else "already-in-collection"),
            })
            if kg in seen:
                continue
            w = by_kg.get(kg)
            if w:
                members.append(_member_summary(w))
                seen.add(kg)

        # Stable display ordering: alpha by title.
        members.sort(key=lambda m: m["title"].lower())

        collections_out.append({
            "slug": slug,
            "title": spec.get("title") or slug,
            "subtitle": spec.get("subtitle"),
            "description": (spec.get("description") or "").strip() or None,
            "source_catalog": spec.get("source_catalog"),
            "url_path": f"/collections/{slug}",
            "include_tags": sorted(include_tags),
            "member_count": len(members),
            "members": members,
        })
        if members:
            n_with_members += 1

    out_feed = {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": _now_utc(),
        "count": len(collections_out),
        "collections": collections_out,
    }
    out.write_text(json.dumps(out_feed, indent=2, ensure_ascii=False) + "\n")
    # Always write the seed audit (even if empty) so the curator can
    # review what matched and what didn't.
    audit_path = Path(seed_audit_csv)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "collection", "seed_title", "kg_id", "match_score", "decision",
        ])
        w.writeheader()
        w.writerows(audit_rows)
    return out, n_with_members
