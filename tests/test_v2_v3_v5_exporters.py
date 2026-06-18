"""Tests for the v2/v3/v4/v5 website-pipeline exporters.

  v2 = enrichment.py       (Catalog & Inventory Sheet merge)
  v3 = masterworks_json.py (museum-accession showcase feed)
  v4 = collections_json.py (per-collection landing pages)
  v5 = image_map.py        (curator KG-# ↔ Drive image map)
"""

from pathlib import Path

import csv
import json

from src.exporters import (
    collections_json, enrichment, image_map, masterworks_json,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _write_feed(p: Path, works: list[dict]) -> None:
    """Write a minimal website_inventory.json-like feed for tests."""
    feed = {
        "schema_version": 1,
        "generated_at": "2026-01-01T00:00:00Z",
        "count": len(works),
        "facets": {
            "classification": [], "tags": [],
            "with_image": sum(1 for w in works
                              if (w.get("image") or {}).get("primary")),
            "without_image": 0,
        },
        "works": works,
    }
    p.write_text(json.dumps(feed))


# ---------------------------------------------------------------------------
# v3 — masterworks
# ---------------------------------------------------------------------------


def test_masterworks_skips_continuation_rows(tmp_path: Path):
    src = tmp_path / "mw.csv"
    src.write_text(
        ",Image,Title,Origin,Date,Medium,Dimensions,Link,File Location,"
        "Acquired By,Provenance,Published and Exhibited,Label Copy\n"
        ",img,Krishna Revels,India,1640,Opaque watercolor,11x20,L,F,"
        "Met,prov,exh,label\n"
        # Title-less continuation row (extra image for a multi-shot work)
        ",img2,,,,,,,,,Met,,,\n"
    )
    out = tmp_path / "mw.json"
    out_path, n = masterworks_json.export_masterworks(
        source_csv=src, out_path=out)
    assert n == 1
    feed = json.loads(out_path.read_text())
    assert feed["works"][0]["title"] == "Krishna Revels"


def test_masterworks_extracts_drive_id_to_view_url(tmp_path: Path):
    src = tmp_path / "mw.csv"
    src.write_text(
        ",Image,Title,Origin,Date,Medium,Dimensions,Link,File Location,"
        "Acquired By,Provenance,Published and Exhibited,Label Copy\n"
        ",img,X,India,1700,m,8x10,,"
        "https://drive.google.com/file/d/ABC123/view?usp=sharing,"
        "Met,prov,exh,label\n"
    )
    out = tmp_path / "mw.json"
    masterworks_json.export_masterworks(source_csv=src, out_path=out)
    feed = json.loads(out.read_text())
    img = feed["works"][0]["image"]
    assert img["drive_file_id"] == "ABC123"
    assert img["url"] == "https://drive.google.com/uc?export=view&id=ABC123"


def test_masterworks_facets_count_acquired_by(tmp_path: Path):
    src = tmp_path / "mw.csv"
    src.write_text(
        ",Image,Title,Origin,Date,Medium,Dimensions,Link,File Location,"
        "Acquired By,Provenance,Published and Exhibited,Label Copy\n"
        ",img,W1,,,,,,,Norton Simon Museum,,,\n"
        ",img,W2,,,,,,,Norton Simon Museum,,,\n"
        ",img,W3,,,,,,,San Diego Museum of Art,,,\n"
    )
    out = tmp_path / "mw.json"
    masterworks_json.export_masterworks(source_csv=src, out_path=out)
    feed = json.loads(out.read_text())
    top = feed["facets"]["acquired_by"][0]
    assert top == {"value": "Norton Simon Museum", "count": 2}


def test_masterworks_emits_empty_feed_when_source_missing(tmp_path: Path):
    out = tmp_path / "mw.json"
    out_path, n = masterworks_json.export_masterworks(
        source_csv=tmp_path / "nonexistent.csv", out_path=out)
    assert n == 0
    feed = json.loads(out_path.read_text())
    assert feed["count"] == 0
    assert "_note" in feed


# ---------------------------------------------------------------------------
# v2 — enrichment merge
# ---------------------------------------------------------------------------


def test_enrichment_matches_by_token_set_ratio(tmp_path: Path):
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        {"kg_id": "KG-100",
         "title": "Krishna Revels with the Gopis",
         "image": {"primary": None, "alternates": [], "thumbnail": None}},
        {"kg_id": "KG-200",
         "title": "A Bronze Vajra",
         "image": {"primary": None, "alternates": [], "thumbnail": None}},
    ])

    src = tmp_path / "src.csv"
    src.write_text(
        "j,Image,Title,Origin,Date,Medium ,Dimensions,Physical Location,"
        "File Location,Acquired From,Literature & Exhibited,Provenance,"
        "Essay Writtenn( Yes/No)\n"
        # Should match KG-100 (token-set match despite word reordering)
        ",,Krishna Revels Gopis with the,,,,,Drawer 13,"
        "https://drive.google.com/file/d/X/view,Christies,lit,prov,Y\n"
    )
    out_feed = tmp_path / "enr.json"
    audit = tmp_path / "audit.csv"
    out, stats = enrichment.export_enrichment(
        source_csv=src, base_feed=feed_path,
        out_feed=out_feed, audit_csv=audit,
    )
    feed = json.loads(out.read_text())
    kg100 = next(w for w in feed["works"] if w["kg_id"] == "KG-100")
    assert kg100["provenance"] == "prov"
    assert kg100["physical_location"] == "Drawer 13"
    assert kg100["acquired_from"] == "Christies"
    assert any("drive.google.com" in u for u in kg100["image"]["alternates"])
    assert stats["matched"] == 1


def test_enrichment_threshold_rejects_weak_match(tmp_path: Path):
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        {"kg_id": "KG-100", "title": "Krishna Revels with the Gopis",
         "image": {"primary": None, "alternates": [], "thumbnail": None}},
    ])
    src = tmp_path / "src.csv"
    src.write_text(
        "j,Image,Title,Origin,Date,Medium ,Dimensions,Physical Location,"
        "File Location,Acquired From,Literature & Exhibited,Provenance,"
        "Essay Writtenn( Yes/No)\n"
        # A completely different work — must NOT match KG-100
        ",,A Bronze Standing Buddha,,,,,Cabinet A,,Sothebys,,Private collection,Y\n"
    )
    out_feed = tmp_path / "enr.json"
    audit = tmp_path / "audit.csv"
    _, stats = enrichment.export_enrichment(
        source_csv=src, base_feed=feed_path,
        out_feed=out_feed, audit_csv=audit, threshold=88,
    )
    feed = json.loads(out_feed.read_text())
    kg100 = next(w for w in feed["works"] if w["kg_id"] == "KG-100")
    assert kg100.get("provenance") is None
    assert stats["matched"] == 0
    assert stats["skipped_low_score"] == 1


def test_enrichment_chains_extra_sources_first_source_wins(tmp_path: Path):
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        {"kg_id": "KG-100", "title": "Krishna Revels with the Gopis",
         "image": {"primary": None, "alternates": [], "thumbnail": None}},
        {"kg_id": "KG-200", "title": "A Bronze Standing Buddha",
         "image": {"primary": None, "alternates": [], "thumbnail": None}},
    ])

    # Primary source: matches KG-100 with prov="primary"
    primary = tmp_path / "primary.csv"
    primary.write_text(
        "j,Image,Title,Origin,Date,Medium ,Dimensions,Physical Location,"
        "File Location,Acquired From,Literature & Exhibited,Provenance,"
        "Essay Writtenn( Yes/No)\n"
        ",,Krishna Revels with the Gopis,,,,,Drawer 13,,Christies,,primary-prov,Y\n"
    )
    # Extra source: would match KG-100 again with prov="from-extra" AND
    # adds a new match for KG-200.  KG-100 must NOT be overwritten.
    extra = tmp_path / "extra.csv"
    extra.write_text(
        "Title,Origin,Date,Medium,Dimensions,Physical Location,"
        "File Location,Acquired From,Literature & Exhibited,Provenance,"
        "SOLD,tab\n"
        "Krishna Revels with the Gopis,,,,,Different Drawer,,,,extra-prov,,2\n"
        "A Bronze Standing Buddha,,,,,Cabinet B,,Sothebys,,b-prov,,2\n"
    )
    out_feed = tmp_path / "enr.json"
    audit = tmp_path / "audit.csv"
    _, stats = enrichment.export_enrichment(
        source_csv=primary, extra_sources=[extra],
        base_feed=feed_path, out_feed=out_feed, audit_csv=audit,
    )
    feed = json.loads(out_feed.read_text())
    kg100 = next(w for w in feed["works"] if w["kg_id"] == "KG-100")
    kg200 = next(w for w in feed["works"] if w["kg_id"] == "KG-200")
    # KG-100 stays on the primary source's values (shorter prov wins
    # because primary saw it first).
    assert kg100["physical_location"] == "Drawer 13"
    # KG-200 picked up entirely from the extra source.
    assert kg200["physical_location"] == "Cabinet B"
    assert kg200["acquired_from"] == "Sothebys"
    assert stats["matched"] == 2


def test_enrichment_skips_sold_rows(tmp_path: Path):
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        {"kg_id": "KG-100", "title": "Krishna Revels with the Gopis",
         "image": {"primary": None, "alternates": [], "thumbnail": None}},
    ])
    src = tmp_path / "src.csv"
    src.write_text(
        "Title,Origin,Date,Medium,Dimensions,Physical Location,"
        "File Location,Acquired From,Literature & Exhibited,Provenance,"
        "SOLD,tab\n"
        "Krishna Revels with the Gopis,,,,,Drawer 13,,Christies,,prov,X,1\n"
    )
    out_feed = tmp_path / "enr.json"
    audit = tmp_path / "audit.csv"
    sold = tmp_path / "sold.csv"
    _, stats = enrichment.export_enrichment(
        source_csv=src, base_feed=feed_path,
        out_feed=out_feed, audit_csv=audit, sold_csv=sold,
    )
    feed = json.loads(out_feed.read_text())
    kg100 = next(w for w in feed["works"] if w["kg_id"] == "KG-100")
    # SOLD-flagged row never merged — the work is unchanged.
    assert kg100.get("provenance") is None
    assert kg100.get("physical_location") is None
    assert stats["matched"] == 0
    assert stats["skipped_sold"] == 1


def test_enrichment_emits_sold_candidate_for_tight_match(tmp_path: Path):
    """A SOLD row that closely matches an active KG-# should land in
    sold_candidates.csv so the curator can confirm before removal."""
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        {"kg_id": "KG-100", "title": "Krishna Revels with the Gopis",
         "image": {"primary": None, "alternates": [], "thumbnail": None}},
        {"kg_id": "KG-200", "title": "A Bronze Vajra",
         "image": {"primary": None, "alternates": [], "thumbnail": None}},
    ])
    src = tmp_path / "src.csv"
    src.write_text(
        "Title,Origin,Date,Medium,Dimensions,Physical Location,"
        "File Location,Acquired From,Literature & Exhibited,Provenance,"
        "SOLD,tab\n"
        # Tight match to KG-100 (identical title) -> sold candidate.
        "Krishna Revels with the Gopis,,,,,,,,,,X,1\n"
        # Weak match (no KG-# above sold_threshold) -> NO candidate.
        "Some Random Sold Painting,,,,,,,,,,X,1\n"
    )
    out_feed = tmp_path / "enr.json"
    audit = tmp_path / "audit.csv"
    sold = tmp_path / "sold.csv"
    _, stats = enrichment.export_enrichment(
        source_csv=src, base_feed=feed_path,
        out_feed=out_feed, audit_csv=audit, sold_csv=sold,
    )
    # Public feed must NOT auto-remove sold candidates — the curator
    # has to confirm.  KG-100 still in the feed unchanged.
    feed = json.loads(out_feed.read_text())
    assert {w["kg_id"] for w in feed["works"]} == {"KG-100", "KG-200"}
    rows = list(csv.DictReader(open(sold)))
    assert len(rows) == 1
    assert rows[0]["kg_id"] == "KG-100"
    assert "review-and-confirm" in rows[0]["action"]
    assert stats["sold_candidates"] == 1
    assert stats["skipped_sold"] == 2


def test_enrichment_audit_row_per_source_row(tmp_path: Path):
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        {"kg_id": "KG-100", "title": "Krishna and Radha",
         "image": {"primary": None, "alternates": [], "thumbnail": None}},
    ])
    src = tmp_path / "src.csv"
    src.write_text(
        "j,Image,Title,Origin,Date,Medium ,Dimensions,Physical Location,"
        "File Location,Acquired From,Literature & Exhibited,Provenance,"
        "Essay Writtenn( Yes/No)\n"
        ",,Krishna and Radha,,,,,Drawer 1,,,Lit,Prov,Y\n"
        ",,Totally unrelated work,,,,,,,,,,N\n"
    )
    out_feed = tmp_path / "enr.json"
    audit = tmp_path / "audit.csv"
    enrichment.export_enrichment(
        source_csv=src, base_feed=feed_path,
        out_feed=out_feed, audit_csv=audit,
    )
    rows = list(csv.DictReader(open(audit)))
    assert len(rows) == 2
    # First row: matched
    assert rows[0]["kg_id"] == "KG-100"
    # Second row: no match
    assert rows[1]["kg_id"] == ""


# ---------------------------------------------------------------------------
# v5 — image_map
# ---------------------------------------------------------------------------


def test_image_map_promotes_primary_and_preserves_old(tmp_path: Path):
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        {"kg_id": "KG-1",
         "title": "X",
         "image": {"primary": "https://old-cdn/x.jpg",
                   "alternates": [], "thumbnail": None}},
    ])
    map_path = tmp_path / "map.csv"
    map_path.write_text(
        "kg_id,drive_url,role,notes\n"
        "KG-1,https://drive.google.com/file/d/NEW/view,primary,front\n"
    )
    image_map.apply_image_map(map_csv=map_path, feed_path=feed_path)
    feed = json.loads(feed_path.read_text())
    img = feed["works"][0]["image"]
    assert img["primary"] == "https://drive.google.com/uc?export=view&id=NEW"
    # Old primary preserved as an alternate so we don't lose Primer's URL
    assert "https://old-cdn/x.jpg" in img["alternates"]


def test_image_map_skips_comments_and_invalid_roles(tmp_path: Path):
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        {"kg_id": "KG-1", "title": "X",
         "image": {"primary": None, "alternates": [], "thumbnail": None}},
    ])
    map_path = tmp_path / "map.csv"
    map_path.write_text(
        "kg_id,drive_url,role,notes\n"
        "# KG-1,https://drive.google.com/file/d/X/view,primary,demo\n"
        "KG-1,https://drive.google.com/file/d/Y/view,not-a-role,demo\n"
        "KG-1,https://drive.google.com/file/d/Z/view,alternate,demo\n"
    )
    stats = image_map.apply_image_map(map_csv=map_path, feed_path=feed_path)
    feed = json.loads(feed_path.read_text())
    alts = feed["works"][0]["image"]["alternates"]
    assert len(alts) == 1
    assert "id=Z" in alts[0]
    assert stats["invalid_role"] == 1


def test_image_map_is_no_op_when_missing(tmp_path: Path):
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        {"kg_id": "KG-1", "title": "X",
         "image": {"primary": "p", "alternates": [], "thumbnail": None}},
    ])
    stats = image_map.apply_image_map(
        map_csv=tmp_path / "nonexistent.csv", feed_path=feed_path)
    feed = json.loads(feed_path.read_text())
    assert feed["works"][0]["image"]["primary"] == "p"
    assert stats["applied"] == 0
    assert "not present" in stats.get("note", "")


def test_image_map_starter_template_has_comment_rows(tmp_path: Path):
    p = image_map.write_starter_template(tmp_path / "map.csv")
    text = p.read_text()
    assert "kg_id,drive_url,role,notes" in text
    # Starter rows are commented out so applying it doesn't error
    assert "# KG-" in text


# ---------------------------------------------------------------------------
# v4 — collections feed
# ---------------------------------------------------------------------------


def _make_work(kg: str, title: str, tags: list[str],
               primary: str | None = None) -> dict:
    return {
        "id": kg.lower(),
        "kg_id": kg,
        "title": title,
        "slug": f"{kg.lower()}-{title.lower().replace(' ', '-')}",
        "url_path": f"/works/{kg.lower()}",
        "tags": tags,
        "image": {"primary": primary, "alternates": [], "thumbnail": None},
    }


def test_collections_tag_filter_picks_members(tmp_path: Path):
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        _make_work("KG-1", "Ragamala Folio", ["ragamala", "indian"]),
        _make_work("KG-2", "Bronze Vajra", ["tibetan", "metal"]),
        _make_work("KG-3", "Another Ragamala", ["ragamala"]),
    ])
    cfg = tmp_path / "coll.yaml"
    cfg.write_text(
        "collections:\n"
        "  - slug: virtual-ragamala\n"
        "    title: Virtual Ragamala\n"
        "    include_tags: [ragamala]\n"
        "    include_kg_ids: []\n"
    )
    out, n = collections_json.export_collections(
        config_yaml=cfg, feed_path=feed_path,
        out_path=tmp_path / "collections.json",
    )
    feed = json.loads(out.read_text())
    coll = feed["collections"][0]
    assert n == 1
    assert coll["slug"] == "virtual-ragamala"
    assert coll["url_path"] == "/collections/virtual-ragamala"
    assert coll["member_count"] == 2
    kg_ids = {m["kg_id"] for m in coll["members"]}
    assert kg_ids == {"KG-1", "KG-3"}


def test_collections_explicit_kg_ids_override_tag_filter(tmp_path: Path):
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        _make_work("KG-1", "Untagged Manuscript", []),
        _make_work("KG-2", "Thangka", ["tibetan", "thangka"]),
    ])
    cfg = tmp_path / "coll.yaml"
    cfg.write_text(
        "collections:\n"
        "  - slug: arcane-masters\n"
        "    title: Arcane Masters\n"
        "    include_tags: []\n"
        "    include_kg_ids: [KG-1]\n"
    )
    out, n = collections_json.export_collections(
        config_yaml=cfg, feed_path=feed_path,
        out_path=tmp_path / "collections.json",
    )
    feed = json.loads(out.read_text())
    coll = feed["collections"][0]
    assert n == 1
    assert {m["kg_id"] for m in coll["members"]} == {"KG-1"}


def test_collections_deduplicates_when_tag_and_kg_overlap(tmp_path: Path):
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        _make_work("KG-1", "Thangka", ["tibetan"]),
    ])
    cfg = tmp_path / "coll.yaml"
    cfg.write_text(
        "collections:\n"
        "  - slug: himalayan\n"
        "    title: Himalayan Art\n"
        "    include_tags: [tibetan]\n"
        "    include_kg_ids: [KG-1]\n"
    )
    out, _ = collections_json.export_collections(
        config_yaml=cfg, feed_path=feed_path,
        out_path=tmp_path / "collections.json",
    )
    feed = json.loads(out.read_text())
    coll = feed["collections"][0]
    assert coll["member_count"] == 1


def test_collections_empty_member_collection_still_emitted(tmp_path: Path):
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        _make_work("KG-1", "Lonely Work", ["solo"]),
    ])
    cfg = tmp_path / "coll.yaml"
    cfg.write_text(
        "collections:\n"
        "  - slug: empty-page\n"
        "    title: Future Collection\n"
        "    include_tags: [no-such-tag]\n"
        "    include_kg_ids: []\n"
    )
    out, n = collections_json.export_collections(
        config_yaml=cfg, feed_path=feed_path,
        out_path=tmp_path / "collections.json",
    )
    feed = json.loads(out.read_text())
    assert n == 0
    # Page is still scaffolded — "Coming soon" UX.
    assert feed["count"] == 1
    assert feed["collections"][0]["member_count"] == 0


def test_collections_seed_titles_fuzzy_match(tmp_path: Path):
    """seed_titles should fuzzy-match against the inventory feed and
    pull matched KG-#s into the collection's members."""
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        _make_work("KG-1", "Krishna and Radha at a Jharokha Window", []),
        _make_work("KG-2", "A Bronze Vajra", []),
        _make_work("KG-3", "Krishna Conversing with a Sakhi", []),
    ])
    cfg = tmp_path / "coll.yaml"
    cfg.write_text(
        "collections:\n"
        "  - slug: rasikapriya\n"
        "    title: Rasikapriya\n"
        "    include_tags: []\n"
        "    include_kg_ids: []\n"
        "    seed_titles:\n"
        '      - "Illustration to a Rasikapriya Series: '
        'Krishna and Radha at a Jharokha Window"\n'
        '      - "Illustration to a Rasikapriya series: '
        'Krishna conversing with a Sakhi"\n'
        '      - "Something Totally Unrelated To Anything"\n'
    )
    audit_path = tmp_path / "audit.csv"
    out, n = collections_json.export_collections(
        config_yaml=cfg, feed_path=feed_path,
        out_path=tmp_path / "collections.json",
        seed_audit_csv=audit_path,
    )
    feed = json.loads(out.read_text())
    coll = feed["collections"][0]
    assert n == 1
    kg_ids = {m["kg_id"] for m in coll["members"]}
    assert kg_ids == {"KG-1", "KG-3"}
    rows = list(csv.DictReader(open(audit_path)))
    # 3 audit rows — 2 matched, 1 no-match.
    assert len(rows) == 3
    matched = [r for r in rows if r["kg_id"]]
    assert len(matched) == 2


def test_collections_no_op_when_config_missing(tmp_path: Path):
    feed_path = tmp_path / "feed.json"
    _write_feed(feed_path, [
        _make_work("KG-1", "X", []),
    ])
    out, n = collections_json.export_collections(
        config_yaml=tmp_path / "nope.yaml",
        feed_path=feed_path,
        out_path=tmp_path / "collections.json",
    )
    feed = json.loads(out.read_text())
    assert n == 0
    assert feed["count"] == 0
    assert "_note" in feed
