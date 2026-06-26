"""Tests for the FastAPI backend (src/api).

Uses a tmp fixture data dir so the suite is independent of whatever's
currently committed in data/.
"""

from pathlib import Path

import json

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from src.api.app import create_app  # noqa: E402
from src.api import query  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _work(kg, title, cls=None, tags=None, year=None, usd=None,
          image=True):
    return {
        "id": kg.lower(), "kg_id": kg,
        "slug": f"{kg.lower()}-{title.lower().replace(' ', '-')}",
        "url_path": f"/works/{kg.lower()}",
        "title": title, "classification": cls, "medium": "Gouache",
        "year": year, "year_display": str(year) if year else None,
        "dimensions": {"height_in": None, "width_in": None,
                       "depth_in": None, "display": None},
        "price": {"usd": usd,
                  "display": f"${usd:,}" if usd else "Price on request",
                  "available": usd is not None},
        "image": {"primary": "http://cdn/x.jpg" if image else None,
                  "alternates": [], "thumbnail": None},
        "tags": tags or [],
        "status": "available",
        "_internal": {"primer_uuid": None, "has_conflict": False},
    }


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    works = [
        _work("KG-1", "Krishna and Radha", "Painting",
              ["vishnu", "19th-century"], 1850, 30000),
        _work("KG-2", "Bronze Buddha", "Sculpture",
              ["buddha", "tibetan", "metal"], 1700, 95000),
        _work("KG-3", "A Tara Thangka", "Painting",
              ["tara", "tibetan", "thangka"], None, None, image=False),
        _work("KG-4", "Untitled", "Sculpture", ["stone"], 200, 5000),
    ]
    (tmp_path / "website_inventory_enriched.json").write_text(json.dumps({
        "schema_version": 1, "generated_at": "2026-01-01T00:00:00Z",
        "count": len(works),
        "facets": {
            "classification": [{"value": "Painting", "count": 2},
                               {"value": "Sculpture", "count": 2}],
            "tags": [{"value": "tibetan", "count": 2}],
            "with_image": 3, "without_image": 1,
        },
        "works": works,
    }))
    (tmp_path / "masterworks.json").write_text(json.dumps({
        "schema_version": 1, "generated_at": "2026-01-01T00:00:00Z",
        "count": 2,
        "facets": {"acquired_by": [{"value": "Met", "count": 1}],
                   "tags": [], "with_image": 2, "without_image": 0},
        "works": [
            {"id": "mw-001", "slug": "mw-001-krishna",
             "url_path": "/masterworks/mw-001-krishna",
             "title": "Krishna Revels", "acquired_by": "Met",
             "tags": ["krishna"], "image": {"drive_file_id": None, "url": None}},
            {"id": "mw-002", "slug": "mw-002-shiva",
             "url_path": "/masterworks/mw-002-shiva",
             "title": "Shiva Nataraja", "acquired_by": "Norton Simon Museum",
             "tags": ["shiva"], "image": {"drive_file_id": None, "url": None}},
        ],
    }))
    (tmp_path / "collections.json").write_text(json.dumps({
        "schema_version": 1, "generated_at": "2026-01-01T00:00:00Z",
        "count": 2,
        "collections": [
            {"slug": "himalayan", "title": "Himalayan", "subtitle": None,
             "description": None, "source_catalog": None,
             "url_path": "/collections/himalayan",
             "hero_image": "http://cdn/x.jpg", "include_tags": ["tibetan"],
             "member_count": 2,
             "members": [{"id": "kg-2", "kg_id": "KG-2", "title": "Bronze Buddha",
                          "url_path": "/works/kg-2", "thumbnail": "http://cdn/x.jpg"},
                         {"id": "kg-3", "kg_id": "KG-3", "title": "A Tara Thangka",
                          "url_path": "/works/kg-3", "thumbnail": None}]},
            {"slug": "empty-one", "title": "Empty", "subtitle": None,
             "description": None, "source_catalog": None,
             "url_path": "/collections/empty-one",
             "hero_image": None, "include_tags": [], "member_count": 0,
             "members": []},
        ],
    }))
    (tmp_path / "site.json").write_text(json.dumps({
        "schema_version": 1, "generated_at": "2026-01-01T00:00:00Z",
        "gallery": {"name": "Kapoor Galleries"},
        "json_ld": {"@type": "ArtGallery"},
    }))
    return tmp_path


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(str(data_dir)))


# ---------------------------------------------------------------------------
# meta
# ---------------------------------------------------------------------------


def test_health_reports_feed_counts(client: TestClient):
    r = client.get("/api/health").json()
    assert r["status"] == "ok"
    assert r["feeds"]["works"]["count"] == 4
    assert r["feeds"]["works"]["source"] == "website_inventory_enriched.json"
    assert r["feeds"]["masterworks"]["count"] == 2
    assert r["feeds"]["collections"]["count"] == 2


def test_facets_passthrough(client: TestClient):
    f = client.get("/api/facets").json()
    assert {"value": "Painting", "count": 2} in f["classification"]


# ---------------------------------------------------------------------------
# works
# ---------------------------------------------------------------------------


def test_works_filter_by_classification(client: TestClient):
    r = client.get("/api/works?classification=Painting").json()
    assert r["total"] == 2
    assert all(w["classification"] == "Painting" for w in r["items"])


def test_works_filter_by_tag(client: TestClient):
    r = client.get("/api/works?tag=tibetan").json()
    assert {w["kg_id"] for w in r["items"]} == {"KG-2", "KG-3"}


def test_works_text_search(client: TestClient):
    r = client.get("/api/works?q=krishna").json()
    assert r["total"] == 1
    assert r["items"][0]["kg_id"] == "KG-1"


def test_works_price_and_image_filters(client: TestClient):
    r = client.get("/api/works?price_min=50000").json()
    assert {w["kg_id"] for w in r["items"]} == {"KG-2"}
    r = client.get("/api/works?has_image=false").json()
    assert {w["kg_id"] for w in r["items"]} == {"KG-3"}
    r = client.get("/api/works?available=true").json()
    assert "KG-3" not in {w["kg_id"] for w in r["items"]}


def test_works_year_range(client: TestClient):
    # KG-3 has no year -> excluded by any year filter.
    r = client.get("/api/works?year_min=1800").json()
    assert {w["kg_id"] for w in r["items"]} == {"KG-1"}


def test_works_sort_desc_price_nulls_last(client: TestClient):
    r = client.get("/api/works?sort=-price").json()
    ids = [w["kg_id"] for w in r["items"]]
    # Highest price first; the null-price work sorts last.
    assert ids[0] == "KG-2"
    assert ids[-1] == "KG-3"


def test_works_pagination_envelope(client: TestClient):
    r = client.get("/api/works?page=1&page_size=2").json()
    assert r["page"] == 1 and r["page_size"] == 2
    assert r["total"] == 4 and r["pages"] == 2
    assert r["has_next"] is True and r["has_prev"] is False
    assert len(r["items"]) == 2
    r2 = client.get("/api/works?page=2&page_size=2").json()
    assert r2["has_next"] is False and r2["has_prev"] is True


def test_work_detail_by_slug_kgid_and_404(client: TestClient):
    slug = client.get("/api/works").json()["items"][0]["slug"]
    assert client.get(f"/api/works/{slug}").status_code == 200
    assert client.get("/api/works/kg-2").status_code == 200
    assert client.get("/api/works/KG-2").status_code == 200  # case-insensitive
    assert client.get("/api/works/does-not-exist").status_code == 404


# ---------------------------------------------------------------------------
# collections
# ---------------------------------------------------------------------------


def test_collections_light_omits_members(client: TestClient):
    r = client.get("/api/collections").json()
    assert r["count"] == 2
    assert all("members" not in c for c in r["collections"])
    # hero_image survives the light projection.
    himalayan = next(c for c in r["collections"] if c["slug"] == "himalayan")
    assert himalayan["hero_image"] == "http://cdn/x.jpg"


def test_collections_exclude_empty(client: TestClient):
    r = client.get("/api/collections?include_empty=false").json()
    assert {c["slug"] for c in r["collections"]} == {"himalayan"}


def test_collections_with_members_flag(client: TestClient):
    r = client.get("/api/collections?with_members=true").json()
    himalayan = next(c for c in r["collections"] if c["slug"] == "himalayan")
    assert len(himalayan["members"]) == 2


def test_collection_detail_and_404(client: TestClient):
    r = client.get("/api/collections/himalayan").json()
    assert r["member_count"] == 2
    assert len(r["members"]) == 2
    assert client.get("/api/collections/nope").status_code == 404


# ---------------------------------------------------------------------------
# masterworks
# ---------------------------------------------------------------------------


def test_masterworks_filter_by_institution(client: TestClient):
    r = client.get("/api/masterworks?acquired_by=Met").json()
    assert r["total"] == 1
    assert r["items"][0]["title"] == "Krishna Revels"


def test_masterworks_detail_and_404(client: TestClient):
    assert client.get("/api/masterworks/mw-001-krishna").status_code == 200
    assert client.get("/api/masterworks/mw-999").status_code == 404


# ---------------------------------------------------------------------------
# site
# ---------------------------------------------------------------------------


def test_site_endpoint(client: TestClient):
    r = client.get("/api/site").json()
    assert r["gallery"]["name"] == "Kapoor Galleries"
    assert r["json_ld"]["@type"] == "ArtGallery"


# ---------------------------------------------------------------------------
# query helpers (unit)
# ---------------------------------------------------------------------------


def test_paginate_clamps_page_size():
    env = query.paginate(list(range(10)), page=1, page_size=9999)
    assert env["page_size"] == 200  # clamped to max


def test_paginate_empty():
    env = query.paginate([], page=3, page_size=10)
    assert env["total"] == 0 and env["pages"] == 0
    assert env["has_next"] is False and env["has_prev"] is True


def test_text_match_prefers_title_over_medium():
    a = {"title": "Krishna", "medium": "ink"}
    b = {"title": "ink study", "medium": "Krishna pigment"}
    assert query.text_match_score(a, "krishna") > query.text_match_score(b, "krishna")


# ---------------------------------------------------------------------------
# resilience
# ---------------------------------------------------------------------------


def test_missing_feeds_dont_crash(tmp_path: Path):
    """A data dir with no feeds should still serve (empty) responses."""
    client = TestClient(create_app(str(tmp_path)))
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/works").json()["total"] == 0
    assert client.get("/api/collections").json()["count"] == 0
    assert client.get("/api/site").json() == {}


def test_hot_reload_on_feed_change(data_dir: Path):
    """Editing a feed file (new mtime) is picked up without restart."""
    import os
    import time

    client = TestClient(create_app(str(data_dir)))
    assert client.get("/api/works").json()["total"] == 4

    feed = data_dir / "website_inventory_enriched.json"
    payload = json.loads(feed.read_text())
    payload["works"] = payload["works"][:1]
    payload["count"] = 1
    feed.write_text(json.dumps(payload))
    # Bump mtime in case the rewrite lands in the same filesystem tick.
    future = time.time() + 5
    os.utime(feed, (future, future))

    assert client.get("/api/works").json()["total"] == 1
