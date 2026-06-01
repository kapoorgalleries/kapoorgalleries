from src.normalize import (
    clean, normalize_artist, normalize_classification, normalize_decimal,
    normalize_price, normalize_title, normalize_year,
)


def test_clean():
    assert clean(" foo ") == "foo"
    assert clean("") is None
    assert clean(None) is None
    assert clean("Unknown") is None
    assert clean("nan") is None


def test_normalize_artist_strips_unknown():
    assert normalize_artist("Unknown Artist") is None
    assert normalize_artist("Anonymous") is None
    assert normalize_artist("Nainsukh") == "Nainsukh"


def test_normalize_decimal_handles_european_format():
    assert normalize_decimal("8,5") == 8.5
    assert normalize_decimal("11.125") == 11.125
    assert normalize_decimal("") is None


def test_normalize_year():
    assert normalize_year("c. 1850") == 1850
    assert normalize_year("1850") == 1850
    assert normalize_year("1701") == 1701
    assert normalize_year("nope") is None


def test_normalize_price_strips_currency():
    assert normalize_price("$35,000") == 35000.0
    assert normalize_price("12000 USD") == 12000.0


def test_normalize_classification_maps():
    assert normalize_classification("Painting") == "Painting"
    assert (
        normalize_classification("Drawing, Collage or other Work on Paper")
        == "Drawing, Collage or other Work on Paper"
    )


def test_normalize_title_collapses_whitespace():
    assert normalize_title("  Hello   World .") == "Hello World"


def test_normalize_title_strips_trailing_comma():
    # price_list_pdf and bulk_upload disagreed only on a trailing comma.
    assert normalize_title("Vajrapani, Hayagriva, Garuda combined,") == \
        "Vajrapani, Hayagriva, Garuda combined"


def test_clean_unescapes_bracket_artifacts():
    # Primer's Artsy CSV escapes square brackets; bulk-upload doesn't.
    assert clean(r"\[FAKE\] Krishna and Ladies") == "[FAKE] Krishna and Ladies"
    assert normalize_title(r"\[FAKE?\] A Prince on Horseback") == \
        "[FAKE?] A Prince on Horseback"


def test_clean_normalizes_space_around_newline():
    # Two sources placed the spaces differently around the line break;
    # both should normalize to the same string so they stop conflicting.
    a = clean("Opaque watercolor on paper  \nCalligraphy panel on verso")
    b = clean("Opaque watercolor on paper\n Calligraphy panel on verso")
    assert a == b == "Opaque watercolor on paper\nCalligraphy panel on verso"
