"""Smoke test for the Textile Boxes ingester."""

from src.ingest.textile_boxes import TextileBoxesIngester


def test_textile_boxes_extracts_six_boxes():
    """The committed Textile_Boxes_2022-07.docx fixture has 6 boxes
    (1, 2, 3, 4, 5 'never opened', 6 'Malian Hunter's Shirts').  Box 5
    omits the colon — the parser must still pick it up."""
    r = TextileBoxesIngester(
        "data/raw/Textile_Boxes_2022-07.docx"
    ).run()
    titles = sorted(o.value for o in r.observations if o.field == "title")
    nums = [int(t.split()[1].rstrip(":")) for t in titles]
    assert nums == [1, 2, 3, 4, 5, 6], titles

    # Every box should get classification=Textile Arts.
    classifications = [
        o.value for o in r.observations if o.field == "classification"
    ]
    assert classifications and all(c == "Textile Arts" for c in classifications)


def test_textile_boxes_records_external_id():
    r = TextileBoxesIngester(
        "data/raw/Textile_Boxes_2022-07.docx"
    ).run()
    extids = sorted(
        o.value for o in r.observations if o.field == "external_id"
    )
    assert extids == [f"Box-{i}" for i in (1, 2, 3, 4, 5, 6)]
    systems = {
        o.value for o in r.observations if o.field == "external_id_system"
    }
    assert systems == {"Textile Boxes 2022-07"}
