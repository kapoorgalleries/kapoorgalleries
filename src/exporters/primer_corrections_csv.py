"""Generate a Primer-corrections punch list.

For every (work_id, field) where the canonical value differs from what the
``artsy_csv`` (Primer→Artsy) snapshot says, emit one row telling the team
exactly what to change *in Primer*. This converts the consolidated record's
auto-resolutions, human-resolutions, and Match Workbook overrides into a
plain to-do list that can be worked through inside the Primer UI.

Columns:
    work_id, field, current_in_primer, should_be, evidence_source, reason

Example:
    KG-1000, classification, Painting,
        "Drawing, Collage or other Work on Paper", auto_resolution,
        "Works on paper map to Artsy's Drawing/Collage category."

If primer_csv exports get added later, the same logic generalizes to any
``stype LIKE 'primer%'`` source.
"""

from __future__ import annotations

import csv
from pathlib import Path

import sqlite_utils


PRIMER_TYPES = ("artsy_csv", "primer_pdf", "primer_csv")


def export_primer_corrections(db: sqlite_utils.Database, out_path: Path | str) -> int:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = db.execute(
        f"""
        WITH primer AS (
          SELECT o.work_id, o.field, o.value AS primer_value
          FROM observations o JOIN sources s ON s.id = o.source_id
          WHERE s.type IN ({','.join('?' * len(PRIMER_TYPES))})
            AND o.value IS NOT NULL AND o.value != ''
        )
        SELECT DISTINCT p.work_id, p.field, p.primer_value
        FROM primer p
        """,
        list(PRIMER_TYPES),
    ).fetchall()

    primer_lookup = {(w, f): v for w, f, v in rows}

    # Pull the canonical works table.
    cols = [d[0] for d in db.execute("SELECT * FROM works LIMIT 0").description]
    work_rows = db.execute(f"SELECT {','.join(cols)} FROM works").fetchall()

    n = 0
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "work_id", "field", "current_in_primer",
            "should_be", "evidence_source", "reason",
        ])
        for row in work_rows:
            rec = dict(zip(cols, row))
            wid = rec["work_id"]
            for field, canonical in rec.items():
                if field in (
                    "work_id", "has_conflict", "conflict_fields",
                    "canonical_updated_at", "primer_uuid",
                ):
                    continue
                if canonical in (None, "", 0):
                    continue
                primer_val = primer_lookup.get((wid, field))
                if primer_val is None:
                    # Field is missing entirely in Primer → could fill in.
                    src_row = db.execute(
                        """SELECT s.type, o.source_row_ref
                           FROM observations o JOIN sources s ON s.id = o.source_id
                           WHERE o.work_id = ? AND o.field = ? AND o.value = ?
                           ORDER BY o.observed_at DESC LIMIT 1""",
                        [wid, field, str(canonical)],
                    ).fetchone()
                    if not src_row:
                        continue
                    stype, row_ref = src_row
                    if stype in PRIMER_TYPES:
                        continue  # already in Primer
                    reason = (row_ref or "").split("reason=", 1)
                    reason_text = reason[1] if len(reason) == 2 else "(filled from " + stype + ")"
                    w.writerow([wid, field, "", canonical, stype, reason_text])
                    n += 1
                elif str(primer_val) != str(canonical):
                    # Real disagreement: Primer is wrong (per the resolution).
                    src_row = db.execute(
                        """SELECT s.type, o.source_row_ref
                           FROM observations o JOIN sources s ON s.id = o.source_id
                           WHERE o.work_id = ? AND o.field = ? AND o.value = ?
                           ORDER BY o.observed_at DESC LIMIT 1""",
                        [wid, field, str(canonical)],
                    ).fetchone()
                    if not src_row:
                        continue
                    stype, row_ref = src_row
                    reason = (row_ref or "").split("reason=", 1)
                    reason_text = reason[1] if len(reason) == 2 else f"(per {stype})"
                    w.writerow([wid, field, primer_val, canonical, stype, reason_text])
                    n += 1
    return n
