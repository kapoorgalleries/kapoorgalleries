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
    .addItem('Highlight conflicts', 'highlightConflicts')
    .addItem('Show gaps for selected work', 'showGapsForSelectedWork')
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
