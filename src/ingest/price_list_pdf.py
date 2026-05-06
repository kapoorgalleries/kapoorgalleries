"""Ingester for show price-list PDFs (e.g. ``Blossom & Sword Price List``).

Expected entry shape (per the Blossom & Sword reference):

    01.   Title (bold)
          Period / school / region
          Medium
          Image: H x W in. (cm.)
          [Folio: H x W in. (cm.)]
          Provenance: ...
          $ price

Entries lack KG-# IDs, so we land them in ``UNRESOLVED-*`` and let a future
title-fuzzy-match step assign them to KG-#s.
"""

from __future__ import annotations

import re

import pdfplumber

from ..ids import unresolved_id
from ..normalize import normalize_decimal, normalize_price, normalize_title
from ..schema import Observation
from ._base import IngestResult, Ingester

ENTRY_HEADER_RE = re.compile(r"^(\d{1,3})\.\s*$")
DIM_RE = re.compile(r"(?:Image|Folio)\s*:\s*(\d+(?:\s*\d/\d)?)\s*[x×]\s*(\d+(?:\s*\d/\d)?)\s*in", re.IGNORECASE)
PRICE_RE = re.compile(r"\$\s*([\d,]+)")


class PriceListPdfIngester(Ingester):
    type = "price_list_pdf"

    def run(self) -> IngestResult:
        observations: list[Observation] = []
        n_pages = 0
        show = self.file_path.stem
        with pdfplumber.open(str(self.file_path)) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                n_pages += 1
                text = page.extract_text() or ""
                lines = [ln.strip() for ln in text.splitlines()]
                # Walk the lines, splitting on entry headers.
                entry_no = None
                buf: list[str] = []
                for line in lines + [""]:
                    m = ENTRY_HEADER_RE.match(line)
                    if m:
                        if entry_no is not None and buf:
                            observations.extend(self._emit(show, entry_no, buf, page_no))
                        entry_no = m.group(1)
                        buf = []
                    else:
                        buf.append(line)
                if entry_no is not None and buf:
                    observations.extend(self._emit(show, entry_no, buf, page_no))
        return IngestResult(
            source=self._make_source(row_count=n_pages),
            observations=observations,
        )

    def _emit(self, show: str, entry_no: str, buf: list[str], page_no: int) -> list[Observation]:
        out: list[Observation] = []
        ref = f"page={page_no};entry={entry_no}"
        title = normalize_title(next((b for b in buf if b), ""))
        if not title:
            return out
        wid = unresolved_id(show, entry_no, title)

        out.append(Observation(work_id=wid, field="title", value=title, source_row_ref=ref, confidence="medium"))
        out.append(Observation(work_id=wid, field="external_id", value=entry_no, source_row_ref=ref, confidence="high"))
        out.append(Observation(work_id=wid, field="external_id_system", value=show, source_row_ref=ref, confidence="high"))
        out.append(Observation(work_id=wid, field="exhibitions", value=show, source_row_ref=ref, confidence="medium"))

        body = "\n".join(buf)
        dm = DIM_RE.search(body)
        if dm:
            for field, val in (("height_in", dm.group(1)), ("width_in", dm.group(2))):
                f = normalize_decimal(val)
                if f is not None:
                    out.append(Observation(work_id=wid, field=field, value=str(f), source_row_ref=ref, confidence="medium"))
        pm = PRICE_RE.search(body)
        if pm:
            price = normalize_price(pm.group(1))
            if price is not None:
                out.append(Observation(work_id=wid, field="price_usd", value=str(price), source_row_ref=ref, confidence="high"))

        prov_idx = next((i for i, b in enumerate(buf) if b.lower().startswith("provenance")), None)
        if prov_idx is not None:
            prov_text = " ".join(buf[prov_idx:]).strip()
            out.append(Observation(work_id=wid, field="provenance_text", value=prov_text,
                                   source_row_ref=ref, confidence="medium"))
        return out
