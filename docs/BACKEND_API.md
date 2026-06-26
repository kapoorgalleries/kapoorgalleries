# Kapoor Galleries Backend API

A read-only REST API that serves the inventory pipeline's generated
feeds to the public website (`kapoorgalleries/sb1-vuxiwzek`).

This repo **is** the backend. The pipeline produces JSON feeds
(`make report`); this layer (`src/api/`) wraps them with server-side
search, filtering, and pagination so the website can query rather than
download-and-filter-client-side.

```
┌─────────────────┐   make report   ┌──────────────┐   GET /api/*   ┌──────────┐
│ ingest + consolidate │ ───────────► │  data/*.json │ ◄──────────── │  website │
│  (Primer/Artsy/…)    │              │  (feeds)     │   FastAPI     │  (SPA)   │
└─────────────────┘                  └──────────────┘               └──────────┘
```

## Run it

```bash
pip install -e '.[api]'          # fastapi + uvicorn
python -m src.cli serve          # http://127.0.0.1:8000  (docs at /docs)

# or directly:
uvicorn src.api.app:app --reload

# point at a different feed dir / lock CORS:
python -m src.cli serve --data-dir data --cors https://kapoorgalleries.com
```

Interactive OpenAPI docs are auto-generated at `/docs` and `/redoc`.

## Endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/api/health` | Liveness + which feeds are loaded, counts, timestamps |
| GET | `/api/works` | Paginated, filterable works grid |
| GET | `/api/works/{slug}` | One work by slug, KG-#, or id |
| GET | `/api/facets` | Pre-computed classification + tag facets |
| GET | `/api/collections` | Collection landing pages (light, no members) |
| GET | `/api/collections/{slug}` | One collection with full member list |
| GET | `/api/masterworks` | Museum-accession showcase, paginated |
| GET | `/api/masterworks/{slug}` | One masterwork |
| GET | `/api/masterworks/facets` | Masterworks facets (acquired_by + tags) |
| GET | `/api/site` | Gallery metadata + JSON-LD |

### `GET /api/works` query parameters

| Param | Type | Example | Notes |
| ----- | ---- | ------- | ----- |
| `classification` | string | `Painting` | Exact match |
| `tag` | string | `tibetan` | Single tag |
| `q` | string | `krishna` | Free-text over title/kg_id/artist/medium/provenance |
| `has_image` | bool | `true` | Works with/without a primary image |
| `available` | bool | `true` | Only works with a set price |
| `year_min` / `year_max` | int | `1700` | Inclusive; works with no year are excluded |
| `price_min` / `price_max` | float | `25000` | Inclusive; unpriced works excluded |
| `sort` | string | `-price` | `kg_id\|title\|year\|price`, prefix `-` for desc; nulls last |
| `page` | int | `1` | 1-indexed |
| `page_size` | int | `24` | Clamped to 1–200 |

**Response envelope** (list endpoints):

```json
{
  "page": 1,
  "page_size": 24,
  "total": 183,
  "pages": 8,
  "has_next": true,
  "has_prev": false,
  "items": [ /* Work objects — see docs/WEBSITE_SCHEMA.md */ ]
}
```

Item shapes are exactly the feed schemas documented in
[`WEBSITE_SCHEMA.md`](./WEBSITE_SCHEMA.md) — the API doesn't reshape
them, so the website's existing TypeScript types apply unchanged.

### Examples

```bash
# Tibetan paintings under $50k, most expensive first
curl "$API/api/works?tag=tibetan&classification=Painting&price_max=50000&sort=-price"

# Search
curl "$API/api/works?q=ragamala&page_size=12"

# A single collection with its members
curl "$API/api/collections/himalayan-art"

# Everything Norton Simon acquired
curl "$API/api/masterworks?acquired_by=Norton%20Simon%20Museum"
```

## Consuming from the website (`sb1-vuxiwzek`)

```ts
const API = import.meta.env.VITE_API_BASE; // e.g. https://api.kapoorgalleries.com

// Grid with server-side filter + pagination
const res = await fetch(
  `${API}/api/works?tag=${tag}&page=${page}&page_size=24`
).then(r => r.json());
// res.items, res.total, res.has_next …

// Detail page
const work = await fetch(`${API}/api/works/${slug}`).then(r => r.json());

// Site chrome (footer/contact/JSON-LD)
const site = await fetch(`${API}/api/site`).then(r => r.json());
```

Because every item shape matches the static feeds, the site can fall
back to the committed JSON (build-time fetch, see
[`WEBSITE_INTEGRATION.md`](./WEBSITE_INTEGRATION.md) §1) if the API is
ever unavailable.

## Configuration (env)

| Var | Default | Purpose |
| --- | ------- | ------- |
| `KG_API_DATA_DIR` | `data` | Directory holding the JSON feeds |
| `KG_API_CORS_ORIGINS` | `*` | Comma-separated allowed origins. **Set to the website origin in production** (a wildcard disables credentialed requests). |
| `KG_API_TITLE` | `Kapoor Galleries API` | OpenAPI title |
| `PORT` | `8000` | Bind port (honored by the Docker `CMD`) |

## Feed freshness

The API caches each feed in memory and reloads it only when the file's
mtime changes — so running `make report` in the same checkout is picked
up live, no restart. In a container the feeds are baked at build time;
**redeploy after `make report`** to refresh, or mount a volume at
`/app/data` and write feeds to it.

## Deploy

A `Dockerfile` and `render.yaml` are included.

```bash
# Local container
docker build -t kg-api .
docker run -p 8000:8000 -e KG_API_CORS_ORIGINS=https://kapoorgalleries.com kg-api

# Render.com — connect the repo (render.yaml is auto-detected), or:
render blueprint launch
```

The image installs **only** the API deps (FastAPI + uvicorn + PyYAML),
not the heavy ingest stack (pdfplumber/pandas/openpyxl), so it's small
and boots fast. Any Docker host works — Render, Fly.io, Cloud Run,
Railway, a plain VM.

Before pointing the live site at it:
1. Set `KG_API_CORS_ORIGINS` to the production origin(s).
2. Put it behind the gallery's domain (e.g. `api.kapoorgalleries.com`).
3. If you want pricing hidden publicly, serve a no-prices feed —
   regenerate `website_inventory.json` with `--no-prices` (see
   `WEBSITE_INTEGRATION.md` §6) into the deployed data dir.

## Why not a database?

The whole inventory is ~1,500 works (~1.6 MB JSON). It fits in memory
with room to spare, and filter/search/sort over that in Python is
sub-millisecond. A database (Supabase/D1) would add operational
surface for no measurable benefit at this scale. If the catalog grows
10–100× or needs multi-user writes, revisit — the `FeedStore`
abstraction is the single seam you'd swap.
