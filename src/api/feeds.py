"""Feed store — loads the pipeline's JSON feeds with mtime-based caching.

The backend serves the static artifacts the inventory pipeline writes
into ``data/`` (``website_inventory_enriched.json``, ``masterworks.json``,
``collections.json``, ``site.json``).  Rather than re-read + re-parse on
every request, ``FeedStore`` caches parsed JSON keyed by path and
reloads only when the file's mtime changes — so ``make report`` in the
same checkout is picked up live without a server restart.

Data directory is configurable via the ``KG_API_DATA_DIR`` env var
(default ``data``) so the same code serves a committed checkout, a
mounted volume, or a test fixture dir.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any


# Canonical feed filenames the pipeline emits.
WORKS_ENRICHED = "website_inventory_enriched.json"
WORKS_BASE = "website_inventory.json"
MASTERWORKS = "masterworks.json"
COLLECTIONS = "collections.json"
SITE = "site.json"


class FeedStore:
    """Thread-safe, mtime-aware cache over the pipeline's JSON feeds."""

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self.data_dir = Path(
            data_dir or os.environ.get("KG_API_DATA_DIR", "data")
        )
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    # -- low-level -----------------------------------------------------

    def _path(self, name: str) -> Path:
        return self.data_dir / name

    def _load(self, name: str) -> Any | None:
        """Return parsed JSON for ``name``, or None if the file is
        absent.  Caches by mtime; reparse only on change."""
        p = self._path(name)
        try:
            mtime = p.stat().st_mtime
        except FileNotFoundError:
            return None
        with self._lock:
            cached = self._cache.get(name)
            if cached and cached[0] == mtime:
                return cached[1]
        # Parse outside the lock — parsing a 1.6 MB feed shouldn't block
        # other readers.  Worst case two threads parse on a cold cache.
        data = json.loads(p.read_text())
        with self._lock:
            self._cache[name] = (mtime, data)
        return data

    # -- feed accessors ------------------------------------------------

    def works_feed(self) -> dict:
        """The works feed — prefers the enriched variant, falls back to
        the base feed, then to an empty envelope."""
        feed = self._load(WORKS_ENRICHED)
        if feed is None:
            feed = self._load(WORKS_BASE)
        return feed or _empty_works()

    def works(self) -> list[dict]:
        return self.works_feed().get("works", [])

    def masterworks_feed(self) -> dict:
        return self._load(MASTERWORKS) or _empty_works()

    def masterworks(self) -> list[dict]:
        return self.masterworks_feed().get("works", [])

    def collections_feed(self) -> dict:
        return self._load(COLLECTIONS) or {"count": 0, "collections": []}

    def collections(self) -> list[dict]:
        return self.collections_feed().get("collections", [])

    def site(self) -> dict:
        return self._load(SITE) or {}

    # -- diagnostics ---------------------------------------------------

    def status(self) -> dict:
        """Health payload: which feeds are present, their counts and
        generated_at timestamps."""
        works_feed = self.works_feed()
        # Did the enriched feed actually load, or did we fall back?
        enriched_present = self._path(WORKS_ENRICHED).exists()
        return {
            "data_dir": str(self.data_dir),
            "feeds": {
                "works": {
                    "present": bool(works_feed.get("works")),
                    "source": (WORKS_ENRICHED if enriched_present
                               else WORKS_BASE),
                    "count": works_feed.get("count", 0),
                    "generated_at": works_feed.get("generated_at"),
                },
                "masterworks": {
                    "present": self._path(MASTERWORKS).exists(),
                    "count": self.masterworks_feed().get("count", 0),
                    "generated_at": self.masterworks_feed().get("generated_at"),
                },
                "collections": {
                    "present": self._path(COLLECTIONS).exists(),
                    "count": self.collections_feed().get("count", 0),
                    "generated_at": self.collections_feed().get("generated_at"),
                },
                "site": {
                    "present": self._path(SITE).exists(),
                    "generated_at": self.site().get("generated_at"),
                },
            },
        }


def _empty_works() -> dict:
    return {
        "schema_version": 1,
        "generated_at": None,
        "count": 0,
        "facets": {"classification": [], "tags": [],
                   "with_image": 0, "without_image": 0},
        "works": [],
    }
