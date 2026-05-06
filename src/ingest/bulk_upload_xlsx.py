"""Ingester for the Artsy Bulk Upload Template xlsx.

Schema (note literal newlines in headers — Artsy's quirk):

    Inventory ID \n (OPTIONAL),  Artist Name\n,  Title\n,  Year\n,  Price\n,
    Medium\n, Materials\n, Height\n, Width\n, Depth, Certificate of Authenticity \n,
    Signature\n, Classification \n

This file (110 KB, 1425 rows) covers a wider KG-# range than the Feb 2026
Artsy CSV — so it pulls in works the consolidator hasn't seen before.
"""

from __future__ import annotations

import openpyxl

from ..ids import parse_kg_id
from ..normalize import (
    clean, normalize_artist, normalize_classification, normalize_decimal,
    normalize_price, normalize_title, normalize_year,
)
from ..schema import Observation
from ._base import IngestResult, Ingester

COLUMN_MAP = {
    "Inventory ID (OPTIONAL)": "_id",
    "Artist Name": "artist",
    "Title": "title",
    "Year": "year",
    "Price": "price_usd",
    "Medium": "medium",
    "Materials": "materials",
    "Height": "height_in",
    "Width": "width_in",
    "Depth": "depth_in",
    "Certificate of Authenticity": "coa_status",
    "Signature": "signature",
    "Classification": "classification",
}

NORMALIZERS = {
    "artist": normalize_artist,
    "title": normalize_title,
    "year": normalize_year,
    "price_usd": normalize_price,
    "classification": normalize_classification,
    "medium": clean,
    "materials": clean,
    "height_in": normalize_decimal,
    "width_in": normalize_decimal,
    "depth_in": normalize_decimal,
    "coa_status": clean,
    "signature": clean,
}


class BulkUploadXlsxIngester(Ingester):
    type = "bulk_upload_xlsx"

    def run(self) -> IngestResult:
        observations: list[Observation] = []
        rows_processed = 0
        wb = openpyxl.load_workbook(filename=str(self.file_path), read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        header_raw = next(rows_iter, None) or ()
        # Strip whitespace + newlines from headers; map to canonical fields.
        header = [(c or "").replace("\n", " ").strip().replace("  ", " ") for c in header_raw]

        # Resolve column index per canonical field.
        idx: dict[str, int] = {}
        for i, h in enumerate(header):
            for src, dst in COLUMN_MAP.items():
                if h == src or h.replace(" ", "") == src.replace(" ", ""):
                    idx[dst] = i
                    break

        seen: set[str] = set()
        for r_i, row in enumerate(rows_iter, start=2):
            rows_processed += 1
            if "_id" not in idx or row[idx["_id"]] is None:
                continue
            kg = parse_kg_id(str(row[idx["_id"]]))
            if not kg:
                continue
            seen.add(kg)
            ref = f"row={r_i}"
            for field, ix in idx.items():
                if field == "_id":
                    continue
                raw = row[ix]
                if raw is None:
                    continue
                norm = NORMALIZERS.get(field, clean)(str(raw))
                if norm is None:
                    continue
                observations.append(Observation(
                    work_id=kg, field=field, value=str(norm),
                    source_row_ref=ref, confidence="high",
                ))
            # Seed the work row
            observations.append(Observation(
                work_id=kg, field="status", value="active",
                source_row_ref="seed", confidence="low",
            ))
        wb.close()
        return IngestResult(
            source=self._make_source(row_count=rows_processed),
            observations=observations,
        )
