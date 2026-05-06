from src.ids import parse_kg_id, unresolved_id, fuzzy_match_title


def test_parse_kg_id_canonical():
    assert parse_kg_id("KG-1042") == "KG-1042"
    assert parse_kg_id(" KG 1042 ") == "KG-1042"
    assert parse_kg_id("kg-1042") == "KG-1042"
    assert parse_kg_id("Inventory KG-9999 — Title") == "KG-9999"


def test_parse_kg_id_misses():
    assert parse_kg_id(None) is None
    assert parse_kg_id("") is None
    assert parse_kg_id("no number here") is None


def test_unresolved_id_is_stable():
    a = unresolved_id("graham", "12", "Krishna")
    b = unresolved_id("graham", "12", "Krishna")
    assert a == b
    assert a.startswith("UNRESOLVED-")


def test_fuzzy_match_title():
    res = fuzzy_match_title(
        "Composite Horse and Rider",
        [("KG-1001", "Composite Camel and Rider"), ("KG-1002", "Folio from a Series")],
        min_score=70,
    )
    assert res is not None
    wid, score = res
    assert wid == "KG-1001"
    assert score >= 70
