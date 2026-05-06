"""Emit one row per conflicting (work_id, field) with all observed values."""

from __future__ import annotations

import csv
from pathlib import Path

import sqlite_utils


def export_conflicts(db: sqlite_utils.Database, out_path: Path | str) -> int:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = db.execute(
        """SELECT v.work_id, v.field, v.distinct_values, v.values_seen,
                  GROUP_CONCAT(DISTINCT s.type) AS source_types
           FROM v_conflicts v
           JOIN observations o ON o.work_id = v.work_id AND o.field = v.field
           JOIN sources s ON s.id = o.source_id
           GROUP BY v.work_id, v.field
           ORDER BY v.work_id, v.field"""
    ).fetchall()
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["work_id", "field", "distinct_values", "values_seen", "source_types"])
        w.writerows(rows)
    return len(rows)
