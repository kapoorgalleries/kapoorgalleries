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

# Numeric-prefix style: "1) Title", "001) Title", "No. 12) Title".
# We require `)` rather than `.` because real inventory entries use ")"
# (e.g. Darion: "74) Persian. ..."), while ".N" is more often a plate
# caption / footnote / list-of-figures reference and produces noise
# when treated as an inventory line.
ENTRY_RE = re.compile(r"^(?:No\.?\s*)?(\d{1,4})\)\s+(.+)$")

# Letter-prefix-id style (Graham, Darion, Huc): "G40502 Akeley, Clar E. Stung, 1914".
# We capture the id and the full remainder; splitting "artist, title" reliably
# would need a per-collection name dictionary, so for now we emit the
# combined string as a single low-confidence `title` and leave artist
# extraction to a future pass.
LETTER_ID_RE = re.compile(r"^([A-Z]\d{4,6})\s+(.+)$")
# Trailing year — "Title, 1914" or "Title, c. 1875" or "Title, c. 1930-31".
YEAR_RE = re.compile(r",\s*(?:c\.?\s*)?(\d{4})(?:-\d+)?\s*$")
HEADER_TOKENS = {"inventory", "page", "media", "location", "partners",
                 "% owned", "gallery cost"}


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
                    line = line.strip()
                    if not line:
                        continue
                    if line.lower() in HEADER_TOKENS:
                        continue
                    extid: str | None = None
                    title: str | None = None

                    m = LETTER_ID_RE.match(line)
                    if m:
                        extid = m.group(1)
                        title = m.group(2)
                    else:
                        m = ENTRY_RE.match(line)
                        if m:
                            extid = m.group(1)
                            title = m.group(2)
                    if not extid or not title:
                        continue
                    title = normalize_title(title)
                    if not title:
                        continue

                    # Pull a trailing year out of the title if present.
                    year: str | None = None
                    ym = YEAR_RE.search(title)
                    if ym:
                        year = ym.group(1)
                        title = title[: ym.start()].strip().rstrip(",").strip()

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
                    if year:
                        observations.append(Observation(
                            work_id=work_id, field="year", value=year,
                            source_row_ref=ref, confidence="medium",
                        ))
        return IngestResult(
            source=self._make_source(row_count=n_pages),
            observations=observations,
        )
