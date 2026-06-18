# Source-side sync removal checklist — 2026-05-07

Companion to `audits/2026-05-07-backup-ingestion.md` and
`scripts/quarantine-backup-ingestion-2026-05-07.gs`. This is Steps 1 and 2
of the next-pass plan: stop the two Windows machines from continuing to
ingest backup trees into Drive **before** the Apps Script reparents
anything. If these steps are skipped, the moved trees will reappear at
their original paths within minutes.

Run order:
1. MSI machine (host name `DESKTOP-CJ8BHBM`) — this checklist.
2. `DESKTOP-AAILIL7` — same checklist, second machine section.
3. 24-hour observation window: dry-run the Apps Script and confirm no
   new ingestion is occurring.
4. Drive-side quarantine (the Apps Script with `DRY_RUN = false`).

Each step lists the exact UI path so a non-technical operator at the
keyboard can follow it without interpretation.

## Machine 1 — MSI (`DESKTOP-CJ8BHBM`)

Signed-in Drive account: `sanjay@kapoors.com` (confirm in step 2; if a
different account is signed in, stop and escalate before changing
anything).

1. Locate the Google Drive desktop icon in the Windows system tray
   (bottom-right, may be hidden behind the `^` chevron). Click it.
2. Click the gear icon in the upper-right of the Drive panel →
   **Preferences**. In the Preferences window, top-right, confirm the
   signed-in account is `sanjay@kapoors.com`. If not, stop.
3. In the left pane select **My Computer** (sometimes labelled
   `DESKTOP-CJ8BHBM`). The right pane lists every folder currently
   syncing **from this PC into Drive**.
4. For each of the following entries, if present, click the folder row
   then click **Stop syncing with Google Drive**, then confirm the
   dialog. Do **not** click "Stop syncing AND remove from Drive" — that
   would delete the cloud copies before quarantine.
   - The external-drive root that contains `WD SmartWare` (typically
     drive letter `F:` or `G:`, label "WD SmartWare" or similar).
   - Any folder whose path contains `WD SmartWare.swstor`.
   - Any folder under the external drive that mentions `Backup` in its
     name.
   - `Seagate Backup Plus Drive [F]` if it appears as a synced folder
     (it may instead be a one-time Drive-side upload — only act if it
     shows up in this Preferences pane).
5. Click **Save**. The Drive client will show "Syncing paused" briefly,
   then return to idle. Wait for the tray icon to show the steady
   (non-animated) state before continuing.
6. Open File Explorer and browse to the external drive. Confirm the
   `WD SmartWare.swstor` tree still exists locally (this is the source
   of truth — we are only stopping the upload, not deleting local
   files).
7. Open https://drive.google.com in a browser, signed in as
   `sanjay@kapoors.com`. Navigate to `Computers` (left sidebar). Confirm
   `DESKTOP-CJ8BHBM` still appears but the folder count under it has
   stopped growing. Note the current top-level folder count here for
   the observation-window check:

   _DESKTOP-CJ8BHBM folder count at removal time:_ `__________`

8. Do **not** unlink the machine from Drive. Unlinking would also stop
   sync of any intentionally-shared folders.

## Machine 2 — `DESKTOP-AAILIL7`

Repeat steps 1–7 above on `DESKTOP-AAILIL7`. Differences to watch for:

- The account signed in may be different from `sanjay@kapoors.com`. If
  so, the audit data already shows that account has been ingesting
  into the same Drive — that means the target folders are owned by a
  different user and the Apps Script (which runs as
  `sanjay@kapoors.com`) will not be able to move them. Stop and
  escalate; do not proceed to the Apps Script step.
- The external-drive label and letter will differ. Match by the
  presence of `WD SmartWare` / `swstor` / backup-named folders rather
  than by drive letter.
- Record the DESKTOP-AAILIL7 top-level folder count at removal time:
  `__________`

## Observation window

After both machines are done:

1. Wait 24 hours.
2. Re-open `https://drive.google.com` → `Computers` →
   `DESKTOP-CJ8BHBM`. Confirm the top-level folder count matches the
   number recorded in step 7 above (no growth).
3. Repeat for `DESKTOP-AAILIL7`.
4. Run the Apps Script with `DRY_RUN = true`. The log should list the
   same instance counts the prior audit found — no new IDs.

Only after all three checks pass should the Apps Script be re-run with
`DRY_RUN = false`.

## Rollback

If the user later realises a folder was syncing intentionally and
should resume:

1. Drive desktop tray → gear → Preferences → My Computer → **Add
   folder** → pick the path.
2. The previously-uploaded copy in Drive will re-link to the local
   folder; no duplicate tree is created.

This rollback is safe to perform at any time and does not interact
with the quarantine moves performed by the Apps Script.
