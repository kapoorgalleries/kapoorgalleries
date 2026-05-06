"""Field normalizers.

Every ingester produces TEXT observations. The consolidator parses types when
building the canonical `works` row. Normalizers here clean cosmetic noise so
two sources are more likely to agree.
"""

from __future__ import annotations

import re
from typing import Optional

DIM_FRACTIONS = {
    "1/8": 0.125, "1/4": 0.25, "3/8": 0.375, "1/2": 0.5,
    "5/8": 0.625, "3/4": 0.75, "7/8": 0.875, "1/3": 0.333, "2/3": 0.667,
}

CLASSIFICATION_MAP = {
    "painting": "Painting",
    "sculpture": "Sculpture",
    "drawing": "Drawing, Collage or other Work on Paper",
    "drawing, collage or other work on paper": "Drawing, Collage or other Work on Paper",
    "design/decorative art": "Design/Decorative Art",
    "design / decorative art": "Design/Decorative Art",
    "decorative": "Design/Decorative Art",
    "textile": "Textile Arts",
    "manuscript": "Other",
    "poster": "Posters",
    "posters": "Posters",
    "travel poster": "Posters",
    "thangka": "Painting",   # thangkas are paintings on cloth in Artsy taxonomy
    "photograph": "Photograph",
    "photo": "Photograph",
    "print": "Print",
    "album": "Drawing, Collage or other Work on Paper",
    "arms": "Design/Decorative Art",
    "weapon": "Design/Decorative Art",
    "furniture": "Design/Decorative Art",
}


def clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "null", "n/a", "unknown"}:
        return None
    return s


def normalize_artist(value: Optional[str]) -> Optional[str]:
    s = clean(value)
    if not s:
        return None
    if s.lower() in {"unknown", "unknown artist", "anonymous"}:
        return None
    return s


def normalize_decimal(value: Optional[str]) -> Optional[float]:
    s = clean(value)
    if s is None:
        return None
    s = s.replace(",", ".")
    s = s.replace(" ", "")
    m = re.match(r"^(-?\d+(?:\.\d+)?)", s)
    if not m:
        return _parse_imperial_dim(s)
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _parse_imperial_dim(s: str) -> Optional[float]:
    """Parse '7 1/2', '8 ⅛', '11 1/4 in.' to a float (inches)."""
    if not s:
        return None
    s = s.lower().replace("in.", "").replace('"', "").strip()
    m = re.match(r"^(\d+)\s+(\d+/\d+)$", s)
    if m:
        whole = int(m.group(1))
        frac = DIM_FRACTIONS.get(m.group(2), 0)
        return whole + frac
    m = re.match(r"^(\d+/\d+)$", s)
    if m:
        return DIM_FRACTIONS.get(m.group(1), None)
    return None


def normalize_int(value: Optional[str]) -> Optional[int]:
    f = normalize_decimal(value)
    return int(f) if f is not None else None


def normalize_year(value: Optional[str]) -> Optional[int]:
    s = clean(value)
    if s is None:
        return None
    m = re.search(r"\b(1[5-9]\d{2}|20\d{2}|21\d{2})\b", s)
    if m:
        return int(m.group(1))
    n = normalize_int(s)
    if n is not None and 100 <= n <= 2100:
        return n
    return None


def normalize_classification(value: Optional[str]) -> Optional[str]:
    s = clean(value)
    if s is None:
        return None
    return CLASSIFICATION_MAP.get(s.lower(), s)


def normalize_price(value: Optional[str]) -> Optional[float]:
    s = clean(value)
    if s is None:
        return None
    s = s.replace("$", "").replace(",", "").replace("USD", "").strip()
    return normalize_decimal(s)


def normalize_title(value: Optional[str]) -> Optional[str]:
    s = clean(value)
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip(" .")
    return s
