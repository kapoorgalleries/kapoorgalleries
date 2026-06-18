# Computer-backup ingestion finding — 2026-05-07

## Findings

- Drive search confirmed at least two Windows machines actively syncing into cloud Drive: `DESKTOP-CJ8BHBM` (multiple folder IDs across separate parents, indicating stacked ingestion runs) and `DESKTOP-AAILIL7`.
- Traced one `DESKTOP-CJ8BHBM` ingestion path: `Backup > Backup > WD SmartWare.swstor > DESKTOP-CJ8BHBM > Volume.<UUID> > Users/sumos and MSI`. This represents a Western Digital external-HDD backup tree of an MSI Windows machine's full `C:` drive being mirrored into Drive. The `Volume.<UUID>` wrapper is consistent with the DriveFS structures previously flagged on 2026-04-19.
- Recent files feed shows continuous live ingestion as of 2026-05-07: email archive PDFs, `.eml` files, and `(attachments)` subfolders streaming into Drive at multi-minute intervals, with `createdTime` values inside the same hour as the audit run.
- Other named backup folders identified in the same scope:
  - `Seagate Backup Plus Drive [F]`
  - `QB2019BackupFiles`
  - `Humbaba EMail Backup`
  - multiple `Gmail Backup (sanjay@kapoorgalleries.com)` instances
  - `Artsys Backup 110305`
- Phone-camera audit conclusion: zero unaccounted-for personal phone photos found across My Drive, `sharedWithMe` content, or sampled `DESKTOP-*` trees. All `IMG`/`PXL`/`HEIC` filenames mapped to gallery inventory clusters (Vajrapani, Yamantaka, Durga, Parvati, Yongle Bronzes, Arader Box #3) or to correctly-filed personal items in `06 Personal / Photos / 2026-04-29 Phone Photos`.
- Workspace shared drives could not be confirmed as accessible through this connector session; `sharedWithMe` results all returned `owner = sanjay@kapoors.com`, indicating cross-account folder sharing rather than native Workspace shared-drive content.

## Next pass when machine-side access is available

1. **Source-side (MSI)** — On the MSI Windows machine, open Google Drive desktop preferences and remove the `WD SmartWare` folder and the external-drive root from sync to stop further cloud ingestion of the backup tree before any Drive-side cleanup runs.
2. **Source-side (DESKTOP-AAILIL7)** — Confirm the same on `DESKTOP-AAILIL7` to ensure no second machine is still uploading.
3. **Drive-side reparent** — Move all `DESKTOP-CJ8BHBM` and `DESKTOP-AAILIL7` folder trees to `99 Delete After Review / System Folders and Binaries / Computer backup ingestion 2026-05-07`, preserving the multi-instance structure for verification before any deletion.
4. **Drive-side triage** — Triage the remaining backup-named folders (`Seagate Backup Plus Drive [F]`, `QB2019BackupFiles`, `Humbaba EMail Backup`, `Gmail Backup` variants, `Artsys Backup 110305`) to determine which are intentional archive records versus sync residue, then route accordingly.

## Execution blocker

This session's Drive connector remains read-only. Both source-side preference changes and Drive-side moves require either the Google Drive desktop client or a Google Apps Script run from `script.google.com`.

## Safety check

No hard deletes are recommended in this pass. All moves should target `99 Delete After Review` until source-side sync is confirmed stopped and the trees are reviewed against the `Volume.<UUID>` pattern previously documented on 2026-04-19.
