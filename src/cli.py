"""Command-line entry point: ``python -m src.cli ...``"""

from __future__ import annotations

import importlib
from pathlib import Path

import click
import yaml

from . import db as dbmod
from . import consolidate as consolidate_mod
from . import reports
from .exporters import (
    artsy_upload_csv, conflicts_csv, gaps_csv, master_csv, master_json,
    primer_corrections_csv, provenance_csv,
)

INGESTERS = {
    "artsy_csv": ("src.ingest.artsy_csv", "ArtsyCsvIngester"),
    "primer_pdf": ("src.ingest.primer_pdf", "PrimerPdfIngester"),
    "match_workbook": ("src.ingest.match_workbook", "MatchWorkbookIngester"),
    "image_dir": ("src.ingest.image_dir", "ImageDirIngester"),
    "price_list_pdf": ("src.ingest.price_list_pdf", "PriceListPdfIngester"),
    "sub_inventory": ("src.ingest.sub_inventory", "SubInventoryIngester"),
    "kg_inventory_pdf": ("src.ingest.kg_inventory_pdf", "KGInventoryPdfIngester"),
    "email_gaps": ("src.ingest.email_gaps", "EmailGapsIngester"),
    "human_resolution": ("src.ingest.human_resolution", "HumanResolutionIngester"),
    "auto_resolution": ("src.ingest.auto_resolution", "AutoResolutionIngester"),
    "bulk_upload_xlsx": ("src.ingest.bulk_upload_xlsx", "BulkUploadXlsxIngester"),
}


def _load_ingester(type_: str):
    if type_ not in INGESTERS:
        raise click.BadParameter(f"Unknown ingester type: {type_}")
    module_name, cls_name = INGESTERS[type_]
    try:
        mod = importlib.import_module(module_name)
        return getattr(mod, cls_name)
    except (ImportError, AttributeError):
        return None  # ingester not yet implemented


__version__ = "0.4.0"


@click.group()
@click.version_option(version=__version__, prog_name="kg-inv")
def cli():
    """Kapoor Galleries master inventory pipeline.

    \b
    Workflow shortcuts:
      make all          re-ingest + consolidate + generate every artifact
      make stats        one-screen dashboard
      make health       full system diagnosis
      make demo         guided tour

    \b
    Single commands (kg-inv ...):
      refresh           ingest + consolidate + report + lint + check-artsy
      triage            interactive conflict resolution
      resolve <kg> <f> <v>  record one human resolution
      promote <kg> <f>  lock in the current canonical value
      conflicts         list unresolved disagreements
      gaps              punch list of nearly-ready works
      show <kg>         full per-work report
      search <text>     substring search
      export-filtered   write a filtered subset CSV
      suggest-rules     mine inventory for new auto-rule candidates
      lint              data-quality findings
      check-artsy       pre-flight Artsy upload validation
    """
    pass


@cli.command("init-db")
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def init_db_cmd(db_path: str):
    """Create the schema."""
    dbmod.init_db(db_path)
    click.echo(f"Initialized {db_path}")


@cli.command()
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
@click.option("--sources", default="catalog/sources.yaml", show_default=True)
def ingest(db_path: str, sources: str):
    """Run every enabled ingester listed in catalog/sources.yaml.

    auto_resolution is special: it runs LAST and reads from the DB rather
    than from the file system, so its observations layer on top of every
    other source.
    """
    src_yaml = yaml.safe_load(Path(sources).read_text()) or []
    db = dbmod.init_db(db_path)
    total_obs = 0
    skipped: list[str] = []
    deferred = []  # auto_resolution etc. — run after all other sources

    for entry in src_yaml:
        if not entry.get("enabled", True):
            skipped.append(f"{entry.get('name')} (disabled)")
            continue
        type_ = entry["type"]
        local = entry.get("local_path")
        cls = _load_ingester(type_)
        if cls is None:
            skipped.append(f"{entry.get('name')} ({type_} ingester not implemented)")
            continue
        if not local or not Path(local).exists():
            skipped.append(f"{entry.get('name')} (no local file at {local})")
            continue
        if type_ == "auto_resolution":
            deferred.append((entry, cls, local))
            continue
        ingester = cls(local, drive_file_id=entry.get("drive_file_id"))
        result = ingester.run()
        result.source.name = entry.get("name") or result.source.name
        sid = dbmod.upsert_source(db, result.source)
        n = dbmod.insert_observations(db, sid, result.observations)
        m = dbmod.insert_images(db, sid, result.images)
        total_obs += n
        click.echo(f"  {entry['name']}: {n} observations, {m} images")

    for entry, cls, local in deferred:
        ingester = cls(local, drive_file_id=entry.get("drive_file_id"), db=db)
        result = ingester.run()
        result.source.name = entry.get("name") or result.source.name
        sid = dbmod.upsert_source(db, result.source)
        n = dbmod.insert_observations(db, sid, result.observations)
        total_obs += n
        click.echo(f"  {entry['name']} (deferred): {n} observations")

    click.echo(f"Inserted {total_obs} observations total.")
    if skipped:
        click.echo("Skipped:")
        for s in skipped:
            click.echo(f"  - {s}")


@cli.command()
@click.argument("yaml_in", type=click.Path(exists=True))
@click.option("--file", "yaml_out", default="data/human_resolutions.yaml", show_default=True,
              help="Append-target for human resolutions.")
def batch_resolve(yaml_in: str, yaml_out: str):
    """Append every entry from `yaml_in` to data/human_resolutions.yaml.

    `yaml_in` should be a YAML list of objects, each with at minimum
    {work_id, field, value} and optionally reason / decided_by /
    decided_at.

    Useful when a curator preps a batch of decisions offline.
    """
    incoming = yaml.safe_load(Path(yaml_in).read_text()) or []
    target = Path(yaml_out)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = yaml.safe_load(target.read_text()) if target.exists() else []
    existing = existing or []
    n = 0
    for e in incoming:
        if not (e.get("work_id") and e.get("field") and e.get("value") not in (None, "")):
            continue
        existing.append(e)
        n += 1
    target.write_text(yaml.safe_dump(existing, sort_keys=False, default_flow_style=False))
    click.echo(f"Appended {n} resolutions from {yaml_in} to {yaml_out}")
    click.echo("Run `make consolidate report` (or `make all`) to refresh master.csv.")


@cli.command("inspect-source")
@click.argument("source_name")
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def inspect_source(source_name: str, db_path: str):
    """Show what one source contributed: works, fields, conflict rate."""
    db = dbmod.get_db(db_path)
    src = db.execute(
        "SELECT id, name, type, row_count FROM sources WHERE name LIKE ?",
        [f"%{source_name}%"],
    ).fetchone()
    if not src:
        click.echo(f"No source matching {source_name!r}.")
        return
    sid, sname, stype, rcount = src

    n_obs = db.execute(
        "SELECT COUNT(*) FROM observations WHERE source_id = ?", [sid]
    ).fetchone()[0]
    n_works = db.execute(
        "SELECT COUNT(DISTINCT work_id) FROM observations WHERE source_id = ?", [sid]
    ).fetchone()[0]
    by_field = db.execute(
        """SELECT field, COUNT(*) FROM observations WHERE source_id = ?
           GROUP BY field ORDER BY 2 DESC""",
        [sid],
    ).fetchall()
    n_chosen = db.execute(
        """SELECT COUNT(*) FROM observations o
           JOIN sources s ON s.id = o.source_id
           WHERE s.id = ?
             AND EXISTS (SELECT 1 FROM works w WHERE w.work_id = o.work_id)""",
        [sid],
    ).fetchone()[0]

    click.echo(f"\n  {sname}")
    click.echo(f"  type={stype}  source-rows={rcount}")
    click.echo(f"  observations={n_obs}  works contributed-to={n_works}")
    click.echo()
    click.echo("  Fields contributed:")
    for f, n in by_field:
        click.echo(f"    {f:25s} {n}")
    click.echo()


@cli.command("source")
@click.argument("action", type=click.Choice(["list", "enable", "disable"]))
@click.argument("name", required=False)
@click.option("--sources", default="catalog/sources.yaml", show_default=True)
def source_cmd(action: str, name: str | None, sources: str):
    """Manage sources.yaml from the CLI.

    Examples:
      kg-inv source list
      kg-inv source enable "Graham Inventory - owned.pdf"
      kg-inv source disable "Inventory for 2024 catalog.xlsx"
    """
    p = Path(sources)
    entries = yaml.safe_load(p.read_text()) or []

    if action == "list":
        click.echo()
        for e in entries:
            enabled = e.get("enabled", True)
            tag = "✓" if enabled else "✗"
            local = e.get("local_path", "")
            local_path = Path(local) if local else None
            if local_path and local_path.exists():
                if local_path.is_file():
                    sz = local_path.stat().st_size
                    if sz >= 1024 * 1024:
                        size_str = f"{sz/1024/1024:.1f}M"
                    elif sz >= 1024:
                        size_str = f"{sz/1024:.0f}K"
                    else:
                        size_str = f"{sz}B"
                else:
                    n = sum(1 for _ in local_path.iterdir())
                    size_str = f"{n} files"
            else:
                size_str = "—"
            click.echo(
                f"  {tag} {size_str:>9}  {e.get('type','?'):20s}  "
                f"{e.get('name','?')}"
            )
        click.echo()
        click.echo("  ✓=enabled  ✗=disabled  size shows local file presence")
        return

    if not name:
        raise click.ClickException("source enable/disable requires a name argument")

    matched = [e for e in entries if (e.get("name") or "") == name]
    if not matched:
        # Allow substring match for convenience.
        matched = [e for e in entries if name.lower() in (e.get("name") or "").lower()]
    if not matched:
        raise click.ClickException(f"No source matching {name!r}")
    if len(matched) > 1:
        raise click.ClickException(
            f"{len(matched)} sources match {name!r}; be more specific:\n  "
            + "\n  ".join((m.get('name') or '?') for m in matched)
        )

    target = matched[0]
    target["enabled"] = (action == "enable")
    p.write_text(yaml.safe_dump(entries, sort_keys=False, default_flow_style=False))
    click.echo(f"{action}d: {target.get('name')}")


@cli.command()
@click.argument("work_id")
@click.argument("field")
@click.argument("value")
@click.option("--reason", default="", help="Why this value is correct.")
@click.option("--by", "decided_by", default="", help="Email of the person making the call.")
@click.option("--dry-run", is_flag=True, default=False,
              help="Print what would be appended without writing to disk.")
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
@click.option("--file", "yaml_path", default="data/human_resolutions.yaml", show_default=True)
def resolve(work_id: str, field: str, value: str, reason: str, decided_by: str,
            dry_run: bool, db_path: str, yaml_path: str):
    """Record an authoritative human decision for one (work, field).

    Example:

      python -m src.cli resolve KG-1000 classification \\
        "Drawing, Collage or other Work on Paper" \\
        --reason "Opaque watercolor on paper." \\
        --by sanjay@kapoors.com

    Appends to data/human_resolutions.yaml and immediately re-runs the
    human_resolution ingester so the master.csv reflects the change without
    a full `make all`.
    """
    from datetime import datetime, timezone
    new_entry = {
        "work_id": work_id,
        "field": field,
        "value": value,
        "reason": reason,
        "decided_by": decided_by,
        "decided_at": datetime.now(timezone.utc).date().isoformat(),
    }
    # Sanity-check the work_id exists in the current works table.
    db = dbmod.get_db(db_path)
    try:
        existing = db.execute(
            "SELECT 1 FROM works WHERE work_id = ?", [work_id]
        ).fetchone()
    except Exception:
        existing = None
    if not existing:
        click.echo(
            f"WARNING: {work_id} is not in works table. "
            f"Run `make all` first, or proceed if you're seeding a new work.",
            err=True,
        )

    if dry_run:
        click.echo("DRY RUN — would append the following YAML entry:\n")
        click.echo(yaml.safe_dump([new_entry], sort_keys=False, default_flow_style=False))
        return

    p = Path(yaml_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    entries = yaml.safe_load(p.read_text()) if p.exists() else []
    entries = entries or []
    # Warn (don't fail) if there's already an entry for this (work, field).
    dupe = next(
        (e for e in entries if e.get("work_id") == work_id and e.get("field") == field),
        None,
    )
    if dupe:
        click.echo(
            f"NOTE: an existing resolution for {work_id}.{field} = "
            f"{dupe.get('value')!r} is already in {yaml_path}. "
            f"Appending the new value; the most-recent wins at consolidate time.",
            err=True,
        )
    entries.append(new_entry)
    p.write_text(yaml.safe_dump(entries, sort_keys=False, default_flow_style=False))
    click.echo(f"Appended to {yaml_path}: {work_id}.{field} = {value!r}")

    # Re-ingest just this source so the change shows up immediately.
    from src.ingest.human_resolution import HumanResolutionIngester
    db = dbmod.init_db(db_path)
    # Drop any prior observations from this source so we don't keep stale rows.
    db.conn.execute(
        """DELETE FROM observations WHERE source_id IN
           (SELECT id FROM sources WHERE type = 'human_resolution')"""
    )
    db.conn.execute("DELETE FROM sources WHERE type = 'human_resolution'")
    db.conn.commit()
    result = HumanResolutionIngester(p).run()
    sid = dbmod.upsert_source(db, result.source)
    n = dbmod.insert_observations(db, sid, result.observations)
    click.echo(f"Re-ingested {n} human resolutions.")
    click.echo("Run `make consolidate report` to refresh master.csv.")


@cli.command("ingest-one")
@click.option("--type", "type_", required=True)
@click.option("--file", "file_path", required=True, type=click.Path(exists=True))
@click.option("--name", default=None)
@click.option("--drive-id", default=None)
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def ingest_one_cmd(type_: str, file_path: str, name: str | None, drive_id: str | None, db_path: str):
    """Run a single ingester ad-hoc."""
    cls = _load_ingester(type_)
    if cls is None:
        raise click.ClickException(f"Ingester for type '{type_}' is not implemented.")
    db = dbmod.init_db(db_path)
    ingester = cls(file_path, drive_file_id=drive_id)
    result = ingester.run()
    if name:
        result.source.name = name
    sid = dbmod.upsert_source(db, result.source)
    n = dbmod.insert_observations(db, sid, result.observations)
    m = dbmod.insert_images(db, sid, result.images)
    click.echo(f"Inserted {n} observations, {m} images from {file_path}")


@cli.command()
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def consolidate(db_path: str):
    """Rebuild the canonical works table from observations."""
    db = dbmod.get_db(db_path)
    stats = consolidate_mod.consolidate(db)
    click.echo(f"Consolidated {stats['works']} works ({stats['with_conflicts']} with conflicts)")


@cli.command()
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def report(db_path: str):
    """Emit master.csv, conflicts.csv, gaps.csv, artsy_upload.csv + markdown reports."""
    db = dbmod.get_db(db_path)
    n = master_csv.export_master_csv(db, "data/master.csv")
    nc = conflicts_csv.export_conflicts(db, "data/conflicts.csv")
    ng = gaps_csv.export_gaps(db, "data/gaps.csv")
    na = artsy_upload_csv.export_artsy_upload(db, "data/artsy_upload.csv")
    np_ = provenance_csv.export_provenance(db, "data/master_provenance.csv")
    npc = primer_corrections_csv.export_primer_corrections(db, "data/primer_corrections.csv")
    nj = master_json.export_master_json(db, "data/master.json")
    reports.coverage_report(db, "reports/coverage_report.md")
    reports.gaps_report(db, "reports/gaps_report.md")
    reports.provenance_report(db, "reports/provenance_report.md")
    click.echo(f"master.csv: {n} rows")
    click.echo(f"conflicts.csv: {nc} rows")
    click.echo(f"gaps.csv: {ng} rows")
    click.echo(f"artsy_upload.csv: {na} rows")
    click.echo(f"master_provenance.csv: {np_} rows")
    click.echo(f"primer_corrections.csv: {npc} rows")
    click.echo(f"master.json: {nj} works")
    click.echo("reports/*.md written")


@cli.command()
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Output JSON instead of the one-line text summary.")
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def overview(as_json: bool, db_path: str):
    """One-line summary suitable for chat/email status updates."""
    db = dbmod.get_db(db_path)
    total = db.execute("SELECT COUNT(*) FROM works").fetchone()[0] or 1
    n_conflicts = db.execute("SELECT COUNT(*) FROM works WHERE has_conflict = 1").fetchone()[0]
    artsy_ready = db.execute("""SELECT COUNT(*) FROM works
        WHERE COALESCE(status,'active') = 'active'
          AND title IS NOT NULL AND classification IS NOT NULL
          AND medium IS NOT NULL AND primary_image_url IS NOT NULL""").fetchone()[0]
    n_artist = db.execute(
        "SELECT COUNT(*) FROM works WHERE artist IS NOT NULL"
    ).fetchone()[0]
    sources = db.execute("SELECT COUNT(DISTINCT name) FROM sources").fetchone()[0]

    if as_json:
        import json
        click.echo(json.dumps({
            "works": total,
            "artsy_eligible": artsy_ready,
            "artsy_eligible_pct": round(100 * artsy_ready / total, 1),
            "attributed": n_artist,
            "attributed_pct": round(100 * n_artist / total, 1),
            "conflicts": n_conflicts,
            "sources": sources,
        }))
    else:
        click.echo(
            f"\n  {total} works · {artsy_ready} Artsy-eligible "
            f"({round(100*artsy_ready/total)}%) · {n_artist} attributed "
            f"({round(100*n_artist/total)}%) · {n_conflicts} conflicts · "
            f"{sources} sources ingested.\n"
        )


@cli.command()
@click.option("--json", "as_json", is_flag=True, default=False)
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def stats(as_json: bool, db_path: str):
    """Show one-screen inventory dashboard."""
    db = dbmod.get_db(db_path)
    total = db.execute("SELECT COUNT(*) FROM works").fetchone()[0]
    if total == 0:
        click.echo("No works yet — run `make all`.")
        return
    conflicts = db.execute("SELECT COUNT(*) FROM works WHERE has_conflict = 1").fetchone()[0]
    artsy_ready = db.execute("""
        SELECT COUNT(*) FROM works
        WHERE COALESCE(status,'active') = 'active'
          AND title IS NOT NULL AND classification IS NOT NULL
          AND medium IS NOT NULL AND primary_image_url IS NOT NULL
    """).fetchone()[0]
    blocked = total - artsy_ready
    coverage = {}
    for f in ("title", "artist", "year", "classification", "medium", "materials",
              "height_in", "width_in", "depth_in", "price_usd", "primary_image_url"):
        n = db.execute(
            f"SELECT COUNT(*) FROM works WHERE {f} IS NOT NULL AND CAST({f} AS TEXT) != ''"
        ).fetchone()[0]
        coverage[f] = n
    sources_data = db.execute(
        "SELECT name, type, row_count FROM sources ORDER BY name"
    ).fetchall()

    if as_json:
        import json
        click.echo(json.dumps({
            "works": total,
            "artsy_eligible": artsy_ready,
            "blocked": blocked,
            "conflicts": conflicts,
            "coverage": coverage,
            "sources": [{"name": r[0], "type": r[1], "rows": r[2]} for r in sources_data],
        }, indent=2))
        return

    click.echo(f"\n  Works:           {total}")
    click.echo(f"  Artsy-eligible:  {artsy_ready}")
    click.echo(f"  Blocked:         {blocked}")
    click.echo(f"  Conflicts:       {conflicts}")
    click.echo()
    click.echo("  Field coverage:")
    for f, n in coverage.items():
        bar = "█" * int(round(n / total * 30))
        click.echo(f"    {f:20s} {bar:30s} {n:4d}/{total} ({round(100*n/total)}%)")
    click.echo()
    click.echo("  Sources ingested:")
    for r in sources_data:
        click.echo(f"    {r[0][:50]:50s} {r[1]:20s} rows={r[2]}")
    click.echo()


@cli.command()
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
@click.option("--limit", default=20, show_default=True)
def conflicts(db_path: str, limit: int):
    """List unresolved conflicts with values + sources, ready for `kg-inv resolve`."""
    db = dbmod.get_db(db_path)
    rows = db.execute(
        """WITH observed AS (
              SELECT o.work_id, o.field, o.value, s.type AS stype
              FROM observations o JOIN sources s ON s.id = o.source_id
              WHERE o.value IS NOT NULL AND o.value != ''
                AND s.type NOT IN ('human_resolution','auto_resolution')
           )
           SELECT o.work_id, o.field,
                  GROUP_CONCAT(DISTINCT o.stype || '=' || o.value) AS sources
           FROM observed o
           GROUP BY o.work_id, o.field
           HAVING COUNT(DISTINCT o.value) > 1
              AND NOT EXISTS (
                  SELECT 1 FROM observations o2 JOIN sources s2 ON s2.id = o2.source_id
                  WHERE o2.work_id = o.work_id AND o2.field = o.field
                    AND s2.type = 'human_resolution'
              )
           ORDER BY o.work_id, o.field
           LIMIT ?""",
        [limit],
    ).fetchall()
    if not rows:
        click.echo("No unresolved conflicts.")
        return
    click.echo(f"  {len(rows)} unresolved conflicts:\n")
    for wid, field, srcs in rows:
        click.echo(f"  {wid}.{field}")
        for s in srcs.split(","):
            click.echo(f"      {s}")
        click.echo(f"      → resolve: kg-inv resolve {wid} {field} \"<value>\" --reason \"...\"")
        click.echo()


@cli.command("export-filtered")
@click.option("--out", "out_path", required=True,
              help="Path to write the filtered CSV (e.g. data/sculptures.csv).")
@click.option("--classification", default=None,
              help="exact match, e.g. 'Sculpture' or 'Painting'.")
@click.option("--year-min", type=int, default=None)
@click.option("--year-max", type=int, default=None)
@click.option("--price-min", type=float, default=None)
@click.option("--price-max", type=float, default=None)
@click.option("--missing-only", default=None,
              help="comma-separated fields; rows must have all of these missing.")
@click.option("--has-image", is_flag=True, default=False,
              help="restrict to rows with primary_image_url.")
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def export_filtered(out_path: str, classification: str | None,
                    year_min: int | None, year_max: int | None,
                    price_min: float | None, price_max: float | None,
                    missing_only: str | None, has_image: bool, db_path: str):
    """Write a filtered subset of master.csv. Useful for batch uploads."""
    db = dbmod.get_db(db_path)
    where = []
    params: list = []
    if classification:
        where.append("classification = ?")
        params.append(classification)
    if year_min is not None:
        where.append("year >= ?")
        params.append(year_min)
    if year_max is not None:
        where.append("year <= ?")
        params.append(year_max)
    if price_min is not None:
        where.append("price_usd >= ?")
        params.append(price_min)
    if price_max is not None:
        where.append("price_usd <= ?")
        params.append(price_max)
    if has_image:
        where.append("primary_image_url IS NOT NULL")
    if missing_only:
        for f in missing_only.split(","):
            where.append(f"{f.strip()} IS NULL")

    sql = "SELECT * FROM works"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY work_id"

    rows = db.execute(sql, params).fetchall()
    cols = [d[0] for d in db.execute("SELECT * FROM works LIMIT 0").description]

    import csv
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for row in rows:
            w.writerow(row)

    click.echo(f"\n  Wrote {len(rows)} rows to {out_path}.\n")


@cli.command()
@click.option("--n", default=5, show_default=True, help="number of works to sample")
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def sample(n: int, db_path: str):
    """Random sample of works for spot-checking."""
    db = dbmod.get_db(db_path)
    rows = db.execute(
        """SELECT work_id, title, classification, year, primary_image_url
           FROM works ORDER BY RANDOM() LIMIT ?""", [n]
    ).fetchall()
    if not rows:
        click.echo("\n  no works.\n")
        return
    click.echo(f"\n  random {len(rows)} works:\n")
    for wid, title, cls, year, img in rows:
        img_tag = "✓" if img else " "
        click.echo(f"  {wid}  {(year or '____')!s:5} {img_tag}  "
                   f"{(cls or '')[:25]:25s}  {(title or '')[:60]}")
    click.echo("\n  ✓=has image")
    click.echo()


@cli.command()
@click.option("--limit", default=20, show_default=True)
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def whatsnew(limit: int, db_path: str):
    """Show works whose canonical record was last updated most recently."""
    db = dbmod.get_db(db_path)
    rows = db.execute(
        """SELECT work_id, title, classification, canonical_updated_at
           FROM works WHERE canonical_updated_at IS NOT NULL
           ORDER BY canonical_updated_at DESC, work_id
           LIMIT ?""",
        [limit],
    ).fetchall()
    if not rows:
        click.echo("\n  no works yet.\n")
        return
    click.echo(f"\n  {limit} most-recently-touched works:\n")
    for wid, title, cls, updated in rows:
        cls_short = (cls or "")[:30]
        click.echo(f"  {wid}  {updated[:19]}  {cls_short:30s} {(title or '')[:50]}")
    click.echo()


@cli.command("duplicate-titles")
@click.option("--limit", default=20, show_default=True)
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def duplicate_titles(limit: int, db_path: str):
    """Find titles that appear on multiple KG-#s (potential dupes)."""
    db = dbmod.get_db(db_path)
    rows = db.execute(
        """SELECT title, COUNT(*) AS n,
                  GROUP_CONCAT(work_id, ', ') AS work_ids
           FROM works
           WHERE title IS NOT NULL AND title != ''
           GROUP BY LOWER(TRIM(title))
           HAVING n > 1
           ORDER BY n DESC, title
           LIMIT ?""",
        [limit],
    ).fetchall()
    if not rows:
        click.echo("\n  No duplicate titles.\n")
        return
    click.echo(f"\n  {len(rows)} duplicate titles:\n")
    for title, n, ids in rows:
        click.echo(f"  {n:3d}  {title[:60]:60s}  ({ids})")
    click.echo()


@cli.command()
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def coverage(db_path: str):
    """Per-field coverage summary (just the coverage table from stats)."""
    db = dbmod.get_db(db_path)
    total = db.execute("SELECT COUNT(*) FROM works").fetchone()[0] or 1
    click.echo()
    for f in ("title", "artist", "year", "classification", "medium", "materials",
              "height_in", "width_in", "depth_in", "price_usd", "primary_image_url",
              "provenance_text", "exhibitions", "publications", "signature",
              "coa_status", "primer_uuid", "location"):
        n = db.execute(
            f"SELECT COUNT(*) FROM works WHERE {f} IS NOT NULL AND CAST({f} AS TEXT) != ''"
        ).fetchone()[0]
        bar = "█" * int(round(n / total * 30))
        click.echo(f"  {f:24s} {bar:30s} {n:4d}/{total} ({round(100*n/total)}%)")
    click.echo()


@cli.command("image-stats")
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def image_stats(db_path: str):
    """Photography backlog broken out by classification."""
    db = dbmod.get_db(db_path)
    rows = db.execute(
        """SELECT classification,
                  COUNT(*) AS total,
                  SUM(CASE WHEN primary_image_url IS NOT NULL THEN 1 ELSE 0 END) AS with_image
           FROM works
           WHERE classification IS NOT NULL
           GROUP BY classification ORDER BY (total - with_image) DESC"""
    ).fetchall()
    if not rows:
        click.echo("\n  no classification data.\n")
        return
    click.echo()
    click.echo(f"  {'class':40s}  {'with':>5s}  {'total':>5s}  {'%':>4s}  {'gap':>5s}")
    for cls, total, with_image in rows:
        pct = round(100 * with_image / total)
        gap = total - with_image
        click.echo(f"  {(cls or '')[:40]:40s}  {with_image:5d}  {total:5d}  {pct:3d}%  {gap:5d}")
    click.echo()


@cli.command()
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def classifications(db_path: str):
    """Distribution of works by classification."""
    db = dbmod.get_db(db_path)
    rows = db.execute(
        """SELECT classification, COUNT(*) AS n FROM works
           WHERE classification IS NOT NULL AND classification != ''
           GROUP BY classification ORDER BY n DESC"""
    ).fetchall()
    if not rows:
        click.echo("\n  no classification data.\n")
        return
    total = sum(n for _, n in rows)
    click.echo(f"\n  {total} classified works:\n")
    for cls, n in rows:
        bar = "█" * int(round(n / total * 30))
        click.echo(f"    {n:5d}  {bar:30s}  {cls}")
    click.echo()


@cli.command()
@click.option("--limit", default=20, show_default=True)
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def mediums(limit: int, db_path: str):
    """Distribution of works by medium (top N)."""
    db = dbmod.get_db(db_path)
    rows = db.execute(
        """SELECT medium, COUNT(*) AS n FROM works
           WHERE medium IS NOT NULL AND medium != ''
           GROUP BY medium
           ORDER BY n DESC, LOWER(medium)
           LIMIT ?""",
        [limit],
    ).fetchall()
    if not rows:
        click.echo("\n  no medium data.\n")
        return
    total = db.execute(
        "SELECT COUNT(*) FROM works WHERE medium IS NOT NULL AND medium != ''"
    ).fetchone()[0]
    click.echo(f"\n  Top {len(rows)} mediums (out of {total} works with medium):\n")
    for medium, n in rows:
        bar = "█" * int(round(n / total * 30))
        click.echo(f"    {n:5d}  {bar:30s}  {medium[:60]}")
    click.echo()


@cli.command()
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def prices(db_path: str):
    """Distribution of works by price band."""
    db = dbmod.get_db(db_path)
    rows = db.execute(
        """SELECT
             CASE
               WHEN price_usd < 1000     THEN 'under $1k'
               WHEN price_usd < 5000     THEN '$1k–$5k'
               WHEN price_usd < 10000    THEN '$5k–$10k'
               WHEN price_usd < 25000    THEN '$10k–$25k'
               WHEN price_usd < 50000    THEN '$25k–$50k'
               WHEN price_usd < 100000   THEN '$50k–$100k'
               WHEN price_usd < 250000   THEN '$100k–$250k'
               ELSE '$250k+'
             END AS bucket,
             COUNT(*) AS n,
             SUM(price_usd) AS total
           FROM works WHERE price_usd IS NOT NULL AND price_usd > 0
           GROUP BY bucket
           ORDER BY MIN(price_usd)"""
    ).fetchall()
    if not rows:
        click.echo("\n  no priced works.\n")
        return
    n_total = sum(n for _, n, _ in rows)
    sum_total = sum(t for _, _, t in rows)
    click.echo(f"\n  {n_total} priced works · total ${sum_total:,.0f}\n")
    for bucket, n, total in rows:
        bar = "█" * int(round(n / n_total * 30))
        click.echo(f"    {bucket:14s} {bar:30s} {n:4d}  ${total:>12,.0f}")
    click.echo()


@cli.command()
@click.option("--limit", default=20, show_default=True)
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def years(limit: int, db_path: str):
    """Distribution of works by year."""
    db = dbmod.get_db(db_path)
    rows = db.execute(
        """SELECT
             CASE
               WHEN year < 1500 THEN 'pre-1500'
               WHEN year < 1700 THEN '1500-1699'
               WHEN year < 1800 THEN '1700-1799'
               WHEN year < 1850 THEN '1800-1849'
               WHEN year < 1900 THEN '1850-1899'
               WHEN year < 1950 THEN '1900-1949'
               WHEN year < 2000 THEN '1950-1999'
               WHEN year >= 2000 THEN '2000+'
             END AS bucket,
             COUNT(*) AS n
           FROM works WHERE year IS NOT NULL
           GROUP BY bucket
           ORDER BY MIN(year)"""
    ).fetchall()
    if not rows:
        click.echo("\n  no year data.\n")
        return
    total = sum(n for _, n in rows)
    click.echo(f"\n  {total} works with year populated:\n")
    for bucket, n in rows:
        bar = "█" * int(round(n / total * 30))
        click.echo(f"    {bucket:12s} {bar:30s} {n}")
    click.echo()


@cli.command()
@click.option("--limit", default=50, show_default=True)
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def artists(limit: int, db_path: str):
    """List artists by work-count, descending."""
    db = dbmod.get_db(db_path)
    rows = db.execute(
        """SELECT artist, COUNT(*) AS n FROM works
           WHERE artist IS NOT NULL AND artist != ''
           GROUP BY artist
           ORDER BY n DESC, LOWER(artist)
           LIMIT ?""",
        [limit],
    ).fetchall()
    if not rows:
        click.echo("\n  no artists assigned yet.\n")
        return
    total_with_artist = db.execute(
        "SELECT COUNT(*) FROM works WHERE artist IS NOT NULL"
    ).fetchone()[0]
    total = db.execute("SELECT COUNT(*) FROM works").fetchone()[0]
    click.echo(f"\n  {total_with_artist}/{total} works have an artist assigned. Top {limit}:\n")
    for artist, n in rows:
        click.echo(f"  {n:4d}  {artist}")
    click.echo()


@cli.command("split-by-classification")
@click.option("--out-dir", default="data/by_classification", show_default=True)
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def split_by_classification(out_dir: str, db_path: str):
    """Write one CSV per classification (Painting, Sculpture, ...).

    Useful when uploading to Artsy in batches — each batch can be one
    classification at a time.
    """
    import csv
    db = dbmod.get_db(db_path)
    cls_set = [r[0] for r in db.execute(
        "SELECT DISTINCT classification FROM works WHERE classification IS NOT NULL"
    ).fetchall()]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cols = [d[0] for d in db.execute("SELECT * FROM works LIMIT 0").description]
    written = []
    for cls in cls_set:
        rows = db.execute(
            f"SELECT {','.join(cols)} FROM works WHERE classification = ? ORDER BY work_id",
            [cls],
        ).fetchall()
        # File-safe filename
        safe = "".join(c if c.isalnum() else "_" for c in cls).strip("_")
        p = out / f"{safe}.csv"
        with p.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(cols)
            for row in rows:
                w.writerow(row)
        written.append((p, len(rows)))
    click.echo()
    for p, n in written:
        click.echo(f"  {n:5d}  {p}")
    click.echo()


@cli.command()
@click.argument("query")
@click.option("--limit", default=30, show_default=True)
@click.option("--year-min", type=int, default=None,
              help="optional: only show works with year >= this")
@click.option("--year-max", type=int, default=None,
              help="optional: only show works with year <= this")
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def search(query: str, limit: int, year_min: int | None,
           year_max: int | None, db_path: str):
    """Substring search across title / medium / materials / provenance.

    Optional --year-min / --year-max narrow the time window.
    """
    db = dbmod.get_db(db_path)
    pat = f"%{query}%"
    where = (
        "(title LIKE ? COLLATE NOCASE "
        "OR medium LIKE ? COLLATE NOCASE "
        "OR materials LIKE ? COLLATE NOCASE "
        "OR provenance_text LIKE ? COLLATE NOCASE)"
    )
    params: list = [pat, pat, pat, pat]
    if year_min is not None:
        where += " AND year >= ?"; params.append(year_min)
    if year_max is not None:
        where += " AND year <= ?"; params.append(year_max)
    params.append(limit)
    rows = db.execute(
        f"""SELECT work_id, title, classification, medium, year
            FROM works WHERE {where} ORDER BY work_id LIMIT ?""",
        params,
    ).fetchall()
    if not rows:
        click.echo(f"\n  no matches for {query!r}.\n")
        return
    click.echo(f"\n  {len(rows)} match{'es' if len(rows) > 1 else ''} for {query!r}:\n")
    for wid, title, cls, medium, year in rows:
        cls_short = (cls or "")[:30]
        medium_short = (medium or "")[:40]
        click.echo(f"  {wid}  {(year or '')!s:5} {cls_short:30s} {(title or '')[:50]}")
    click.echo()


@cli.command()
@click.argument("work_id")
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def show(work_id: str, db_path: str):
    """Show everything the system knows about one work (canonical + observations)."""
    db = dbmod.get_db(db_path)
    work = db.execute("SELECT * FROM works WHERE work_id = ?", [work_id]).fetchone()
    if not work:
        click.echo(f"No work found with id {work_id}.")
        return
    cols = [d[0] for d in db.execute("SELECT * FROM works LIMIT 0").description]
    rec = dict(zip(cols, work))
    click.echo(f"\n  {work_id}  {(rec.get('title') or '<untitled>')[:80]}")
    click.echo("  " + "─" * 60)
    fields = [f for f in cols if f not in
              ("work_id", "has_conflict", "conflict_fields", "canonical_updated_at")]
    for f in fields:
        v = rec.get(f)
        if v in (None, ""):
            continue
        click.echo(f"    {f:24s} {v}")
    if rec.get("has_conflict"):
        click.echo()
        click.echo(f"  Conflicts: {rec.get('conflict_fields')}")
    click.echo()
    click.echo("  Observation history:")
    for r in db.execute(
        """SELECT o.field, o.value, s.type, o.observed_at, o.source_row_ref
           FROM observations o JOIN sources s ON s.id = o.source_id
           WHERE o.work_id = ? ORDER BY o.field, o.observed_at""",
        [work_id],
    ).fetchall():
        ref = r[4] or ""
        click.echo(f"    {r[0]:24s} {r[2]:18s} {(r[1] or '')[:60]}  ({ref[:30]})")
    img = db.execute(
        "SELECT bytes, is_placeholder, image_url FROM work_images WHERE work_id = ? ORDER BY id",
        [work_id],
    ).fetchall()
    if img:
        click.echo()
        click.echo(f"  Images ({len(img)}):")
        for r in img:
            tag = "PLACEHOLDER" if r[1] else "real"
            url = (r[2] or "")[:60]
            click.echo(f"    {r[0]} bytes ({tag})  {url}")
    click.echo()


@cli.command()
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
@click.option("--max-missing", default=2, show_default=True,
              help="show works missing this many or fewer fields")
@click.option("--limit", default=50, show_default=True)
def gaps(db_path: str, max_missing: int, limit: int):
    """List works closest to Artsy-upload-ready (missing few fields)."""
    db = dbmod.get_db(db_path)
    rows = db.execute(
        """SELECT work_id, title, artist,
                  (CASE WHEN title IS NULL THEN 1 ELSE 0 END
                 + CASE WHEN classification IS NULL THEN 1 ELSE 0 END
                 + CASE WHEN medium IS NULL THEN 1 ELSE 0 END
                 + CASE WHEN primary_image_url IS NULL THEN 1 ELSE 0 END
                 + CASE WHEN height_in IS NULL THEN 1 ELSE 0 END
                 + CASE WHEN width_in IS NULL THEN 1 ELSE 0 END) AS missing,
                  (CASE WHEN title IS NULL THEN 'title,' ELSE '' END
                 || CASE WHEN classification IS NULL THEN 'classification,' ELSE '' END
                 || CASE WHEN medium IS NULL THEN 'medium,' ELSE '' END
                 || CASE WHEN primary_image_url IS NULL THEN 'image,' ELSE '' END
                 || CASE WHEN height_in IS NULL THEN 'height,' ELSE '' END
                 || CASE WHEN width_in IS NULL THEN 'width,' ELSE '' END) AS missing_fields
           FROM works
           WHERE (CASE WHEN title IS NULL THEN 1 ELSE 0 END
                + CASE WHEN classification IS NULL THEN 1 ELSE 0 END
                + CASE WHEN medium IS NULL THEN 1 ELSE 0 END
                + CASE WHEN primary_image_url IS NULL THEN 1 ELSE 0 END
                + CASE WHEN height_in IS NULL THEN 1 ELSE 0 END
                + CASE WHEN width_in IS NULL THEN 1 ELSE 0 END) BETWEEN 1 AND ?
           ORDER BY missing ASC, work_id
           LIMIT ?""",
        [max_missing, limit],
    ).fetchall()
    click.echo(f"\n  Works closest to upload-ready (missing ≤ {max_missing} fields):\n")
    n = 0
    for wid, title, artist, missing, mf in rows:
        if missing == 0 or missing > max_missing:
            continue
        n += 1
        mf_clean = mf.rstrip(",") or "—"
        click.echo(f"  {wid}  ({missing} missing: {mf_clean})")
        click.echo(f"      {(title or '')[:70]}")
    if n == 0:
        click.echo("  (none)")
    click.echo()


@cli.command()
@click.argument("work_id")
@click.argument("field")
@click.option("--by", "decided_by", default="auto-promoter", show_default=True)
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
@click.option("--file", "yaml_path", default="data/human_resolutions.yaml", show_default=True)
def promote(work_id: str, field: str, decided_by: str, db_path: str, yaml_path: str):
    """Promote the current canonical value to a permanent human_resolution.

    Use when the auto_resolution rule's decision is correct and you want
    to lock it in for this specific work — so the conflict disappears
    even if the rule changes later.
    """
    db = dbmod.get_db(db_path)
    row = db.execute(
        f"SELECT {field} FROM works WHERE work_id = ?", [work_id]
    ).fetchone()
    if not row or row[0] is None:
        raise click.ClickException(
            f"No canonical value for {work_id}.{field}. Run `make all` first."
        )
    value = str(row[0])

    p = Path(yaml_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    entries = yaml.safe_load(p.read_text()) if p.exists() else []
    entries = entries or []
    from datetime import datetime, timezone
    entries.append({
        "work_id": work_id,
        "field": field,
        "value": value,
        "reason": f"Promoted from auto/curator decision via `kg-inv promote`.",
        "decided_by": decided_by,
        "decided_at": datetime.now(timezone.utc).date().isoformat(),
    })
    p.write_text(yaml.safe_dump(entries, sort_keys=False, default_flow_style=False))
    click.echo(f"Promoted {work_id}.{field} = {value!r} to human_resolution.")
    click.echo("Run `make consolidate report` to refresh master.csv.")


@cli.command()
@click.option("--by", "decided_by", default="", show_default=True)
@click.option("--limit", default=20, show_default=True)
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
@click.option("--file", "yaml_path", default="data/human_resolutions.yaml", show_default=True)
def triage(decided_by: str, limit: int, db_path: str, yaml_path: str):
    """Interactively walk through unresolved conflicts, recording decisions.

    For each conflict, shows the values and their sources, prompts for a
    pick (1, 2, ..., 's' to skip, 'q' to stop), records the decision in
    data/human_resolutions.yaml.
    """
    from datetime import datetime, timezone

    if not decided_by:
        decided_by = click.prompt("Your email", type=str)

    db = dbmod.get_db(db_path)
    raw = db.execute(
        """SELECT o.work_id, o.field, s.type, o.value
           FROM observations o JOIN sources s ON s.id = o.source_id
           WHERE o.value IS NOT NULL AND o.value != ''
             AND s.type NOT IN ('human_resolution','auto_resolution')
           ORDER BY o.work_id, o.field"""
    ).fetchall()

    # Group (work, field) -> list of unique (source, value) pairs.
    grouped: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for w, f, stype, val in raw:
        pairs = grouped.setdefault((w, f), [])
        if (stype, val) not in pairs:
            pairs.append((stype, val))

    # A real conflict has ≥ 2 distinct values among non-resolution sources.
    rows = []
    has_human = {
        (w, f) for (w, f) in db.execute(
            """SELECT DISTINCT o.work_id, o.field FROM observations o
               JOIN sources s ON s.id = o.source_id
               WHERE s.type = 'human_resolution'"""
        ).fetchall()
    }
    for (w, f), pairs in grouped.items():
        distinct_vals = {v for _, v in pairs}
        if len(distinct_vals) > 1 and (w, f) not in has_human:
            rows.append((w, f, pairs))
    rows.sort(key=lambda r: (r[0], r[1]))
    rows = rows[:limit]

    if not rows:
        click.echo("\n  No unresolved conflicts. Nothing to triage.\n")
        return

    p = Path(yaml_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    entries = yaml.safe_load(p.read_text()) if p.exists() else []
    entries = entries or []

    decided = 0
    skipped = 0
    for wid, field, options in rows:
        click.echo()
        click.echo(f"  {wid}.{field}")
        # Show context: title for the work
        ctx = db.execute("SELECT title FROM works WHERE work_id = ?", [wid]).fetchone()
        if ctx and ctx[0]:
            click.echo(f"  Title: {ctx[0]}")
        for i, (src, val) in enumerate(options, start=1):
            click.echo(f"    [{i}] {val}   ({src})")
        click.echo("    [s] skip  [q] quit")

        choice = click.prompt("Pick", type=str, default="s").strip().lower()
        if choice == "q":
            break
        if choice == "s":
            skipped += 1
            continue
        try:
            n = int(choice)
            if not 1 <= n <= len(options):
                click.echo("  invalid; skipping.")
                skipped += 1
                continue
        except ValueError:
            click.echo("  invalid; skipping.")
            skipped += 1
            continue

        chosen_src, chosen_val = options[n - 1]
        reason = click.prompt("Reason (optional)", default="", show_default=False)
        entries.append({
            "work_id": wid, "field": field, "value": chosen_val,
            "reason": reason or f"Picked {chosen_src} value via kg-inv triage.",
            "decided_by": decided_by,
            "decided_at": datetime.now(timezone.utc).date().isoformat(),
        })
        decided += 1

    if decided > 0:
        p.write_text(yaml.safe_dump(entries, sort_keys=False, default_flow_style=False))
        click.echo()
        click.echo(f"  Decided: {decided}   Skipped: {skipped}")
        click.echo(f"  Wrote {yaml_path}.  Run `make consolidate report` to refresh master.csv.")
    else:
        click.echo()
        click.echo(f"  Decided: {decided}   Skipped: {skipped}")
        click.echo("  No decisions recorded — leaving file untouched.")


@cli.command()
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def lint(db_path: str):
    """Flag data-quality issues without changing anything."""
    db = dbmod.get_db(db_path)
    findings: list[tuple[str, str, str]] = []  # (severity, work_id, message)

    # Implausibly old years.
    for r in db.execute(
        "SELECT work_id, year FROM works WHERE year IS NOT NULL AND year < 100"
    ).fetchall():
        findings.append(("error", r[0], f"year {r[1]} looks wrong (< 100)"))

    # Implausibly large dimensions (>200 inches = 5+ metres).
    for r in db.execute(
        """SELECT work_id, height_in, width_in FROM works
           WHERE (height_in IS NOT NULL AND height_in > 200)
              OR (width_in IS NOT NULL AND width_in > 200)"""
    ).fetchall():
        findings.append(("warn", r[0], f"large dimensions h={r[1]} w={r[2]} (>200 in)"))

    # Trailing whitespace in titles.
    for r in db.execute(
        "SELECT work_id, title FROM works WHERE title IS NOT NULL AND title != TRIM(title)"
    ).fetchall():
        findings.append(("warn", r[0], "title has leading/trailing whitespace"))

    # Placeholder titles ("Need title", "Untitled", etc. en masse).
    placeholders = db.execute(
        """SELECT title, COUNT(*) FROM works
           WHERE LOWER(TRIM(title)) IN ('need title', 'untitled', 'no title',
                                         'tbd', 'placeholder')
           GROUP BY LOWER(TRIM(title))"""
    ).fetchall()
    for title, n in placeholders:
        if n >= 5:
            findings.append(("warn", "—", f"{n} works share placeholder title {title!r} — fill in real titles"))

    # Active works without an image — break out into KG-# ranges so the
    # photography backlog is visible per cohort.
    no_img = db.execute(
        """SELECT work_id FROM works
           WHERE COALESCE(status, 'active') = 'active' AND primary_image_url IS NULL"""
    ).fetchall()
    if no_img:
        from collections import Counter
        buckets: Counter = Counter()
        for (wid,) in no_img:
            try:
                n = int(wid.split("-")[1])
                buckets[f"KG-{n//100:02d}xx"] += 1
            except (IndexError, ValueError):
                buckets["other"] += 1
        findings.append(("info", "—", f"{len(no_img)} active works have no primary_image_url"))
        for bucket, n in sorted(buckets.items()):
            findings.append(("info", bucket, f"  {n} works in {bucket} range need photography"))

    # Active works with placeholder PNG only.
    for r in db.execute(
        """SELECT DISTINCT i.work_id FROM work_images i
           JOIN works w ON w.work_id = i.work_id
           WHERE i.is_placeholder = 1
             AND COALESCE(w.status, 'active') = 'active'
             AND NOT EXISTS (
               SELECT 1 FROM work_images i2
               WHERE i2.work_id = i.work_id AND i2.is_placeholder = 0
             )"""
    ).fetchall():
        findings.append(("warn", r[0], "active work has only placeholder image"))

    # Duplicate primer_uuid (a KG-# being recorded as the same Primer record twice).
    for r in db.execute(
        """SELECT primer_uuid, GROUP_CONCAT(work_id) FROM works
           WHERE primer_uuid IS NOT NULL
           GROUP BY primer_uuid HAVING COUNT(DISTINCT work_id) > 1"""
    ).fetchall():
        findings.append(("error", r[1], f"primer_uuid {r[0]} maps to >1 KG-# ({r[1]})"))

    # Inconsistent classification capitalization across the inventory.
    cls_variants = db.execute(
        """SELECT classification, COUNT(*) FROM works
           WHERE classification IS NOT NULL GROUP BY classification ORDER BY 2 DESC"""
    ).fetchall()
    if len({c[0].lower() for c in cls_variants}) < len(cls_variants):
        findings.append(("info", "—", "classification has case-only variants — consider normalizing"))

    # Suspicious artist values that look like consignment/workshop tags.
    for r in db.execute(
        """SELECT work_id, artist FROM works
           WHERE artist IS NOT NULL
             AND (LOWER(artist) LIKE '%consignment%'
               OR LOWER(artist) LIKE '%consignmnet%'
               OR LOWER(artist) LIKE '%unspecified%'
               OR LOWER(artist) = 'unknown'
               OR LOWER(artist) = 'unknown artist')"""
    ).fetchall():
        findings.append(("warn", r[0], f"suspicious artist value {r[1]!r} — likely belongs in another field"))

    if not findings:
        click.echo("\n  no issues found.\n")
        return

    by_sev: dict[str, list] = {"error": [], "warn": [], "info": []}
    for sev, wid, msg in findings:
        by_sev[sev].append((wid, msg))
    click.echo()
    for sev in ("error", "warn", "info"):
        rows = by_sev[sev]
        if not rows:
            continue
        click.echo(f"  {sev}: {len(rows)} finding(s)")
        for wid, msg in rows[:20]:
            click.echo(f"    [{sev:5s}] {wid:14s} {msg}")
        if len(rows) > 20:
            click.echo(f"    … and {len(rows) - 20} more {sev}s")
        click.echo()


@cli.command()
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
@click.option("--sources", default="catalog/sources.yaml", show_default=True)
@click.option("--commit", is_flag=True, default=False,
              help="git-commit the regenerated artifacts after refresh.")
@click.pass_context
def refresh(ctx, db_path: str, sources: str, commit: bool):
    """One-stop: init-db + ingest + consolidate + report + lint + check-artsy.

    Pass --commit to also stage and commit the regenerated CSV/JSON
    artifacts (useful when iterating on rules).
    """
    click.echo("\n  ┌── refresh ───────────────────────────────────────")
    ctx.invoke(init_db_cmd, db_path=db_path)
    ctx.invoke(ingest, db_path=db_path, sources=sources)
    ctx.invoke(consolidate, db_path=db_path)
    ctx.invoke(report, db_path=db_path)
    click.echo("\n  ├── post-checks ──────────────────────────────────")
    ctx.invoke(lint, db_path=db_path)
    ctx.invoke(check_artsy)
    if commit:
        import subprocess
        click.echo("\n  ├── committing artifacts ─────────────────────────")
        subprocess.run([
            "git", "add",
            "data/master.csv", "data/master.json", "data/master_provenance.csv",
            "data/conflicts.csv", "data/gaps.csv", "data/artsy_upload.csv",
            "data/primer_corrections.csv", "reports/",
        ], check=False)
        r = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], capture_output=True
        )
        if r.returncode == 0:
            click.echo("    no changes to commit.")
        else:
            subprocess.run(
                ["git", "commit", "-m", "chore: refresh inventory artifacts"],
                check=False,
            )
            click.echo("    committed (push manually).")
    click.echo("\n  └── refreshed.\n")


@cli.command("suggest-rules")
@click.option("--min-support", default=5, show_default=True,
              help="minimum number of matching works for a rule to be suggested")
@click.option("--min-purity", default=0.9, show_default=True,
              help="fraction of matches that share the candidate field-value (0..1)")
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def suggest_rules(min_support: int, min_purity: float, db_path: str):
    """Mine the existing inventory for new auto-resolution rule candidates.

    For every (title-keyword, classification) pair, count: how often does
    a title containing this keyword have *this* classification?  If the
    count is >= min_support and the purity (matching/total) is >=
    min_purity, suggest a rule.  Same for medium-keyword.
    """
    import re
    from collections import Counter, defaultdict

    db = dbmod.get_db(db_path)
    rows = db.execute(
        "SELECT title, medium, classification FROM works WHERE classification IS NOT NULL"
    ).fetchall()

    # Tokenize titles to single-word keywords (length >= 4 to avoid noise).
    title_classes: dict[str, Counter] = defaultdict(Counter)
    medium_classes: dict[str, Counter] = defaultdict(Counter)
    title_mediums: dict[str, Counter] = defaultdict(Counter)
    for title, medium, cls in rows:
        for tok in re.findall(r"[a-z]{4,}", (title or "").lower()):
            title_classes[tok][cls] += 1
            if medium:
                title_mediums[tok][medium] += 1
        for tok in re.findall(r"[a-z]{4,}", (medium or "").lower()):
            medium_classes[tok][cls] += 1

    # Skip tokens already covered by an existing rule.
    rules_path = Path("data/auto_resolution_rules.yaml")
    existing_keywords: set[str] = set()
    if rules_path.exists():
        for r in (yaml.safe_load(rules_path.read_text()) or []):
            for k, v in (r.get("if") or {}).items():
                if "_contains" in k and isinstance(v, str):
                    existing_keywords.add(v.lower())

    suggestions: list[tuple[float, str, str, str, int, str]] = []
    for token, counter in title_classes.items():
        if token in existing_keywords:
            continue
        total = sum(counter.values())
        if total < min_support:
            continue
        cls, n = counter.most_common(1)[0]
        purity = n / total
        if purity >= min_purity:
            suggestions.append((purity, "title_contains", token, cls, n,
                                f"{n}/{total} works with title containing {token!r}"))
    for token, counter in medium_classes.items():
        if token in existing_keywords:
            continue
        total = sum(counter.values())
        if total < min_support:
            continue
        cls, n = counter.most_common(1)[0]
        purity = n / total
        if purity >= min_purity:
            suggestions.append((purity, "medium_contains", token, cls, n,
                                f"{n}/{total} works with medium containing {token!r}"))

    # Also: where a title-keyword strongly predicts a specific medium, suggest
    # a medium-fill rule.  (Example: 'khanjar' → "Jade-hilted dagger…")
    for token, counter in title_mediums.items():
        if token in existing_keywords:
            continue
        total = sum(counter.values())
        if total < min_support:
            continue
        medium, n = counter.most_common(1)[0]
        purity = n / total
        if purity >= min_purity:
            suggestions.append((
                purity, "title_contains", token,
                f"medium={medium}", n,
                f"{n}/{total} works with title containing {token!r}"))

    suggestions.sort(key=lambda x: (-x[4], -x[0]))
    if not suggestions:
        click.echo("\n  No new high-purity patterns found above the thresholds.\n")
        return

    click.echo(f"\n  {len(suggestions)} suggested rules (purity ≥ {min_purity:.0%}, support ≥ {min_support}):\n")
    for purity, key, tok, cls, n, evidence in suggestions[:20]:
        click.echo(f"  - if: {{ {key}: {tok} }}  =>  classification: {cls}  ({evidence}, purity {purity:.0%})")
    if len(suggestions) > 20:
        click.echo(f"  ... and {len(suggestions)-20} more")
    click.echo()
    click.echo("  Add the ones you trust to data/auto_resolution_rules.yaml and re-run `make all`.")
    click.echo()


ARTSY_VALID_CLASSIFICATIONS = {
    "Painting",
    "Sculpture",
    "Drawing, Collage or other Work on Paper",
    "Print",
    "Photograph",
    "Video/Film/Animation",
    "Performance Art",
    "Installation",
    "Design/Decorative Art",
    "Textile Arts",
    "Posters",
    "Books and Portfolios",
    "Other",
    "Mixed Media",
    "Jewelry",
    "Reproduction",
    "Ephemera or Merchandise",
}


@cli.command("check-artsy")
@click.option("--file", "csv_path", default="data/artsy_upload.csv", show_default=True)
def check_artsy(csv_path: str):
    """Pre-flight validate the Artsy upload CSV against known Artsy rules."""
    import csv
    issues: list[tuple[str, str, str]] = []
    p = Path(csv_path)
    if not p.exists():
        raise click.ClickException(f"{csv_path} doesn't exist. Run `make all` first.")
    with p.open(newline="") as fh:
        reader = csv.DictReader(fh)
        # Strip column whitespace
        reader.fieldnames = [(c or "").strip() for c in (reader.fieldnames or [])]
        for i, row in enumerate(reader, start=2):
            row = {k.strip(): (v or "").strip() for k, v in row.items()}
            wid = row.get("Inventory ID (OPTIONAL)") or f"row{i}"

            title = row.get("Title")
            cls = row.get("Classification")
            medium = row.get("Medium")
            year = row.get("Year")
            h = row.get("Height")
            w = row.get("Width")
            d = row.get("Depth")
            price = row.get("Price")

            if not title:
                issues.append(("error", wid, "title is empty"))
            if not cls:
                issues.append(("error", wid, "classification is empty"))
            elif cls not in ARTSY_VALID_CLASSIFICATIONS:
                issues.append(("error", wid, f"classification {cls!r} not in Artsy's list"))
            if not medium:
                issues.append(("error", wid, "medium is empty"))

            for label, v in (("year", year), ("height", h), ("width", w),
                             ("depth", d), ("price", price)):
                if not v:
                    continue
                try:
                    f = float(v)
                except ValueError:
                    issues.append(("warn", wid, f"{label}={v!r} not numeric"))
                    continue
                if label == "year" and not (0 < f < 2200):
                    issues.append(("warn", wid, f"year {f} implausible"))
                if label in {"height", "width", "depth"} and f <= 0:
                    issues.append(("warn", wid, f"{label} {f} ≤ 0"))
                if label == "price" and f < 0:
                    issues.append(("warn", wid, f"price {f} < 0"))

    if not issues:
        # Count rows for the OK message.
        with p.open(newline="") as fh:
            n_rows = sum(1 for _ in csv.reader(fh)) - 1
        click.echo(f"\n  artsy_upload.csv: OK ({n_rows} rows in {csv_path}).\n")
        return

    by_sev: dict[str, list] = {"error": [], "warn": []}
    for sev, wid, msg in issues:
        by_sev[sev].append((wid, msg))
    click.echo()
    for sev in ("error", "warn"):
        rows = by_sev[sev]
        if not rows:
            continue
        click.echo(f"  {sev}: {len(rows)} finding(s)")
        for wid, msg in rows[:30]:
            click.echo(f"    [{sev}] {wid:14s} {msg}")
        if len(rows) > 30:
            click.echo(f"    … and {len(rows)-30} more {sev}s")
        click.echo()


if __name__ == "__main__":
    cli()
