"""Site-metadata endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_store
from ..feeds import FeedStore

router = APIRouter(prefix="/api/site", tags=["site"])


@router.get("")
def get_site(store: FeedStore = Depends(get_store)) -> dict:
    """Gallery-wide metadata: name, address, hours, contact, social,
    navigation, and the pre-built JSON-LD block for SEO."""
    return store.site()
