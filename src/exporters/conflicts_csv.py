"""Emit one row per conflicting (work_id, field) with all observed values."""

from __future__ import annotations

import csv
from pathlib import Path

import sqlite_utils


def export_conflicts(db: sqlite_utils.Database, out_path: Path | str) -> int:
    """Emit only *unresolved* conflicts.

    A conflict exists when ≥2 distinct values come from observation sources
    (i.e. excluding ``human_resolution`` / ``auto_resolution``) AND no
    ``human_resolution`` is present for that (work, field).
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = db.execute(
        """WITH observed AS (
              SELECT o.work_id, o.field, o.value, s.type AS stype
              FROM observations o JOIN sources s ON s.id = o.source_id
              WHERE o.value IS NOT NULL AND o.value != ''
                AND s.type NOT IN ('human_resolution','auto_resolution')
           ),
           agg AS (
              SELECT work_id, field,
                     COUNT(DISTINCT value) AS distinct_values,
                     GROUP_CONCAT(DISTINCT value) AS values_seen,
                     GROUP_CONCAT(DISTINCT stype) AS source_types
              FROM observed
              GROUP BY work_id, field
              HAVING distinct_values > 1
           )
           SELECT a.work_id, a.field, a.distinct_values,
                  REPLACE(a.values_seen, ',', ' || ') AS values_seen,
                  a.source_types
           FROM agg a
           WHERE NOT EXISTS (
              SELECT 1 FROM observations o2 JOIN sources s2 ON s2.id = o2.source_id
              WHERE o2.work_id = a.work_id AND o2.field = a.field
                AND s2.type = 'human_resolution'
           )
           ORDER BY a.work_id, a.field"""
    ).fetchall()
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["work_id", "field", "distinct_values", "values_seen", "source_types"])
        w.writerows(rows)
    return len(rows)
