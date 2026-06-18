/**
 * Kapoor Galleries — Master Inventory System (Apps Script)
 *
 * Lives inside the empty `KG Master Inventory System - 2026-05-06` sheet
 * and pulls the latest master.csv from this GitHub repo.
 *
 * Menu:
 *   Inventory ▾ Refresh from repo
 *               Highlight conflicts
 *               Show gaps for selected work
 *               Open Drive folder for KG-#
 *
 * One-time setup: edit MASTER_CSV_URL below to point at this repo's raw URL.
 */

// CHANGE ME after first push: raw-content URL of data/master.csv on the
// branch you want the sheet to track.
var MASTER_CSV_URL =
  'https://raw.githubusercontent.com/kapoorgalleries/kapoorgalleries/' +
  'claude/gallery-inventory-system-phuSJ/data/master.csv';

var MASTER_SHEET = 'Master';
var CONFLICT_RED = '#ffd6d6';

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Inventory')
    .addItem('Refresh from repo', 'refreshFromRepo')
    .addItem('Show stats', 'showStats')
    .addItem('Show price distribution', 'showPriceDistribution')
    .addItem('Show timeline (history.csv)', 'showTimeline')
    .addItem('Show photo queue', 'showPhotoQueue')
    .addItem('Highlight conflicts', 'highlightConflicts')
    .addSeparator()
    .addItem('Review sold candidates', 'reviewSoldCandidates')
    .addSeparator()
    .addItem('Inspect selected work', 'showGapsForSelectedWork')
    .addItem('Suggest resolution for selected cell', 'suggestResolution')
    .addItem('Open Drive folder for KG-#', 'openDriveForSelectedWork')
    .addToUi();
}


// Pulls data/sold_candidates.csv from the repo and shows each
// candidate (KG-#, match_score, external title, current title) in a
// sidebar.  For each row, the curator either:
//
//   - Clicks "Confirm sold" — writes status='sold' into the Master
//     sheet for that KG-# and shows the row-level git command the
//     curator should run locally to persist the change to master.csv.
//   - Clicks "Reject" — paints a note in the audit so the next
//     pipeline run can skip this candidate.
//
// We deliberately do not auto-flip status because title collisions
// across centuries are real ("Krishna and Radha" exists 30+ times).
// The 95-threshold from the pipeline cuts the false-positive rate
// but cannot eliminate it.
function reviewSoldCandidates() {
  var url = MASTER_CSV_URL.replace(/master\.csv$/, 'sold_candidates.csv');
  var resp = UrlFetchApp.fetch(url, {muteHttpExceptions: true});
  if (resp.getResponseCode() !== 200) {
    SpreadsheetApp.getUi().alert(
      'sold_candidates.csv not found at ' + url + '.\n' +
      'Run `kg-inv enrich-website` locally and push to populate.'
    );
    return;
  }
  var rows = Utilities.parseCsv(resp.getContentText());
  if (rows.length < 2) {
    SpreadsheetApp.getUi().alert(
      'No sold candidates pending review.\n' +
      'Either nothing in the curator sheet has the SOLD flag, or all ' +
      'flagged rows already match works that fall below the 95 ' +
      'confidence threshold.'
    );
    return;
  }
  var header = rows[0];
  var idx = {};
  header.forEach(function (h, i) { idx[h] = i; });

  var html =
    '<style>body{font-family:Arial,sans-serif;padding:14px;font-size:13px}' +
    '.cand{margin:10px 0;padding:10px;border:1px solid #eee;border-radius:4px}' +
    '.kg{font-weight:bold;color:#1976d2}' +
    '.score{color:#080;float:right;font-size:12px}' +
    '.row{margin:4px 0}' +
    '.label{color:#888;font-size:11px;text-transform:uppercase;letter-spacing:0.5px}' +
    'pre{background:#f4f4f4;padding:6px;font-size:11px;white-space:pre-wrap;border-radius:4px}' +
    'button{padding:6px 12px;margin-right:6px;cursor:pointer;border-radius:3px;border:1px solid #ccc}' +
    'button.confirm{background:#fee;border-color:#c00;color:#900}' +
    'button.reject{background:#f4f4f4}</style>' +
    '<h3>Sold candidates · ' + (rows.length - 1) + ' pending review</h3>' +
    '<p style="color:#888">Fuzzy-matched (score ≥ 95) from the curator ' +
    'Catalog & Inventory Sheet. Confirm only after spot-checking the ' +
    'title against the current Master row.</p>';

  for (var i = 1; i < rows.length; i++) {
    var r = rows[i];
    var kg = r[idx['kg_id']] || '';
    var score = r[idx['match_score']] || '?';
    var ext = (r[idx['external_title']] || '').replace(/</g, '&lt;');
    var cur = (r[idx['current_title']] || '').replace(/</g, '&lt;');
    var safeKg = kg.replace(/'/g, '');
    html +=
      '<div class="cand">' +
      '<div class="score">match ' + score + '/100</div>' +
      '<div class="kg">' + kg + '</div>' +
      '<div class="row"><span class="label">Curator sheet says:</span><br>' + ext + '</div>' +
      '<div class="row"><span class="label">Current Master row:</span><br>' + cur + '</div>' +
      '<div class="row" style="margin-top:8px">' +
      '<button class="confirm" onclick="google.script.run.applySoldStatus(\'' + safeKg + '\')">Confirm sold &amp; flip Master row</button>' +
      '</div>' +
      '<div class="row"><span class="label">To persist to master.csv:</span>' +
      '<pre>python -m src.cli resolve ' + safeKg + ' status sold \\\n' +
      '  --reason "Curator sheet SOLD flag confirmed via Apps Script" \\\n' +
      '  --by your.email@kapoors.com</pre></div>' +
      '</div>';
  }
  SpreadsheetApp.getUi().showSidebar(
    HtmlService.createHtmlOutput(html).setTitle('Sold candidates')
  );
}


// Called from the sold-candidates sidebar.  Locates the KG-# row in
// the Master sheet, flips its `status` cell to 'sold', and paints
// the row pink so the curator sees the change reflected in the
// sheet immediately.  Note: this does NOT push to the repo — the
// curator still has to run `kg-inv resolve ... status sold` locally
// to make the master.csv change durable.  The sheet edit is a
// preview / fast-feedback mechanism, not the source of truth.
function applySoldStatus(kgId) {
  if (!kgId) return;
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(MASTER_SHEET);
  if (!sheet) {
    SpreadsheetApp.getUi().alert('Run "Refresh from repo" first.');
    return;
  }
  var data = sheet.getDataRange().getValues();
  if (data.length < 2) return;
  var header = data[0];
  var idCol = header.indexOf('work_id');
  var statusCol = header.indexOf('status');
  if (idCol < 0 || statusCol < 0) {
    SpreadsheetApp.getUi().alert(
      'Master sheet missing work_id or status column.'
    );
    return;
  }
  for (var r = 1; r < data.length; r++) {
    if (String(data[r][idCol]) === kgId) {
      sheet.getRange(r + 1, statusCol + 1).setValue('sold');
      sheet.getRange(r + 1, 1, 1, header.length)
        .setBackground('#ffe4e4');
      ss.toast('Marked ' + kgId + ' as sold (preview).', 'Inventory', 4);
      return;
    }
  }
  SpreadsheetApp.getUi().alert(
    kgId + ' not found in Master sheet — Refresh from repo first?'
  );
}

// Pulls data/photo_queue.csv from the repo and shows the
// "ready when photographed" punch list grouped by classification
// in a sidebar — same data as reports/photo_queue.md.
function showPhotoQueue() {
  var url = MASTER_CSV_URL.replace(/master\.csv$/, 'photo_queue.csv');
  var resp = UrlFetchApp.fetch(url, {muteHttpExceptions: true});
  if (resp.getResponseCode() !== 200) {
    SpreadsheetApp.getUi().alert(
      'photo_queue.csv not found at ' + url + '.\n' +
      'Run `make all` locally and push to populate.'
    );
    return;
  }
  var rows = Utilities.parseCsv(resp.getContentText());
  if (rows.length < 2) { SpreadsheetApp.getUi().alert('photo_queue.csv is empty.'); return; }
  var header = rows[0];
  var idx = {};
  header.forEach(function (h, i) { idx[h] = i; });

  // Bucket by classification, ready-when-photographed only.
  var byCls = {};
  var nNeedsMeta = 0;
  for (var i = 1; i < rows.length; i++) {
    var r = rows[i];
    if (r[idx['ready_when_photographed']] !== 'yes') { nNeedsMeta++; continue; }
    var cls = r[idx['classification']] || 'Unknown';
    (byCls[cls] = byCls[cls] || []).push(r);
  }
  var clsNames = Object.keys(byCls).sort();
  var nReady = clsNames.reduce(function (s, c) { return s + byCls[c].length; }, 0);

  var html =
    '<style>body{font-family:Arial,sans-serif;padding:14px;font-size:12px}' +
    'h2{margin:14px 0 4px;font-size:14px;color:#444}' +
    'h3{margin:18px 0 4px;font-size:13px;color:#222;border-bottom:1px solid #eee;padding-bottom:2px}' +
    'table{border-collapse:collapse;width:100%}' +
    'th,td{padding:3px 6px;border-bottom:1px solid #f3f3f3;text-align:left;vertical-align:top}' +
    'th{background:#fafafa;color:#555}' +
    'td.r{text-align:right;color:#888}' +
    '.meta{color:#888;margin-bottom:10px}</style>' +
    '<h2>Photography punch list</h2>' +
    '<div class="meta"><b>' + nReady + '</b> works become Artsy-eligible the moment they\'re photographed. ' +
    '<br>Plus <b>' + nNeedsMeta + '</b> more need a photo + metadata fill (see reports/photo_queue.md).</div>';
  clsNames.forEach(function (cls) {
    var works = byCls[cls];
    html += '<h3>' + cls + ' (' + works.length + ')</h3>';
    html += '<table><tr><th>KG-#</th><th>Title</th><th>Medium</th><th>Year</th></tr>';
    works.forEach(function (r) {
      var t = (r[idx['title']] || '').slice(0, 55);
      var m = (r[idx['medium']] || '').slice(0, 32);
      html += '<tr><td>' + r[idx['work_id']] + '</td><td>' + t +
              '</td><td>' + m + '</td><td class="r">' +
              (r[idx['year']] || '') + '</td></tr>';
    });
    html += '</table>';
  });
  SpreadsheetApp.getUi().showSidebar(
    HtmlService.createHtmlOutput(html).setTitle('Photo queue · ' + nReady + ' ready')
  );
}

// Pulls data/history.csv from the repo and shows the trend in a sidebar.
// Writes a quick-glance table; deltas are calculated against the row before.
function showTimeline() {
  var url = MASTER_CSV_URL.replace(/master\.csv$/, 'history.csv');
  var resp = UrlFetchApp.fetch(url, {muteHttpExceptions: true});
  if (resp.getResponseCode() !== 200) {
    SpreadsheetApp.getUi().alert(
      'history.csv not found at ' + url + '.\n' +
      'Run `kg-inv timeline` locally and push to populate.'
    );
    return;
  }
  var rows = Utilities.parseCsv(resp.getContentText());
  if (rows.length < 2) {
    SpreadsheetApp.getUi().alert('history.csv has no data rows yet.');
    return;
  }
  var header = rows[0];
  var idx = {};
  header.forEach(function (h, i) { idx[h] = i; });

  function delta(curr, prev, col) {
    if (!prev) return '';
    var d = parseInt(curr[idx[col]], 10) - parseInt(prev[idx[col]], 10);
    if (isNaN(d) || d === 0) return '';
    return ' <span style="color:' + (d > 0 ? '#080' : '#a00') + '">'
      + (d > 0 ? '+' : '') + d + '</span>';
  }

  var html = '<style>body{font-family:Arial,sans-serif;padding:14px;font-size:13px}'
    + 'table{border-collapse:collapse;width:100%}'
    + 'th,td{padding:6px 10px;border-bottom:1px solid #eee;text-align:right}'
    + 'th:first-child,td:first-child{text-align:left}</style>'
    + '<h3>Inventory timeline</h3>'
    + '<table><tr><th>Date</th><th>Works</th><th>Eligible</th>'
    + '<th>Attributed</th><th>Conflicts</th></tr>';
  for (var i = 1; i < rows.length; i++) {
    var prev = i > 1 ? rows[i-1] : null;
    html += '<tr><td>' + rows[i][idx['date']] + '</td>'
      + '<td>' + rows[i][idx['works']] + delta(rows[i], prev, 'works') + '</td>'
      + '<td>' + rows[i][idx['artsy_eligible']] + delta(rows[i], prev, 'artsy_eligible') + '</td>'
      + '<td>' + rows[i][idx['attributed']] + delta(rows[i], prev, 'attributed') + '</td>'
      + '<td>' + rows[i][idx['conflicts']] + delta(rows[i], prev, 'conflicts') + '</td></tr>';
  }
  html += '</table>';
  SpreadsheetApp.getUi().showSidebar(
    HtmlService.createHtmlOutput(html).setTitle('Inventory timeline')
  );
}

function showPriceDistribution() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(MASTER_SHEET);
  if (!sheet) { SpreadsheetApp.getUi().alert('Refresh first.'); return; }
  var data = sheet.getDataRange().getValues();
  if (data.length < 2) return;
  var header = data[0];
  var priceCol = header.indexOf('price_usd');
  if (priceCol < 0) { SpreadsheetApp.getUi().alert('No price_usd column.'); return; }

  var bands = [
    { label: 'under $1k', max: 1000, n: 0, total: 0 },
    { label: '$1k–$5k',    max: 5000, n: 0, total: 0 },
    { label: '$5k–$10k',   max: 10000, n: 0, total: 0 },
    { label: '$10k–$25k',  max: 25000, n: 0, total: 0 },
    { label: '$25k–$50k',  max: 50000, n: 0, total: 0 },
    { label: '$50k–$100k', max: 100000, n: 0, total: 0 },
    { label: '$100k–$250k', max: 250000, n: 0, total: 0 },
    { label: '$250k+',      max: Infinity, n: 0, total: 0 },
  ];
  for (var r = 1; r < data.length; r++) {
    var p = parseFloat(data[r][priceCol]);
    if (!p || p <= 0) continue;
    for (var i = 0; i < bands.length; i++) {
      if (p < bands[i].max) {
        bands[i].n++;
        bands[i].total += p;
        break;
      }
    }
  }
  var totalN = bands.reduce(function(s, b) { return s + b.n; }, 0);
  var totalSum = bands.reduce(function(s, b) { return s + b.total; }, 0);
  var html = '<style>body{font-family:Arial,sans-serif;padding:14px}'
    + 'table{border-collapse:collapse;width:100%;font-size:12px}'
    + 'td,th{padding:3px 6px;text-align:left}.bar{background:#1976d2;height:8px;border-radius:4px}</style>'
    + '<h3>' + totalN + ' priced works · $' + Math.round(totalSum).toLocaleString() + '</h3>'
    + '<table><tr><th>band</th><th>count</th><th>%</th><th>total</th></tr>';
  for (var j = 0; j < bands.length; j++) {
    var b = bands[j];
    if (b.n === 0) continue;
    var pct = Math.round(100 * b.n / totalN);
    html += '<tr><td>' + b.label + '</td><td>' + b.n
        + '</td><td><div class="bar" style="width:' + pct + '%"></div> ' + pct + '%</td>'
        + '<td>$' + Math.round(b.total).toLocaleString() + '</td></tr>';
  }
  html += '</table>';
  SpreadsheetApp.getUi().showSidebar(
    HtmlService.createHtmlOutput(html).setTitle('Inventory · prices')
  );
}

function refreshFromRepo() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(MASTER_SHEET) || ss.insertSheet(MASTER_SHEET);
  sheet.clear();

  var resp = UrlFetchApp.fetch(MASTER_CSV_URL, {muteHttpExceptions: true});
  if (resp.getResponseCode() !== 200) {
    SpreadsheetApp.getUi().alert(
      'Failed to fetch master.csv (HTTP ' + resp.getResponseCode() + ').\n' +
      'Check MASTER_CSV_URL at the top of Code.gs.'
    );
    return;
  }
  var rows = Utilities.parseCsv(resp.getContentText());
  if (rows.length === 0) return;
  sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
  sheet.setFrozenRows(1);
  sheet.autoResizeColumns(1, Math.min(rows[0].length, 24));
  highlightConflicts();
  SpreadsheetApp.getActiveSpreadsheet().toast(
    'Imported ' + (rows.length - 1) + ' rows from repo.', 'Inventory', 5
  );
}

function highlightConflicts() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(MASTER_SHEET);
  if (!sheet) return;
  var data = sheet.getDataRange().getValues();
  if (data.length < 2) return;
  var header = data[0];

  // Find each <field>_conflict column and remember the index it points at.
  var conflictCols = [];  // {target: 5, flag: 27}
  for (var c = 0; c < header.length; c++) {
    var name = String(header[c]);
    if (name.length > 9 && name.slice(-9) === '_conflict') {
      var target = name.slice(0, -9);
      var ti = header.indexOf(target);
      if (ti >= 0) conflictCols.push({target: ti, flag: c});
    }
  }
  if (conflictCols.length === 0) return;

  for (var r = 1; r < data.length; r++) {
    for (var i = 0; i < conflictCols.length; i++) {
      var cc = conflictCols[i];
      if (String(data[r][cc.flag]) === '1') {
        sheet.getRange(r + 1, cc.target + 1).setBackground(CONFLICT_RED);
      }
    }
  }
}

function showGapsForSelectedWork() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(MASTER_SHEET);
  if (!sheet) {
    SpreadsheetApp.getUi().alert('Run "Refresh from repo" first.');
    return;
  }
  var row = sheet.getActiveCell().getRow();
  if (row < 2) {
    SpreadsheetApp.getUi().alert('Select a row in the Master sheet.');
    return;
  }
  var header = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  var values = sheet.getRange(row, 1, 1, sheet.getLastColumn()).getValues()[0];
  var rec = {};
  header.forEach(function (h, i) { rec[h] = values[i]; });

  var required = ['title', 'classification', 'medium', 'primary_image_url'];
  var core = ['title', 'artist', 'year', 'classification', 'medium',
              'height_in', 'width_in', 'primary_image_url', 'price_usd'];
  var missingArtsy = required.filter(function (f) { return !rec[f]; });
  var missingCore  = core.filter(function (f) { return !rec[f]; });
  var conflicts = String(rec.conflict_fields || '').split(',').filter(Boolean);

  var html =
    '<h3>' + (rec.work_id || '?') + ' &mdash; ' +
    (rec.title || '<i>(no title)</i>') + '</h3>' +
    '<p><b>Artsy-blocking missing:</b> ' +
    (missingArtsy.length ? missingArtsy.join(', ') : '&mdash;') + '</p>' +
    '<p><b>Core fields missing:</b> ' +
    (missingCore.length ? missingCore.join(', ') : '&mdash;') + '</p>' +
    '<p><b>Conflicting fields:</b> ' +
    (conflicts.length ? conflicts.join(', ') : '&mdash;') + '</p>' +
    '<hr>' +
    '<p><a target="_blank" href="' +
    'https://drive.google.com/drive/search?q=' + encodeURIComponent(rec.work_id) +
    '">Search Drive for ' + rec.work_id + '</a></p>';

  SpreadsheetApp.getUi().showSidebar(
    HtmlService.createHtmlOutput(html).setTitle('Inventory · ' + rec.work_id)
  );
}

function showStats() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(MASTER_SHEET);
  if (!sheet) { SpreadsheetApp.getUi().alert('Run "Refresh from repo" first.'); return; }
  var data = sheet.getDataRange().getValues();
  if (data.length < 2) return;
  var header = data[0];
  var idx = function (name) { return header.indexOf(name); };
  var n = data.length - 1;
  var conflicts = 0;
  var artsyReady = 0;
  var perField = {};
  ['title','artist','year','classification','medium','materials',
   'height_in','width_in','depth_in','price_usd','primary_image_url'].forEach(function (f) {
    perField[f] = 0;
  });
  var hasConflictCol = idx('has_conflict');
  for (var r = 1; r < data.length; r++) {
    if (hasConflictCol >= 0 && String(data[r][hasConflictCol]) === '1') conflicts++;
    Object.keys(perField).forEach(function (f) {
      if (idx(f) >= 0 && data[r][idx(f)] !== '' && data[r][idx(f)] !== null) perField[f]++;
    });
    var t = data[r][idx('title')], cls = data[r][idx('classification')],
        m = data[r][idx('medium')], img = data[r][idx('primary_image_url')];
    if (t && cls && m && img) artsyReady++;
  }
  var html = '<style>body{font-family:Arial,sans-serif;padding:14px}'
    + 'table{border-collapse:collapse;width:100%}td,th{padding:2px 6px}'
    + '.bar{background:#1976d2;height:8px;border-radius:4px}</style>'
    + '<h2>Inventory · ' + n + ' works</h2>'
    + '<table><tr><th align=left>Artsy-eligible</th><td>' + artsyReady + ' (' + Math.round(100*artsyReady/n) + '%)</td></tr>'
    + '<tr><th align=left>Conflicts</th><td>' + conflicts + '</td></tr></table><br>'
    + '<h3>Field coverage</h3><table>';
  Object.keys(perField).forEach(function (f) {
    var pct = Math.round(100 * perField[f] / n);
    html += '<tr><th align=left>' + f + '</th>'
        + '<td><div class="bar" style="width:' + pct + '%"></div></td>'
        + '<td>' + perField[f] + '/' + n + ' (' + pct + '%)</td></tr>';
  });
  html += '</table>';
  SpreadsheetApp.getUi().showSidebar(
    HtmlService.createHtmlOutput(html).setTitle('Inventory · stats')
  );
}

function suggestResolution() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(MASTER_SHEET);
  if (!sheet) { SpreadsheetApp.getUi().alert('Run "Refresh from repo" first.'); return; }
  var cell = sheet.getActiveCell();
  var row = cell.getRow();
  var col = cell.getColumn();
  if (row < 2) { SpreadsheetApp.getUi().alert('Click a cell in the data area first.'); return; }
  var header = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  var field = header[col - 1];
  var workId = sheet.getRange(row, 1).getValue();

  // Find the conflict-flag column for this field.
  var flagCol = header.indexOf(field + '_conflict');
  if (flagCol < 0 || String(sheet.getRange(row, flagCol + 1).getValue()) !== '1') {
    SpreadsheetApp.getUi().alert(
      'No conflict on ' + workId + '.' + field + '.\n' +
      'This panel only helps for cells flagged as conflicts (red).'
    );
    return;
  }

  var current = sheet.getRange(row, col).getValue();
  // Pull observations from data/master_provenance.csv.
  var url = MASTER_CSV_URL.replace(/master\.csv$/, 'master_provenance.csv');
  var resp = UrlFetchApp.fetch(url, {muteHttpExceptions: true});
  var alts = [];
  if (resp.getResponseCode() === 200) {
    var rows = Utilities.parseCsv(resp.getContentText());
    var hp = rows[0];
    for (var i = 1; i < rows.length; i++) {
      if (rows[i][hp.indexOf('work_id')] === workId &&
          rows[i][hp.indexOf('field')] === field) {
        var altVals = rows[i][hp.indexOf('alternative_values')];
        var altSrcs = rows[i][hp.indexOf('alternative_sources')];
        if (altVals) {
          altVals.split(' || ').forEach(function (v, j) {
            alts.push({ value: v, source: altSrcs.split(',')[j] || '?' });
          });
        }
        break;
      }
    }
  }

  // Build a pre-rendered command list (no client-side string juggling).
  var commands = alts.map(function (a) {
    return {
      value: a.value, source: a.source,
      cmd: 'python -m src.cli resolve ' + workId + ' ' + field
         + ' "' + a.value.replace(/"/g, '\\"') + '"'
         + ' --reason "..." --by your.email@kapoors.com',
    };
  });

  var html = '<style>body{font-family:Arial,sans-serif;padding:14px;font-size:13px}'
    + 'pre{background:#f4f4f4;padding:8px;white-space:pre-wrap;border-radius:4px;font-size:11px}'
    + 'button{margin-top:6px;padding:6px 10px;cursor:pointer}'
    + '.alt{margin:8px 0;padding:8px;border:1px solid #eee;border-radius:4px}</style>'
    + '<h3>Resolve ' + workId + '.' + field + '</h3>'
    + '<p><b>Currently in master.csv:</b> <code>' + (current || '<i>(empty)</i>') + '</code></p>'
    + '<p><b>Pick one of these and run the command in a terminal:</b></p>';
  commands.forEach(function (c, i) {
    var safeCmd = c.cmd.replace(/&/g, '&amp;').replace(/</g, '&lt;');
    html += '<div class="alt"><b>' + (c.value || '<i>(empty)</i>') + '</b>'
        + ' &mdash; <i>' + c.source + '</i>'
        + '<pre>' + safeCmd + '</pre></div>';
  });

  SpreadsheetApp.getUi().showSidebar(
    HtmlService.createHtmlOutput(html).setTitle('Resolve · ' + workId)
  );
}

function openDriveForSelectedWork() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(MASTER_SHEET);
  if (!sheet) return;
  var row = sheet.getActiveCell().getRow();
  if (row < 2) return;
  var workId = sheet.getRange(row, 1).getValue();
  if (!workId) return;
  var url = 'https://drive.google.com/drive/search?q=' + encodeURIComponent(workId);
  var html = '<script>window.open("' + url + '","_blank");google.script.host.close();</script>';
  SpreadsheetApp.getUi().showModalDialog(
    HtmlService.createHtmlOutput(html).setHeight(1).setWidth(1),
    'Opening Drive search…'
  );
}
