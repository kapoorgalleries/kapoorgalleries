"""SQLite helpers built on sqlite-utils."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import sqlite_utils

from .schema import DDL, Observation, SourceRecord, WorkImage

DB_PATH = Path("data/inventory.db")


def get_db(path: Path | str = DB_PATH) -> sqlite_utils.Database:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite_utils.Database(str(path))
    return db


def init_db(path: Path | str = DB_PATH) -> sqlite_utils.Database:
    db = get_db(path)
    for stmt in [s.strip() for s in DDL.split(";") if s.strip()]:
        db.execute(stmt + ";")
    db.conn.commit()
    return db


def upsert_source(db: sqlite_utils.Database, src: SourceRecord) -> int:
    existing = db.execute(
        "SELECT id FROM sources WHERE name = ? AND extracted_at = ?",
        [src.name, src.extracted_at],
    ).fetchone()
    if existing:
        return int(existing[0])
    cur = db.conn.execute(
        """INSERT INTO sources (name, type, drive_file_id, drive_file_path,
                                file_modified_at, extracted_at, row_count, parser_version)
           VALUES (?,?,?,?,?,?,?,?)""",
        [src.name, src.type, src.drive_file_id, src.drive_file_path,
         src.file_modified_at, src.extracted_at, src.row_count, src.parser_version],
    )
    db.conn.commit()
    return int(cur.lastrowid)


def insert_observations(
    db: sqlite_utils.Database, source_id: int, obs: Iterable[Observation]
) -> int:
    rows = [
        (o.work_id, o.field, o.value, source_id, o.source_row_ref, o.confidence, o.observed_at)
        for o in obs
        if o.value not in (None, "")
    ]
    if not rows:
        return 0
    db.conn.executemany(
        """INSERT INTO observations (work_id, field, value, source_id,
                                     source_row_ref, confidence, observed_at)
           VALUES (?,?,?,?,?,?,?)""",
        rows,
    )
    db.conn.commit()
    return len(rows)


def insert_images(db: sqlite_utils.Database, source_id: int, images: Iterable[WorkImage]) -> int:
    rows = [
        (i.work_id, i.image_url, i.drive_file_id, i.bytes, int(i.is_placeholder), source_id)
        for i in images
    ]
    if not rows:
        return 0
    db.conn.executemany(
        """INSERT INTO work_images (work_id, image_url, drive_file_id, bytes,
                                     is_placeholder, source_id)
           VALUES (?,?,?,?,?,?)""",
        rows,
    )
    db.conn.commit()
    return len(rows)


def latest_source_for_observation(
    db: sqlite_utils.Database, work_id: str, field: str
) -> tuple[str | None, str | None, str | None]:
    """Return (value, source_type, observed_at) of most-recent observation."""
    row = db.execute(
        """SELECT o.value, s.type, o.observed_at
           FROM observations o JOIN sources s ON s.id = o.source_id
           WHERE o.work_id = ? AND o.field = ? AND o.value IS NOT NULL AND o.value != ''
           ORDER BY o.observed_at DESC LIMIT 1""",
        [work_id, field],
    ).fetchone()
    return tuple(row) if row else (None, None, None)
