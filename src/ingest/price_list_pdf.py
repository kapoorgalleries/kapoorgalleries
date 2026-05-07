"""Ingester for show price-list PDFs.

Two layouts in the wild:

1. **Blossom & Sword** (entry numbers, no KG-#)::

    01.
    Title (bold)
    Period / school / region
    Medium
    Image: H x W in. (cm.)
    Provenance: ...
    $ price

2. **Art of the Himalayas** (entry numbers + KG-# on header line)::

    1. KG-1741 $30,000
    Title, century
    Medium
    H x W in. (cm.)
    Published: ...
    Provenance: ...

Layout 1 entries land in ``UNRESOLVED-*`` (later fuzzy-matched).
Layout 2 entries link to their KG-# directly.
"""

from __future__ import annotations

import re

import pdfplumber

from ..ids import unresolved_id
from ..normalize import normalize_decimal, normalize_price, normalize_title
from ..schema import Observation
from ._base import IngestResult, Ingester

ENTRY_HEADER_RE = re.compile(r"^(\d{1,3})\.\s*$")
# Himalayas variant: "1. KG-1741 $30,000" — number, KG id, optional price.
KG_HEADER_RE = re.compile(
    r"^(\d{1,3})\.\s+(KG-?\d{4})(?:\s+\$\s*([\d,]+))?\s*$"
)
# Width/height: "29 1/4 x 20 in.", "39 ½ x 23 ½ in.", "42 1⁄2 x 27 3⁄4 in."
# (Unicode fraction-slash U+2044 and vulgar fractions ¼½¾⅛⅜⅝⅞.)
DIM_NUM = r"\d+(?:\s*\d[/⁄]\d|\s*[¼½¾⅛⅜⅝⅞]|\.\d+)?"
DIM_RE = re.compile(
    r"(?:(?:Image|Folio)\s*:\s*)?"
    rf"({DIM_NUM})\s*[x×]\s*({DIM_NUM})\s*in",
    re.IGNORECASE,
)
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
                entry_no: str | None = None
                kg_id: str | None = None
                inline_price: str | None = None
                buf: list[str] = []
                for line in lines + [""]:
                    m_kg = KG_HEADER_RE.match(line)
                    m_plain = ENTRY_HEADER_RE.match(line) if not m_kg else None
                    if m_kg or m_plain:
                        if entry_no is not None and buf:
                            observations.extend(self._emit(
                                show, entry_no, kg_id, inline_price, buf, page_no,
                            ))
                        if m_kg:
                            entry_no = m_kg.group(1)
                            kg_id = m_kg.group(2).replace("KG", "KG-").replace("KG--", "KG-")
                            if not kg_id.startswith("KG-"):
                                kg_id = f"KG-{kg_id[2:]}"
                            inline_price = m_kg.group(3)
                        else:
                            entry_no = m_plain.group(1)
                            kg_id = None
                            inline_price = None
                        buf = []
                    else:
                        buf.append(line)
                if entry_no is not None and buf:
                    observations.extend(self._emit(
                        show, entry_no, kg_id, inline_price, buf, page_no,
                    ))
        return IngestResult(
            source=self._make_source(row_count=n_pages),
            observations=observations,
        )

    def _emit(self, show: str, entry_no: str, kg_id: str | None,
              inline_price: str | None, buf: list[str], page_no: int) -> list[Observation]:
        out: list[Observation] = []
        ref = f"page={page_no};entry={entry_no}"
        title = normalize_title(next((b for b in buf if b), ""))
        if not title:
            return out

        # If we have a KG-# from the header, use it as the work_id;
        # else fall back to UNRESOLVED-* keyed by show+entry+title.
        wid = kg_id if kg_id else unresolved_id(show, entry_no, title)

        out.append(Observation(work_id=wid, field="title", value=title, source_row_ref=ref, confidence="medium"))
        if not kg_id:
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
        # Use inline price (Himalayas) if present, otherwise scan body.
        price_str = inline_price or (PRICE_RE.search(body).group(1) if PRICE_RE.search(body) else None)
        if price_str:
            price = normalize_price(price_str)
            if price is not None:
                out.append(Observation(work_id=wid, field="price_usd", value=str(price), source_row_ref=ref, confidence="high"))

        prov_idx = next((i for i, b in enumerate(buf) if b.lower().startswith("provenance")), None)
        if prov_idx is not None:
            prov_text = " ".join(buf[prov_idx:]).strip()
            out.append(Observation(work_id=wid, field="provenance_text", value=prov_text,
                                   source_row_ref=ref, confidence="medium"))
        return out
