"""Masterworks endpoints — museum-accession showcase."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_store
from ..feeds import FeedStore
from ..query import paginate, search_ranked

router = APIRouter(prefix="/api/masterworks", tags=["masterworks"])


@router.get("")
def list_masterworks(
    store: FeedStore = Depends(get_store),
    acquired_by: str | None = Query(
        None, description="Filter by institution, e.g. 'Norton Simon Museum'"),
    tag: str | None = Query(None),
    q: str | None = Query(None, description="Free-text search"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=200),
) -> dict:
    """Paginated list of works the gallery placed in museum collections."""
    works = store.masterworks()
    if acquired_by:
        works = [w for w in works if (w.get("acquired_by") or "") == acquired_by]
    if tag:
        works = [w for w in works if tag in (w.get("tags") or [])]
    if q:
        works = search_ranked(works, q, limit=len(works))
    return paginate(works, page=page, page_size=page_size)


@router.get("/facets")
def masterworks_facets(store: FeedStore = Depends(get_store)) -> dict:
    """Facets block from the masterworks feed (acquired_by + tags)."""
    return store.masterworks_feed().get("facets", {})


@router.get("/{slug}")
def get_masterwork(slug: str, store: FeedStore = Depends(get_store)) -> dict:
    """A single masterwork by slug or id."""
    needle = slug.strip().lower()
    for w in store.masterworks():
        if (w.get("slug", "").lower() == needle
                or w.get("id", "").lower() == needle):
            return w
    raise HTTPException(
        status_code=404, detail=f"No masterwork matching '{slug}'")
