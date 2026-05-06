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
    artsy_upload_csv, conflicts_csv, gaps_csv, master_csv,
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


@click.group()
def cli():
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


@cli.command("source")
@click.argument("action", type=click.Choice(["list"]))
@click.option("--sources", default="catalog/sources.yaml", show_default=True)
def source_cmd(action: str, sources: str):
    """Manage sources.yaml from the CLI."""
    if action == "list":
        entries = yaml.safe_load(Path(sources).read_text()) or []
        click.echo()
        for e in entries:
            enabled = e.get("enabled", True)
            tag = "✓" if enabled else "✗"
            local = e.get("local_path", "")
            exists = "•" if local and Path(local).exists() else " "
            click.echo(f"  {tag} {exists}  {e.get('type','?'):20s}  {e.get('name','?')}")
        click.echo()
        click.echo(f"  ✓=enabled  ✗=disabled  •=local file present")


@cli.command()
@click.argument("work_id")
@click.argument("field")
@click.argument("value")
@click.option("--reason", default="", help="Why this value is correct.")
@click.option("--by", "decided_by", default="", help="Email of the person making the call.")
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
@click.option("--file", "yaml_path", default="data/human_resolutions.yaml", show_default=True)
def resolve(work_id: str, field: str, value: str, reason: str, decided_by: str,
            db_path: str, yaml_path: str):
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
    p = Path(yaml_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    entries = yaml.safe_load(p.read_text()) if p.exists() else []
    entries = entries or []
    entries.append({
        "work_id": work_id,
        "field": field,
        "value": value,
        "reason": reason,
        "decided_by": decided_by,
        "decided_at": datetime.now(timezone.utc).date().isoformat(),
    })
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
    reports.coverage_report(db, "reports/coverage_report.md")
    reports.gaps_report(db, "reports/gaps_report.md")
    reports.provenance_report(db, "reports/provenance_report.md")
    click.echo(f"master.csv: {n} rows")
    click.echo(f"conflicts.csv: {nc} rows")
    click.echo(f"gaps.csv: {ng} rows")
    click.echo(f"artsy_upload.csv: {na} rows")
    click.echo(f"master_provenance.csv: {np_} rows")
    click.echo(f"primer_corrections.csv: {npc} rows")
    click.echo("reports/*.md written")


@cli.command()
@click.option("--db", "db_path", default="data/inventory.db", show_default=True)
def stats(db_path: str):
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
    click.echo(f"\n  Works:           {total}")
    click.echo(f"  Artsy-eligible:  {artsy_ready}")
    click.echo(f"  Blocked:         {blocked}")
    click.echo(f"  Conflicts:       {conflicts}")
    click.echo()
    click.echo("  Field coverage:")
    for f in ("title", "artist", "year", "classification", "medium", "materials",
              "height_in", "width_in", "depth_in", "price_usd", "primary_image_url"):
        n = db.execute(
            f"SELECT COUNT(*) FROM works WHERE {f} IS NOT NULL AND CAST({f} AS TEXT) != ''"
        ).fetchone()[0]
        bar = "█" * int(round(n / total * 30))
        click.echo(f"    {f:20s} {bar:30s} {n:4d}/{total} ({round(100*n/total)}%)")
    click.echo()
    click.echo("  Sources ingested:")
    for r in db.execute("SELECT name, type, row_count FROM sources ORDER BY name").fetchall():
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


if __name__ == "__main__":
    cli()
