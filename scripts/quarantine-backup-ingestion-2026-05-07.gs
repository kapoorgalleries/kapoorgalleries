// Quarantine backup-ingestion trees — generated 2026-05-07.
//
// Reparents every My Drive folder named DESKTOP-CJ8BHBM or DESKTOP-AAILIL7
// (the audit found multiple instances of each, one per ingestion run) into:
//
//     99 Delete After Review
//       / System Folders and Binaries
//         / Computer backup ingestion 2026-05-07
//
// How to run:
//   1. Go to https://script.google.com and create a new project under
//      sanjay@kapoors.com (the owner account).
//   2. Paste this file in as Code.gs.
//   3. Enable the advanced Drive service: Services + → "Drive API" → Add
//      (identifier must remain `Drive`).
//   4. Confirm the quarantine path's first two segments already exist in My
//      Drive ("99 Delete After Review" and "System Folders and Binaries");
//      the script auto-creates only the date-stamped leaf.
//   5. Run `main` with DRY_RUN = true first, read the log, then flip
//      DRY_RUN = false and run again to perform the moves.
//
// Safety:
//   - Source-side sync removal (Steps 1 & 2 of the next-pass plan) MUST
//     be completed on the MSI machine and DESKTOP-AAILIL7 BEFORE this
//     script is run, or new ingestion will continue to recreate folders
//     after the move.
//   - The script never trashes or deletes anything; it only reparents.
//   - Folders already under the quarantine path are skipped.

var DRY_RUN = true;

var SOURCE_FOLDER_NAMES = ['DESKTOP-CJ8BHBM', 'DESKTOP-AAILIL7'];

var QUARANTINE_PATH = [
  '99 Delete After Review',
  'System Folders and Binaries',
  'Computer backup ingestion 2026-05-07'
];

function main() {
  var quarantine = resolveQuarantineLeaf_();
  Logger.log('Quarantine leaf: %s (id=%s)', formatPath_(quarantine), quarantine.getId());
  Logger.log('DRY_RUN = %s', DRY_RUN);

  var summary = { moved: 0, skipped: 0, alreadyQuarantined: 0, errors: 0 };

  SOURCE_FOLDER_NAMES.forEach(function (name) {
    var iter = DriveApp.getFoldersByName(name);
    var count = 0;
    while (iter.hasNext()) {
      count++;
      var folder = iter.next();
      try {
        processFolder_(folder, quarantine, summary);
      } catch (err) {
        summary.errors++;
        Logger.log('ERROR processing %s (id=%s): %s', name, folder.getId(), err);
      }
    }
    Logger.log('Found %s instance(s) of %s', count, name);
  });

  Logger.log(
    'Summary — moved: %s, already quarantined: %s, skipped: %s, errors: %s',
    summary.moved, summary.alreadyQuarantined, summary.skipped, summary.errors
  );
}

function processFolder_(folder, quarantine, summary) {
  var currentPath = formatPath_(folder);

  if (isDescendantOf_(folder, quarantine)) {
    summary.alreadyQuarantined++;
    Logger.log('SKIP (already under quarantine): %s', currentPath);
    return;
  }

  if (folder.getId() === quarantine.getId()) {
    summary.skipped++;
    Logger.log('SKIP (folder is the quarantine itself): %s', currentPath);
    return;
  }

  if (DRY_RUN) {
    Logger.log('DRY-RUN would move: %s  →  %s', currentPath, formatPath_(quarantine));
    return;
  }

  reparent_(folder, quarantine);
  summary.moved++;
  Logger.log('MOVED: %s  →  %s', currentPath, formatPath_(quarantine));
}

function reparent_(folder, destination) {
  // Use the advanced Drive service so we handle the legacy multi-parent case
  // explicitly. In Drive v3 single-parent mode each folder still has exactly
  // one parent, but the API call is the same shape.
  var file = Drive.Files.get(folder.getId(), { fields: 'id, parents', supportsAllDrives: true });
  var currentParents = (file.parents || []).join(',');
  Drive.Files.update({}, folder.getId(), null, {
    addParents: destination.getId(),
    removeParents: currentParents,
    supportsAllDrives: true,
    fields: 'id, parents'
  });
}

function isDescendantOf_(folder, ancestor) {
  var ancestorId = ancestor.getId();
  var seen = {};
  var stack = [folder];
  while (stack.length) {
    var node = stack.pop();
    var parents = node.getParents();
    while (parents.hasNext()) {
      var parent = parents.next();
      var pid = parent.getId();
      if (pid === ancestorId) return true;
      if (seen[pid]) continue;
      seen[pid] = true;
      stack.push(parent);
    }
  }
  return false;
}

function resolveQuarantineLeaf_() {
  var root = DriveApp.getRootFolder();
  var current = root;

  for (var i = 0; i < QUARANTINE_PATH.length; i++) {
    var segment = QUARANTINE_PATH[i];
    var children = current.getFoldersByName(segment);
    var next = null;
    while (children.hasNext()) {
      var candidate = children.next();
      if (next) {
        throw new Error(
          'Ambiguous quarantine path: multiple folders named "' + segment +
          '" under "' + current.getName() + '". Resolve manually before re-running.'
        );
      }
      next = candidate;
    }
    if (!next) {
      var isLeaf = (i === QUARANTINE_PATH.length - 1);
      if (!isLeaf) {
        throw new Error(
          'Quarantine path segment missing: "' + segment + '" under "' +
          current.getName() + '". Create it manually before re-running ' +
          '(the script only auto-creates the date-stamped leaf).'
        );
      }
      if (DRY_RUN) {
        Logger.log('DRY-RUN would create leaf "%s" under %s', segment, formatPath_(current));
        // Return a sentinel that downstream callers can format, but never act on.
        // We attach an id so formatPath_ works.
        return { __virtual: true, getId: function () { return '(would-be-created)'; },
                 getName: function () { return segment; }, getParents: function () {
                   var done = false;
                   return { hasNext: function () { return !done; },
                            next: function () { done = true; return current; } };
                 } };
      }
      next = current.createFolder(segment);
      Logger.log('Created leaf folder "%s" under %s', segment, formatPath_(current));
    }
    current = next;
  }
  return current;
}

function formatPath_(folder) {
  var segments = [folder.getName()];
  var parents = folder.getParents();
  var guard = 0;
  while (parents.hasNext() && guard < 64) {
    var parent = parents.next();
    segments.unshift(parent.getName());
    parents = parent.getParents();
    guard++;
  }
  return '/' + segments.join('/');
}
