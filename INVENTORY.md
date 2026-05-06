# Kapoor Galleries — Master Inventory System

A reproducible, conflict-aware ETL pipeline that consolidates every gallery
inventory source (Primer Archives, Artsy bulk-upload exports, Match
Workbook, sub-inventories, image folders, gap-report emails) into one
canonical record per work — with **per-field provenance**, **flagged
(never silently merged) conflicts**, and a **two-way Primer cleanup
punch list**.

[![CI](https://github.com/kapoorgalleries/kapoorgalleries/actions/workflows/inventory.yml/badge.svg)](https://github.com/kapoorgalleries/kapoorgalleries/actions/workflows/inventory.yml)

## What's in this repo

```
src/                 ETL: ingesters → consolidate → exporters → reports
catalog/sources.yaml Source registry: every Drive file the pipeline ingests
data/                inventory.db, master.csv, conflicts.csv, gaps.csv,
                     artsy_upload.csv, master_provenance.csv,
                     primer_corrections.csv, raw/  (auto-rebuilt by CI)
reports/             markdown coverage / gaps / provenance reports
apps_script/         Code.gs that lives inside the master Sheet
tests/               23 passing pytest tests
.github/workflows/   inventory.yml: auto-rebuild on every push
tools/               operator runbooks (e.g. fetching the 108 MB Primer PDF)
```

## How a value reaches the master sheet

```
Drive / Gmail file ──► ingester ──► observations table (long format)
                                            │
                                            ▼
                                  consolidate.py picks the canonical
                                  value per field by priority:
                                     1. human_resolution   (always wins)
                                     2. auto_resolution    (rules-based)
                                     3. match_workbook     (curator)
                                     4. Primer-derived     (artsy_csv,
                                                            primer_pdf)
                                     5. otherwise most-recent
                                            │
                                            ▼
                                  works table (canonical, one row per KG-#)
                                            │
                            ┌───────────────┼───────────────┐
                            ▼               ▼               ▼
                  data/master.csv   data/conflicts.csv   reports/*.md
                  +_conflict cols   data/gaps.csv        coverage_report
                                    data/artsy_upload    gaps_report
                                    data/master_         provenance_report
                                       provenance
                                    data/primer_
                                       corrections
                                            │
                                            ▼
                  apps_script/Code.gs ──► KG Master Inventory Sheet
                  (Refresh / Stats /       (conflicts painted red,
                   Suggest Resolution)      Inventory ▾ menu)
```

## Cumulative impact (this branch)

| Metric | Initial | Now |
|---|---:|---:|
| Works | 652 | **652** |
| Sources ingested | 1 | **5** (Artsy CSV + Match Workbook + Image Dir + auto + human) |
| Artsy-eligible rows | 420 | **568** (+148, 87% of inventory) |
| classification coverage | 78.5% | **91%** |
| medium coverage | 81.6% | **93%** |
| Real conflicts caught | 1 | **11** |
| Primer corrections suggested | — | **529** |

## CLI

```bash
# Workflow shortcuts (Makefile)
make all                    # init + ingest + consolidate + report
make stats                  # one-screen dashboard
make health                 # full system diagnosis
make demo                   # guided tour of features

# Single commands (kg-inv ...)
kg-inv refresh              # ingest + consolidate + report + lint + check-artsy
kg-inv triage               # interactive conflict resolution
kg-inv resolve <kg> <f> <v> # record one human resolution
kg-inv promote <kg> <f>     # lock in current canonical value
kg-inv batch-resolve <yaml> # bulk-apply pre-prepared resolutions

# Read-only views
kg-inv stats                # dashboard with progress bars
kg-inv conflicts            # list unresolved disagreements
kg-inv gaps --max-missing 1 # punch list of nearly-ready works
kg-inv show KG-1312         # everything we know about one work
kg-inv search "Krishna"     # substring search across fields
kg-inv artists              # roster sorted by work-count
kg-inv lint                 # data-quality findings
kg-inv check-artsy          # pre-flight Artsy upload validation
kg-inv inspect-source <s>   # what one source contributed
kg-inv source list          # registry status
kg-inv source enable/disable <name>  # toggle from CLI
kg-inv suggest-rules        # mine inventory for new rule candidates
kg-inv export-filtered      # write a filtered subset CSV
```

## Adding a new source

1. Drop the file at `data/raw/<name>` (or run `./scripts/bootstrap.sh`
   for bulk Drive download via `gdown`).
2. Append an entry to `catalog/sources.yaml` with `type:` matching one
   of the ingesters in `src/cli.py:INGESTERS`.
3. `make all` (locally) — or just push and let CI rebuild.

## Going to the Sheet

`apps_script/Code.gs` lives inside the empty
`KG Master Inventory System - 2026-05-06` Google Sheet
([1Kf175...](https://docs.google.com/spreadsheets/d/1Kf175vGkFiOMLGFoslUTjsA4hUpnIEeauh_WjSaSjUc/edit)).
Paste it once via Extensions → Apps Script. After that, the
**Inventory ▾** menu has:

- **Refresh from repo** — pulls master.csv from this branch and renders
  it; conflicts are auto-painted red.
- **Show stats** — sidebar with progress bars per field.
- **Highlight conflicts** — re-runs only the painter (faster).
- **Inspect selected work** — sidebar showing missing/conflict status.
- **Suggest resolution for selected cell** — for any red cell, shows
  the alternatives and a ready-to-copy `kg-inv resolve …` command.
- **Open Drive folder for KG-#** — opens a Drive search in a new tab.

## Resolution loop

When the master sheet shows red, the team has two options:

1. **Add a deterministic rule** to `data/auto_resolution_rules.yaml`
   (e.g. "medium contains paper → classification = Drawing"). Rules
   apply across the whole inventory in one pass. 13 rules currently
   live.

2. **Record a per-(work, field) human decision** with `kg-inv resolve`,
   appended to `data/human_resolutions.yaml`. Always wins, never
   silently overridden. Useful when no general rule applies.

Both flow through to `master.csv` on the next `make all` (or CI run),
which propagates to the Google Sheet on the next **Refresh from repo**.

## Two-way Primer punch list

`data/primer_corrections.csv` is the *reverse* of master.csv: it
enumerates every (work_id, field) where the consolidated record
disagrees with what's currently in Primer (per the Primer→Artsy CSV
snapshot). Each row is a single, specific Primer-edit instruction with
the evidence and reason.

Currently 529 corrections; mostly classification fixes for paper-medium
works that Primer has tagged as "Painting" but should be "Drawing,
Collage or other Work on Paper" for Artsy.

## Source priority — why it wins what it wins

- **Primer is authoritative for facts** (KG-#s, image URLs, dimensions
  Primer has measured) but its category labels are coarse (everything
  paper-on-paper is "Painting" in Primer).
- **The Match Workbook is authoritative for Artsy categories**. The
  curator built it specifically to map gallery works to Artsy's taxonomy.
- **Auto-resolution rules are authoritative for gallery conventions**
  (e.g. all sandstone works are sculpture).
- **Humans are authoritative for everything else**.

Conflicts are still flagged (red in the Sheet, in `conflicts.csv`,
filterable in `kg-inv conflicts`) because they reveal Primer
data-quality problems worth fixing — the system never silently smooths
them over.

## Known limitations

- No live Primer API. The 108 MB `KG_Available Works_5-13-2025_1065.pdf`
  and 172 MB `KG Inventory - 9-25-2025.pdf` are too big to fetch through
  the Drive MCP in-session — drop them into `data/raw/` per
  [`tools/FETCH_PRIMER_PDFS.md`](tools/FETCH_PRIMER_PDFS.md).
- Sub-inventory ingesters (Graham, Darion, Huc, Torr, Textile Boxes)
  are stubs; they need title-fuzzy-matching to KG-#s once the source
  files are dropped locally.
- The artist field is at 0% coverage because Primer records every work
  as "Unknown Artist" — these are assignable, not structurally missing.
- The 27 KB `Inventory_for_2024_catalog.xlsx` is cached but its
  year-grouped layout doesn't carry KG-#s, so a parser is deferred
  until the value is clearer.
