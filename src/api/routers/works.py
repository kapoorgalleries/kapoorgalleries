"""Works endpoints — the core inventory grid + detail."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_store
from ..feeds import FeedStore
from ..query import filter_works, paginate, sort_works

router = APIRouter(prefix="/api/works", tags=["works"])


@router.get("")
def list_works(
    store: FeedStore = Depends(get_store),
    classification: str | None = Query(None, description="Exact classification match"),
    tag: str | None = Query(None, description="Tag filter (e.g. 'tibetan')"),
    q: str | None = Query(None, description="Free-text search"),
    has_image: bool | None = Query(None),
    available: bool | None = Query(None, description="Only works with a set price"),
    year_min: int | None = Query(None),
    year_max: int | None = Query(None),
    price_min: float | None = Query(None),
    price_max: float | None = Query(None),
    sort: str | None = Query(
        None,
        description="Sort key: kg_id|title|year|price, prefix '-' for desc",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=200),
) -> dict:
    """Paginated, filterable list of available works."""
    works = filter_works(
        store.works(),
        classification=classification, tag=tag, q=q,
        has_image=has_image, available=available,
        year_min=year_min, year_max=year_max,
        price_min=price_min, price_max=price_max,
    )
    works = sort_works(works, sort)
    return paginate(works, page=page, page_size=page_size)


@router.get("/{slug}")
def get_work(slug: str, store: FeedStore = Depends(get_store)) -> dict:
    """A single work by slug, KG-#, or id (case-insensitive)."""
    needle = slug.strip().lower()
    for w in store.works():
        if (w.get("slug", "").lower() == needle
                or w.get("kg_id", "").lower() == needle
                or w.get("id", "").lower() == needle):
            return w
    raise HTTPException(status_code=404, detail=f"No work matching '{slug}'")
