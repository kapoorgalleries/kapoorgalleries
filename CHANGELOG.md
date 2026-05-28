# Changelog

## 0.4.0 — current branch · 120+ commits

Major milestones since the initial commit (2026-05-06):

> 1,528 works · 600 Artsy-eligible (39%) · 128 attributed (8%) · 24 conflicts · 9 sources ingested · 83 tests · 42 CLI commands · CI green.

### 0.4.5 — travel posters reclassified to "Posters"

- **25 vintage travel/advertising posters** (Visit Kashmir, SwissAir to
  India, Air India, etc.) were split between `artsy_csv` = "Posters"
  and `bulk_upload_xlsx` = "Drawing, Collage or other Work on Paper".
  Per owner decision, these belong in Artsy's dedicated **Posters**
  category.  Resolved all 25 and **reversed the 4 travel-poster
  auto-rules** (Visit India / travel poster / Sabena / Air India) that
  had previously mapped to Drawing/Collage.
- **Conflicts dropped 49 → 24.**  Remaining conflicts are now a long
  tail of ≤4-work patterns needing per-case judgment, not systematic
  source-mapping drift.

### 0.4.4 — conflict-pattern tooling + first bulk resolution

- **`kg-inv conflict-patterns`** — collapses the conflict list into
  distinct disagreement patterns.  Revealed that 211 of 257 conflicts
  were a single pattern: works-on-paper classified "Painting" in
  `artsy_csv` (Primer's internal value) vs "Drawing, Collage or other
  Work on Paper" in `bulk_upload_xlsx` (the Artsy-correct value).
- **`kg-inv resolve-pattern`** — settles every work matching one
  pattern in a single command (with `--dry-run`, `--prefer`
  validation, and human-resolution skip-guard).
- **Applied the 211-work resolution** — verified all 211 have a
  paper/wasli medium, so "Drawing, Collage or other Work on Paper" is
  unambiguously the Artsy classification.  **Conflicts dropped
  257 → 49.**  Recorded in `data/human_resolutions.yaml`, attributed
  to sanjay@kapoors.com.
- **`audit-rules` REDUNDANT status** — distinguishes genuinely-unused
  rules (DEAD: 1) from safety-net rules matching already-correct works
  (REDUNDANT: 10).  Was previously over-reporting 11 as DEAD.
- **`suggest-rules` noise filter** — drops stopword medium-descriptors
  (gold/paper/with) and placeholder-title clusters (Need title /
  Untitled); 77 → 66 actionable candidates.

### 0.4.3 — Himalayas price list + cross-reference + Textile Boxes

- **Art of the Himalayas price list** (12 KG-# linked thangkas) —
  first price-list source with direct KG-# linkage; pulls price,
  dimensions, provenance, exhibition into the master record.  Two
  works added below the previous KG-1000 floor (KG-0012, KG-0906)
  that no other source carried.
- **Textile Boxes ingester** — 6-box hierarchy from the docx;
  classification=Textile Arts, provenance_text=full description.
- **`kg-inv match-external`** — fuzzy-match sub-inventory entries
  against KG-# titles; filters out generic KG titles ("Untitled",
  "Portrait") that would attract false positives, combines
  token_set + partial_ratio for stricter matching.
- **Mixed-fraction dim parser fixes** — `normalize_decimal('29 1/4')`
  was parsing as 291.0 (space-strip-then-regex bug); now handles
  ASCII fractions, unicode vulgar fractions (¼ ½ ¾ ⅛ ⅜ ⅝ ⅞), and
  unicode fraction-slash (U+2044) correctly.
- **Surfaced 10 new real conflicts** between the Himalayas and bulk
  upload sources — price disagreements (KG-1813 $24k vs $38k,
  KG-2106 $30k vs $80k), title strip vs full-version differences.

### 0.4.2 — Graham sub-inventory + curator tooling

- **Graham Inventory ingester** (105 owned-collection works) — first
  enabled sub-inventory, ~50 KB PDF committed for CI rebuilds.  Parser
  is conservative on artist/title splitting (combined-string title)
  but extracts year reliably (42 of 105).
- **`kg-inv timeline`** — append-only `data/history.csv` snapshot of
  overview metrics (works, eligible, attributed, conflicts).  Same-day
  re-runs replace, don't accumulate.
- **`kg-inv audit-rules`** — DEAD/SUSPECT/OK status per auto-resolution
  rule, based on actual firing counts and curator overrides in the
  human_resolutions layer.  Currently 11 of 40 rules DEAD in this
  inventory — candidates for pruning.
- **`kg-inv check-artsy` strengthened** — placeholder-title detection
  ("Untitled", "Need title"), oversize-dimension warnings (>200 in),
  excessively-long titles.  Caught 24 placeholder titles in the
  current upload-ready set.
- **Apps Script "Show timeline"** — pulls `history.csv` and renders a
  per-day table with green/red deltas, so curators see progress
  without leaving the Sheet.
- **`Inventory_for_2024_catalog.xlsx` reclassified as `reference`**
  (not inventory) — it's a curatorial brainstorm document with 170
  untethered title strings, no KG-# / artist / medium.

### 0.4.1 — output determinism & comma-value bug fixes

- **Dropped `canonical_updated_at` from `master.csv` / `master.json`** — it
  was the consolidate-run timestamp, identical for every row, causing
  1,415-row diffs on every `make all` run.  Still in the SQLite `works`
  table for any consumer that needs it.
- **`coverage_report.md` now shows file mtime instead of extraction
  time** — same per-run-timestamp problem; report no longer drifts on
  every `make all`.
- **`provenance_report.md` "Conflict counts per field" no longer
  inflated by resolution sources** — was reading from the
  `v_conflicts` view, which counted auto-resolution overrides as
  conflicts against Primer.  Numbers now match `data/conflicts.csv`
  exactly (was: classification 486 / medium 21 / artist 21 / …;
  now: classification 243 / medium 7 / no phantom artist column).
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
- **7 new determinism + regression tests** pinning byte-equality of
  exports (CSV / JSON / coverage report), comma-value preservation,
  and resolution-source exclusion from conflict counts.

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
