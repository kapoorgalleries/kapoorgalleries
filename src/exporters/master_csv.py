"""Export the canonical `works` table to a wide CSV.

Each canonical field gets a paired ``<field>_conflict`` column (1/0) so the
Apps Script can paint conflicting cells red without needing a second query.
"""

from __future__ import annotations

import csv
from pathlib import Path

import sqlite_utils

from ..schema import CANONICAL_FIELDS

EXTRA_COLS = ("has_conflict", "conflict_fields", "canonical_updated_at")


def export_master_csv(db: sqlite_utils.Database, out_path: Path | str) -> int:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = list(db.execute(
        f"""SELECT work_id, {','.join(CANONICAL_FIELDS)}, {','.join(EXTRA_COLS)}
            FROM works ORDER BY work_id"""
    ).fetchall())

    headers = ["work_id"] + list(CANONICAL_FIELDS) + list(EXTRA_COLS)
    # Append per-field conflict flag columns at the end.
    field_conflict_cols = [f"{f}_conflict" for f in CANONICAL_FIELDS]
    headers += field_conflict_cols

    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        for row in rows:
            base = list(row)
            conflict_fields = (row[len(CANONICAL_FIELDS) + 1 + 1] or "").split(",")
            flags = [1 if f in conflict_fields else 0 for f in CANONICAL_FIELDS]
            w.writerow(base + flags)
    return len(rows)
