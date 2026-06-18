"""Ingester for the Primer→Artsy CSV export (e.g. ``Artsy_2-16-2026.csv``).

Schema (header row from the Feb 2026 export):

    Work_Number,Work_Artist,Work_Title,Work_Year,Work_Price,Work_Type,
    Work_Medium,I_Iinfo::D__Height,I_Iinfo::D__Width,I_Iinfo::D__Depth,
    I_Imgs::URL_public

FileMaker exports use ``Table::field`` namespacing. Multi-image works produce
extra rows where only ``I_Imgs::URL_public`` is populated and every other
column is blank — those rows belong to the *previous* KG-#.
"""

from __future__ import annotations

import csv
from typing import Optional

from ..ids import parse_kg_id
from ..normalize import (
    clean, normalize_artist, normalize_classification, normalize_decimal,
    normalize_price, normalize_title, normalize_year,
)
from ..schema import Observation, WorkImage
from ._base import IngestResult, Ingester

# Map Artsy export column -> canonical observation field.
COLUMN_MAP: dict[str, str] = {
    "Work_Artist": "artist",
    "Work_Title": "title",
    "Work_Year": "year",
    "Work_Price": "price_usd",
    "Work_Type": "classification",
    "Work_Medium": "medium",
    "I_Iinfo::D__Height": "height_in",
    "I_Iinfo::D__Width": "width_in",
    "I_Iinfo::D__Depth": "depth_in",
}

NORMALIZERS = {
    "artist": normalize_artist,
    "title": normalize_title,
    "year": normalize_year,
    "price_usd": normalize_price,
    "classification": normalize_classification,
    "medium": clean,
    "height_in": normalize_decimal,
    "width_in": normalize_decimal,
    "depth_in": normalize_decimal,
}


def _strip_primer_uuid(url: str) -> Optional[str]:
    """Pull the primer UUID out of a primerws.com URL.

    >>> _strip_primer_uuid("https://data-us-east-1.primerws.com/kapoor_galleries/i/abc-123/foo.jpg?...")
    'abc-123'
    """
    import re
    m = re.search(r"/i/([0-9a-f-]{8,})/", url)
    return m.group(1) if m else None


class ArtsyCsvIngester(Ingester):
    type = "artsy_csv"

    def run(self) -> IngestResult:
        observations: list[Observation] = []
        images: list[WorkImage] = []
        current_kg: Optional[str] = None
        seen_works: set[str] = set()
        rows_processed = 0

        with self.file_path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            # FileMaker exports often pad column names with trailing whitespace.
            reader.fieldnames = [(c or "").strip() for c in (reader.fieldnames or [])]
            for i, row in enumerate(reader, start=2):  # data rows start at line 2
                rows_processed += 1
                # Strip whitespace from every value once.
                row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
                kg = parse_kg_id(row.get("Work_Number") or "")
                if kg:
                    current_kg = kg
                    seen_works.add(kg)
                if not current_kg:
                    continue

                # Field observations (only when the column is populated).
                for col, field in COLUMN_MAP.items():
                    raw = row.get(col)
                    if raw is None:
                        continue
                    norm = NORMALIZERS[field](raw)
                    if norm is None:
                        continue
                    observations.append(Observation(
                        work_id=current_kg,
                        field=field,
                        value=str(norm),
                        source_row_ref=f"line={i}",
                        confidence="high",
                    ))

                # Image URL → image record + primary_image_url + primer_uuid.
                url = clean(row.get("I_Imgs::URL_public") or "")
                if url:
                    images.append(WorkImage(
                        work_id=current_kg,
                        image_url=url,
                        is_placeholder=False,
                    ))
                    # Only the FIRST image row for a work sets primary_image_url.
                    is_first_image_for_work = (
                        kg is not None
                        and not any(
                            o for o in observations
                            if o.work_id == current_kg and o.field == "primary_image_url"
                        )
                    )
                    if is_first_image_for_work:
                        observations.append(Observation(
                            work_id=current_kg,
                            field="primary_image_url",
                            value=url,
                            source_row_ref=f"line={i}",
                            confidence="high",
                        ))
                        uuid = _strip_primer_uuid(url)
                        if uuid:
                            observations.append(Observation(
                                work_id=current_kg,
                                field="primer_uuid",
                                value=uuid,
                                source_row_ref=f"line={i}",
                                confidence="high",
                            ))

        source = self._make_source(row_count=rows_processed)
        # Add a placeholder observation per seen work so consolidate.py creates a row.
        for w in sorted(seen_works):
            observations.append(Observation(
                work_id=w, field="status", value="active",
                source_row_ref="seed", confidence="low",
            ))
        return IngestResult(source=source, observations=observations, images=images)
