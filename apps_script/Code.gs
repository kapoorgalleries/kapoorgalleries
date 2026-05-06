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
    .addItem('Highlight conflicts', 'highlightConflicts')
    .addSeparator()
    .addItem('Inspect selected work', 'showGapsForSelectedWork')
    .addItem('Suggest resolution for selected cell', 'suggestResolution')
    .addItem('Open Drive folder for KG-#', 'openDriveForSelectedWork')
    .addToUi();
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

  var html = '<style>body{font-family:Arial,sans-serif;padding:14px;font-size:13px}'
    + 'pre{background:#f4f4f4;padding:8px;white-space:pre-wrap;border-radius:4px}'
    + 'button{margin-top:6px;padding:6px 10px;cursor:pointer}</style>'
    + '<h3>Resolve ' + workId + '.' + field + '</h3>'
    + '<p><b>Currently in master.csv:</b> <code>' + (current || '<i>(empty)</i>') + '</code></p>'
    + '<p><b>Alternatives observed:</b></p><ul>';
  alts.forEach(function (a) {
    html += '<li><code>' + a.value + '</code> &mdash; <i>' + a.source + '</i>'
        + ' <button onclick="pickValue(' + JSON.stringify(a.value) + ')">Use this</button></li>';
  });
  html += '<li><i>or</i> <input id="custom" placeholder="custom value"> '
        + '<button onclick="pickValue(document.getElementById(\'custom\').value)">Use custom</button></li></ul>'
        + '<div id="cmd"></div>'
        + '<script>function pickValue(v){'
        + 'var cmd = "python -m src.cli resolve ' + workId + ' ' + field + ' \\\"" + v + "\\\""'
        + ' + " --reason \\\"...\\\""'
        + ' + " --by your.email@kapoors.com";'
        + 'document.getElementById("cmd").innerHTML = '
        + '"<p><b>Run this in your terminal:</b></p><pre>" + cmd + "</pre>"'
        + ' + "<button onclick=\\\"navigator.clipboard.writeText(\'\" + cmd.replace(/\'/g, \\\"\\\\\\\\&apos;\\\") + \"\')\\\">Copy command</button>";'
        + '}</script>';

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
