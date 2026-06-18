"""Tests for the v2/v3/v5 website-pipeline exporters.

  v2 = enrichment.py  (Catalog & Inventory Sheet merge)
  v3 = masterworks_json.py  (museum-accession showcase feed)
  v5 = image_map.py  (curator KG-# ↔ Drive image map)
"""

from pathlib import Path

import csv
import json

from src.exporters import enrichment, image_map, masterworks_json


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
