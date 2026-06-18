"""Ingester for emailed Artsy gap reports (Sarah Fenner et al.).

Expects a JSON file at ``data/raw/email_gaps_<sender>.json`` of the shape:

    [
      {"thread_id": "...", "subject": "...", "from": "...", "date": "...",
       "body": "...full text..."},
      ...
    ]

The Gmail MCP tool cannot dump straight to disk, so the user runs:

    python -m src.fetch_gmail --query "from:sarah.fenner@artsy.net" \\
        --out data/raw/email_gaps_sarah_fenner.json

(or pastes the JSON manually). Then this ingester scans bodies for KG-####
mentioned alongside trigger phrases like "missing", "incomplete", "blocked",
"ineligible" and flags those works as ``artsy_eligibility = blocked``.
"""

from __future__ import annotations

import json
import re

from ..ids import KG_RE
from ..schema import Observation
from ._base import IngestResult, Ingester

BLOCK_TRIGGER_RE = re.compile(
    r"(missing|incomplete|blocked|ineligible|cannot upload|won.t upload|gap)",
    re.IGNORECASE,
)


class EmailGapsIngester(Ingester):
    type = "email_gaps"

    def run(self) -> IngestResult:
        observations: list[Observation] = []
        threads = json.loads(self.file_path.read_text())
        for t in threads:
            body = t.get("body") or ""
            subj = t.get("subject") or ""
            full = subj + "\n" + body
            kgs = {f"KG-{m.group(1)}" for m in KG_RE.finditer(full)}
            if not kgs:
                continue
            triggered = bool(BLOCK_TRIGGER_RE.search(full))
            ref = f"thread={t.get('thread_id', '?')}"
            for kg in kgs:
                if triggered:
                    observations.append(Observation(
                        work_id=kg,
                        field="artsy_eligibility",
                        value=f"blocked: see {t.get('from','sender')} {t.get('date','')[:10]}",
                        source_row_ref=ref,
                        confidence="medium",
                    ))
        return IngestResult(
            source=self._make_source(row_count=len(threads)),
            observations=observations,
        )
