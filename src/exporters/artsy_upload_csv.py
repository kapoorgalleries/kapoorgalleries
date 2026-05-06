"""Build the Artsy bulk-upload CSV (only Artsy-eligible rows).

Eligibility: status='active' AND title/classification/medium/primary_image_url
are all populated. Output columns match the Artsy template exactly.
"""

from __future__ import annotations

import csv
from pathlib import Path

import sqlite_utils

ARTSY_HEADER = [
    "Inventory ID (OPTIONAL)",
    "Artist Name ",
    "Title ",
    "Year ",
    "Price ",
    "Medium ",
    "Materials ",
    "Height ",
    "Width ",
    "Depth",
    "Certificate of Authenticity ",
    "Signature ",
    "Classification ",
]


def export_artsy_upload(db: sqlite_utils.Database, out_path: Path | str) -> int:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = db.execute(
        """SELECT work_id, artist, title, year, price_usd, medium, materials,
                  height_in, width_in, depth_in, coa_status, signature, classification
           FROM works
           WHERE COALESCE(status,'active') = 'active'
             AND title IS NOT NULL
             AND classification IS NOT NULL
             AND medium IS NOT NULL
             AND primary_image_url IS NOT NULL
           ORDER BY work_id"""
    ).fetchall()
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(ARTSY_HEADER)
        for r in rows:
            w.writerow([
                r[0],                 # Inventory ID
                r[1] or "Unknown Artist",
                r[2] or "",
                r[3] or "",
                r[4] or "",
                r[5] or "",           # Medium
                r[6] or r[5] or "",   # Materials -> fall back to medium
                r[7] or "",
                r[8] or "",
                r[9] or "",
                r[10] or "",
                r[11] or "",
                r[12] or "",
            ])
    return len(rows)
