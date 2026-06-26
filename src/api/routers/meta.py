"""Health, root, and facet endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_store
from ..feeds import FeedStore

router = APIRouter(tags=["meta"])


@router.get("/")
def root() -> dict:
    """API index — lists the available top-level routes."""
    return {
        "name": "Kapoor Galleries API",
        "version": "1.0.0",
        "endpoints": [
            "/api/health",
            "/api/works",
            "/api/works/{slug}",
            "/api/facets",
            "/api/collections",
            "/api/collections/{slug}",
            "/api/masterworks",
            "/api/masterworks/{slug}",
            "/api/site",
            "/docs",
        ],
    }


@router.get("/api/health")
def health(store: FeedStore = Depends(get_store)) -> dict:
    """Liveness + feed-presence report.  Always 200 so a load balancer
    can hit it; inspect ``feeds`` for whether data is actually loaded."""
    return {"status": "ok", **store.status()}


@router.get("/api/facets")
def facets(store: FeedStore = Depends(get_store)) -> dict:
    """Pre-computed filter facets (classification + tag counts) from the
    works feed — so the website can build dropdowns without scanning."""
    return store.works_feed().get("facets", {})
