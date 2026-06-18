# Image folder inventory — Kapoor Galleries Drive (2026-06-18)

Catalog of the 21 Drive folders that hold all photographic and video
content. Cataloged by a parallel agent crawl; see the source for the
filename and pattern observations.

## Critical constraint

**No image filename contains a KG-# token.** Every image follows
`<YYMMDD>_KapoorGalleries[_<Subject>]_<4-digit-seq>.jpg`. To wire
images to inventory rows, one of these has to happen:

1. **Contact-sheet PDF mining** — every shoot folder ships a
   `*_ContactSheet.pdf`. If the PDF includes KG-# annotations alongside
   sequence numbers, we can extract a `date-seq → KG-#` map.
2. **Curator sidecar map** — a manually-maintained
   `data/image_map.csv` with columns `kg_id, drive_folder, image_seq`.
3. **Filename rewrite** — relabel images at the source. Heaviest
   touch; only worth it if the gallery already plans a Drive cleanup.

Until one of the above happens, the website feed uses the
**Primer CDN URLs** (already in `primary_image_url` for ~640 works,
~45% coverage). The remaining 776 active works show no image on the
website.

## Folder roster

| # | Name | Drive ID | Role | LowRes/FullRes | Est. images | Likely inventory? |
|---|---|---|---|---|---:|---|
| 1 | Images (root) | `1s4emmeulXSxWnB3iOkTZ_XivU5NntWll` | umbrella | — | (children) | mixed |
| 2 | 210212 Missing Shots FINALS | `12jNakWR07xOWtjBcgPXHTypi0RXvWbMr` | shoot | yes | ~30 | ✓ |
| 3 | 200915 Headshots | `14-gJmPMTzN1AwaXzhB0Ygn2BMuCWEMpf` | people | yes | ~500 | ✗ |
| 4 | 201013 Flats | `19H8fGDR0ZrDaKD8n_C-z1ymyL9IMJ_11` | shoot | yes | ~150 | ✓ |
| 5 | 240829 Flat Art | `1NzXRKnGsYZLNWz-1m7gkQqSKqKGokgsp` | shoot | yes | ~150 | ✓ |
| 6 | 250623 3D Objects | `1RR4U5_Q9K7HYeivLQ-RYrCTDNd-4-y6u` | shoot | yes | ~60 | ✓ |
| 7 | 220128 Flats | `1TAt6-1DE8EgcVUZao5dHDAnUHXXOI5h0` | shoot | yes | ~90 | ✓ |
| 8 | 240130 Flats | `1XfmzOiSDMIyeSrZnFlC2gb4snIUV6OGC` | shoot | yes | ~40 | ✓ |
| 9 | 200225 Flats | `1adimXbGmt83Xq9R1safF2sTGrZbBc6xh` | shoot | JPEG/TIFF | ~350 | ✓ |
| 10 | Edited Finals | `1gqy8Ue4IkSo1KXgWryXiDXfLFy-P10z9` | rollup | per-shoot subs | 1000s | curated overlap |
| 11 | 240228 Flats | `1khiAM0dUCV2kGVUL1iLv4MaSubJqjot5` | shoot | yes | ~50 | ✓ |
| 12 | 210122 General Shoot | `1mp5O4i2R58YSePRxONVwPT3Sbs1Ro52h` | shoot | yes | ~165 (Flats+Statues) | ✓ |
| 13 | 240130 3D Objects | `1nmlfGRmtpxairheQWJ0FSgKz4NK_BzG7` | shoot | yes | ~220 | ✓ |
| 14 | 240228 3D Objects | `1ovlpMkEAkNnrOPiVYolrMtGH7KXgf9yc` | shoot | yes | ~165 | ✓ |
| 15 | 220308 Flat Art | `1pPA3jcLwEwojJYbSTeYlvx6xQywmVgtN` | shoot | yes | ~140 | ✓ |
| 16 | 200915 Statues | `1w6GMrKuuBdMu7K2LeRO1TP6Ot9l078r8` | shoot | yes | ~106 | ✓ |
| 17 | 220217 Flats | `1w71DUO08rDKtVQDoShWyMma1RgcIgVcH` | shoot | yes | ~34 | ✓ |
| 18 | 201014 Objects | `1whdB5B5RalYDJ_b8qHVjjQD4lDkuIbAu` | shoot | yes | ~130 | ✓ |
| 19 | 200916 Gallery Interiors | `1xJaXCKZGot0Zk4RucpOUnULnishyqctn` | space | + Reprocessed | ~70 | ✗ |
| 20 | 240829 3D Objects | `1xYAUxD1FzJxpjs-UXCQyllxeL2MRonir` | shoot | yes | ~220 | ✓ |
| 21 | 251223 Video Shoot | `1yTIUaQcZmDEnlMbf5IwGmMzUBRPrkoT-` | video | (videos only) | 0 imgs | ✗ |

**Aggregate**: ~14 inventory shoots → estimated **900–1200 distinct
artworks photographed**, spanning Feb 2020 – June 2025.

## Important deduplication rules

- **Within a shoot folder, LowRes and FullRes contain the same images
  at different resolutions.** Always dedupe on LowRes (or FullRes) —
  never count both.
- **Folder #10 "Edited Finals" overlaps the per-shoot folders.** It's
  a curated rollup of selects. Treating it as a separate set would
  double-count.
- **Folders #3, #19, #21 are NOT artwork inventory** — they're
  people / gallery space / video. Exclude from the inventory→image
  mapping work entirely.

## Recommended next step (the bridge to a complete feed)

Mine the ContactSheet PDFs for KG-# annotations. If the format is
consistent — e.g. each contact sheet thumbnail is labeled with its
KG-# — we can build the date-seq → KG-# map automatically with
pdfplumber + regex.

If not, fall back to a one-time curator pass: produce a sidecar
`data/image_map.csv` and merge it into `website_inventory.json` via
the exporter's `alternates` field.
