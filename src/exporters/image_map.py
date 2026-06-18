"""Curator-maintained image map: KG-# → Drive image URLs.

The 21 photo-shoot Drive folders contain thousands of artwork images
named only by date+sequence (``240828_KapoorGalleries_0193.jpg``) —
the filenames do NOT carry KG-#s.  We can't auto-map from the filename
alone or from the contact-sheet PDFs (which just label thumbnails with
those same date-seq filenames; no KG-# annotations).

So the bridge is curator-maintained: a sidecar CSV at
``data/image_map.csv`` with one row per (KG-#, image) pair.  This
exporter merges that CSV into the website feed's ``image.alternates``
arrays (and bumps ``image.primary`` to the curator's preferred shot
when ``role == "primary"``).

The CSV format is intentionally simple so curators can edit it in
Sheets:

    kg_id,drive_url,role,notes
    KG-1023,https://drive.google.com/file/d/AAA/view,primary,detail front
    KG-1023,https://drive.google.com/file/d/BBB/view,alternate,verso
    KG-1024,https://drive.google.com/file/d/CCC/view,alternate,detail

``role`` is one of: ``primary``, ``alternate``, ``thumbnail``.

If the CSV doesn't exist, the exporter no-ops (the base feed is
already correct).  This lets `make report` run on a fresh checkout
without the map yet built.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


VALID_ROLES = frozenset({"primary", "alternate", "thumbnail"})


def _drive_view_to_uc(url: str) -> str:
    """Rewrite a sharing URL (`/file/d/<id>/view?...`) to the direct
    `/uc?export=view&id=<id>` form so img tags can render it."""
    if not url:
        return ""
    m = re.search(r"/file/d/([A-Za-z0-9_-]+)", url)
    if m:
        return f"https://drive.google.com/uc?export=view&id={m.group(1)}"
    m = re.search(r"[?&]id=([A-Za-z0-9_-]+)", url)
    if m:
        return f"https://drive.google.com/uc?export=view&id={m.group(1)}"
    return url


def apply_image_map(
    *,
    map_csv: Path | str = "data/image_map.csv",
    feed_path: Path | str = "data/website_inventory.json",
    out_path: Path | str | None = None,
) -> dict:
    """Apply image_map.csv to the website feed in-place (or to
    `out_path` if given).  Returns stats."""
    fp = Path(feed_path)
    mp = Path(map_csv)
    if out_path is None:
        out_path = fp

    feed = json.loads(fp.read_text())
    by_kg = {w["kg_id"]: w for w in feed["works"]}

    if not mp.exists():
        Path(out_path).write_text(
            json.dumps(feed, indent=2, ensure_ascii=False) + "\n")
        return {
            "map_rows": 0, "applied": 0, "missing_kg": 0,
            "invalid_role": 0, "note": f"{mp} not present (no-op)",
        }

    stats = {"map_rows": 0, "applied": 0,
             "missing_kg": 0, "invalid_role": 0}
    with mp.open(newline="") as fh:
        for raw in csv.DictReader(fh):
            stats["map_rows"] += 1
            kg_id = (raw.get("kg_id") or "").strip()
            url = _drive_view_to_uc((raw.get("drive_url") or "").strip())
            role = (raw.get("role") or "alternate").strip().lower()
            # Skip CSV comment lines — the starter template uses `#` as
            # a comment prefix on the example rows.
            if not kg_id or kg_id.startswith("#") or not url:
                continue
            if kg_id not in by_kg:
                stats["missing_kg"] += 1
                continue
            if role not in VALID_ROLES:
                stats["invalid_role"] += 1
                continue
            img = by_kg[kg_id].setdefault("image", {
                "primary": None, "alternates": [], "thumbnail": None,
            })
            if role == "primary":
                # Push the previous primary down to alternates so
                # we don't lose Primer's URL when a curator promotes a
                # local shot.
                if img.get("primary") and img["primary"] != url:
                    if url not in (img.get("alternates") or []):
                        img.setdefault("alternates", []).insert(0, img["primary"])
                img["primary"] = url
            elif role == "thumbnail":
                img["thumbnail"] = url
            else:  # alternate
                alts = img.setdefault("alternates", [])
                if url not in alts:
                    alts.append(url)
            stats["applied"] += 1

    # Recompute with_image facet in case a previously-imageless work
    # picked up a primary URL.
    if "facets" in feed:
        n_with = sum(1 for w in feed["works"]
                     if (w.get("image") or {}).get("primary"))
        feed["facets"]["with_image"] = n_with
        feed["facets"]["without_image"] = len(feed["works"]) - n_with

    Path(out_path).write_text(
        json.dumps(feed, indent=2, ensure_ascii=False) + "\n")
    return stats


def write_starter_template(path: Path | str = "data/image_map.csv") -> Path:
    """Write a starter template with a header row and 2 commented
    examples — enough for a curator to know the schema."""
    p = Path(path)
    if p.exists():
        return p
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "kg_id,drive_url,role,notes\n"
        "# KG-1023,https://drive.google.com/file/d/EXAMPLE_ID/view?usp=sharing,primary,front view\n"
        "# KG-1023,https://drive.google.com/file/d/EXAMPLE_ID2/view?usp=sharing,alternate,verso (calligraphy)\n"
    )
    return p
