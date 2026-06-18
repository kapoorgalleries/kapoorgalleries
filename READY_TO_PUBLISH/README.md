# READY_TO_PUBLISH — Issuu upload runbook

Each subdirectory here is one Issuu publication "package". A package is just:

```
READY_TO_PUBLISH/<package>/
├── manifest.json       # metadata + Drive source for the PDF
├── issuu_command.sh    # thin wrapper -> scripts/issuu_upload.sh
└── document.pdf        # the file to upload (NOT committed; fetched per-machine)
```

`_template/` is the starting point for a new package — copy it and edit the manifest.

## Important: where this can run

The download and upload steps need outbound network access to:

- `drive.google.com` / `drive.usercontent.google.com` (to fetch the source PDFs)
- `api.issuu.com` (to create drafts and upload files)

Run these scripts on a machine with open egress (a laptop or a CI runner).
Restricted/sandboxed environments with a host allowlist will fail at the
firewall before auth or sharing settings even matter.

## One-time setup

- `gdown`, `jq`, and `curl` installed (`pip install gdown`).
- Each `manifest.json` has a valid `driveFileId`.
- Each source PDF in Drive is shared **"Anyone with the link" (Viewer)**.
  Verify in an incognito window: if the link previews while logged out, `gdown`
  can fetch it. (Workspace org policy may block this — see Troubleshooting.)

## Publish flow

```bash
# From the repo root.
export ISSUU_API_TOKEN='<issuu-api-token>'   # do not commit this

# 1. Pull each package's PDF from Drive into its directory.
./scripts/fetch_pdfs.sh

# 2. Create an Issuu draft per package and upload the file.
./scripts/upload_all.sh
```

Dry run first if you want to see what would happen without hitting the API:

```bash
DRY_RUN=1 ./scripts/upload_all.sh
```

## What the scripts do

- **`scripts/fetch_pdfs.sh`** — for each package, if `document.pdf` is missing
  and the manifest has a `driveFileId`, fetches it with `gdown`. Skips packages
  whose file is already present. Verifies the download is actually a PDF (guards
  against gdown silently saving a Drive permission/error page).
- **`scripts/upload_all.sh`** — runs every package's `issuu_command.sh`, with a
  summary at the end. One package failing does not abort the rest.
- **`scripts/issuu_upload.sh`** — creates the draft (`POST /v2/drafts`), uploads
  the file (`PATCH /v2/drafts/<slug>/upload`), and publishes only if the manifest
  has `"publish": true`. On success it writes a `.uploaded` marker so reruns are
  idempotent — delete the marker to force a re-upload.

## manifest.json fields

| field                 | meaning                                                        |
|-----------------------|----------------------------------------------------------------|
| `file`                | filename in the package dir (always `document.pdf` here)        |
| `title`               | publication title shown on Issuu (**required**)                 |
| `description`         | listing description                                            |
| `access`              | `PUBLIC` or `PRIVATE`                                          |
| `type`                | Issuu publication type (e.g. `editorial`)                       |
| `publish`            | `false` = leave as draft for review; `true` = publish on upload |
| `downloadable`        | allow readers to download the original                         |
| `preview`             | preview/teaser mode                                           |
| `originalPublishDate` | optional `YYYY-MM-DD` original publication date                 |
| `driveFileId`         | Google Drive file ID used by `fetch_pdfs.sh`                    |
| `driveSourceTitle`    | original Drive filename (informational)                         |

All packages currently ship with `"publish": false`, so uploads land as
**drafts** — review them in the Issuu dashboard, then publish.

## Current packages

| package                        | title                        | driveFileId                         |
|--------------------------------|------------------------------|-------------------------------------|
| `bhagvata-purana-manuscript`   | Bhagvata Purana Manuscript   | `1-0aXflc8gNkTp2Mc_eLRukwYu1YcN6NP` |
| `bhagvata-purana-manuscript-2` | Bhagvata Purana Manuscript 2 | `1MBZMqgGxBNP8V9MqRzdDrmbGZkG-bEqM` |
| `issuu-pdf`                    | ISSUU PDF                    | `1w9bRm7OvwqDyT0S-TuVQTXmTUFDvkcL0` |

## Troubleshooting

- **`fetch_pdfs.sh` reports "not a PDF"** — the file isn't shared publicly, or
  the host can't reach Drive. Re-check sharing in incognito.
- **"Anyone with the link" won't stick / option is greyed out** — a Google
  Workspace admin policy is blocking external link sharing for the domain. Have
  the admin allow it (Admin console → Apps → Google Workspace → Drive and Docs →
  Sharing settings), or re-upload from a personal Google account that isn't bound
  by the org policy and use that file's ID.
- **`ISSUU_API_TOKEN is not set`** — export it in the shell before running.
- **A package keeps getting skipped** — it already has a `.uploaded` marker;
  delete `READY_TO_PUBLISH/<package>/.uploaded` to re-upload.

## Adding a new package

```bash
cp -r READY_TO_PUBLISH/_template READY_TO_PUBLISH/my-new-package
# edit READY_TO_PUBLISH/my-new-package/manifest.json (title, driveFileId, ...)
./scripts/fetch_pdfs.sh
./scripts/upload_all.sh
```
