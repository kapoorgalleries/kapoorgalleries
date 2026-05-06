"""Rules-based field inference / conflict auto-resolution.

For situations where a deterministic rule can resolve a conflict (or fill a
gap) without human review.  Rules live in
``data/auto_resolution_rules.yaml``::

    - if:
        medium_contains: paper
      then:
        classification: "Drawing, Collage or other Work on Paper"
      reason: "All works on paper map to Artsy's 'Drawing/Collage' category."

    - if:
        materials_in: ["Sandstone", "Schist", "Bronze", "Stucco"]
      then:
        classification: Sculpture

The ingester evaluates each rule against every work, looks up the relevant
fields from the consolidated table OR from raw observations, and emits an
observation with ``source.type = 'auto_resolution'`` and confidence
``'medium'``.  The consolidator places auto_resolution **below**
``human_resolution`` but **above** Primer for the rule's target field — so
it fills gaps, but a human override always wins.

The point: codify the gallery's conventions ("works on paper count as
Drawing for Artsy") so the same fix doesn't have to be made 140 times.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import sqlite_utils
import yaml

from ..schema import Observation
from ._base import IngestResult, Ingester


def _get_observed(db: sqlite_utils.Database, work_id: str, field: str) -> str | None:
    row = db.execute(
        """SELECT value FROM observations WHERE work_id = ? AND field = ?
              AND value IS NOT NULL AND value != ''
           ORDER BY observed_at DESC LIMIT 1""",
        [work_id, field],
    ).fetchone()
    return row[0] if row else None


class AutoResolutionIngester(Ingester):
    """Reads rules from ``self.file_path`` and applies them against ``db``."""

    type = "auto_resolution"

    def __init__(self, file_path: Path | str, drive_file_id: str | None = None,
                 db: sqlite_utils.Database | None = None):
        super().__init__(file_path, drive_file_id)
        self.db = db

    def run(self) -> IngestResult:
        observations: list[Observation] = []
        if self.db is None or not self.file_path.exists():
            return IngestResult(
                source=self._make_source(row_count=0), observations=observations,
            )

        rules = yaml.safe_load(self.file_path.read_text()) or []
        work_ids = [r[0] for r in self.db.execute(
            "SELECT DISTINCT work_id FROM observations"
        ).fetchall()]
        now = datetime.now(timezone.utc).isoformat()

        applied = 0
        for rule_idx, rule in enumerate(rules, start=1):
            cond = rule.get("if", {})
            then = rule.get("then", {})
            reason = rule.get("reason", "")
            if not then:
                continue

            for w in work_ids:
                if not _matches(self.db, w, cond):
                    continue
                for field, value in then.items():
                    # Don't overwrite an existing value for this field on this work.
                    existing = _get_observed(self.db, w, field)
                    if existing == str(value):
                        continue
                    observations.append(Observation(
                        work_id=w,
                        field=field,
                        value=str(value),
                        source_row_ref=f"rule={rule_idx};reason={reason}",
                        confidence="medium",
                        observed_at=now,
                    ))
                    applied += 1
        return IngestResult(
            source=self._make_source(row_count=len(rules)),
            observations=observations,
        )


def _matches(db: sqlite_utils.Database, work_id: str, cond: dict) -> bool:
    """Evaluate the `if:` clause for one work."""
    for key, expected in cond.items():
        # Patterns: <field>_contains, <field>_eq, <field>_in
        if key.endswith("_contains"):
            field = key[: -len("_contains")]
            actual = (_get_observed(db, work_id, field) or "").lower()
            if str(expected).lower() not in actual:
                return False
        elif key.endswith("_eq"):
            field = key[: -len("_eq")]
            actual = _get_observed(db, work_id, field)
            if actual != str(expected):
                return False
        elif key.endswith("_in"):
            field = key[: -len("_in")]
            actual = (_get_observed(db, work_id, field) or "").lower()
            if not isinstance(expected, list):
                return False
            if actual not in {str(e).lower() for e in expected}:
                return False
        elif key.endswith("_missing"):
            field = key[: -len("_missing")]
            actual = _get_observed(db, work_id, field)
            if bool(actual) == bool(expected):  # _missing: true means actual must be falsy
                return False
        else:
            # Default: equality on field name.
            actual = _get_observed(db, work_id, key)
            if actual != str(expected):
                return False
    return True
