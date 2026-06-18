"""Generated artifacts should be byte-for-byte identical across consolidate runs.

Set iteration order, dict insertion order, and now()-derived timestamps have
all caused spurious git diffs in the past.  This test pins them down.
"""

from pathlib import Path

from src import reports
from src.consolidate import consolidate
from src.db import init_db, insert_observations, upsert_source
from src.exporters import master_csv, master_json, provenance_csv
from src.schema import Observation, SourceRecord


def _seed(db, work_id, field, value, stype, observed_at="2026-01-01"):
    sid = upsert_source(db, SourceRecord(name=f"t-{stype}", type=stype, extracted_at=observed_at))
    insert_observations(db, sid, [Observation(
        work_id=work_id, field=field, value=value, observed_at=observed_at,
    )])


def _populate(db_path: Path):
    db = init_db(db_path)
    # Two works with multiple alternative values, to exercise both
    # canonical-pick stability and alternative-set sorting.
    _seed(db, "KG-1", "title", "First Work", "artsy_csv")
    _seed(db, "KG-1", "classification", "Posters", "artsy_csv")
    _seed(db, "KG-1", "classification", "Print", "bulk_upload_xlsx")
    _seed(db, "KG-2", "title", "Second Work", "artsy_csv")
    _seed(db, "KG-2", "classification", "Sculpture", "artsy_csv")
    consolidate(db)
    return db


def test_master_csv_byte_identical_across_runs(tmp_path: Path):
    db = _populate(tmp_path / "t.db")
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    master_csv.export_master_csv(db, a)
    master_csv.export_master_csv(db, b)
    assert a.read_bytes() == b.read_bytes()


def test_master_json_byte_identical_across_runs(tmp_path: Path):
    db = _populate(tmp_path / "t.db")
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    master_json.export_master_json(db, a)
    master_json.export_master_json(db, b)
    assert a.read_bytes() == b.read_bytes()


def test_master_csv_omits_canonical_updated_at(tmp_path: Path):
    """It's the consolidate-run timestamp; identical for every row, only churn."""
    db = _populate(tmp_path / "t.db")
    out = tmp_path / "m.csv"
    master_csv.export_master_csv(db, out)
    header = out.read_text().splitlines()[0]
    assert "canonical_updated_at" not in header


def test_provenance_csv_alt_values_sorted(tmp_path: Path):
    """alt_values must be sorted so set-iteration order doesn't leak into output."""
    db = _populate(tmp_path / "t.db")
    out = tmp_path / "p.csv"
    provenance_csv.export_provenance(db, out)
    text = out.read_text()
    # KG-1 has classifications {'Posters', 'Print'}.  Whichever wins canonically,
    # the alternative listing must be in sorted order ('Posters' < 'Print').
    # We don't assert which is canonical — only that the alt list is sorted.
    for line in text.splitlines():
        if line.startswith("KG-1,classification,"):
            # alternative_values is the 6th column (0-indexed 5).
            cols = line.split(",")
            # alt_count, alternative_values, alternative_sources are last 3.
            alt_values = cols[-2]
            if alt_values and " || " in alt_values:
                parts = alt_values.split(" || ")
                assert parts == sorted(parts), f"alt_values not sorted: {parts}"


def test_coverage_report_byte_identical_across_runs(tmp_path: Path):
    """Earlier the report wrote per-run extracted_at timestamps, dirtying
    git on every `make all`.  It now uses file_modified_at (file mtime,
    stable across reruns) so two consecutive renders must match."""
    db = _populate(tmp_path / "t.db")
    a = tmp_path / "cov_a.md"
    b = tmp_path / "cov_b.md"
    reports.coverage_report(db, a)
    reports.coverage_report(db, b)
    assert a.read_bytes() == b.read_bytes()


def test_provenance_report_excludes_resolution_sources_from_conflict_counts(tmp_path: Path):
    """A value supplied by an auto/human resolution must not count as a
    conflict against an observation source — otherwise the report
    over-counts and disagrees with data/conflicts.csv."""
    db = init_db(tmp_path / "t.db")
    # Real disagreement between two observation sources → should count.
    _seed(db, "KG-A", "classification", "Painting", "artsy_csv")
    _seed(db, "KG-A", "classification", "Drawing", "bulk_upload_xlsx")
    # Auto-resolution overrides Primer's classification → must NOT count.
    _seed(db, "KG-B", "classification", "Painting", "artsy_csv")
    _seed(db, "KG-B", "classification", "Sculpture", "auto_resolution")
    consolidate(db)

    out = tmp_path / "prov.md"
    reports.provenance_report(db, out)
    text = out.read_text()
    # Pull out just the conflict-count section so we don't accidentally
    # match the upstream per-source provenance table.
    section = text.split("## Conflict counts per field", 1)[1]
    assert "| classification | 1 |" in section
    # KG-B's resolution-vs-source split must not have inflated the count.
    assert "| classification | 2 |" not in section


def test_photo_queue_splits_ready_vs_needs_metadata(tmp_path: Path):
    """photo_queue_report buckets photo-blocked works into:
      - ready_when_photographed (has cls + medium) → in the headline count
      - still_needs_metadata    (lacks cls or medium) → listed but excluded
    External (sub-inventory) works should not appear at all.
    """
    db = init_db(tmp_path / "t.db")
    # Ready: has title + cls + medium, no image
    _seed(db, "KG-ready", "title", "Ready Buddha", "artsy_csv")
    _seed(db, "KG-ready", "classification", "Sculpture", "artsy_csv")
    _seed(db, "KG-ready", "medium", "Bronze", "artsy_csv")
    # Needs metadata: has title + image-missing, lacks medium
    _seed(db, "KG-needs", "title", "Half-ready Buddha", "artsy_csv")
    _seed(db, "KG-needs", "classification", "Sculpture", "artsy_csv")
    # Already eligible: has image — should be excluded
    _seed(db, "KG-eligible", "title", "Already photographed", "artsy_csv")
    _seed(db, "KG-eligible", "classification", "Sculpture", "artsy_csv")
    _seed(db, "KG-eligible", "medium", "Bronze", "artsy_csv")
    _seed(db, "KG-eligible", "primary_image_url", "http://x/y.jpg", "artsy_csv")
    # External sub-inventory — should never appear
    _seed(db, "UNRESOLVED-ext", "title", "External record", "sub_inventory")
    _seed(db, "UNRESOLVED-ext", "status", "external", "sub_inventory")
    consolidate(db)

    md_path = tmp_path / "pq.md"
    csv_path = tmp_path / "pq.csv"
    _, n_ready = reports.photo_queue_report(db, md_path, csv_path)
    text = md_path.read_text()

    assert n_ready == 1
    assert "1 active works become Artsy-eligible" in text
    assert "KG-ready" in text
    # The metadata-needing work is listed but not in the headline count.
    assert "KG-needs" in text
    assert "Still needs metadata" in text
    # Already-eligible and external must NOT appear.
    assert "KG-eligible" not in text
    assert "UNRESOLVED-ext" not in text


def test_conflicts_csv_preserves_comma_values(tmp_path: Path):
    """Values like 'Drawing, Collage or other Work on Paper' contain commas.
    The exporter must not split them into distinct entries — earlier
    SQL-side GROUP_CONCAT did exactly that."""
    from src.exporters import conflicts_csv as conflicts_csv_mod

    db = init_db(tmp_path / "t.db")
    _seed(db, "KG-X", "classification", "Painting", "artsy_csv")
    _seed(db, "KG-X", "classification", "Drawing, Collage or other Work on Paper",
          "bulk_upload_xlsx")
    consolidate(db)

    out = tmp_path / "c.csv"
    conflicts_csv_mod.export_conflicts(db, out)
    import csv as _csv
    rows = list(_csv.reader(out.open()))
    # Header + one conflict row.
    assert len(rows) == 2
    header, row = rows
    assert int(row[header.index("distinct_values")]) == 2
    # The full comma-containing classification must be present in values_seen.
    assert "Drawing, Collage or other Work on Paper" in row[header.index("values_seen")]
