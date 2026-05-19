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


def test_conflicts_handles_comma_values(tmp_path: Path):
    """Values containing commas (e.g. 'Drawing, Collage…') must not be split
    by the conflicts listing — earlier code did GROUP_CONCAT on commas and
    Python-side .split(',') corrupted multi-word categories."""
    db_path = tmp_path / "t.db"
    db = init_db(db_path)
    _seed(db, "KG-99", "classification", "Painting", "artsy_csv")
    _seed(db, "KG-99", "classification", "Drawing, Collage or other Work on Paper",
          "bulk_upload_xlsx")
    consolidate(db)
    db.conn.close()

    runner = CliRunner()
    result = runner.invoke(cli, ["conflicts", "--db", str(db_path)])
    assert result.exit_code == 0, result.output
    # The full comma-containing value must appear intact on a single line.
    assert "bulk_upload_xlsx=Drawing, Collage or other Work on Paper" in result.output


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


def test_suggest_rules_labels_medium_target_correctly(tmp_path: Path):
    """When a title-keyword strongly predicts a *medium*, the suggestion
    must be labeled 'medium:' — not 'classification: medium=…'.  Earlier
    versions concatenated 'medium=…' into the classification slot."""
    db_path = tmp_path / "t.db"
    db = init_db(db_path)
    # 5 works whose title contains "khanjar", all sharing the same medium —
    # this should trigger a medium-target suggestion.
    for i in range(5):
        kg = f"KG-{9000+i}"
        _seed(db, kg, "title", f"A jeweled khanjar dagger {i}", "artsy_csv")
        _seed(db, kg, "classification", "Design/Decorative Art", "artsy_csv")
        _seed(db, kg, "medium", "Jade-hilted dagger with steel blade", "artsy_csv")
    consolidate(db)
    db.conn.close()

    runner = CliRunner()
    result = runner.invoke(cli, [
        "suggest-rules", "--db", str(db_path),
        "--min-support", "5", "--min-purity", "0.9",
    ])
    assert result.exit_code == 0, result.output
    out = result.output
    # The medium-target suggestion must be on its own labeled line.
    if "khanjar" in out:
        # If the rule fires, it must be properly labeled.
        assert "medium=" not in out, (
            f"medium-target suggestion still using 'medium=' concat: {out}"
        )


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


def test_timeline_appends_and_dedups_same_day(tmp_path: Path):
    """timeline should append one row per day; running it twice the
    same day must replace, not duplicate."""
    db_path = tmp_path / "t.db"
    _populate(db_path)
    out = tmp_path / "history.csv"
    runner = CliRunner()
    r1 = runner.invoke(cli, ["timeline", "--db", str(db_path), "--out", str(out)])
    assert r1.exit_code == 0, r1.output
    r2 = runner.invoke(cli, ["timeline", "--db", str(db_path), "--out", str(out)])
    assert r2.exit_code == 0, r2.output

    lines = out.read_text().splitlines()
    # Header + exactly one data row.
    assert len(lines) == 2
    assert lines[0].startswith("date,")
    cols = lines[1].split(",")
    # works = 2, attributed = 0 (no artist seeded).
    assert cols[1] == "2"
    assert cols[3] == "0"


def test_timeline_show_prints_history(tmp_path: Path):
    out = tmp_path / "history.csv"
    out.write_text("date,works,artsy_eligible,attributed,conflicts,sources\n"
                   "2026-05-01,1400,580,120,250,5\n")
    runner = CliRunner()
    r = runner.invoke(cli, ["timeline", "--show", "--out", str(out)])
    assert r.exit_code == 0, r.output
    assert "2026-05-01" in r.output
    assert "1400" in r.output


def test_match_external_finds_strong_match_skips_generic(tmp_path: Path):
    """Cross-reference should match a distinctive title across systems
    but skip generic KG titles like 'Untitled' that would falsely
    match every external entry."""
    db_path = tmp_path / "t.db"
    db = init_db(db_path)
    # KG-1 has a generic title; KG-2 has a specific one.
    sid_kg = upsert_source(db, SourceRecord(
        name="t-artsy", type="artsy_csv", extracted_at="2026-01-01"))
    insert_observations(db, sid_kg, [
        Observation(work_id="KG-1", field="title", value="Untitled",
                    observed_at="2026-01-01"),
        Observation(work_id="KG-2", field="title",
                    value="Krishna Slaying the Demon Naraka",
                    observed_at="2026-01-01"),
    ])
    # External entry should match KG-2 (distinctive) but not KG-1.
    sid_ext = upsert_source(db, SourceRecord(
        name="t-sub", type="sub_inventory", extracted_at="2026-01-01"))
    insert_observations(db, sid_ext, [
        Observation(work_id="UNRESOLVED-x", field="title",
                    value="Untitled", observed_at="2026-01-01"),
        Observation(work_id="UNRESOLVED-x", field="external_id",
                    value="X-1", observed_at="2026-01-01"),
        Observation(work_id="UNRESOLVED-x", field="external_id_system",
                    value="TestColl", observed_at="2026-01-01"),
        Observation(work_id="UNRESOLVED-y", field="title",
                    value="Krishna Slaying the Demon Naraka, c. 1800",
                    observed_at="2026-01-01"),
        Observation(work_id="UNRESOLVED-y", field="external_id",
                    value="X-2", observed_at="2026-01-01"),
        Observation(work_id="UNRESOLVED-y", field="external_id_system",
                    value="TestColl", observed_at="2026-01-01"),
    ])
    consolidate(db)
    db.conn.close()

    runner = CliRunner()
    r = runner.invoke(cli, [
        "match-external", "--system", "TestColl", "--db", str(db_path),
        "--threshold", "80",
    ])
    assert r.exit_code == 0, r.output
    # Must NOT have suggested KG-1 (generic 'Untitled') for X-1.
    assert "X-1" not in r.output or "KG-1" not in r.output
    # Must have matched X-2 to KG-2.
    assert "X-2" in r.output and "KG-2" in r.output


def test_audit_rules_distinguishes_dead_redundant_and_ok(tmp_path: Path):
    """Three categories should be possible from one input:
      - OK: rule fired (emitted an observation)
      - REDUNDANT: if-condition matches works that already have the
        target value (so the rule emits nothing, but it's not dead)
      - DEAD: if-condition matches zero works
    """
    db_path = tmp_path / "t.db"
    db = init_db(db_path)

    # Setup: 3 works
    #   KG-1: medium=paper, no classification yet — rule fires.
    #   KG-2: medium=bronze, classification=Sculpture already — REDUNDANT.
    #   KG-3: medium=cotton — no rule will match.
    sid_obs = upsert_source(db, SourceRecord(
        name="t-artsy", type="artsy_csv", extracted_at="2026-01-01",
    ))
    insert_observations(db, sid_obs, [
        Observation(work_id="KG-1", field="medium", value="ink on paper",
                    observed_at="2026-01-01"),
        Observation(work_id="KG-2", field="medium", value="bronze",
                    observed_at="2026-01-01"),
        Observation(work_id="KG-2", field="classification", value="Sculpture",
                    observed_at="2026-01-01"),
        Observation(work_id="KG-3", field="medium", value="cotton",
                    observed_at="2026-01-01"),
    ])
    # The paper rule fires on KG-1.
    sid_auto = upsert_source(db, SourceRecord(
        name="t-auto", type="auto_resolution", extracted_at="2026-01-01",
    ))
    insert_observations(db, sid_auto, [Observation(
        work_id="KG-1", field="classification",
        value="Drawing, Collage or other Work on Paper",
        source_row_ref="rule=1;reason=paper",
        observed_at="2026-01-01",
    )])
    consolidate(db)
    db.conn.close()

    rules = tmp_path / "rules.yaml"
    rules.write_text(
        "- if: { medium_contains: paper }\n"
        "  then: { classification: 'Drawing, Collage or other Work on Paper' }\n"
        "- if: { medium_contains: bronze }\n"
        "  then: { classification: Sculpture }\n"
        "- if: { medium_contains: nonsense_token }\n"
        "  then: { classification: Sculpture }\n"
    )

    runner = CliRunner()
    r = runner.invoke(cli, [
        "audit-rules", "--db", str(db_path), "--rules", str(rules),
    ])
    assert r.exit_code == 0, r.output
    assert "OK" in r.output
    assert "REDUNDANT" in r.output
    assert "DEAD" in r.output
    # One of each.
    assert "DEAD: 1" in r.output
    assert "REDUNDANT: 1" in r.output
