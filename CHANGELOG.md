# Changelog

## 0.4.0 — current branch · 120+ commits

Major milestones since the initial commit (2026-05-06):

> 1,528 works (1,417 active + 111 external) · **624 Artsy-eligible & import-ready (44%)** · **621 photo-away** · 128 attributed (9%) · 6 conflicts · 9 sources · **89 tests** · 42 CLI commands · CI green.
>
> Combined ready-or-photo-away: **1,245 of 1,417 active works (88%)**.

### 0.4.11 — Artsy upload pre-flight hardening

- **`artsy_upload.csv` headers now byte-for-byte match the official
  Artsy template** (literal embedded newlines: `"Title\n"`,
  `"Inventory ID \n (OPTIONAL)"`).  The export previously used tidied
  trailing-space headers that Artsy's column-matching importer would
  have failed to map.  Verified equal to
  `data/raw/Kapoor_Galleries_Bulk_upload_Template_Artsy.xlsx`.
- **'Untitled' vs 'Need title' distinction** made consistent across
  check-artsy, the upload exporter, and lint via a shared
  `normalize.INTERNAL_PLACEHOLDER_TITLES` constant.  'Untitled' is a
  valid art title (kept); internal placeholders error and are held
  back from the upload CSV.  Eligible count is now an honest **624**
  (was 637 before holding back 13 'Need title' works).
- **check-artsy column reader** collapses internal whitespace so it
  parses the newline headers and reports the real KG-# (was silently
  falling back to "row5").
- **Full pre-flight audit** of the 624-row export: 0 invalid
  classifications, 0 bad years (range 101–1971), 0 non-numeric or
  out-of-range dimensions/prices.  Import-ready.

### 0.4.10 — photography punch list

- **`reports/photo_queue.md` + `data/photo_queue.csv`** emitted by
  `make report`.  Markdown is grouped by classification (Sculpture 224,
  Drawing/Collage 191, Painting 117, Photograph 27, Print 26, …) with
  KG-# / title / medium / year so a photographer can find each work
  in storage.  CSV is one row per work with a
  `ready_when_photographed` boolean for shoot-day check-off.
- **Apps Script "Show photo queue"** menu item renders the same data
  in a sidebar in the master Sheet (pulls `photo_queue.csv` via
  UrlFetchApp, buckets by classification).
- Filtering excludes external sub-inventory records (status='external')
  and works that already have a primary image, so the count is honest.

### 0.4.9 — 36 derivable mediums (only-need-image: 585 → 621)

For 36 of the 89 works missing only `medium` and image, the title or
classification gave unambiguous medium:
- 21 sculptures with explicit material in title (bronze, gold, gilt-
  bronze, stone, ivory, sandstone, etc.).
- 7 photographs (19th/early-20th c. Indian subjects) → gelatin silver
  print (period default).
- 3 illustrated books (Royle's Himalayan botany, Kipling Jungle Book,
  period photo albums) → "Lithograph plates bound in book" /
  "Photographic prints bound in album".
- 2 prints: KG-2110 "46 Etchings of India" (etching) and KG-2237
  Mordaunt's Cock Match (hand-coloured aquatint with stipple).
- 3 decorative arts: 2 watered-steel swords/knives, 1 Japanese
  akoda nari kabuto (iron with lacquer).

### 0.4.8 — push 22 nearly-ready works, fix Air India over-firing

- **Resolved 22 nearly-ready works** (44 field resolutions): 14 more
  travel/airline posters (Kashmir Calling, Pan Am India, TWA India,
  Fly Japan Air Lines, etc.), 8 Indian miniatures / manuscript folios.
- **Caught the Air India auto-rule over-firing on 8 ephemera works**
  (postcards / tickets / timetables / in-flight menus / safety
  pamphlets are NOT travel posters).  Reclassified each as
  "Ephemera or Merchandise".
- **Added `_excludes` pattern to the auto_resolution matcher** — lets
  a `title_contains` rule skip false-positive cohorts.  Tightened
  Visit India / Air India / Sabena rules with
  `title_excludes: ["ticket","timetable","postcard","menu","pamphlet",
                    "brochure","safety","in flight"]`.
- **Sub-inventory works stamped `status='external'`** — Graham/
  Textile-Boxes entries no longer pollute the eligibility denominator.
  Honest active-works percentage is now 45% instead of a diluted 42%.
- **38 image-only-blocked works classified** from title hints
  (sandstone heads, Pala bronzes, Tibetan thangkas, Indian miniatures,
  Daniell Calcutta views as aquatints, Air France travel poster,
  pashmina shawl, Japanese cloisonné polearm, gau amulet box, etc.).
  "Only-need-image" cohort 547 → 585.
- **17 nearly-ready works pushed over the line** via per-work medium /
  classification fills.  Artsy-eligible 600 → 615 (subsequently 637).

### 0.4.7 — long-tail conflict cleanup → 6 irreducible conflicts

- **4 more travel posters → "Posters"** (Sabena, Pan Am, Kashmir, Simla)
  matching the 25 already resolved.  17 → 13.
- **2 illuminated manuscripts → "Drawing, Collage or other Work on
  Paper"** (consistent with the plurality of 21 of 38 other
  manuscripts in the inventory).
- **KG-1012 Khanjar** — `match_workbook` recorded `classification =
  "Khanjar"` (not a valid Artsy category; it's the object type).
  Resolved to `Design/Decorative Art`.  Medium also expanded to the
  full string from `bulk_upload`.
- **KG-1093 thangka medium** — dropped redundant "Thangka -" prefix
  since the form is captured by `classification = Painting`.
- **8 Himalayas-vs-bulk title prefixes** — `price_list_pdf` appended
  "..., 18th century" / "..., 1600-1699" to titles; resolved to the
  bare bulk-upload title (century belongs in `year`, not `title`).
- **KG-1443 manuscript medium** — dropped redundant ", Manuscript"
  suffix.

**Conflicts: 17 → 6.**  The remaining 6 are genuinely irreducible:
- `KG-1312` (6 field conflicts) — the known duplicate-ID Primer bug:
  two physically different works ("Battle between Banasura and
  Krishna" 1700 vs "Vasishtha Teaches Rama and Lakshmana" 1775) share
  one KG-#.  Needs Primer-side renumbering, not a resolution-layer
  pick.
- `KG-1813 / 1814 / 2106 / 2224 / 2375` — real price/dimension
  disagreements between the Himalayas price list and the bulk upload
  for the same physical work (e.g. KG-2106 \$30k vs \$80k).  Need
  physical verification, not a guess.

**Session total**: conflicts 257 → 6 (97.7% reduction).

### 0.4.6 — normalization fixes clear cosmetic conflicts

- **Unescape FileMaker bracket artifacts** — Primer's Artsy CSV exports
  `\[FAKE\]` while the bulk-upload xlsx has `[FAKE]`; `clean()` now
  unescapes, so they stop registering as title conflicts.
- **Normalize spacing around newlines** — `"paper  \nInscribed"` vs
  `"paper\n Inscribed"` were flagged as medium conflicts though
  identical; `clean()` collapses the spacing.
- **Strip trailing commas from titles** — `normalize_title` now strips
  a trailing comma (price-list vs bulk-upload disagreed only on that).
- **Conflicts dropped 24 → 17.**  The remaining 17 are genuine: the
  KG-1312 duplicate-ID Primer bug, 4 Posters-vs-Print works, and a
  handful of real price/dimension disagreements between the Himalayas
  price list and the bulk upload.

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
