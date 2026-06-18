"""Emit one row per work, listing missing canonical fields."""

from __future__ import annotations

import csv
from pathlib import Path

import sqlite_utils

from ..schema import ARTSY_REQUIRED_FIELDS, CANONICAL_FIELDS

# Fields we consider "core" for a usable inventory record.
CORE_FIELDS = (
    "title", "artist", "year", "classification", "medium",
    "height_in", "width_in", "primary_image_url", "price_usd",
)


def export_gaps(db: sqlite_utils.Database, out_path: Path | str) -> int:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = list(CANONICAL_FIELDS)
    rows = db.execute(
        f"SELECT work_id, {','.join(fields)} FROM works ORDER BY work_id"
    ).fetchall()
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "work_id", "missing_core", "missing_artsy_required",
            "core_completeness_pct", "missing_fields",
        ])
        for row in rows:
            wid = row[0]
            values = dict(zip(fields, row[1:]))
            missing = [f for f in CORE_FIELDS if not values.get(f)]
            missing_artsy = [f for f in ARTSY_REQUIRED_FIELDS if not values.get(f)]
            pct = round(100 * (len(CORE_FIELDS) - len(missing)) / len(CORE_FIELDS), 1)
            w.writerow([wid, len(missing), len(missing_artsy), pct, ",".join(missing)])
    return len(rows)
