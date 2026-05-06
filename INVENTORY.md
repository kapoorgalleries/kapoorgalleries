# Kapoor Galleries — Master Inventory System

A reproducible pipeline that consolidates every gallery inventory source
(Primer Archives, Artsy bulk-upload exports, catalog PDFs, sub-inventories,
legacy folders, email gap reports) into a single canonical record per
work — with full per-field provenance and **flagged, never silently merged,
conflicts**.

## What's in this repo

```
src/                 ETL: ingesters → consolidate → exporters → reports
catalog/sources.yaml Source registry: every Drive file we ingest
data/                inventory.db, master.csv, conflicts.csv, gaps.csv,
                     artsy_upload.csv  (committed)
data/raw/            local cache of Drive files  (gitignored)
reports/             markdown coverage / gaps / provenance reports
apps_script/         Google Apps Script that lives in the master Sheet
tests/               pytest fixtures and unit tests
```

## How a value gets to the master sheet

```
Drive file  ──► ingester ──► observations table (long format, one row per
                              (work_id, field, value, source, timestamp))
                                       │
                                       ▼
                             consolidate.py picks the canonical value
                             per field:  Primer-derived first, otherwise
                             most recent.  Distinct competing values
                             flag the field as a conflict.
                                       │
                                       ▼
                             works table (canonical, one row per KG-#)
                                       │
                                       ▼
                             master.csv  + per-field _conflict columns
                                       │
                                       ▼
                             Apps Script → Google Sheet,
                                          conflicts painted red
```

## First-time setup

```bash
pip install -e .
```

## Running the pipeline

```bash
make all      # init-db + ingest + consolidate + report
# or step-by-step:
make init
make ingest
make consolidate
make report
```

You don't need every source file to run the pipeline — anything missing from
`data/raw/` is logged and skipped. The `Artsy_2-16-2026.csv` (already cached)
is enough to produce a working `master.csv` and `artsy_upload.csv`.

## Adding a new source

1. Drop the file at `data/raw/<name>`.
2. Append an entry to `catalog/sources.yaml` with `type:` matching one of the
   ingesters listed in `src/cli.py:INGESTERS`.
3. `make ingest && make consolidate && make report`.

## Pushing to the Google Sheet

Apps Script lives in `apps_script/Code.gs`. Paste it into the empty
`KG Master Inventory System - 2026-05-06` sheet via Extensions → Apps Script.
On reload the sheet gains an **Inventory ▾** menu with **Refresh from repo**,
**Highlight conflicts**, and **Show gaps for selected work**. See
`apps_script/README.md` for full instructions.

## Source-of-truth rules

- **KG-#### IDs come from Primer.** Anything without one becomes
  `UNRESOLVED-<sha1>` and is surfaced for human triage in `gaps.csv`.
- **Primer-derived sources win** when picking the canonical value of a field
  (the Feb 2026 Artsy CSV is treated as Primer-derived because it *is* a
  Primer dump).
- **Conflicts are visible, never silent.** Every distinct value any source
  ever emitted is in `observations`, listed in `conflicts.csv`, and painted
  red in the Sheet.

## Known limitations

- No live Primer API; we depend on exports (CSV / printed PDF). The two
  Primer-page PDF exports we know about (May 2025, Sep 2025) are >100 MB
  each and must be cached locally — see
  [`tools/FETCH_PRIMER_PDFS.md`](tools/FETCH_PRIMER_PDFS.md).
- Sub-inventory ingesters (Graham, Darion, Huc, Torr, European Sculpture,
  Textile Boxes) are stubs that need title-based fuzzy matching to KG-#.
- Email gap-report parsing is heuristic; refining it once we ingest a real
  Sarah Fenner thread dump is a follow-up.
- The `artist` field comes back at 0% coverage from Primer — every work is
  recorded with `Unknown Artist`. These are assignable; once entered in
  Primer (or supplied via a sub-inventory ingester) they'll flow through.
