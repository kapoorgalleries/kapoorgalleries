"""Per-(work_id, field) provenance long-format CSV.

One row per populated field of every work, showing exactly which source
the canonical value came from and what alternative observations exist.

Columns:
    work_id, field, canonical_value, canonical_source, alt_count,
    alternative_values, alternative_sources

Example:
    KG-1000, classification, "Drawing, Collage or other Work on Paper",
        match_workbook, 1, "Painting", "artsy_csv"

This is the file to consult when a row in master.csv looks wrong: it
tells you who said what, so you know whether to fix Primer, fix the
Match Workbook, or add a human resolution.
"""

from __future__ import annotations

import csv
from pathlib import Path

import sqlite_utils

from ..consolidate import PRIORITY_BANDS, _pick_canonical


def export_provenance(db: sqlite_utils.Database, out_path: Path | str) -> int:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = db.execute(
        """SELECT o.work_id, o.field, o.value, s.type, o.observed_at
           FROM observations o JOIN sources s ON s.id = o.source_id
           WHERE o.value IS NOT NULL AND o.value != ''
           ORDER BY o.work_id, o.field, o.observed_at"""
    ).fetchall()

    by_field: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
    for w, f, v, st, oa in rows:
        by_field.setdefault((w, f), []).append((v, st, oa))

    n = 0
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "work_id", "field", "canonical_value", "canonical_source",
            "alt_count", "alternative_values", "alternative_sources",
        ])
        for (w, f), obs in sorted(by_field.items()):
            chosen_value = _pick_canonical(obs)
            # Find one tuple with that value to identify its source.
            chosen_tuple = next(t for t in obs if t[0] == chosen_value)
            chosen_src = chosen_tuple[1]
            alts = [t for t in obs if t[0] != chosen_value]
            alt_values = list({t[0] for t in alts})
            alt_sources = list({t[1] for t in alts})
            writer.writerow([
                w, f, chosen_value, chosen_src,
                len(alt_values), " || ".join(alt_values), ",".join(sorted(alt_sources)),
            ])
            n += 1
    return n
