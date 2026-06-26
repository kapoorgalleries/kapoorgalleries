# Integrating `data/website_inventory.json` with `sb1-vuxiwzek`

Quick start for whoever's wiring up the public-facing Kapoor Galleries
website (StackBlitz project `kapoorgalleries/sb1-vuxiwzek`).

> **Two ways to consume the data:**
> 1. **Static feeds** (this doc) — fetch the committed `data/*.json`
>    at build time and filter client-side. Simplest; no server.
> 2. **Live REST API** ([`BACKEND_API.md`](./BACKEND_API.md)) — point
>    the site at `/api/works?...` for server-side search, filter, and
>    pagination. Same item shapes, so the two are interchangeable and
>    the API can fall back to the static feeds.

> **Status today** (2026-06-18): 1,377 active works in the feed.
> 624 (45%) have images via Primer's CDN. The remaining 753 active
> works are awaiting a date-seq → KG-# mapping from the Drive shoots
> (see `IMAGE_FOLDERS.md` for why).

## 1 · Pull the feed

The pipeline writes `data/website_inventory.json` on every `make all`
in the inventory repo. Three ways to consume:

**A. Build-time fetch (recommended for a static site):**
```bash
# In sb1-vuxiwzek's prebuild step
curl -fsSL \
  https://raw.githubusercontent.com/kapoorgalleries/kapoorgalleries/claude/gallery-inventory-system-phuSJ/data/website_inventory.json \
  -o public/inventory.json
```

**B. Runtime fetch (SPA):**
```ts
// vite/react/svelte – wherever your data loader lives
const feed = await fetch("/inventory.json").then(r => r.json());
```

**C. Import as a module (small, type-safe, no network):**
```ts
import feed from "./inventory.json" assert { type: "json" };
```

Use **A** unless the site needs live updates. The feed is regenerated
on every push and deterministically ordered, so the diff between
successive checkins is meaningful.

## 2 · TypeScript types

Copy `docs/WEBSITE_SCHEMA.md`'s TypeScript block into a `types.ts`
file in `sb1-vuxiwzek`. It's the source of truth.

A minimal hand-written extract:

```ts
// src/types/inventory.ts
export type Feed = {
  schema_version: 1;
  generated_at: string;
  count: number;
  facets: {
    classification: Array<{ value: string; count: number }>;
    tags:           Array<{ value: string; count: number }>;
    with_image:     number;
    without_image:  number;
  };
  works: Work[];
};

export type Work = {
  id: string;
  kg_id: string;
  slug: string;
  url_path: string;
  title: string;
  classification: string | null;
  medium: string | null;
  year: number | null;
  year_display: string | null;
  artist?: string;
  period_school_region?: string;
  materials?: string;
  provenance?: string;
  exhibitions?: string;
  publications?: string;
  signature?: string;
  coa_status?: string;
  dimensions: {
    height_in: number | null;
    width_in:  number | null;
    depth_in:  number | null;
    display:   string | null;
  };
  price: {
    usd: number | null;
    display: string;
    available: boolean;
  };
  image: {
    primary: string | null;
    alternates: string[];
    thumbnail: string | null;
  };
  tags: string[];
  status: "available";
};
```

## 3 · Routing

```
/                       → home / hero
/works                  → grid view, all works
/works?cls=Sculpture    → filter by classification
/works?tag=tibetan      → filter by tag
/works/<slug>           → individual work detail page
```

Each work's `url_path` is pre-baked — drop it straight into your
router config. With SvelteKit:

```ts
// src/routes/works/[slug]/+page.ts
export const load = async ({ params, fetch }) => {
  const feed: Feed = await fetch("/inventory.json").then(r => r.json());
  const work = feed.works.find(w => w.slug === params.slug);
  if (!work) throw error(404);
  return { work };
};
```

## 4 · Filter / facet UI

Don't re-derive dropdown options from `feed.works.map(w => w.classification)`
— the `facets` block at the top is pre-computed, ordered, and
includes counts so you can label them nicely:

```ts
{feed.facets.classification.map(f => (
  <option value={f.value}>{f.value} ({f.count})</option>
))}
```

## 5 · Images — the gap & the workaround

**Today**, `work.image.primary` is set for 624 of 1,377 works (Primer's
signed CDN URLs). The remaining 753 active works have `null` — show a
clean "image coming" placeholder card.

**Be aware:** Primer URLs are signed with an expiry token
(`?Expires=…&Signature=…`). They're not permanent. Current tokens
expire ~2027. If the site is meant to live longer than that, we'll
need to either (a) re-sign on each pipeline run, or (b) mirror the
images into the gallery's own CDN (S3/Cloudflare).

**The bigger fix**: the gallery has thousands of unprocessed shoot
images in Drive. None of those filenames encode KG-#s today (see
`IMAGE_FOLDERS.md`). To wire those in:

1. Mine the ContactSheet PDFs in each shoot folder for KG-#
   annotations → produce `data/image_map.csv` with
   `kg_id, drive_folder_id, image_seq, role`.
2. Augment the website exporter to merge that file into each work's
   `image.alternates` list.
3. (Optional) move the FullRes TIFs into a public CDN bucket so the
   site can serve high-res when zoomed.

This is a curator-side task and not blocking — the site can ship with
the 624 Primer-imaged works on day one.

## 6 · Public-deploy variant (no prices)

For a deploy where you don't want USD values exposed:

```bash
# In the inventory repo
python -m src.cli export-website \
  --no-prices \
  --out /tmp/inventory_public.json
```

This zeroes out `price.usd`, sets `price.display` to "Price on request"
everywhere, and sets `price.available: false`. Drop that JSON into the
public site instead of the canonical one.

## 7 · Hot reload during local dev

Symlink the feed file into the sb1 project:

```bash
# In sb1-vuxiwzek/public/
ln -s /path/to/kapoorgalleries/data/website_inventory.json inventory.json
# Then run `make all` in the inventory repo — Vite picks up the change.
```

## 8 · Stop-the-presses fields

Two flags the site should respect:

- **`work.status !== "available"`**: shouldn't happen in v1
  (everything emitted IS available). If a future version adds `"sold"`,
  hide such works from the public grid.
- **`work._internal.has_conflict`**: should be `false` in production.
  If you see `true`, it means an unresolved data disagreement leaked
  through — the inventory pipeline normally holds these back. Log it
  loud and skip the work.

## 9 · The richer enriched feed (recommended for v1)

`make report` now produces two inventory feeds:

- `data/website_inventory.json` — base feed (1,377 active works).
- **`data/website_inventory_enriched.json` — base feed PLUS curator-
  grade fields** (provenance, physical location, acquired-from,
  publications/exhibitions) merged in from the master Catalog &
  Inventory Google Sheet via fuzzy title match.

Today the enriched feed adds these fields to ~125 works (8.8% of the
inventory). The frontend should prefer the enriched feed when it
exists and gracefully fall back to the base — the schemas are
identical except for the three extra optional fields documented in
`WEBSITE_SCHEMA.md`.

There's a sibling `data/enrichment_audit.csv` that records every
match the system made (KG-#, score, external title, what was merged).
Spot-check it once after each pipeline run — wrong matches at the
high-confidence threshold (>=88) are rare but possible.

## 10 · Masterworks / museum-accessions feed

A separate `/masterworks` page is sourced from
`data/masterworks.json`:

```ts
import mw from "./masterworks.json" assert { type: "json" };
const norton = mw.works.filter(w => w.acquired_by === "Norton Simon Museum");
```

Each masterwork carries:
- A `label_copy` field that's typically scholarly prose with poetry
  citations — use a `<article>` wrapper with serif typography.
- A `museum_link` URL to the institution's collection record — show
  as "View at the Metropolitan Museum" / "View at Norton Simon" link.
- `acquired_by` makes a great filter facet (Norton Simon 45, San
  Diego 36, Rietberg 27, LACMA 17, Mingei 16, Met 2, Princeton 3, …).

This page is **historical showcase content**, not for sale. Make that
visually clear in the layout (no price, no "inquire" button — instead
"In the collection of the Metropolitan Museum of Art since 2003").

## 11 · Image map workflow (for shoot images)

`data/image_map.csv` is a curator-maintained spreadsheet that bridges
KG-#s to the Drive photo shoots. Once filled in by the gallery,
`make report` merges it into the website feed automatically.

Initialize:
```bash
python -m src.cli apply-image-map --init
# Opens data/image_map.csv with a starter template.
```

Edit (in Sheets or any CSV editor):
```csv
kg_id,drive_url,role,notes
KG-1023,https://drive.google.com/file/d/AAA/view,primary,front
KG-1023,https://drive.google.com/file/d/BBB/view,alternate,verso
KG-1023,https://drive.google.com/file/d/CCC/view,thumbnail,tight-crop
```

`role` is one of `primary`, `alternate`, `thumbnail`. When a curator
promotes a Drive image to `primary`, the previous Primer CDN URL is
preserved as an alternate so we don't lose it.

Drive sharing URLs are auto-rewritten to direct
`drive.google.com/uc?export=view&id=<id>` form, which an `<img>` tag
can render directly (provided the file is set to "Anyone with the
link" — the gallery's default for these folders).

## 12 · Collection landing pages (`/collections/<slug>`)

`data/collections.json` drives a set of curated landing pages mapped
to the gallery's past catalog publications and thematic groupings:

| slug                      | source catalog                       | populated today |
| ------------------------- | ------------------------------------ | --------------- |
| `incarnations-of-devotion` | 2021 Catalogue                       | 243 works       |
| `god-goddess`              | God / Goddess 2020 Catalogue         | 219 works       |
| `indian-miniatures`        | Indian Miniatures cohort             | 132 works       |
| `portraits`                | Portraits catalogue                  | 131 works       |
| `himalayan-art`            | Himalayan Art cohort                 | 47 works        |
| `virtual-ragamala`         | Virtual Ragamala                     | 37 works        |
| `arcane-masters`           | Arcane Masters catalogue (unsold)    | 54 works        |
| `rasikapriya`              | Rasikapriya 2024                     | 8 works         |
| `travel-posters`           | Travel Posters                       | 1 work          |

Membership is driven by `data/collections.yaml` and is a union of:

- `include_tags`: any work carrying one of the listed tag values
  (e.g. `ragamala` → Virtual Ragamala).
- `include_kg_ids`: explicit curator-maintained KG-# list, used for
  catalogs whose membership can't be reduced to a tag filter.
- `seed_titles`: a list of title strings (typically extracted from a
  Drive catalog folder). The exporter fuzzy-matches each (rapidfuzz
  token-set-ratio, threshold 90) against the inventory feed and adds
  the best match. `data/collection_seed_audit.csv` records every
  decision so the curator can spot-check.

To populate one of the scaffolded collections, add an explicit
KG-# list to the YAML:

```yaml
- slug: arcane-masters
  title: "Arcane Masters"
  include_tags: []
  include_kg_ids:
    - KG-1023
    - KG-1187
    - KG-1305
```

Then re-run `make report` (or `python -m src.cli export-collections`).
Scaffolded collections still appear in the feed with `member_count: 0`
— render them as "Coming soon" rather than 404.

Each collection ships with `members[].thumbnail` (falls back to the
work's primary image), so the index card grid can render without a
secondary lookup.

```ts
// SvelteKit-ish
// src/routes/collections/[slug]/+page.ts
export const load = async ({ params, fetch }) => {
  const feed = await fetch("/collections.json").then(r => r.json());
  const coll = feed.collections.find(c => c.slug === params.slug);
  if (!coll) throw error(404);
  return { coll };
};
```

## 13 · Site metadata (`data/site.json`)

A single JSON document the SPA can fetch at build time for
gallery name, address, hours, contact, social, memberships,
navigation, and a pre-built JSON-LD `ArtGallery` block for SEO.

```ts
import site from "./site.json" assert { type: "json" };

// Footer
<footer>
  <p>{site.gallery.name} · {site.address.street}, {site.address.city}</p>
  <p>{site.contact.phone_us} · {site.contact.email_general}</p>
</footer>

// Head — paste the structured-data block
<script type="application/ld+json">
  {JSON.stringify(site.json_ld)}
</script>
```

The schema is curator-edited in `data/site.yaml` — re-run
`make report` (or `python -m src.cli export-site`) after edits.

## 14 · Year fallback (`era_display`)

The base feed now ships an optional `era_display` string for works
whose `year` is null but whose tags carry a period inference. The
site can render this in place of a blank date:

```ts
const dateLabel =
  work.year_display ?? work.era_display ?? "Date unknown";
```

Examples today: `"19th century"`, `"Ancient"`, `"Contemporary"`.
Only emitted when `year === null`; works with a year never carry
this key so there's no redundant signal.

## 15 · Sold-state plumbing

The enrichment step (§9) now consults a `SOLD` column in the curator
Catalog & Inventory Sheet. Rows with `SOLD` set are excluded from
the enrichment merge — but the inventory pipeline does NOT
auto-remove sold works from the public feed, because a fuzzy title
match can collide across centuries ("Krishna and Radha" exists 30+
times in the inventory).

Instead, every SOLD row whose fuzzy title match exceeds 95 (vs the
88-threshold used for normal enrichment) is recorded in
`data/sold_candidates.csv` with shape:

```csv
kg_id,match_score,external_title,current_title,action
KG-1010,100,A Gray Schist Relief…,A gray schist relief…,review-and-confirm-…
```

The curator reviews this file periodically and confirms — then either:
1. Sets `status="sold"` on the work in the canonical master CSV
   (Apps Script supports this; once the master flips status, the
   work drops out of the website feed via the existing filter).
2. Adds it to a forthcoming `data/sold_overrides.yaml` for fast
   removal without round-tripping through the master.

Today (2026-06): 3 candidates pending curator review.

## 16 · Open questions for the site author

These are decisions the inventory pipeline can't make for you:

- **Year fallback**: 519 of 1,377 works have no `year`. The pipeline
  now ships `era_display` as the "era from tags" option for the
  small fraction (5 today) where the title carries a century word.
  For the remaining 514, the site still has to choose: blank vs
  "Date unknown" vs hide.
- **Artist fallback**: 1,249 of 1,377 have no artist on file. Render
  as "Artist unknown" or omit the field entirely?
- **Sold-state**: see §14. Pipeline emits candidates; curator
  confirms; site doesn't need to change anything yet.
- **Primer URL expiry**: see §5 — needs a long-term plan before launch.
- **Empty collections**: 3 of 9 collection pages have 0 members
  pending a curator-supplied KG-# list. Render as "Coming soon"
  rather than 404? (Recommended.)

If you have a preferred shape for any of these, the schema can
expand in a v1-compatible way (e.g. add `artist_display` with a
preferred fallback) — just say.
