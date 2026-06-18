# `website_inventory.json` schema (v1)

Stable contract between the Kapoor Galleries inventory pipeline and
the public-facing site (`kapoorgalleries/sb1-vuxiwzek`).

Top-level shape:

```ts
type Feed = {
  schema_version: 1;
  generated_at: string;        // ISO 8601 UTC, e.g. "2026-06-18T14:23:11Z"
  count: number;               // number of works (== works.length)
  facets: Facets;              // pre-computed filter dropdowns
  works: Work[];
};

type Facets = {
  classification: { value: string; count: number }[];  // sorted desc by count
  tags:           { value: string; count: number }[];  // ditto
  with_image:     number;
  without_image:  number;
};
```

## `Work`

```ts
type Work = {
  // identifiers
  id:        string;   // "kg-1023" — lowercased, slug-safe
  kg_id:     string;   // "KG-1023" — canonical display form
  slug:      string;   // "kg-1023-kakubha-ragini-folio-from-a-ragamala"
  url_path:  string;   // "/works/kg-1023-kakubha-ragini-folio-from-a-ragamala"

  // primary text
  title:           string;          // never empty
  classification:  string | null;   // one of Artsy's 17 categories; null only if missing
  medium:          string | null;
  year:            number | null;   // 1850, -200 (BCE), etc.
  year_display:    string | null;   // "1850", "circa 1700", etc.

  // optional — present only when populated upstream
  artist?:                 string;
  period_school_region?:   string;
  materials?:              string;
  provenance?:             string;
  exhibitions?:            string;
  publications?:           string;
  signature?:              string;
  coa_status?:             string;

  // structured fields
  dimensions: {
    height_in: number | null;
    width_in:  number | null;
    depth_in:  number | null;
    display:   string | null;   // "29 1/4 × 20 in. (74.3 × 50.8 cm.)"
  };

  price: {
    usd:       number | null;
    display:   string;          // "$30,000" or "Price on request"
    available: boolean;         // true if usd > 0 AND not redacted
  };

  image: {
    primary:    string | null;  // CDN URL — typically Primer's signed S3
    alternates: string[];       // additional shots; populated as image map fills in
    thumbnail:  string | null;  // explicit thumbnail; may be null even with primary
  };

  // search / filter
  tags:    string[];     // ["19th-century", "tibetan", "thangka", "metal", ...]
  status:  "available";  // currently the only emitted value
                          // (sold / hidden are filtered out upstream)

  // not for display — surfaced for internal use
  _internal: {
    primer_uuid:  string | null;
    has_conflict: boolean;      // expected false in production
  };
};
```

## Tag taxonomy (current)

Inferred from title + classification + medium + year. Multiple tags
per work allowed; tags are additive filters.

**Period** (one of):
`ancient` · `medieval` · `early-modern` · `18th-century` ·
`19th-century` · `20th-century` · `21st-century` · plus
century-from-year fallbacks (`13th-century`, `15th-century` …).

**Region**:
`tibetan` · `indian` · `nepalese` · `south-east-asian` · `persian` ·
`japanese` · `chinese` · `western`.

**Subject**:
`thangka` · `mandala` · `buddha` · `vishnu` · `shiva` · `tara` ·
`avalokiteshvara` · `manuscript` · `ragamala` · `portrait` ·
`weapon` · `jewelry`.

**Medium family**:
`metal` · `stone` · `wood` · `works-on-paper` · `textile-ground`.

## Stability & versioning

- `schema_version: 1` will tick on any breaking change.
- Optional fields (artist, materials, provenance, etc.) may appear
  on more works over time; their absence on a work is not a guarantee.
- New tags will be added in v1. The frontend should treat unknown
  tag values as opaque filter strings.
- `_internal` is reserved — its keys may change without a version
  bump. Do not render to users.

## Example work

```json
{
  "id": "kg-1813",
  "kg_id": "KG-1813",
  "slug": "kg-1813-large-thangka-white-tara-tibetan",
  "url_path": "/works/kg-1813-large-thangka-white-tara-tibetan",
  "title": "Large Thangka White Tara Tibetan",
  "classification": "Painting",
  "medium": "Gouache on cotton",
  "year": 1801,
  "year_display": "1801",
  "dimensions": {
    "height_in": 34.5,
    "width_in": 23.5,
    "depth_in": null,
    "display": "34 1/2 × 23 1/2 in. (87.6 × 59.7 cm.)"
  },
  "price": {
    "usd": 38000,
    "display": "$38,000",
    "available": true
  },
  "image": {
    "primary": "https://data-us-east-1.primerws.com/.../white_tara.jpg?Expires=...",
    "alternates": [],
    "thumbnail": null
  },
  "tags": [
    "19th-century",
    "tibetan",
    "tara",
    "textile-ground"
  ],
  "status": "available",
  "_internal": { "primer_uuid": "...", "has_conflict": false },
  "provenance": "Southern Alleghenies Museum of Art (SAMA)...",
  "exhibitions": "KG_Art_of_the_Himalayas_Price_List"
}
```
