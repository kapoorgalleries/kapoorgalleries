"""Pin the website_inventory exporter contract.

The shape is the website's only ground truth, so any change to it
should be deliberate.
"""

from pathlib import Path

import csv
import json

from src.exporters.website_inventory import (
    _decimal_to_fraction, _dimensions_display, _infer_tags, _slug,
    export_website_inventory,
)


def _write_master_csv(p: Path, rows: list[dict]) -> None:
    cols = [
        "work_id", "title", "artist", "year", "period_school_region",
        "classification", "medium", "materials",
        "height_in", "width_in", "depth_in", "price_usd",
        "status", "provenance_text", "exhibitions", "publications",
        "signature", "coa_status", "primary_image_url", "primer_uuid",
        "location", "external_id", "external_id_system",
        "artsy_eligibility", "has_conflict", "conflict_fields",
    ]
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def test_export_filters_status_and_placeholders(tmp_path: Path):
    csv_path = tmp_path / "master.csv"
    _write_master_csv(csv_path, [
        {"work_id": "KG-1", "title": "A Krishna",
         "classification": "Painting", "medium": "Watercolor",
         "status": "active"},
        # status != active -> excluded
        {"work_id": "KG-2", "title": "Sold work",
         "classification": "Painting", "medium": "Watercolor",
         "status": "sold"},
        # 'Need title' placeholder -> excluded
        {"work_id": "KG-3", "title": "Need title",
         "classification": "Painting", "medium": "Watercolor",
         "status": "active"},
        # 'Untitled' is a legitimate art title -> KEEP
        {"work_id": "KG-4", "title": "Untitled",
         "classification": "Sculpture", "medium": "Bronze",
         "status": "active"},
        # external sub-inventory -> excluded
        {"work_id": "UNRESOLVED-X", "title": "Graham record",
         "classification": "", "medium": "",
         "status": "external"},
    ])
    out = tmp_path / "feed.json"
    out_path, n = export_website_inventory(None, out, source_csv=csv_path)
    feed = json.load(open(out_path))

    ids = {w["kg_id"] for w in feed["works"]}
    assert ids == {"KG-1", "KG-4"}, ids
    assert n == 2
    assert feed["schema_version"] == 1
    assert feed["count"] == 2


def test_export_emits_facets_and_tags(tmp_path: Path):
    csv_path = tmp_path / "master.csv"
    _write_master_csv(csv_path, [
        {"work_id": "KG-1", "title": "Thangka of Tara, 18th century",
         "classification": "Painting", "medium": "Mineral pigment on cloth",
         "year": "1750", "status": "active"},
        {"work_id": "KG-2", "title": "Bronze Buddha Tibetan",
         "classification": "Sculpture", "medium": "Bronze",
         "year": "1850", "status": "active"},
    ])
    out = tmp_path / "feed.json"
    export_website_inventory(None, out, source_csv=csv_path)
    feed = json.load(open(out))

    classifications = {f["value"] for f in feed["facets"]["classification"]}
    assert classifications == {"Painting", "Sculpture"}

    tag_values = {f["value"] for f in feed["facets"]["tags"]}
    # 18th-century period inferred from title pattern; tibetan + buddha
    # tags from KG-2.
    assert "tibetan" in tag_values
    assert "buddha" in tag_values
    assert "18th-century" in tag_values
    assert "metal" in tag_values  # Bronze -> metal medium-family


def test_no_prices_strips_usd(tmp_path: Path):
    csv_path = tmp_path / "master.csv"
    _write_master_csv(csv_path, [
        {"work_id": "KG-1", "title": "A Krishna",
         "classification": "Painting", "medium": "Watercolor",
         "status": "active", "price_usd": "30000"},
    ])
    out = tmp_path / "feed.json"
    export_website_inventory(None, out, source_csv=csv_path, include_prices=False)
    work = json.load(open(out))["works"][0]
    assert work["price"]["usd"] is None
    assert work["price"]["display"] == "Price on request"
    assert work["price"]["available"] is False


def test_dimensions_display_renders_fraction_and_cm():
    # 29.25 inches -> "29 1/4 in. (74.3 cm.)"
    out = _dimensions_display(29.25, 20.0, None)
    assert "29 1/4" in out
    assert "20" in out
    assert "in." in out
    assert "cm" in out
    # No dims -> empty
    assert _dimensions_display(None, None, None) == ""


def test_decimal_to_fraction_known_values():
    assert _decimal_to_fraction(29.25) == "29 1/4"
    assert _decimal_to_fraction(7.5) == "7 1/2"
    assert _decimal_to_fraction(0.125) == "1/8"
    assert _decimal_to_fraction(34) == "34"
    assert _decimal_to_fraction(None) == ""


def test_slug_is_url_safe():
    assert _slug("A Krishna and Radha") == "a-krishna-and-radha"
    assert _slug("Drawing, Collage or other Work on Paper") == \
        "drawing-collage-or-other-work-on-paper"
    assert _slug("[FAKE?] A Prince on Horseback") == \
        "fake-a-prince-on-horseback"


def test_infer_tags_basic_patterns():
    tags = _infer_tags(
        "Krishna and Radha in a Pavilion",
        "Drawing, Collage or other Work on Paper",
        "Opaque watercolor on paper",
        1820,
    )
    assert "19th-century" in tags
    assert "vishnu" in tags  # Krishna -> vishnu group
    assert "works-on-paper" in tags


def test_period_inferred_from_regional_school(tmp_path: Path):
    """Tag inference should derive a period tag from regional-school
    cues when the title/year don't otherwise carry one."""
    csv_path = tmp_path / "master.csv"
    _write_master_csv(csv_path, [
        # Pahari school -> 18th-century inferred.
        {"work_id": "KG-1", "title": "Krishna and Radha, Pahari School",
         "classification": "Painting",
         "medium": "Opaque watercolor on paper",
         "status": "active"},
        # Mughal -> early-modern.
        {"work_id": "KG-2", "title": "A Mughal hunting scene",
         "classification": "Painting", "medium": "Wasli",
         "status": "active"},
        # Gandharan -> ancient.
        {"work_id": "KG-3", "title": "A Gandharan Bodhisattva",
         "classification": "Sculpture", "medium": "Grey schist",
         "status": "active"},
        # No school cue + no year -> NO period tag (don't make things up).
        {"work_id": "KG-4", "title": "A Bronze Vajra",
         "classification": "Sculpture", "medium": "Bronze",
         "status": "active"},
    ])
    out = tmp_path / "feed.json"
    export_website_inventory(None, out, source_csv=csv_path)
    feed = json.load(open(out))
    by_kg = {w["kg_id"]: w for w in feed["works"]}
    assert "18th-century" in by_kg["KG-1"]["tags"]
    assert "early-modern" in by_kg["KG-2"]["tags"]
    assert "ancient" in by_kg["KG-3"]["tags"]
    period_like = [t for t in by_kg["KG-4"]["tags"]
                   if t.endswith("-century") or
                   t in ("ancient", "medieval", "early-modern")]
    assert period_like == []


def test_era_display_fills_when_year_missing(tmp_path: Path):
    csv_path = tmp_path / "master.csv"
    _write_master_csv(csv_path, [
        # Year missing but title strongly hints at 19th century.
        {"work_id": "KG-1",
         "title": "Thangka of Tara, 19th century",
         "classification": "Painting",
         "medium": "Mineral pigment on cloth",
         "status": "active"},
        # Year missing AND no period hint -> era_display stays None.
        {"work_id": "KG-2", "title": "A Bronze Vajra",
         "classification": "Sculpture", "medium": "Bronze",
         "status": "active"},
        # Year present -> era_display NOT emitted (would be redundant).
        {"work_id": "KG-3", "title": "Krishna on a Terrace",
         "classification": "Painting", "medium": "Watercolor",
         "year": "1820", "status": "active"},
    ])
    out = tmp_path / "feed.json"
    export_website_inventory(None, out, source_csv=csv_path)
    feed = json.load(open(out))
    by_kg = {w["kg_id"]: w for w in feed["works"]}
    assert by_kg["KG-1"]["era_display"] == "19th century"
    assert by_kg["KG-2"].get("era_display") is None
    # Works with a year don't carry the redundant era_display key.
    assert "era_display" not in by_kg["KG-3"]


def test_active_count_matches_master_csv(tmp_path: Path):
    """Spot check on real data — feed should have the right number of
    works from data/master.csv (active + non-placeholder)."""
    if not Path("data/master.csv").exists():
        return  # tolerant when run before make all
    out = tmp_path / "feed.json"
    _, n = export_website_inventory(None, out, source_csv="data/master.csv")
    # Active count today ~= 1416; minus 39 'Need title' placeholders.
    # Allow some drift but sanity-check the order of magnitude.
    assert 1000 < n < 1500
