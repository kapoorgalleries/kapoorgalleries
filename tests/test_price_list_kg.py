"""Smoke tests for the Himalayas-style price list parser."""

from src.ingest.price_list_pdf import PriceListPdfIngester


def test_himalayas_price_list_links_kg_numbers():
    """KG-# from the entry header line should land directly on
    the KG- work_id (not UNRESOLVED-*) and pull in price + dims."""
    r = PriceListPdfIngester(
        "data/raw/KG_Art_of_the_Himalayas_Price_List.pdf"
    ).run()
    works = sorted({o.work_id for o in r.observations})
    # Twelve KG-# entries in this list, all should bind directly.
    kg_works = [w for w in works if w.startswith("KG-")]
    assert len(kg_works) == 12, kg_works

    by_w = {}
    for o in r.observations:
        by_w.setdefault(o.work_id, {})[o.field] = o.value

    # Spot-check KG-1741: Vajrapani, $30,000, 29 1/4 x 20 in.
    rec = by_w["KG-1741"]
    assert rec.get("price_usd") == "30000.0"
    assert rec.get("height_in") == "29.25"
    assert rec.get("width_in") == "20.0"
    # KG-1812 uses unicode fraction-slash "42 1⁄2" — must parse to 42.5.
    rec = by_w["KG-1812"]
    assert rec.get("height_in") == "42.5"
    assert rec.get("width_in") == "27.75"


def test_normalize_decimal_handles_mixed_fractions():
    """Regression: '29 1/4' was being parsed as 291.0 because the
    space was stripped before the regex matched the integer part."""
    from src.normalize import normalize_decimal
    assert normalize_decimal("29 1/4") == 29.25
    assert normalize_decimal("8 1/2") == 8.5
    assert normalize_decimal("39 ½") == 39.5
    assert normalize_decimal("42 1⁄2") == 42.5
    # Plain numbers still work.
    assert normalize_decimal("23.625") == 23.625
    assert normalize_decimal("17") == 17.0
