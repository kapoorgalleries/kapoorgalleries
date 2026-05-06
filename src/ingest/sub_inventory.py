"""Ingester for sub-inventory PDFs (Graham, Darion, Huc, Torr, etc.).

These rarely contain KG-#s. We extract entries with whatever id system they
use, store them under ``UNRESOLVED-<sha1>`` work_ids, and let consolidate.py /
gaps.csv surface them for human title-fuzzy matching against KG-# records.
"""

from __future__ import annotations

import re

import pdfplumber

from ..ids import unresolved_id
from ..normalize import normalize_title
from ..schema import Observation
from ._base import IngestResult, Ingester

# Most sub-inventories number entries 1., 2., 3. or "No. 12" or "001."
ENTRY_RE = re.compile(r"^(?:No\.?\s*)?(\d{1,4})[.)]\s+(.+)$")


class SubInventoryIngester(Ingester):
    type = "sub_inventory"

    def run(self) -> IngestResult:
        observations: list[Observation] = []
        n_pages = 0
        with pdfplumber.open(str(self.file_path)) as pdf:
            collection = self.file_path.stem.replace("_", " ")
            for page_no, page in enumerate(pdf.pages, start=1):
                n_pages += 1
                text = page.extract_text() or ""
                for line in text.splitlines():
                    m = ENTRY_RE.match(line.strip())
                    if not m:
                        continue
                    extid = m.group(1).strip()
                    title = normalize_title(m.group(2))
                    if not title:
                        continue
                    work_id = unresolved_id(collection, extid, title)
                    ref = f"page={page_no}"
                    observations.append(Observation(
                        work_id=work_id, field="title", value=title,
                        source_row_ref=ref, confidence="low",
                    ))
                    observations.append(Observation(
                        work_id=work_id, field="external_id", value=extid,
                        source_row_ref=ref, confidence="high",
                    ))
                    observations.append(Observation(
                        work_id=work_id, field="external_id_system", value=collection,
                        source_row_ref=ref, confidence="high",
                    ))
        return IngestResult(
            source=self._make_source(row_count=n_pages),
            observations=observations,
        )
