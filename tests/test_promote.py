"""kg-inv promote turns the canonical value into a permanent human_resolution."""

from pathlib import Path

import yaml
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


def test_promote_appends_human_resolution(tmp_path: Path):
    db_path = tmp_path / "t.db"
    db = init_db(db_path)
    _seed(db, "KG-9", "classification", "Painting", "artsy_csv")
    _seed(db, "KG-9", "classification", "Drawing, Collage or other Work on Paper",
          "match_workbook", "2026-02-01")
    consolidate(db)
    db.conn.close()

    yaml_path = tmp_path / "human.yaml"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "promote", "KG-9", "classification",
        "--db", str(db_path), "--file", str(yaml_path),
        "--by", "test@kapoors.com",
    ])
    assert result.exit_code == 0, result.output
    assert "Promoted KG-9.classification" in result.output

    entries = yaml.safe_load(yaml_path.read_text())
    assert len(entries) == 1
    e = entries[0]
    assert e["work_id"] == "KG-9"
    assert e["field"] == "classification"
    assert e["value"] == "Drawing, Collage or other Work on Paper"
    assert e["decided_by"] == "test@kapoors.com"
