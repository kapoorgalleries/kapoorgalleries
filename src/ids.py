"""KG-#### parsing and fuzzy matching utilities."""

from __future__ import annotations

import hashlib
import re
from typing import Iterable, Optional

from rapidfuzz import fuzz, process

KG_RE = re.compile(r"\bKG[-\s]?(\d{3,5})\b", re.IGNORECASE)


def parse_kg_id(text: str | None) -> Optional[str]:
    """Find the first KG-#### in `text` and return canonical 'KG-####'."""
    if not text:
        return None
    m = KG_RE.search(text)
    return f"KG-{m.group(1)}" if m else None


def unresolved_id(*parts: str) -> str:
    """Stable synthetic id for sources that don't carry a KG-#."""
    h = hashlib.sha1("||".join(p or "" for p in parts).encode()).hexdigest()[:10]
    return f"UNRESOLVED-{h}"


def fuzzy_match_title(
    needle: str, haystack: Iterable[tuple[str, str]], min_score: int = 80
) -> Optional[tuple[str, int]]:
    """Match `needle` against (work_id, title) candidates; return (work_id, score) or None."""
    if not needle:
        return None
    titles = [t for _, t in haystack if t]
    if not titles:
        return None
    by_title = {t: w for w, t in haystack if t}
    res = process.extractOne(needle, titles, scorer=fuzz.WRatio)
    if not res:
        return None
    title, score, _ = res
    if score < min_score:
        return None
    return by_title[title], int(score)
