"""FastAPI application factory for the Kapoor Galleries backend.

Serves the inventory pipeline's JSON feeds as a queryable REST API the
public website (``kapoorgalleries/sb1-vuxiwzek``) consumes.  The feeds
are produced by ``make report`` in this same repo; this layer adds
server-side filtering, search, pagination, and CORS.

Run locally::

    python -m src.cli serve            # or: uvicorn src.api.app:app
    KG_API_DATA_DIR=data uvicorn src.api.app:app --reload

Configuration (env):
    KG_API_DATA_DIR       directory holding the JSON feeds (default: data)
    KG_API_CORS_ORIGINS   comma-separated allowed origins (default: *)
    KG_API_TITLE          OpenAPI title override
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .feeds import FeedStore
from .routers import collections, masterworks, meta, site, works


def _cors_origins() -> list[str]:
    raw = os.environ.get("KG_API_CORS_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


def create_app(data_dir: str | None = None) -> FastAPI:
    """Build the FastAPI app.  ``data_dir`` overrides KG_API_DATA_DIR
    (used by tests to point at a fixture directory)."""
    app = FastAPI(
        title=os.environ.get("KG_API_TITLE", "Kapoor Galleries API"),
        version="1.0.0",
        description=(
            "Public read API for the Kapoor Galleries inventory: works, "
            "collections, masterworks, and site metadata.  Backed by the "
            "inventory pipeline's generated feeds."
        ),
    )

    origins = _cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        # Credentials can't be combined with a wildcard origin per the
        # CORS spec; only enable them when origins are explicit.
        allow_credentials=origins != ["*"],
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )

    # One shared, mtime-cached feed store for the process.
    store = FeedStore(data_dir)
    app.state.store = store

    app.include_router(meta.router)
    app.include_router(works.router)
    app.include_router(collections.router)
    app.include_router(masterworks.router)
    app.include_router(site.router)

    return app


# Module-level app for `uvicorn src.api.app:app`.
app = create_app()
