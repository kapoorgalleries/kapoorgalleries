# Changelog

## 0.4.0 — current branch · 120+ commits

Major milestones since the initial commit (2026-05-06):

> 1,415 works · 600 Artsy-eligible (42%) · 128 attributed (9%) · 247 conflicts · 6 sources ingested · 67 tests · 33 CLI commands · CI green.

### 0.4.1 — output determinism & comma-value bug fixes

- **Dropped `canonical_updated_at` from `master.csv` / `master.json`** — it
  was the consolidate-run timestamp, identical for every row, causing
  1,415-row diffs on every `make all` run.  Still in the SQLite `works`
  table for any consumer that needs it.
- **`coverage_report.md` now shows file mtime instead of extraction
  time** — same per-run-timestamp problem; report no longer drifts on
  every `make all`.
- **Sorted `master_provenance.csv` `alt_values`** — set iteration order
  isn't stable; same data was producing different orderings across runs.
- **Fixed comma-splitting in three places** (kg-inv conflicts CLI,
  `data/conflicts.csv`, gaps_report.md "Unresolved conflicts" table):
  values like "Drawing, Collage or other Work on Paper" were being
  fragmented into apparent extra entries because SQLite's
  `GROUP_CONCAT` uses comma as separator.  All replaced with
  Python-side aggregation.
- **`kg-inv compare KG-X KG-Y`** — side-by-side work comparison, marks
  differing fields with ≠.  Useful for spotting duplicate-ID Primer
  bugs (e.g. KG-1312).
- **6 new determinism + regression tests** pinning byte-equality of
  exports (CSV / JSON / coverage report) and comma-value preservation.

### 0.4 — bulk upload + data quality

- **Bulk Upload Template ingester** — pulled the 110 KB
  `Kapoor Galleries - Bulk upload Template Artsy.xlsx` (1,415 KG-#s,
  expanding the master record from 652 to **1,415 works** [+763]).
- **Three-bug column-mapping fix** for the xlsx: Artsy's "Medium"
  column actually contains classification, "Materials" contains medium,
  and Excel parsed `11,125` as integer 11125 (recovered to 11.125).
- **Classification taxonomy normalization** — 21 variants down to 8
  Artsy-valid values (`Poster`→`Posters`, `Object`→`Sculpture`,
  `Manuscript Cover` case dedupe, etc.).
- **Suspicious-artist normalization** — Weiner/Wiener/LaPuma
  Consignment / Unspecified Artist all stripped at consolidation.
- **Year and title insights** — `kg-inv years` histogram, `kg-inv
  artists` roster.
- **Per-classification splitter** — `kg-inv split-by-classification`
  for batched Artsy uploads.

### 0.3 — operational tooling

- **`kg-inv` CLI** with 19 subcommands (refresh, triage, resolve,
  promote, batch-resolve, stats, conflicts, gaps, show, search,
  artists, years, lint, check-artsy, inspect-source, source list/
  enable/disable, suggest-rules, export-filtered,
  split-by-classification).
- **`make` shortcuts** — `make stats / lint / health / demo`.
- **Apps Script** — Refresh / Stats / Highlight conflicts / Inspect /
  Suggest Resolution / Open Drive — plus a static
  [`viewer/index.html`](viewer/index.html) sortable HTML browser.
- **`kg-inv check-artsy`** — pre-flight Artsy upload validation.
- **`data/primer_corrections.csv`** — 500+ specific edit instructions
  to make IN Primer to align it with the consolidated record.
- **`kg-inv suggest-rules`** — pattern-mines the inventory for new
  auto-rule candidates.
- **39 tests** covering ingesters, consolidation, resolution
  priority, exports, and CLI views.

### 0.2 — resolution layer

- **`auto_resolution_rules.yaml`** with 38 rules (paper→Drawing,
  sandstone/schist/bronze→Sculpture, khanjar→Decorative, etc.).
- **`human_resolutions.yaml`** + `kg-inv resolve` and `kg-inv promote`
  for per-(work, field) authoritative decisions.
- **Source priority:** human > auto > match_workbook > Primer-derived.
- **Conflict suppression** — resolution sources don't inflate the
  conflict count; conflicts are real disagreements among observation
  sources.
- **`data/master_provenance.csv`** — long-format CSV showing which
  source provided each canonical value.

### 0.1 — pipeline live

- **Long-format observations** table (every value, every source,
  every timestamp) with idempotent canonical works rebuild.
- **Ingesters** for Artsy CSV (Primer→Artsy snapshot), Match Workbook,
  KG Inventory PDF (page-streamed), Primer PDF, Price-list PDF,
  Sub-inventory PDFs, Image directories, Email gap reports.
- **Source registry** in `catalog/sources.yaml`.
- **GitHub Actions CI** rebuilds artifacts on every push.
- **Apps Script** wired to GitHub raw URL (paste once, Refresh ad-lib).
