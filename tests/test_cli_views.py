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
