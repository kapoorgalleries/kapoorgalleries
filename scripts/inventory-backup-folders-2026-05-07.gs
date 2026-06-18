// Inventory backup-ingestion folders — generated 2026-05-07 (READ-ONLY).
//
// Produces a CSV listing every My Drive folder whose name matches a
// DESKTOP-* host or a Volume.<UUID> wrapper (the DriveFS pattern from the
// 2026-04-19 finding), plus the named backup folders called out in the
// 2026-05-07 audit. The CSV gives the post-quarantine review hard data
// (id, path, owner, createdTime, direct child counts) instead of clicking
// through folder trees.
//
// This script NEVER moves, trashes, or deletes anything. The only write it
// performs is creating the CSV report file in My Drive root (toggle off
// with WRITE_CSV_FILE = false to log-only).
//
// Setup:
//   1. script.google.com → new project under sanjay@kapoors.com.
//   2. Paste as Code.gs.
//   3. Services + → "Drive API" → Add (identifier must stay `Drive`).
//   4. Run `main`. Open the logged CSV file URL (or copy the logged CSV).
//
// Note on execution limits: Apps Script caps a single run at ~6 minutes.
// This script only counts DIRECT children of each matched folder (one
// Drive.Files.list page-walk per folder), not recursive sizes, so it stays
// well under the limit even with many matches.

var WRITE_CSV_FILE = true;

var EXACT_NAMES = ['DESKTOP-CJ8BHBM', 'DESKTOP-AAILIL7'];

// name-contains queries (Drive v3 q syntax). Volume. catches Volume.<UUID>.
var NAME_CONTAINS = ['DESKTOP-', 'Volume.'];

// Named backup folders from the 2026-05-07 audit triage list.
var NAMED_BACKUPS = [
  'Seagate Backup Plus Drive [F]',
  'QB2019BackupFiles',
  'Humbaba EMail Backup',
  'Gmail Backup',
  'Artsys Backup 110305'
];

var FOLDER_MIME = 'application/vnd.google-apps.folder';

function main() {
  var rows = [];
  var seen = {};

  EXACT_NAMES.forEach(function (n) { collect_(queryExactName_(n), rows, seen); });
  NAME_CONTAINS.forEach(function (s) { collect_(queryNameContains_(s), rows, seen); });
  NAMED_BACKUPS.forEach(function (n) { collect_(queryNameContains_(n), rows, seen); });

  rows.sort(function (a, b) { return a.path < b.path ? -1 : (a.path > b.path ? 1 : 0); });

  var csv = toCsv_(rows);
  Logger.log('Matched %s folder(s).', rows.length);
  Logger.log('\n%s', csv);

  if (WRITE_CSV_FILE) {
    var name = 'backup-folder-inventory-2026-05-07.csv';
    var file = DriveApp.createFile(name, csv, MimeType.CSV);
    Logger.log('CSV report written: %s (%s)', file.getName(), file.getUrl());
  }
}

function collect_(matches, rows, seen) {
  matches.forEach(function (f) {
    if (seen[f.id]) return;
    seen[f.id] = true;
    var counts = childCounts_(f.id);
    rows.push({
      id: f.id,
      name: f.name,
      path: resolvePath_(f.id),
      owner: f.owner,
      createdTime: f.createdTime || '',
      modifiedTime: f.modifiedTime || '',
      childFolders: counts.folders,
      childFiles: counts.files
    });
  });
}

function queryExactName_(name) {
  return listFolders_("name = '" + escapeQ_(name) + "' and mimeType = '" + FOLDER_MIME + "' and trashed = false");
}

function queryNameContains_(substr) {
  return listFolders_("name contains '" + escapeQ_(substr) + "' and mimeType = '" + FOLDER_MIME + "' and trashed = false");
}

function listFolders_(q) {
  var out = [];
  var pageToken = null;
  do {
    var resp = Drive.Files.list({
      q: q,
      pageSize: 1000,
      fields: 'nextPageToken, files(id, name, createdTime, modifiedTime, owners(emailAddress))',
      includeItemsFromAllDrives: false,
      supportsAllDrives: true,
      pageToken: pageToken
    });
    (resp.files || []).forEach(function (f) {
      out.push({
        id: f.id,
        name: f.name,
        createdTime: f.createdTime,
        modifiedTime: f.modifiedTime,
        owner: (f.owners && f.owners[0] && f.owners[0].emailAddress) || ''
      });
    });
    pageToken = resp.nextPageToken;
  } while (pageToken);
  return out;
}

function childCounts_(parentId) {
  var folders = 0, files = 0;
  var pageToken = null;
  do {
    var resp = Drive.Files.list({
      q: "'" + parentId + "' in parents and trashed = false",
      pageSize: 1000,
      fields: 'nextPageToken, files(mimeType)',
      supportsAllDrives: true,
      pageToken: pageToken
    });
    (resp.files || []).forEach(function (f) {
      if (f.mimeType === FOLDER_MIME) folders++; else files++;
    });
    pageToken = resp.nextPageToken;
  } while (pageToken);
  return { folders: folders, files: files };
}

var pathCache_ = {};
function resolvePath_(id) {
  var segments = [];
  var cur = id;
  var guard = 0;
  while (cur && guard < 64) {
    if (pathCache_[cur]) { segments.unshift(pathCache_[cur]); break; }
    var meta = Drive.Files.get(cur, { fields: 'id, name, parents', supportsAllDrives: true });
    segments.unshift(meta.name);
    pathCache_[cur] = meta.name;
    cur = (meta.parents && meta.parents[0]) || null;
    guard++;
  }
  return '/' + segments.join('/');
}

function toCsv_(rows) {
  var header = ['id', 'name', 'path', 'owner', 'createdTime', 'modifiedTime', 'childFolders', 'childFiles'];
  var lines = [header.map(csvCell_).join(',')];
  rows.forEach(function (r) {
    lines.push([
      r.id, r.name, r.path, r.owner, r.createdTime, r.modifiedTime, r.childFolders, r.childFiles
    ].map(csvCell_).join(','));
  });
  return lines.join('\n');
}

function csvCell_(v) {
  var s = String(v == null ? '' : v);
  if (/[",\n]/.test(s)) s = '"' + s.replace(/"/g, '""') + '"';
  return s;
}

function escapeQ_(s) {
  return String(s).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}
