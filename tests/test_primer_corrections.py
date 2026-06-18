"""Verify the Primer-corrections punch list generation."""

from pathlib import Path

import yaml

from src.consolidate import consolidate
from src.db import init_db, insert_observations, upsert_source
from src.exporters.primer_corrections_csv import export_primer_corrections
from src.ingest.auto_resolution import AutoResolutionIngester
from src.ingest.human_resolution import HumanResolutionIngester
from src.schema import Observation, SourceRecord


def _seed(db, work_id, field, value, stype, observed_at="2026-01-01"):
    sid = upsert_source(db, SourceRecord(name=f"t-{stype}", type=stype, extracted_at=observed_at))
    insert_observations(db, sid, [Observation(
        work_id=work_id, field=field, value=value, observed_at=observed_at,
    )])


def test_corrections_flag_fields_where_primer_disagrees(tmp_path: Path):
    db = init_db(tmp_path / "t.db")
    _seed(db, "KG-A", "classification", "Painting", "artsy_csv")
    _seed(db, "KG-A", "classification", "Drawing", "match_workbook", "2026-02-01")
    consolidate(db)
    out = tmp_path / "out.csv"
    n = export_primer_corrections(db, out)
    text = out.read_text()
    assert n == 1
    assert "KG-A,classification,Painting,Drawing" in text


def test_corrections_flag_fields_missing_in_primer(tmp_path: Path):
    db = init_db(tmp_path / "t.db")
    # No Primer observation for materials at all.
    _seed(db, "KG-B", "title", "Foo", "artsy_csv")
    _seed(db, "KG-B", "materials", "Sandstone", "match_workbook", "2026-02-01")
    consolidate(db)
    out = tmp_path / "out.csv"
    n = export_primer_corrections(db, out)
    text = out.read_text()
    assert n == 1
    assert ",materials,," in text  # current_in_primer is empty


def test_corrections_skip_when_primer_agrees(tmp_path: Path):
    db = init_db(tmp_path / "t.db")
    _seed(db, "KG-C", "classification", "Sculpture", "artsy_csv")
    _seed(db, "KG-C", "medium", "Sandstone", "artsy_csv")
    consolidate(db)
    out = tmp_path / "out.csv"
    n = export_primer_corrections(db, out)
    # Primer already has the canonical value; no correction needed.
    assert n == 0


def test_corrections_respect_human_override(tmp_path: Path):
    db = init_db(tmp_path / "t.db")
    _seed(db, "KG-D", "classification", "Painting", "artsy_csv")
    _seed(db, "KG-D", "classification", "Drawing", "match_workbook", "2026-02-01")

    # Human says "no, it really is Painting"
    yp = tmp_path / "h.yaml"
    yp.write_text(yaml.safe_dump([{
        "work_id": "KG-D", "field": "classification",
        "value": "Painting", "decided_by": "test",
        "decided_at": "2026-05-06",
    }]))
    res = HumanResolutionIngester(yp).run()
    sid = upsert_source(db, res.source)
    insert_observations(db, sid, res.observations)

    consolidate(db)
    out = tmp_path / "out.csv"
    n = export_primer_corrections(db, out)
    # Primer (Painting) matches the human-resolved canonical (Painting):
    # no correction needed.
    assert n == 0
