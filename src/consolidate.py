"""Build the canonical ``works`` table from raw observations.

Source priority for choosing the canonical value of a field (highest first):

1. ``human_resolution`` — explicit human decision in
   ``data/human_resolutions.yaml``. Always wins.
2. ``auto_resolution`` — rules-based inference from
   ``data/auto_resolution_rules.yaml`` (e.g. "medium contains paper →
   classification = Drawing"). Fills gaps but loses to a human.
3. ``match_workbook`` — the curator-built Artsy Match Workbook, which is
   tighter on classification/materials than Primer.
4. Primer-derived (``artsy_csv``, ``primer_pdf``, ``primer_csv``) — the
   primary system of record.
5. Otherwise, most recent observation by ``observed_at``.

We never silently merge: if more than one *distinct* value exists for a
(work_id, field) we set ``has_conflict = 1`` and list the offending fields in
``conflict_fields`` so the Apps Script can paint them red.

A field with a ``human_resolution`` observation is never marked as
conflicting — the human has spoken.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import sqlite_utils

from .normalize import (
    normalize_artist, normalize_decimal, normalize_int, normalize_price,
    normalize_year,
)
from .schema import CANONICAL_FIELDS

# Priority bands, highest wins. Within a band, most-recent observation wins.
PRIORITY_BANDS: tuple[set[str], ...] = (
    {"human_resolution"},
    {"auto_resolution"},
    {"match_workbook"},
    {"artsy_csv", "primer_pdf", "primer_csv"},
)
PRIMER_TYPES = {"artsy_csv", "primer_pdf", "primer_csv"}  # legacy alias for tests

NUMERIC_FIELDS = {"height_in", "width_in", "depth_in", "price_usd"}
INT_FIELDS = {"year"}


def _coerce(field: str, value: Optional[str]):
    if value is None or value == "":
        return None
    if field in NUMERIC_FIELDS:
        return normalize_decimal(value) if field != "price_usd" else normalize_price(value)
    if field in INT_FIELDS:
        return normalize_year(value) if field == "year" else normalize_int(value)
    if field == "artist":
        # Filter out placeholders ("Unknown", "Unspecified Artist", etc.).
        return normalize_artist(value)
    return value


def _pick_canonical(rows: list[tuple[str, str, str]]) -> Optional[str]:
    """rows = [(value, source_type, observed_at), ...] all for one (work, field).

    Walks ``PRIORITY_BANDS`` top to bottom, returning the most-recent value
    from the highest-priority band that has any observation.  Falls back to
    "globally most recent" if no band matches.
    """
    if not rows:
        return None
    for band in PRIORITY_BANDS:
        in_band = [r for r in rows if r[1] in band]
        if in_band:
            return sorted(in_band, key=lambda r: r[2], reverse=True)[0][0]
    return sorted(rows, key=lambda r: r[2], reverse=True)[0][0]


def _has_human_resolution(rows: list[tuple[str, str, str]]) -> bool:
    return any(r[1] == "human_resolution" for r in rows)


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
            # Conflict detection only considers OBSERVATION sources.  Resolution
            # sources (human/auto) are decisions, not disagreements — they pick
            # a winner, they don't create one.
            observed_vals = {
                r[0] for r in rows
                if r[1] not in ("human_resolution", "auto_resolution")
            }
            # A human resolution closes the conflict outright.
            if len(observed_vals) > 1 and not _has_human_resolution(rows):
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
