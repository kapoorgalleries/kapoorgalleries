# Source materials index — Kapoor Galleries website pipeline

Every Drive folder and Sheet shared in this session, what's in it, and
how it relates to the website feed.

## A · Photo shoots (21 folders)

Already cataloged in detail at `IMAGE_FOLDERS.md`. Key fact:
**filenames are date+sequence (`240828_KapoorGalleries_0193.jpg`),
never KG-#.** Wiring shoot images to inventory rows needs either
contact-sheet PDF mining or a curator sidecar map.

- Root: `1s4emmeulXSxWnB3iOkTZ_XivU5NntWll`
- 20 shoot/catalog folders listed in `IMAGE_FOLDERS.md`.
- ~14 inventory shoots → ~900–1,200 unmapped artworks photographed.

## B · Artsy operational archive

**Folder**: `1pVtK4FC8Eu3EGFjpaCG33-DQ7T_wjsjR` ("Artsy")

Monthly upload batches and the duplicate-review queue. Mostly
operational; only tangentially relevant to the website. Contents:
- `Review - Duplicate Candidates` — currently contains campaign docs,
  not actual duplicate lists.
- `Needs Triage`
- `Archive Review - Legacy`
- Per-month batches: `March '25 Upload`, `April '25`, `May '25`,
  `July '25`, `Sept. '25`.

Not pipelined into the website. **Useful context for the
operational Artsy upload flow** (the May 29 "imports broke" call
with Peyton).

## C · KG Website folder

**Folder**: `1XWpvtwHBOVZMiCBeHYMmXTl2vXCMDtRR` ("KG Website")

Source-of-truth materials for the public site. Contents:
- `Needs Triage`
- `Wordpress Website` — legacy WP migration materials.
- `2024 Updates`
- **`Masterworks and Museum Accessions`** — sub-folder with two
  files:
  - `Masterworks and Museum Accessions` (Sheet, 192 MB) — high-prestige
    showcase works that should anchor the website's hero sections.
  - `Notable Sales Page` (Doc, 4.6 MB) — copy for the "Notable Sales"
    page.

**These two files are the showcase content for the website.**
First-class candidates for a `/masterworks` and `/notable-sales`
page. Each needs its own dedicated landing page on the site.

## D · Catalog & Inventory master spreadsheet

**Sheet**: `121gNT3a36wmecXZn_dnbd7FrwEqMiuZ9NqzG2Ssocb4`
("Catalog & Inventory", **500 MB**)

The richest curator-grade content I've found. Sample columns:
- Title, Origin, Date, Medium, Dimensions
- **Physical Location** — where in the gallery ("Glass Cabinet",
  "Drawer 13", "Closet A2", "Gallery 4/28")
- **File Location** — per-work Drive folder link
- **Acquired From** — auction house, dealer, estate
- **Literature & Exhibited** — citation-grade bibliography
- **Provenance** — full chain back to known prior owners
- **Essay Written (Y/N)** — flag for whether scholarly text exists

**This is the most leveraged enrichment source for the website.**
Provenance, location, literature, exhibitions are all critical
gallery-grade fields the public site needs but the canonical
`master.csv` mostly lacks (1% coverage on most of these).

**Catch**: the Sheet has no KG-# column in the snippet I saw — works
are identified by title only. Mapping it to existing KG-# inventory
requires title-fuzzy-match (the same `kg-inv match-external` tool I
built earlier will work; just need to run it against this sheet).

## E · Inventory Files folder (vast archive)

**Folder**: `1hq46lLQF08vDfgTSNDgGlPVJIBoruvzi` ("Inventory Files")

24 sub-folders organized by cohort, catalog, or acquisition source:

**Past catalog publications:**
- Arcane Masters catalogue (unsold only)
- God/Goddess 2020 Catalogue
- Virtual Ragamala
- 2021 Catalogue - Incarnations of Devotion
- 2022 Catalog
- 2024 Uploads
- Rasikapriya 2024

**Cohort organization:**
- Portraits, Portraits catalogue, Indian Miniatures
- Travel Posters
- Indian Objects, Himalayan Art, Gandharan pieces
- KG Textile Works, Tibetan Trunks
- Krishnanagar Clay Figures

**Acquisition sources:**
- Sotheby's acquisitions June 2020
- Concept Art Gallery Acquisitions March 2020
- Ghose Estate Consignment

**Other:**
- Review - Duplicate Candidates
- Archive Review - Legacy
- Misc, Barthe Photos Prior to PU

These are folders of folders; each leaf likely has its own catalog
PDF / images / metadata. **The catalog publications** (Arcane Masters,
Incarnations of Devotion, God/Goddess) are particularly valuable —
they're curated scholarly groupings that map well to website
"collection" pages.

## What's actually in the website feed today

`data/website_inventory.json` (the v1 I just shipped):
- 1,377 active works from the canonical `master.csv`.
- Field coverage: title 100%, classification 93%, medium 94%,
  year 63%, image 45%.
- Empty on the gallery-grade fields the user just dropped:
  provenance 1%, exhibitions 1%, publications 0%, signature 1%,
  location 0%.

## Proposed next priorities (in order of leverage)

### v2 — wire in the rich curator data (highest impact)
Pull the Catalog & Inventory spreadsheet, fuzzy-match titles to
existing KG-#s, and merge provenance / literature / location into
each work's record. Expected impact: provenance jumps from 1% to
likely 30–50% coverage; exhibitions and literature similarly.

### v3 — masterworks & notable-sales pages
Add a separate feed for the showcase content (`/masterworks`,
`/notable-sales`) sourced from the Masterworks and Museum
Accessions Sheet + Notable Sales Page Doc. These pages need
dedicated routes on `sb1-vuxiwzek`.

### v4 — collection landing pages
Pre-define "collection" groupings from the Inventory Files archive
(Arcane Masters, Incarnations of Devotion, Rasikapriya, Travel
Posters, Himalayan, etc.) — each becomes a curated landing page on
the website with hand-selected works.

### v5 — wire shoot images to works
Mine ContactSheet PDFs or build a curator sidecar map; merge into
`image.alternates`. Once done, image coverage jumps from 45% to
near-complete.

### v6 — operational (not website) backlogs
The Artsy archive (folder B) and the various "Needs Triage" /
"Review - Duplicate Candidates" folders feed the upload-side
workflow, not the website. Different track.

---

## Open questions

These are decisions only the gallery can make:

1. **Which collection landings to publish in v1.0?** Some of the
   catalogs (Arcane Masters "unsold only") explicitly exclude sold
   works — others may not. Site needs a published-set decision per
   collection.
2. **Where do prices live?** Public site, or "Price on request" by
   default with prices only on a logged-in admin view? Currently
   the feed has both variants (`--no-prices` flag).
3. **What's the legal posture on provenance disclosure?**
   Provenance chains may name living individuals; some auction
   contracts restrict republication. Need a per-work or
   per-collection visibility rule.
4. **Whose Drive credentials does the site use to fetch images
   long-term?** Primer URLs expire ~2027. Mirroring to a public
   Cloudflare/S3 bucket needs a one-time operational decision.
