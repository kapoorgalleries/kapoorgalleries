"""Verify the Artsy Bulk Upload xlsx ingester routes columns correctly."""

from pathlib import Path

import openpyxl

from src.ingest.bulk_upload_xlsx import BulkUploadXlsxIngester


def _build_xlsx(tmp_path: Path) -> Path:
    p = tmp_path / "bulk.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "Inventory ID \n (OPTIONAL)", "Artist Name\n", "Title\n", "Year\n",
        "Price\n", "Medium\n", "Materials\n", "Height\n", "Width\n", "Depth",
        "Certificate of Authenticity\n", "Signature\n", "Classification\n",
    ])
    # KG-A: paper work — Excel parsed "11,125" as 11125 (decimal recovery).
    ws.append([
        "KG-A", "Unknown Artist", "A Test", 1850, None,
        "Drawing, Collage or other Work on Paper",  # this column is classification!
        "Opaque watercolor on paper",                # this column is medium!
        " ",          # height — blank
        11125.0,      # width — should recover to 11.125
        None, None, "No signature", None,
    ])
    # KG-B: a sculpture — small dimensions stay as-is.
    ws.append([
        "KG-B", "Unknown Artist", "A Sculpture", None, 50000,
        "Sculpture", "Sandstone", 40, 26, 12, None, None, None,
    ])
    wb.save(p)
    return p


def test_bulk_upload_routes_medium_to_classification(tmp_path: Path):
    p = _build_xlsx(tmp_path)
    res = BulkUploadXlsxIngester(p).run()
    by_field = {(o.work_id, o.field): o.value for o in res.observations}

    # The xlsx "Medium" column held the Artsy classification — should land in classification.
    assert by_field[("KG-A", "classification")] == "Drawing, Collage or other Work on Paper"
    # The xlsx "Materials" column held the actual medium — should land in medium.
    assert by_field[("KG-A", "medium")] == "Opaque watercolor on paper"


def test_bulk_upload_recovers_european_decimal_dimensions(tmp_path: Path):
    p = _build_xlsx(tmp_path)
    res = BulkUploadXlsxIngester(p).run()
    by_field = {(o.work_id, o.field): o.value for o in res.observations}

    # 11125 (Excel parsed "11,125" as integer) recovered to 11.125
    assert by_field[("KG-A", "width_in")] == "11.125"
    # Sculpture's small dimensions stay as-is
    assert by_field[("KG-B", "height_in")] == "40.0"
    assert by_field[("KG-B", "width_in")] == "26.0"
    assert by_field[("KG-B", "depth_in")] == "12.0"


def test_bulk_upload_classification_taxonomy_is_normalized(tmp_path: Path):
    p = _build_xlsx(tmp_path)
    res = BulkUploadXlsxIngester(p).run()
    by_field = {(o.work_id, o.field): o.value for o in res.observations}

    assert by_field[("KG-B", "classification")] == "Sculpture"
