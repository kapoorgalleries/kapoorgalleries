"""Ingest the printed KG inventory PDF (e.g. ``KG Inventory - 9-25-2025.pdf``).

This is the 172 MB book-style export the gallery referred to as "primer pages".
Pages are page-streamed; never load the whole PDF into memory.

Each entry on a page typically looks like:

    KG-####    Title in title case
               Artist or "Unknown Artist"
               Period / school / region, century
               Medium
               H × W (× D) in.
               $ price

Parsing is heuristic and emits low-confidence observations. Conflicts with the
Artsy CSV (Primer-derived) will be flagged in the Sheet for human review.
"""

from __future__ import annotations

import re
from typing import Iterator

import pdfplumber

from ..ids import KG_RE, parse_kg_id
from ..normalize import (
    clean, normalize_classification, normalize_decimal, normalize_price,
    normalize_title, normalize_year,
)
from ..schema import Observation
from ._base import IngestResult, Ingester

# H × W (× D) in inches, fractions allowed.
DIM_RE = re.compile(
    r"(\d+(?:\s*\d/\d)?(?:\.\d+)?)\s*[×x]\s*(\d+(?:\s*\d/\d)?(?:\.\d+)?)"
    r"(?:\s*[×x]\s*(\d+(?:\s*\d/\d)?(?:\.\d+)?))?\s*in",
    re.IGNORECASE,
)
PRICE_RE = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)")
YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")


def _split_into_entries(text: str) -> Iterator[tuple[str, str]]:
    """Split a page's text into (kg_id, entry_text) chunks."""
    pos = 0
    matches = list(KG_RE.finditer(text))
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end]
        kg = parse_kg_id(chunk[:20])
        if kg:
            yield kg, chunk


class KGInventoryPdfIngester(Ingester):
    type = "kg_inventory_pdf"

    def run(self) -> IngestResult:
        observations: list[Observation] = []
        pages_seen = 0
        with pdfplumber.open(str(self.file_path)) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                pages_seen += 1
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                for kg, entry in _split_into_entries(text):
                    ref = f"page={page_no}"
                    obs = self._parse_entry(kg, entry, ref)
                    observations.extend(obs)
        return IngestResult(
            source=self._make_source(row_count=pages_seen),
            observations=observations,
        )

    def _parse_entry(self, kg: str, entry: str, ref: str) -> list[Observation]:
        out: list[Observation] = []

        # Title: first non-KG line that looks like sentence/title case.
        lines = [ln.strip() for ln in entry.splitlines() if ln.strip()]
        # Drop the KG-#### token from the first line.
        if lines:
            lines[0] = re.sub(r"^KG[-\s]?\d{3,5}\s*", "", lines[0]).strip()
        title = next((ln for ln in lines[:3] if ln and not ln.startswith("$")), None)
        title = normalize_title(title)
        if title:
            out.append(Observation(work_id=kg, field="title", value=title, source_row_ref=ref, confidence="low"))

        # Year (first 4-digit year in 1500–2099).
        ym = YEAR_RE.search(entry)
        if ym:
            year = normalize_year(ym.group(1))
            if year:
                out.append(Observation(work_id=kg, field="year", value=str(year), source_row_ref=ref, confidence="low"))

        # Dimensions.
        dm = DIM_RE.search(entry)
        if dm:
            for field, val in (("height_in", dm.group(1)), ("width_in", dm.group(2)), ("depth_in", dm.group(3))):
                f = normalize_decimal(val) if val else None
                if f is not None:
                    out.append(Observation(work_id=kg, field=field, value=str(f), source_row_ref=ref, confidence="low"))

        # Price.
        pm = PRICE_RE.search(entry)
        if pm:
            price = normalize_price(pm.group(1))
            if price is not None:
                out.append(Observation(work_id=kg, field="price_usd", value=str(price), source_row_ref=ref, confidence="low"))

        # Classification keyword guess.
        for kw, cls in (("painting", "Painting"), ("sculpture", "Sculpture"),
                        ("drawing", "Drawing, Collage or other Work on Paper"),
                        ("manuscript", "Other"), ("textile", "Textile Arts"),
                        ("dagger", "Design/Decorative Art"), ("khanjar", "Design/Decorative Art")):
            if kw in entry.lower():
                out.append(Observation(work_id=kg, field="classification", value=cls, source_row_ref=ref, confidence="low"))
                break

        return out


# Primer-style (per-page object) PDFs share the same parser.
class PrimerPdfIngester(KGInventoryPdfIngester):
    type = "primer_pdf"
