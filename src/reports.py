"""Markdown reports: coverage, gaps, provenance."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import sqlite_utils

from .schema import CANONICAL_FIELDS


def coverage_report(db: sqlite_utils.Database, out_path: Path | str) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    total = db.execute("SELECT COUNT(*) FROM works").fetchone()[0] or 1
    lines = [
        "# Inventory coverage",
        "",
        f"- Total works: **{total}**",
        f"- Works with at least one conflict: **{db.execute('SELECT COUNT(*) FROM works WHERE has_conflict = 1').fetchone()[0]}**",
        "",
        "## Field-level coverage",
        "",
        "| Field | Populated | % |",
        "|---|---:|---:|",
    ]
    for f in CANONICAL_FIELDS:
        n = db.execute(
            f"SELECT COUNT(*) FROM works WHERE {f} IS NOT NULL AND CAST({f} AS TEXT) != ''"
        ).fetchone()[0]
        lines.append(f"| {f} | {n} | {round(100 * n / total, 1)}% |")

    lines += [
        "",
        "## Sources ingested",
        "",
        "| Source | Type | Rows | Source modified |",
        "|---|---|---:|---|",
    ]
    # file_modified_at is the source file's mtime (stable across reruns);
    # extracted_at is a per-run timestamp and would dirty git on every
    # `make all`.  Sort by name so order is also deterministic.
    for r in db.execute(
        "SELECT name, type, row_count, file_modified_at FROM sources ORDER BY name"
    ).fetchall():
        ts = (r[3] or "").split(".")[0]  # trim microseconds
        lines.append(f"| {r[0]} | {r[1]} | {r[2] or ''} | {ts} |")

    out.write_text("\n".join(lines) + "\n")
    return out


def gaps_report(db: sqlite_utils.Database, out_path: Path | str, top_n: int = 50) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = db.execute(
        """SELECT work_id, title, artist, classification, medium, primary_image_url
           FROM works
           WHERE primary_image_url IS NULL
              OR title IS NULL OR classification IS NULL OR medium IS NULL
           ORDER BY work_id"""
    ).fetchall()
    blocked = []
    miss_counter = Counter()
    for wid, title, artist, classification, medium, image in rows:
        missing = []
        if not title: missing.append("title")
        if not classification: missing.append("classification")
        if not medium: missing.append("medium")
        if not image: missing.append("image")
        blocked.append((wid, title, artist, ",".join(missing)))
        for m in missing:
            miss_counter[m] += 1

    lines = [
        "# Artsy upload gaps",
        "",
        f"- Works blocked from Artsy upload: **{len(blocked)}**",
        "",
        "## What's missing most often",
        "",
        "| Missing field | Works |",
        "|---|---:|",
    ]
    for field, n in miss_counter.most_common():
        lines.append(f"| {field} | {n} |")

    # Prioritized triage: works missing only 1 field (closest to ready), then 2, etc.
    triage = sorted(
        [(wid, title, artist, missing) for wid, title, artist, missing in blocked],
        key=lambda r: (len(r[3].split(",")) if r[3] else 0, r[0]),
    )
    lines += [
        "",
        "## Triage: closest to upload-ready first",
        "",
        "Sorted by *number of missing fields ascending* — the smallest punch list at the top.",
        "",
        "| KG-# | Missing | Title | Artist |",
        "|---|---|---|---|",
    ]
    for wid, title, artist, missing in triage[:top_n]:
        n_missing = len(missing.split(","))
        lines.append(f"| {wid} | {n_missing}: {missing} | {(title or '')[:60]} | {artist or ''} |")

    lines += [
        "",
        "## Unresolved conflicts",
        "",
        "Each row blocks confidence in the canonical value.",
        "Resolve with: `python -m src.cli resolve <KG-#> <field> \"<value>\" --reason \"...\"`",
        "",
        "| KG-# | Field | Distinct values | Sources |",
        "|---|---|---|---|",
    ]
    # Aggregate Python-side — values like "Drawing, Collage or other Work on
    # Paper" contain commas that would be split by SQL-level GROUP_CONCAT.
    raw = db.execute(
        """SELECT o.work_id, o.field, o.value, s.type AS stype
           FROM observations o JOIN sources s ON s.id = o.source_id
           WHERE o.value IS NOT NULL AND o.value != ''
             AND s.type NOT IN ('human_resolution','auto_resolution')"""
    ).fetchall()
    has_human = {
        (w, f) for (w, f) in db.execute(
            """SELECT DISTINCT o.work_id, o.field FROM observations o
               JOIN sources s ON s.id = o.source_id
               WHERE s.type = 'human_resolution'"""
        ).fetchall()
    }
    by_wf: dict[tuple[str, str], dict] = {}
    for w, f, v, st in raw:
        rec = by_wf.setdefault((w, f), {"values": set(), "stypes": set()})
        rec["values"].add(v)
        rec["stypes"].add(st)
    conflicts_rows = sorted(
        (w, f, sorted(rec["values"]), sorted(rec["stypes"]))
        for (w, f), rec in by_wf.items()
        if len(rec["values"]) > 1 and (w, f) not in has_human
    )[:30]
    for w, f, vals, stypes in conflicts_rows:
        # Pipe-escape values for the markdown table.
        vals_str = " \\| ".join(v.replace("|", "\\|") for v in vals)
        lines.append(f"| {w} | {f} | {vals_str} | {','.join(stypes)} |")

    out.write_text("\n".join(lines) + "\n")
    return out


def provenance_report(db: sqlite_utils.Database, out_path: Path | str) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Provenance: which source contributed which fields",
        "",
        "| Source | Field | Observations |",
        "|---|---|---:|",
    ]
    for r in db.execute(
        """SELECT s.name, o.field, COUNT(*) AS n
           FROM observations o JOIN sources s ON s.id = o.source_id
           GROUP BY s.name, o.field ORDER BY s.name, n DESC"""
    ).fetchall():
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} |")

    lines += ["", "## Conflict counts per field", "", "| Field | Works with conflict |", "|---|---:|"]
    # Mirror the gaps-report logic: a "conflict" is a real disagreement
    # among observation sources, ignoring (a) resolution-layer values
    # and (b) any (work, field) where a human resolution exists.
    # v_conflicts counts everything, which inflates the totals (e.g.
    # auto_resolution introducing classification: Sculpture against
    # Primer's Painting would show as a conflict).
    raw = db.execute(
        """SELECT o.work_id, o.field, o.value
           FROM observations o JOIN sources s ON s.id = o.source_id
           WHERE o.value IS NOT NULL AND o.value != ''
             AND s.type NOT IN ('human_resolution','auto_resolution')"""
    ).fetchall()
    has_human = {
        (w, f) for (w, f) in db.execute(
            """SELECT DISTINCT o.work_id, o.field FROM observations o
               JOIN sources s ON s.id = o.source_id
               WHERE s.type = 'human_resolution'"""
        ).fetchall()
    }
    by_field: dict[str, set] = {}
    seen: dict[tuple[str, str], set] = {}
    for w, f, v in raw:
        seen.setdefault((w, f), set()).add(v)
    for (w, f), vals in seen.items():
        if len(vals) > 1 and (w, f) not in has_human:
            by_field.setdefault(f, set()).add(w)
    for field, works in sorted(by_field.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        lines.append(f"| {field} | {len(works)} |")

    out.write_text("\n".join(lines) + "\n")
    return out
