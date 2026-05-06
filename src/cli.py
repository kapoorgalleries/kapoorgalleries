"""Command-line entry point: ``python -m src.cli ...``"""

from __future__ import annotations

import importlib
from pathlib import Path

import click
import yaml

from . import db as dbmod
from . import consolidate as consolidate_mod
from . import reports
from .exporters import artsy_upload_csv, conflicts_csv, gaps_csv, master_csv

INGESTERS = {
    "artsy_csv": ("src.ingest.artsy_csv", "ArtsyCsvIngester"),
    "primer_pdf": ("src.ingest.primer_pdf", "PrimerPdfIngester"),
    "match_workbook": ("src.ingest.match_workbook", "MatchWorkbookIngester"),
    "image_dir": ("src.ingest.image_dir", "ImageDirIngester"),
    "price_list_pdf": ("src.ingest.price_list_pdf", "PriceListPdfIngester"),
    "sub_inventory": ("src.ingest.sub_inventory", "SubInventoryIngester"),
    "kg_inventory_pdf": ("src.ingest.kg_inventory_pdf", "KGInventoryPdfIngester"),
    "email_gaps": ("src.ingest.email_gaps", "EmailGapsIngester"),
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
    """Run every enabled ingester listed in catalog/sources.yaml."""
    src_yaml = yaml.safe_load(Path(sources).read_text()) or []
    db = dbmod.init_db(db_path)
    total_obs = 0
    skipped: list[str] = []
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
        ingester = cls(local, drive_file_id=entry.get("drive_file_id"))
        result = ingester.run()
        result.source.name = entry.get("name") or result.source.name
        sid = dbmod.upsert_source(db, result.source)
        n = dbmod.insert_observations(db, sid, result.observations)
        m = dbmod.insert_images(db, sid, result.images)
        total_obs += n
        click.echo(f"  {entry['name']}: {n} observations, {m} images")
    click.echo(f"Inserted {total_obs} observations total.")
    if skipped:
        click.echo("Skipped:")
        for s in skipped:
            click.echo(f"  - {s}")


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
    reports.coverage_report(db, "reports/coverage_report.md")
    reports.gaps_report(db, "reports/gaps_report.md")
    reports.provenance_report(db, "reports/provenance_report.md")
    click.echo(f"master.csv: {n} rows")
    click.echo(f"conflicts.csv: {nc} rows")
    click.echo(f"gaps.csv: {ng} rows")
    click.echo(f"artsy_upload.csv: {na} rows")
    click.echo("reports/*.md written")


if __name__ == "__main__":
    cli()
