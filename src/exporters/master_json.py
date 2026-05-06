"""Compact JSON export of the master record.

One JSON object per work, suitable for the Apps Script sidebar /
fetch-once-and-render-many-views consumers. Smaller than the CSV
because empty fields are omitted.
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlite_utils


def export_master_json(db: sqlite_utils.Database, out_path: Path | str) -> int:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = [d[0] for d in db.execute("SELECT * FROM works LIMIT 0").description]
    rows = db.execute(f"SELECT {','.join(cols)} FROM works ORDER BY work_id").fetchall()
    # canonical_updated_at is the consolidate run time, identical across all
    # rows.  Including it would cause every row to diff on every run; drop it.
    skip_cols = {"canonical_updated_at"}
    docs = []
    for row in rows:
        rec = {
            c: v for c, v in zip(cols, row)
            if c not in skip_cols and (v not in (None, "", 0) or c == "has_conflict")
        }
        docs.append(rec)
    out.write_text(json.dumps(docs, indent=2, ensure_ascii=False))
    return len(docs)
