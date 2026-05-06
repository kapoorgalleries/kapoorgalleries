"""Build the canonical ``works`` table from raw observations.

Source priority for choosing the canonical value of a field:

1. Anything from a Primer-derived source (`type` starts with ``primer_`` or
   ``artsy_csv``, since the Artsy CSV is itself a Primer dump).
2. Otherwise, the most recent observation by ``observed_at``.

We never silently merge: if more than one *distinct* value exists for a
(work_id, field) we set ``has_conflict = 1`` and list the offending fields in
``conflict_fields`` so the Apps Script can paint them red.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import sqlite_utils

from .normalize import (
    normalize_decimal, normalize_int, normalize_price, normalize_year,
)
from .schema import CANONICAL_FIELDS

PRIMER_TYPES = {"artsy_csv", "primer_pdf", "primer_csv"}

NUMERIC_FIELDS = {"height_in", "width_in", "depth_in", "price_usd"}
INT_FIELDS = {"year"}


def _coerce(field: str, value: Optional[str]):
    if value is None or value == "":
        return None
    if field in NUMERIC_FIELDS:
        return normalize_decimal(value) if field != "price_usd" else normalize_price(value)
    if field in INT_FIELDS:
        return normalize_year(value) if field == "year" else normalize_int(value)
    return value


def _pick_canonical(rows: list[tuple[str, str, str]]) -> Optional[str]:
    """rows = [(value, source_type, observed_at), ...] all for one (work, field)."""
    if not rows:
        return None
    primer_rows = [r for r in rows if r[1] in PRIMER_TYPES]
    pool = primer_rows if primer_rows else rows
    pool_sorted = sorted(pool, key=lambda r: r[2], reverse=True)
    return pool_sorted[0][0]


def consolidate(db: sqlite_utils.Database) -> dict:
    """Rebuild the `works` table; idempotent."""
    db.execute("DELETE FROM works")
    db.conn.commit()

    work_ids = [r[0] for r in db.execute("SELECT DISTINCT work_id FROM observations").fetchall()]
    now = datetime.now(timezone.utc).isoformat()

    inserted = 0
    conflicts_total = 0
    for w in work_ids:
        # Per-field observations.
        obs = db.execute(
            """SELECT o.field, o.value, s.type, o.observed_at
               FROM observations o JOIN sources s ON s.id = o.source_id
               WHERE o.work_id = ? AND o.value IS NOT NULL AND o.value != ''""",
            [w],
        ).fetchall()

        by_field: dict[str, list[tuple[str, str, str]]] = {}
        for field, value, stype, obsv_at in obs:
            by_field.setdefault(field, []).append((value, stype, obsv_at))

        canonical: dict[str, object] = {}
        conflict_fields: list[str] = []
        for field in CANONICAL_FIELDS:
            rows = by_field.get(field, [])
            distinct_vals = {r[0] for r in rows}
            if len(distinct_vals) > 1:
                conflict_fields.append(field)
            chosen = _pick_canonical(rows)
            canonical[field] = _coerce(field, chosen)

        if conflict_fields:
            conflicts_total += 1

        cols = list(CANONICAL_FIELDS) + ["has_conflict", "conflict_fields", "canonical_updated_at", "work_id"]
        vals = [canonical.get(f) for f in CANONICAL_FIELDS] + [
            int(bool(conflict_fields)),
            ",".join(conflict_fields) or None,
            now,
            w,
        ]
        placeholders = ",".join("?" for _ in cols)
        db.conn.execute(
            f"INSERT INTO works ({','.join(cols)}) VALUES ({placeholders})",
            vals,
        )
        inserted += 1

    db.conn.commit()
    return {"works": inserted, "with_conflicts": conflicts_total}
