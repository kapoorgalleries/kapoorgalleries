# Backup-named folder triage — 2026-05-07

Companion to `audits/2026-05-07-backup-ingestion.md`. The audit flagged a
set of backup-named folders that are **not** part of the active
`DESKTOP-*` ingestion and so are out of scope for the Apps Script
quarantine. Each needs a human decision: intentional archive (keep, and
optionally relabel) versus sync residue / duplicate (route to
`99 Delete After Review`).

Do not move or delete any of these until classified. Fill in the
Decision column, then act per the routing rules at the bottom.

## How to classify each folder

For each row, in the Drive UI (signed in as `sanjay@kapoors.com`):

1. Open the folder. Note the newest `Modified` date among its contents.
2. Check whether a same-named folder exists elsewhere in My Drive
   (Drive search by name) — duplicates suggest sync residue.
3. Decide using the rule of thumb:
   - **Archive (keep)** — single instance, contents are a deliberate
     point-in-time export the gallery may need (tax, accounting, email
     records), not still being written to.
   - **Residue (quarantine)** — duplicated, partially-uploaded, or part
     of a desktop-sync tree that the source-side checklist is stopping.
   - **Unsure** — leave for the attorney/accountant to weigh in;
     park in `99 Delete After Review` but flag in the notes.

## Folders to triage

| Folder | Likely origin | What to verify | Decision (Archive / Quarantine / Unsure) | Notes |
| --- | --- | --- | --- | --- |
| `Seagate Backup Plus Drive [F]` | Second external-drive backup root | Is it still growing? Does it overlap the WD SmartWare tree? | | |
| `QB2019BackupFiles` | QuickBooks 2019 backups | Confirm with accounting whether these `.qbb` files are the system of record | | |
| `Humbaba EMail Backup` | One-off email export | Single instance? Date range of messages? | | |
| `Gmail Backup (sanjay@kapoorgalleries.com)` (instance 1) | Mailbox export | Compare against other Gmail Backup instances for overlap | | |
| `Gmail Backup (sanjay@kapoorgalleries.com)` (instance 2+) | Mailbox export duplicates | Likely duplicates of instance 1 — verify before keeping multiple | | |
| `Artsys Backup 110305` | Legacy Artsys (gallery inventory system) export, dated 2011-03-05 | Is the data already superseded by current inventory records? | | |

> The `Gmail Backup` row count is approximate — the audit noted
> "multiple instances." Enumerate the exact set during triage (the
> inventory script below will list them with IDs and createdTime).

## Routing rules

- **Archive** → leave in place. If the name is ambiguous, optionally
  move into a clearly-labelled `00 Archives / <category>` folder so it
  is not re-flagged in future audits. Record the final location in
  Notes.
- **Quarantine** → move into
  `99 Delete After Review / System Folders and Binaries / Computer backup ingestion 2026-05-07`
  (the same leaf the Apps Script uses) so all residue is reviewed
  together. Do this manually in the Drive UI — these names are not in
  the script's `SOURCE_FOLDER_NAMES` list and should not be added to it
  without confirming they are pure residue.
- **Unsure** → quarantine as above, but add a line to Notes and raise
  with the accountant (QuickBooks) or attorney (email records) before
  any deletion.

## Safety

No hard deletes in this pass. Quarantine only. Deletion happens, if at
all, after the 30-day-ish review period in `99 Delete After Review` and
after the relevant stakeholder has signed off on each archive-class
folder.
