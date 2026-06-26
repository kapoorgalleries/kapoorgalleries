"""Collections endpoints — landing-page groupings."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_store
from ..feeds import FeedStore

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.get("")
def list_collections(
    store: FeedStore = Depends(get_store),
    include_empty: bool = Query(
        True, description="Include collections with 0 members"),
    with_members: bool = Query(
        False, description="Embed each collection's full member list"),
) -> dict:
    """All collections.  By default members are omitted for a light
    index payload (use ``with_members=true`` or the detail endpoint)."""
    colls = store.collections()
    if not include_empty:
        colls = [c for c in colls if c.get("member_count", 0) > 0]
    if not with_members:
        colls = [{k: v for k, v in c.items() if k != "members"} for c in colls]
    return {"count": len(colls), "collections": colls}


@router.get("/{slug}")
def get_collection(slug: str, store: FeedStore = Depends(get_store)) -> dict:
    """A single collection with its full member list."""
    needle = slug.strip().lower()
    for c in store.collections():
        if c.get("slug", "").lower() == needle:
            return c
    raise HTTPException(
        status_code=404, detail=f"No collection matching '{slug}'")
