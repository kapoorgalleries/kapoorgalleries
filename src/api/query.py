"""Query helpers — filtering, searching, sorting, pagination.

Pure functions over the in-memory work lists so they're trivially
testable without spinning up the HTTP layer.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable


# Fields a free-text ``q`` search scans, in priority order.  A match in
# an earlier field ranks higher.
_SEARCH_FIELDS = (
    "title", "kg_id", "artist", "classification", "medium",
    "period_school_region", "provenance", "acquired_from",
)


def text_match_score(work: dict, needle: str) -> int:
    """Score a work against a lowercased search needle.  0 = no match.
    Higher = better (earlier-field and prefix matches win)."""
    if not needle:
        return 0
    best = 0
    for weight, field in zip(range(len(_SEARCH_FIELDS), 0, -1), _SEARCH_FIELDS):
        val = work.get(field)
        if not val:
            continue
        hay = str(val).lower()
        if needle in hay:
            # Prefix / whole-field matches score a touch higher.
            bonus = 2 if hay.startswith(needle) else 0
            best = max(best, weight * 2 + bonus)
    return best


def _as_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def filter_works(
    works: Iterable[dict],
    *,
    classification: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    has_image: bool | None = None,
    available: bool | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
) -> list[dict]:
    """Apply the website's filter set to a work list.  Each filter is
    AND-combined.  ``q`` keeps only works that text-match."""
    needle = (q or "").strip().lower()
    out: list[dict] = []
    for w in works:
        if classification and (w.get("classification") or "") != classification:
            continue
        if tag and tag not in (w.get("tags") or []):
            continue
        if has_image is not None:
            present = bool((w.get("image") or {}).get("primary"))
            if present != has_image:
                continue
        if available is not None:
            avail = bool((w.get("price") or {}).get("available"))
            if avail != available:
                continue
        if year_min is not None or year_max is not None:
            yr = w.get("year")
            if yr is None:
                continue
            if year_min is not None and yr < year_min:
                continue
            if year_max is not None and yr > year_max:
                continue
        if price_min is not None or price_max is not None:
            usd = _as_float((w.get("price") or {}).get("usd"))
            if usd is None:
                continue
            if price_min is not None and usd < price_min:
                continue
            if price_max is not None and usd > price_max:
                continue
        if needle and not text_match_score(w, needle):
            continue
        out.append(w)
    return out


# Allowed sort keys -> (extractor, default-for-missing).  Missing values
# sort last on ascending, first on descending.
_SORT_KEYS: dict[str, Callable[[dict], Any]] = {
    "kg_id": lambda w: w.get("kg_id") or "",
    "title": lambda w: (w.get("title") or "").lower(),
    "year": lambda w: w.get("year"),
    "price": lambda w: _as_float((w.get("price") or {}).get("usd")),
}


def sort_works(works: list[dict], sort: str | None) -> list[dict]:
    """Sort by ``<key>`` or ``-<key>`` (descending).  Unknown keys are
    a no-op (preserves the feed's deterministic order)."""
    if not sort:
        return works
    desc = sort.startswith("-")
    key = sort[1:] if desc else sort
    extractor = _SORT_KEYS.get(key)
    if not extractor:
        return works

    def is_missing(v: Any) -> bool:
        return v is None or v == ""

    # Partition so works with a missing sort value always land at the
    # end — regardless of ascending/descending direction.  Present
    # values are sorted among themselves; missing ones keep feed order.
    present = [w for w in works if not is_missing(extractor(w))]
    missing = [w for w in works if is_missing(extractor(w))]
    present.sort(key=extractor, reverse=desc)
    return present + missing


def paginate(
    items: list[Any], *, page: int = 1, page_size: int = 24,
) -> dict:
    """Return a pagination envelope.  ``page`` is 1-indexed."""
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    pages = (total + page_size - 1) // page_size if total else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
        "items": items[start:end],
    }


def search_ranked(
    works: Iterable[dict], q: str, limit: int = 20,
) -> list[dict]:
    """Rank works by text-match score (descending), drop non-matches."""
    needle = (q or "").strip().lower()
    if not needle:
        return []
    scored = [
        (text_match_score(w, needle), w) for w in works
    ]
    scored = [(s, w) for s, w in scored if s > 0]
    scored.sort(key=lambda t: t[0], reverse=True)
    return [w for _, w in scored[:limit]]
