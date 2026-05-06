"""Verify init_db actually drops + recreates rather than 'create if not exists'."""

from pathlib import Path

from src.db import init_db, insert_observations, upsert_source
from src.schema import Observation, SourceRecord


def test_init_db_resets_existing_db(tmp_path: Path):
    p = tmp_path / "t.db"

    # First run: seed data
    db = init_db(p)
    sid = upsert_source(db, SourceRecord(name="t", type="artsy_csv", extracted_at="2026-01-01"))
    insert_observations(db, sid, [Observation(work_id="KG-1", field="title", value="Test")])
    n_before = db.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    n_sources = db.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    assert n_before == 1
    assert n_sources == 1
    db.conn.close()

    # Second run: init should clear
    db = init_db(p)
    n_after = db.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    n_sources_after = db.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    assert n_after == 0
    assert n_sources_after == 0


def test_init_db_creates_views(tmp_path: Path):
    """Schema includes the v_conflicts view after init."""
    db = init_db(tmp_path / "t.db")
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'view'"
    ).fetchall()
    assert any(r[0] == "v_conflicts" for r in rows)


def test_init_db_idempotent(tmp_path: Path):
    """Calling init_db twice in a row doesn't error."""
    p = tmp_path / "t.db"
    init_db(p)
    init_db(p)  # Should drop+recreate cleanly
