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

    # Pull raw observations and aggregate in Python — SQLite's GROUP_CONCAT
    # uses comma as separator and DISTINCT can't take a custom one, so values
    # like "Drawing, Collage or other Work on Paper" would split.
    raw = db.execute(
        """SELECT o.work_id, o.field, o.value, s.type AS stype
           FROM observations o JOIN sources s ON s.id = o.source_id
           WHERE o.value IS NOT NULL AND o.value != ''
             AND s.type NOT IN ('human_resolution','auto_resolution')"""
    ).fetchall()
    has_human = {
        (w, f) for (w, f) in db.execute(
            """SELECT DISTINCT o.work_id, o.field FROM observations o
               JOIN sources s ON s.id = o.source_id
               WHERE s.type = 'human_resolution'"""
        ).fetchall()
    }

    by_field: dict[tuple[str, str], dict] = {}
    for w, f, v, st in raw:
        rec = by_field.setdefault((w, f), {"values": set(), "stypes": set()})
        rec["values"].add(v)
        rec["stypes"].add(st)

    out_rows = []
    for (w, f), rec in by_field.items():
        if len(rec["values"]) < 2 or (w, f) in has_human:
            continue
        out_rows.append((
            w, f, len(rec["values"]),
            " || ".join(sorted(rec["values"])),
            ",".join(sorted(rec["stypes"])),
        ))
    out_rows.sort(key=lambda r: (r[0], r[1]))

    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["work_id", "field", "distinct_values", "values_seen", "source_types"])
        w.writerows(out_rows)
    return len(out_rows)
