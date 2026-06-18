# Integrating `data/website_inventory.json` with `sb1-vuxiwzek`

Quick start for whoever's wiring up the public-facing Kapoor Galleries
website (StackBlitz project `kapoorgalleries/sb1-vuxiwzek`).

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

## 9 · Open questions for the site author

These are decisions the inventory pipeline can't make for you:

- **Year fallback**: shows of works without a year (519 of 1,377).
  Render as blank, as "Date unknown", or as the era from tags?
- **Artist fallback**: 1,249 of 1,377 have no artist on file. Render
  as "Artist unknown" or omit the field entirely?
- **Sold-state**: how to surface works that sell (will need a new
  status field plumbed through).
- **Primer URL expiry**: see §5 — needs a long-term plan before launch.

If you have a preferred shape for any of these, the schema can
expand in a v1-compatible way (e.g. add `artist_display` with a
preferred fallback) — just say.
