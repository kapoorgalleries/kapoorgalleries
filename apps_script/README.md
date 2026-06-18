# Apps Script — Kapoor Galleries Master Inventory

These two files (`Code.gs`, `appsscript.json`) live inside the empty
`KG Master Inventory System - 2026-05-06` Google Sheet and pull the master
record directly from this repo's `data/master.csv`.

## Install (one-time, ~3 minutes)

1. Open the master sheet:
   <https://docs.google.com/spreadsheets/d/1Kf175vGkFiOMLGFoslUTjsA4hUpnIEeauh_WjSaSjUc/edit>
2. **Extensions → Apps Script**.
3. Paste the contents of `Code.gs` into the editor (replace the default
   `myFunction` stub).
4. Open the manifest: ⚙️ (left sidebar) → **Show "appsscript.json" manifest
   file** → ON. Replace the manifest contents with `appsscript.json`.
5. **Save** (💾) and name the project `KG Inventory`.
6. Reload the spreadsheet tab. A new **Inventory ▾** menu appears.

## Daily use

- **Inventory ▾ Refresh from repo** — pulls the latest `master.csv` from
  this repo's `claude/gallery-inventory-system-phuSJ` branch and renders it
  into the `Master` tab. Conflicts are auto-painted red.
- **Inventory ▾ Highlight conflicts** — re-runs only the highlighter (faster
  than a full refresh).
- **Inventory ▾ Show gaps for selected work** — opens a sidebar listing
  Artsy-blocking missing fields, core-missing fields, and conflicting fields
  for whichever row your cursor is in.
- **Inventory ▾ Open Drive folder for KG-#** — opens a Drive search for the
  selected KG-#### in a new tab.

## Editing the source URL

The first time you push a new branch (or merge to `main`), update the
`MASTER_CSV_URL` constant at the top of `Code.gs` to point at the desired
branch's raw URL. After merging the PR to `main`:

```javascript
var MASTER_CSV_URL =
  'https://raw.githubusercontent.com/kapoorgalleries/kapoorgalleries/' +
  'main/data/master.csv';
```

## Development with `clasp` (optional)

If you prefer to iterate locally:

```bash
npm install -g @google/clasp
clasp login
clasp clone <SCRIPT_ID>     # SCRIPT_ID from URL of the Apps Script project
clasp push                   # after each edit to Code.gs / appsscript.json
```
