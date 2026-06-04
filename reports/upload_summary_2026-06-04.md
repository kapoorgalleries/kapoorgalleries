# Kapoor Galleries — Bulk Upload Summary

**Date:** 2026-06-04
**File:** `kapoor_galleries_artsy_upload_2026-06-04.csv` (623 rows, official Artsy template)
**For:** Peyton Sandler (Artsy)
**FYI:** Sarah Fenner

---

## TL;DR

All 623 rows are **re-imports** of works Artsy already has from the
February 2026 Primer→Artsy snapshot — **not new additions**. The data
has been cleaned up substantially since then. **Please do not run as
a fresh bulk import** until we figure out the overwrite path per
your 5/29 guidance.

## What changed vs the Feb 2026 snapshot

| Field | Works changed | Why |
|---|---:|---|
| **Classification** | **526** | Mostly Indian miniatures on paper reclassified from "Painting" → "Drawing, Collage or other Work on Paper" (Artsy's category for works on paper), plus a batch of travel posters moved to "Posters." |
| **Medium** | **117** | Filled-in or corrected medium strings — completions of truncated values (e.g. `'Jade-hilted and jeweled'` → `'Jade-hilted and jeweled Khanjar'`), removal of redundant suffixes, normalization of internal whitespace. |
| **Title** | **5** | FileMaker bracket-escape artifacts (`'\[FAKE?\] A Prince…'` → `'[FAKE?] A Prince…'`) and internal newline cleanups. No semantic title changes. |
| **Price** | 0 | (Earlier check showed 141 — was a float-vs-int serialization artifact; no actual value differences.) |

### Concrete examples
- **KG-1000:** `Painting` → `Drawing, Collage or other Work on Paper`
- **KG-1319:** medium `Linen backed poster` → `Lithographic print on paper` (travel poster reclassified to Posters category)
- **KG-1428:** title `\[FAKE?\] A Prince on Horseback` → `[FAKE?] A Prince on Horseback`

## Where the corrections came from

- Cross-referenced **9 sources** (Feb 2026 Artsy CSV, the broader Bulk Upload template, Match Workbook, Image Dir, Graham sub-inventory, Textile Boxes, Art of the Himalayas price list, plus auto- and human-resolution layers).
- Surfaced **257 cross-source conflicts** at start; settled all but one through documented per-work decisions (`data/human_resolutions.yaml`, 448 entries, all attributed to sanjay@kapoors.com with reason text).
- The remaining one work is **KG-1312** — see below.

## Held out of the upload

**KG-1312:** Primer has two physically different works under this
inventory number ("Battle between Banasura and Krishna," 1700, $26k,
13×14 vs "Vasishtha Teaches Rama and Lakshmana," 1775, $50k, 9×20).
Marked `status='needs_renumbering'`, excluded from the upload CSV
entirely. Will return once Primer assigns one of them a new KG-#.

## What's coming next (separate workflow, not in this batch)

A photography sprint will produce images for **621 more works** that
are otherwise upload-ready (classification + medium + title all in
place). When those have images:
- They'll be true **new additions** to Artsy (no overwrite question).
- Expected breakdown: 224 Sculpture, 191 Drawing/Collage, 117
  Painting, 27 Photograph, 26 Print, and smaller cohorts.

## Questions for Artsy

1. **Is there an overwrite path** on your end that can safely take
   this 623-row re-import, or should I wait until that's wired up?
2. **If we should hold off**, is a subset safer to send first — for
   example, just the 526 classification corrections, which would
   improve discoverability without touching prices or descriptions?
3. **Any preference on cadence** for the photo-sprint additions —
   one big batch, or rolling as shoots are completed?

## Trust notes

- Every change is traceable: `data/human_resolutions.yaml` records
  each decision with field, old/new value, reason, and decided_by.
- The export passes a CI strict pre-flight (no invalid
  classifications, no bad years, no duplicate Inventory IDs, no
  placeholder titles, no out-of-range dimensions).
- Headers in the CSV byte-for-byte match the official Artsy
  bulk-upload template (verified against
  `data/raw/Kapoor_Galleries_Bulk_upload_Template_Artsy.xlsx`).

---

Happy to walk through any of this on our 11:30am call.

— Sanjay
