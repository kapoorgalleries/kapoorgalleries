"""Human + auto-resolution priority and conflict suppression."""

from pathlib import Path

import yaml

from src.consolidate import consolidate
from src.db import init_db, insert_observations, upsert_source
from src.ingest.auto_resolution import AutoResolutionIngester
from src.ingest.human_resolution import HumanResolutionIngester
from src.schema import Observation, SourceRecord


def _seed_observation(db, work_id, field, value, stype, observed_at="2026-01-01"):
    src = SourceRecord(name=f"test-{stype}", type=stype, extracted_at=observed_at)
    sid = upsert_source(db, src)
    insert_observations(db, sid, [
        Observation(work_id=work_id, field=field, value=value, observed_at=observed_at),
    ])


def test_human_resolution_wins_and_clears_conflict(tmp_path: Path):
    db = init_db(tmp_path / "t.db")
    _seed_observation(db, "KG-1", "classification", "Painting", "artsy_csv", "2026-01-01")
    _seed_observation(db, "KG-1", "classification", "Drawing, Collage or other Work on Paper",
                      "match_workbook", "2026-01-02")

    yp = tmp_path / "human.yaml"
    yp.write_text(yaml.safe_dump([{
        "work_id": "KG-1", "field": "classification",
        "value": "Painting",  # human says Painting wins
        "decided_by": "test", "decided_at": "2026-05-06",
    }]))
    res = HumanResolutionIngester(yp).run()
    sid = upsert_source(db, res.source)
    insert_observations(db, sid, res.observations)

    consolidate(db)
    row = db.execute(
        "SELECT classification, has_conflict FROM works WHERE work_id='KG-1'"
    ).fetchone()
    assert row[0] == "Painting"
    # Human resolution suppresses the conflict flag.
    assert row[1] == 0


def test_auto_resolution_fills_gap_without_creating_a_conflict(tmp_path: Path):
    db = init_db(tmp_path / "t.db")
    _seed_observation(db, "KG-2", "medium", "Opaque watercolor on paper", "artsy_csv")
    # No classification observation at all.

    rp = tmp_path / "rules.yaml"
    rp.write_text(yaml.safe_dump([
        {"if": {"medium_contains": "paper"},
         "then": {"classification": "Drawing, Collage or other Work on Paper"},
         "reason": "test"},
    ]))
    res = AutoResolutionIngester(rp, db=db).run()
    sid = upsert_source(db, res.source)
    insert_observations(db, sid, res.observations)

    consolidate(db)
    row = db.execute(
        "SELECT classification, has_conflict FROM works WHERE work_id='KG-2'"
    ).fetchone()
    assert row[0] == "Drawing, Collage or other Work on Paper"
    # No competing observation; not a conflict.
    assert row[1] == 0


def test_auto_resolution_does_not_inflate_conflict_count(tmp_path: Path):
    """Primer says X, auto-resolution says Y: the underlying observed sources
    only have one value, so no conflict — auto_resolution is a *resolution*,
    not an observation."""
    db = init_db(tmp_path / "t.db")
    _seed_observation(db, "KG-3", "classification", "Painting", "artsy_csv")

    rp = tmp_path / "rules.yaml"
    rp.write_text(yaml.safe_dump([
        {"if": {"classification_eq": "Painting"},
         "then": {"classification": "Drawing, Collage or other Work on Paper"},
         "reason": "test"},
    ]))
    res = AutoResolutionIngester(rp, db=db).run()
    sid = upsert_source(db, res.source)
    insert_observations(db, sid, res.observations)

    consolidate(db)
    row = db.execute(
        "SELECT classification, has_conflict FROM works WHERE work_id='KG-3'"
    ).fetchone()
    assert row[0] == "Drawing, Collage or other Work on Paper"
    # Only one observed value (Painting); auto-resolution overrode it.
    assert row[1] == 0
