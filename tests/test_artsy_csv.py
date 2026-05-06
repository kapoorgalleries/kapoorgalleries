"""End-to-end test of the Artsy CSV ingester against a tiny fixture."""

from pathlib import Path

from src.db import init_db, insert_observations, insert_images, upsert_source
from src.consolidate import consolidate
from src.ingest.artsy_csv import ArtsyCsvIngester


def test_artsy_ingester_handles_multi_image_and_conflicts(tmp_path: Path):
    db_path = tmp_path / "test.db"
    db = init_db(db_path)
    fixture = Path(__file__).parent / "fixtures" / "artsy_sample.csv"
    result = ArtsyCsvIngester(fixture).run()
    sid = upsert_source(db, result.source)
    insert_observations(db, sid, result.observations)
    insert_images(db, sid, result.images)

    work_ids = {r[0] for r in db.execute("SELECT DISTINCT work_id FROM observations").fetchall()}
    assert work_ids == {"KG-9000", "KG-9001", "KG-9006"}

    # KG-9001 should have 2 image rows (the multi-image continuation).
    n_imgs = db.execute(
        "SELECT COUNT(*) FROM work_images WHERE work_id = 'KG-9001'"
    ).fetchone()[0]
    assert n_imgs == 2

    # Artist 'Unknown' must be normalized to NULL.
    obs = db.execute(
        "SELECT field, value FROM observations WHERE work_id='KG-9001' AND field='artist'"
    ).fetchall()
    assert obs == []  # no artist observation since Unknown -> None

    # Consolidation: KG-9006 should flag a height conflict (40 vs 42).
    consolidate(db)
    works = db.execute(
        "SELECT work_id, has_conflict, conflict_fields FROM works WHERE work_id='KG-9006'"
    ).fetchone()
    assert works[1] == 1
    assert "height_in" in works[2]
