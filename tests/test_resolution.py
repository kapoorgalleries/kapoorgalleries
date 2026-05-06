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


def test_match_workbook_beats_primer(tmp_path: Path):
    """Match Workbook is in priority band 3, beats artsy_csv (band 4)."""
    db = init_db(tmp_path / "t.db")
    _seed_observation(db, "KG-X", "classification", "Painting", "artsy_csv", "2026-04-01")
    _seed_observation(db, "KG-X", "classification", "Drawing", "match_workbook", "2026-01-01")
    consolidate(db)
    row = db.execute(
        "SELECT classification FROM works WHERE work_id='KG-X'"
    ).fetchone()
    assert row[0] == "Drawing"  # Match Workbook wins despite being older


def test_human_resolution_warns_on_unknown_field(tmp_path: Path):
    """Typos like 'classifcation' should produce a warning, not silently no-op."""
    import warnings
    yp = tmp_path / "h.yaml"
    yp.write_text(yaml.safe_dump([{
        "work_id": "KG-X", "field": "classifcation",  # typo
        "value": "Drawing", "decided_by": "test", "decided_at": "2026-05-06",
    }]))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        res = HumanResolutionIngester(yp).run()
    assert any("classifcation" in str(w.message) for w in caught)
    # No observation emitted for the bad field.
    assert all(o.field != "classifcation" for o in res.observations)


def test_priority_human_beats_auto_beats_match_beats_primer(tmp_path: Path):
    """Verify the full priority cascade."""
    db = init_db(tmp_path / "t.db")
    _seed_observation(db, "KG-Y", "classification", "Painting", "artsy_csv")
    _seed_observation(db, "KG-Y", "classification", "Drawing", "match_workbook")
    _seed_observation(db, "KG-Y", "classification", "Sculpture", "auto_resolution")
    _seed_observation(db, "KG-Y", "classification", "Print", "human_resolution")
    consolidate(db)
    row = db.execute(
        "SELECT classification, has_conflict FROM works WHERE work_id='KG-Y'"
    ).fetchone()
    assert row[0] == "Print"  # Human always wins
    assert row[1] == 0  # Human resolution closes the conflict
