"""Ingester for human-decided field values.

This is how the team closes the loop on a flagged conflict: when the master
sheet shows a red cell for, say, ``KG-1000.classification``, a human
inspects the conflicting values, decides which is correct, and records the
decision in ``data/human_resolutions.yaml``::

    - work_id: KG-1000
      field: classification
      value: "Drawing, Collage or other Work on Paper"
      reason: "Opaque watercolor on paper; Artsy categorises this as Drawing."
      decided_by: sanjay@kapoors.com
      decided_at: 2026-05-06

Every entry becomes one observation with ``source.type = 'human_resolution'``,
``confidence = 'authoritative'`` and the latest possible timestamp. The
consolidator treats this source type as **highest priority**, above Primer.

The CLI helper ``kg-inv resolve`` appends to the YAML — so most users will
never edit the file directly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..schema import Observation
from ._base import IngestResult, Ingester


class HumanResolutionIngester(Ingester):
    type = "human_resolution"

    def run(self) -> IngestResult:
        observations: list[Observation] = []
        if not self.file_path.exists():
            return IngestResult(
                source=self._make_source(row_count=0), observations=observations,
            )

        entries = yaml.safe_load(self.file_path.read_text()) or []
        for i, e in enumerate(entries, start=1):
            work_id = e.get("work_id")
            field = e.get("field")
            value = e.get("value")
            if not work_id or not field or value in (None, ""):
                continue
            decided_at = e.get("decided_at") or datetime.now(timezone.utc).isoformat()
            ref = (
                f"row={i};by={e.get('decided_by','?')}"
                + (f";reason={e['reason']}" if e.get("reason") else "")
            )
            observations.append(Observation(
                work_id=str(work_id),
                field=str(field),
                value=str(value),
                source_row_ref=ref,
                confidence="authoritative",
                observed_at=str(decided_at),
            ))
        return IngestResult(
            source=self._make_source(row_count=len(entries)),
            observations=observations,
        )
