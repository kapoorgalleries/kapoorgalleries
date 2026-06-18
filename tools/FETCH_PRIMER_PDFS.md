# Fetching Primer PDFs into `data/raw/`

The Primer-page PDF exports the gallery refers to (per the user) live both
in **Drive** and in **Gmail attachments**. They are too large (>100 MB) for
the Drive MCP to stream into this session, so they have to be cached to
`data/raw/` once. The pipeline picks them up automatically on the next
`make ingest`.

## 1. From Drive (recommended — fastest)

Two Primer-style exports are registered in `catalog/sources.yaml`:

| File | Drive ID | Size | Works | Date |
|---|---|---:|---:|---|
| `KG_Available Works_5-13-2025_1065.pdf` | `1XDpGBR7V1DnjSkNkQOVcg-vRUXoJd59i` | 108 MB | 1,059 | May 13 2025 |
| `KG Inventory - 9-25-2025.pdf` | `16io-Drs2YYwpq4m3nifxfwT3YEqKwlFk` | 172 MB | (TBD) | Sep 25 2025 |

Open each Drive URL, click **Download**, save to `data/raw/` with the
filename listed under `local_path:` in `sources.yaml`:

```
data/raw/KG_Available_Works_2025-05-13.pdf
data/raw/KG_Inventory_2025-09-25.pdf
```

Or use `gdown` from the CLI:

```bash
pip install gdown
gdown 1XDpGBR7V1DnjSkNkQOVcg-vRUXoJd59i -O data/raw/KG_Available_Works_2025-05-13.pdf
gdown 16io-Drs2YYwpq4m3nifxfwT3YEqKwlFk -O data/raw/KG_Inventory_2025-09-25.pdf
```

## 2. From Gmail (alternative)

The May 13 2025 export is also attached to the **"Primer Exports"** Gmail
thread (thread id `196c67161fbd97f4`) sent from `trivedi@kapoors.com`.
Search Gmail for:

```
from:trivedi@kapoors.com subject:"Primer Exports" filename:pdf
```

Download the attachment (`KG_Available Works_5-13-2025_1065.pdf`) and save
it to `data/raw/KG_Available_Works_2025-05-13.pdf`.

## 3. Run the pipeline

Once the file is in place:

```bash
make ingest         # picks up the new source automatically
make consolidate
make report
```

The `kg_inventory_pdf` ingester page-streams the PDF (never loads the full
file into memory), parses each Primer page entry into observations, and
layers them onto the Artsy CSV data. Conflicts (e.g. a price differing
between the May 13 export and the Feb 16 Artsy snapshot) will surface in
`data/conflicts.csv` and be painted red in the Sheet.

## Newer exports

If your team generates a fresher Primer export, follow the same pattern:

1. Drop the PDF in `data/raw/`.
2. Append a new entry to `catalog/sources.yaml` with `type: kg_inventory_pdf`
   and the new file's `drive_file_id`/`local_path`.
3. `make all` — the consolidator will treat newer-timestamped sources as
   higher priority for canonical-value selection.
