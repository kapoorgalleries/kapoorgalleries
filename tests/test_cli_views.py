"""Smoke tests for the read-only kg-inv CLI views."""

from pathlib import Path

from click.testing import CliRunner

from src.cli import cli
from src.consolidate import consolidate
from src.db import init_db, insert_observations, upsert_source
from src.schema import Observation, SourceRecord


def _seed(db, work_id, field, value, stype, observed_at="2026-01-01"):
    sid = upsert_source(db, SourceRecord(name=f"t-{stype}", type=stype, extracted_at=observed_at))
    insert_observations(db, sid, [Observation(
        work_id=work_id, field=field, value=value, observed_at=observed_at,
    )])


def _populate(db_path: Path):
    db = init_db(db_path)
    _seed(db, "KG-1", "title", "A Krishna Painting", "artsy_csv")
    _seed(db, "KG-1", "classification", "Painting", "artsy_csv")
    _seed(db, "KG-1", "medium", "Watercolor on paper", "artsy_csv")
    _seed(db, "KG-1", "year", "1850", "artsy_csv")
    _seed(db, "KG-1", "primary_image_url", "http://example/x.jpg", "artsy_csv")
    _seed(db, "KG-2", "title", "Sandstone Buddha", "artsy_csv")
    _seed(db, "KG-2", "classification", "Sculpture", "artsy_csv")
    _seed(db, "KG-2", "medium", "Sandstone", "artsy_csv")
    _seed(db, "KG-2", "primary_image_url", "http://example/y.jpg", "artsy_csv")
    consolidate(db)
    db.conn.close()


def test_search_finds_substring_in_title(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "Krishna", "--db", str(db_path)])
    assert result.exit_code == 0, result.output
    assert "KG-1" in result.output


def test_show_displays_canonical_values(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["show", "KG-2", "--db", str(db_path)])
    assert result.exit_code == 0, result.output
    assert "Sandstone Buddha" in result.output
    assert "Sculpture" in result.output


def test_compare_marks_differences_and_matches(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["compare", "KG-1", "KG-2", "--db", str(db_path)])
    assert result.exit_code == 0, result.output
    # Differing classifications → at least one ≠ row.
    assert "≠" in result.output
    # Both works show up in the header.
    assert "KG-1" in result.output and "KG-2" in result.output


def test_compare_unknown_id(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["compare", "KG-1", "KG-NOPE", "--db", str(db_path)])
    assert result.exit_code == 0, result.output
    assert "No work found" in result.output


def test_stats_runs_clean(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["stats", "--db", str(db_path)])
    assert result.exit_code == 0, result.output
    assert "Works:" in result.output


def test_lint_runs_clean(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--db", str(db_path)])
    assert result.exit_code == 0, result.output


def test_export_filtered_writes_csv(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    out = tmp_path / "sculptures.csv"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "export-filtered", "--out", str(out),
        "--classification", "Sculpture",
        "--db", str(db_path),
    ])
    assert result.exit_code == 0, result.output
    text = out.read_text()
    assert "KG-2" in text
    assert "KG-1" not in text


def test_suggest_rules_runs_without_error(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, [
        "suggest-rules", "--db", str(db_path),
        "--min-support", "1", "--min-purity", "0.5",
    ])
    assert result.exit_code == 0, result.output


def test_years_runs(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    # Set a year so the histogram has a bucket.
    db = init_db(db_path)
    _seed(db, "KG-1", "year", "1850", "artsy_csv")
    consolidate(db)
    db.conn.close()

    runner = CliRunner()
    result = runner.invoke(cli, ["years", "--db", str(db_path)])
    assert result.exit_code == 0, result.output


def test_artists_runs(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["artists", "--db", str(db_path)])
    assert result.exit_code == 0, result.output


def test_inspect_source_runs(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["inspect-source", "test-artsy_csv",
                                   "--db", str(db_path)])
    assert result.exit_code == 0, result.output


def test_prices_runs(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    db = init_db(db_path)
    _seed(db, "KG-1", "price_usd", "12000", "artsy_csv")
    consolidate(db)
    db.conn.close()
    runner = CliRunner()
    result = runner.invoke(cli, ["prices", "--db", str(db_path)])
    assert result.exit_code == 0, result.output


def test_overview_runs(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["overview", "--db", str(db_path)])
    assert result.exit_code == 0, result.output


def test_whatsnew_runs(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["whatsnew", "--db", str(db_path)])
    assert result.exit_code == 0, result.output


def test_sample_runs(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["sample", "--n", "1", "--db", str(db_path)])
    assert result.exit_code == 0, result.output


def test_overview_json_emits_valid_json(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["overview", "--json", "--db", str(db_path)])
    assert result.exit_code == 0, result.output
    import json
    payload = json.loads(result.output.strip().split("\n")[-1])
    assert "works" in payload
    assert "artsy_eligible" in payload


def test_stats_json_emits_valid_json(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["stats", "--json", "--db", str(db_path)])
    assert result.exit_code == 0, result.output
    import json
    payload = json.loads(result.output)
    assert "coverage" in payload


def test_mediums_runs(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["mediums", "--db", str(db_path)])
    assert result.exit_code == 0, result.output


def test_classifications_runs(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["classifications", "--db", str(db_path)])
    assert result.exit_code == 0, result.output


def test_image_stats_runs(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["image-stats", "--db", str(db_path)])
    assert result.exit_code == 0, result.output


def test_duplicate_titles_runs(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["duplicate-titles", "--db", str(db_path)])
    assert result.exit_code == 0, result.output


def test_split_by_classification_writes_per_class_csvs(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    out = tmp_path / "byc"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "split-by-classification", "--out-dir", str(out),
        "--db", str(db_path),
    ])
    assert result.exit_code == 0, result.output
    files = list(out.glob("*.csv"))
    assert len(files) >= 1


def test_gaps_runs(tmp_path: Path):
    db_path = tmp_path / "t.db"
    _populate(db_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["gaps", "--max-missing", "5",
                                   "--db", str(db_path)])
    assert result.exit_code == 0, result.output


def test_batch_resolve_appends_entries(tmp_path: Path):
    """batch-resolve reads a YAML file and appends to human_resolutions.yaml."""
    import yaml as _yaml
    in_path = tmp_path / "in.yaml"
    in_path.write_text(_yaml.safe_dump([
        {"work_id": "KG-1", "field": "title", "value": "Test 1"},
        {"work_id": "KG-2", "field": "title", "value": "Test 2"},
    ]))
    out_path = tmp_path / "human.yaml"

    runner = CliRunner()
    result = runner.invoke(cli, [
        "batch-resolve", str(in_path), "--file", str(out_path),
    ])
    assert result.exit_code == 0, result.output
    entries = _yaml.safe_load(out_path.read_text())
    assert len(entries) == 2
    assert entries[0]["work_id"] == "KG-1"


def test_check_artsy_runs(tmp_path: Path):
    """check-artsy needs a real CSV file."""
    p = tmp_path / "upload.csv"
    p.write_text(
        '"Inventory ID (OPTIONAL)","Artist Name ","Title ","Year ","Price ","Medium ","Materials ","Height ","Width ",Depth,"Certificate of Authenticity ","Signature ","Classification "\n'
        'KG-1,Unknown,A test,1850,,Watercolor,Watercolor,8,10,,,,Painting\n'
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["check-artsy", "--file", str(p)])
    assert result.exit_code == 0, result.output
