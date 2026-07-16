/**
 * Budget Primer — Google Doc <-> report sync.
 *
 * SETUP (once)
 * ------------
 * 1. Open the doc -> Extensions -> Apps Script.
 * 2. Delete the placeholder code, paste this whole file, and Save.
 * 3. In the left sidebar hit "+" next to Services, add "Drive API", click Add.
 *    (Used to replace the doc body by importing Markdown — Google converts it
 *    to real headings/bold/links/lists for us.)
 * 4. Reload the doc. A "Budget Primer" menu appears.
 * 5. First run asks you to authorise — it is your own script acting as you.
 *
 * THE TWO DIRECTIONS
 * ------------------
 * doc -> report : edit the doc, then run `make pull-doc` in the repo. It
 *   fetches this doc, validates it, and refuses to write if anything is
 *   malformed. Review the git diff, `make html`, push.
 *
 * report -> doc : when prose changes on the code side (content.md pushed to
 *   GitHub), run Budget Primer -> "Update from report (safe)". It refreshes
 *   the doc ONLY when that cannot lose anything:
 *     - if the doc has no edits since the last sync, it updates silently;
 *     - if the doc was edited but its content already matches the report
 *       (your edits were pulled and republished), it just records the sync;
 *     - if the doc has edits the report does not have, it STOPS and tells
 *       you to run `make pull-doc` first (or use Force replace to discard).
 *   "Enable hourly auto-sync" runs the same safe check on a timer, so pushed
 *   changes appear in the doc within the hour with no clicking at all.
 *
 * ADDING A NEW SECTION FROM THE DOC (no code changes)
 * ---------------------------------------------------
 * Add a line  [[extra.<page>.<your-slug>]]  followed by your content —
 * headings (Heading 2/3), paragraphs and "- " bullets all work. It renders
 * at the end of that page. Valid <page> names:
 *   basics, process, spent, categories, cip, onetime, funding, taxes, whopays
 *
 * RULES THAT KEEP THE BUILD WORKING
 * ---------------------------------
 * * Keep every existing [[key]] marker exactly as-is (they render small and
 *   grey). Renaming or deleting one fails the build loudly — it never
 *   silently drops text. The real headings are what you edit against.
 * * A slot can hold more than one paragraph: leave a blank line between them.
 * * Footnote refs are stable ids like [^act99]; the report numbers them
 *   automatically. Every [^id] must have a matching entry under [[sources]].
 * * Figures, Table 1 and all dollar amounts are generated from the budget
 *   data — they are not in this doc and cannot be edited here.
 * * The published HTML is generated; never hand-edit it. Prose lives here
 *   (or in content.md), layout lives in the renderer.
 */

var CONTENT_URL =
  'https://raw.githubusercontent.com/dtomkatsu/BudgetPrimerFinal/main/report2027/content.md';

function onOpen() {
  DocumentApp.getUi()
    .createMenu('Budget Primer')
    .addItem('Update from report (safe)', 'updateFromReport')
    .addItem('Preview report content (no changes)', 'previewReportContent')
    .addSeparator()
    .addItem('Enable hourly auto-sync', 'enableAutoSync')
    .addItem('Disable auto-sync', 'disableAutoSync')
    .addSeparator()
    .addItem('Force replace doc with report content', 'replaceDocWithReportContent')
    .addItem('Tidy [[key]] markers', 'tidyKeyMarkers')
    .addToUi();
}

/** Fetch content.md, failing with a readable message rather than a stack trace. */
function fetchContent_() {
  var res = UrlFetchApp.fetch(CONTENT_URL + '?t=' + Date.now(),
                              { muteHttpExceptions: true });
  var code = res.getResponseCode();
  if (code !== 200) {
    throw new Error(
      'Could not fetch the report content (HTTP ' + code + ').\n\n' +
      (code === 404
        ? 'content.md is not on the main branch yet — push it first.'
        : CONTENT_URL));
  }
  var md = res.getContentText();
  // Guard against replacing the doc with an error page or a truncated file.
  if (md.indexOf('[[sources]]') === -1 || md.indexOf('[[basics.p1]]') === -1) {
    throw new Error('Fetched content does not look like the primer — aborting ' +
                    'so the doc is not clobbered.');
  }
  return md;
}

function previewReportContent() {
  var ui = DocumentApp.getUi();
  try {
    var md = fetchContent_();
    var keys = (md.match(/^\[\[[A-Za-z0-9._-]+\]\]$/gm) || []).length;
    ui.alert('Report content looks good',
             keys + ' sections fetched, ' + md.length + ' characters.\n\n' +
             'First lines:\n\n' + md.split('\n').slice(0, 6).join('\n'),
             ui.ButtonSet.OK);
  } catch (e) {
    ui.alert('Preview failed', e.message, ui.ButtonSet.OK);
  }
}

// ---------------------------------------------------------------------------
// report -> doc, the safe way
// ---------------------------------------------------------------------------

function contentHash_(md) {
  return Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, md,
                                 Utilities.Charset.UTF_8)
    .map(function (b) { return ((b & 0xff) + 0x100).toString(16).slice(1); })
    .join('');
}

/** Rough mirror of pull_doc.py's normalise(): enough to tell "same content,
 *  different cosmetics" from a real difference. */
function normalise_(md) {
  return md
    .replace(/\r\n/g, '\n')
    .replace(/ /g, ' ')
    .replace(/\\([\[\]*_`#\\])/g, '$1')
    .replace(/[ \t]+$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

/** This doc's own content, exported as Markdown. */
function exportDocMarkdown_(docId) {
  var res = UrlFetchApp.fetch(
    'https://docs.google.com/document/d/' + docId + '/export?format=markdown',
    { headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
      muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) {
    throw new Error('Could not export this doc for comparison (HTTP ' +
                    res.getResponseCode() + ').');
  }
  return res.getContentText();
}

/** Overwrite the doc body with md, dim the markers, record the sync state. */
function replaceDoc_(docId, md) {
  var blob = Utilities.newBlob(md, 'text/markdown', 'content.md');
  Drive.Files.update({ mimeType: 'application/vnd.google-apps.document' },
                     docId, blob);
  var dimmed = dimKeyMarkers_();
  recordSync_(docId, md);
  return dimmed;
}

function recordSync_(docId, md) {
  var props = PropertiesService.getDocumentProperties();
  props.setProperty('SYNC_HASH', contentHash_(md));
  // stamp AFTER our own writes so they don't count as "user edits"
  props.setProperty('SYNC_TIME',
    String(DriveApp.getFileById(docId).getLastUpdated().getTime()));
}

/**
 * The safe report->doc refresh. Returns {status, message}; never loses edits.
 * status: 'current' | 'updated' | 'recorded' | 'conflict' | 'unsynced'
 */
function syncFromReport_() {
  var md = fetchContent_();
  var docId = DocumentApp.getActiveDocument().getId();
  var props = PropertiesService.getDocumentProperties();
  var lastHash = props.getProperty('SYNC_HASH');
  var lastTime = Number(props.getProperty('SYNC_TIME') || 0);

  if (lastHash && contentHash_(md) === lastHash) {
    // report unchanged since last sync — but the doc may have drifted;
    // nothing to push either way.
    return { status: 'current',
             message: 'The doc already has the latest report content.' };
  }

  var docEdited = !lastTime ||
    DriveApp.getFileById(docId).getLastUpdated().getTime() > lastTime + 2500;

  if (!docEdited) {
    var dimmed = replaceDoc_(docId, md);
    return { status: 'updated',
             message: 'Doc updated from the report (' + dimmed +
                      ' markers dimmed). Reload to see it.' };
  }

  // Doc was edited (or never synced). If its content already equals the
  // report's — e.g. the edits were pulled via `make pull-doc` and republished
  // — there is nothing to lose: just record the state.
  if (normalise_(exportDocMarkdown_(docId)) === normalise_(md)) {
    recordSync_(docId, md);
    return { status: 'recorded',
             message: 'Doc and report already match — sync state recorded.' };
  }

  if (!lastTime) {
    return { status: 'unsynced',
             message: 'This doc has never been synced. Use "Force replace ' +
                      'doc with report content" once to initialise (it ' +
                      'overwrites the doc — make a copy first if needed).' };
  }
  return { status: 'conflict',
           message: 'This doc has edits that are not in the report yet.\n\n' +
                    'Run `make pull-doc` in the repo to bring them in first, ' +
                    'then update again — or use "Force replace" to discard ' +
                    'the doc edits.' };
}

function updateFromReport() {
  var ui = DocumentApp.getUi();
  try {
    var out = syncFromReport_();
    ui.alert('Update from report', out.message, ui.ButtonSet.OK);
  } catch (e) {
    ui.alert('Update failed', e.message, ui.ButtonSet.OK);
  }
}

/** Trigger entry point — same logic, no UI. Conflicts just wait for a human. */
function autoSyncFromReport() {
  try {
    var out = syncFromReport_();
    console.log('auto-sync: ' + out.status + ' — ' + out.message);
  } catch (e) {
    console.log('auto-sync failed: ' + e.message);
  }
}

function enableAutoSync() {
  removeAutoSyncTriggers_();
  ScriptApp.newTrigger('autoSyncFromReport').timeBased().everyHours(1).create();
  DocumentApp.getUi().alert('Auto-sync on',
    'The doc will refresh from the report hourly — but only when that ' +
    'cannot lose doc edits. Conflicts wait for a manual `make pull-doc`.',
    DocumentApp.getUi().ButtonSet.OK);
}

function disableAutoSync() {
  var n = removeAutoSyncTriggers_();
  DocumentApp.getUi().alert('Auto-sync off',
    n ? 'Hourly trigger removed.' : 'No trigger was set.',
    DocumentApp.getUi().ButtonSet.OK);
}

function removeAutoSyncTriggers_() {
  var n = 0;
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'autoSyncFromReport') {
      ScriptApp.deleteTrigger(t); n++;
    }
  });
  return n;
}

// ---------------------------------------------------------------------------
// force replace (destructive) + marker cosmetics
// ---------------------------------------------------------------------------

function replaceDocWithReportContent() {
  var ui = DocumentApp.getUi();
  var md;
  try {
    md = fetchContent_();
  } catch (e) {
    ui.alert('Fetch failed', e.message, ui.ButtonSet.OK);
    return;
  }

  var ok = ui.alert(
    'Replace this document?',
    'This overwrites the ENTIRE document with the report\'s current prose ' +
    '(' + (md.match(/^\[\[[A-Za-z0-9._-]+\]\]$/gm) || []).length + ' sections).\n\n' +
    'Anything currently in this doc is lost, and existing comments will ' +
    'detach. Make a copy first if you need the old version.\n\nContinue?',
    ui.ButtonSet.OK_CANCEL);
  if (ok !== ui.Button.OK) return;

  var docId = DocumentApp.getActiveDocument().getId();
  try {
    var dimmed = replaceDoc_(docId, md);
  } catch (e) {
    ui.alert('Replace failed',
             e.message + '\n\nIf this mentions "Drive", add the Drive API ' +
             'service in the Apps Script sidebar (step 3 of setup).',
             ui.ButtonSet.OK);
    return;
  }

  ui.alert('Done',
           'Reload the doc to see the new content.\n\n' +
           dimmed + ' [[key]] markers were dimmed so the real headings stand out.',
           ui.ButtonSet.OK);
}

/**
 * Push the [[key]] markers into the background: small, grey, italic. They have
 * to stay in the text (the build maps them to slots), but nobody should have to
 * read them — the real headings are what you edit against.
 */
function dimKeyMarkers_() {
  var body = DocumentApp.getActiveDocument().getBody();
  var paras = body.getParagraphs();
  var n = 0;
  for (var i = 0; i < paras.length; i++) {
    var p = paras[i];
    if (!/^\s*\[\[[A-Za-z0-9._-]+\]\]\s*$/.test(p.getText())) continue;
    p.editAsText()
      .setFontSize(7.5)
      .setForegroundColor('#9aa5a0')   // recedes against body copy
      .setItalic(true)
      .setBold(false);
    p.setSpacingBefore(10).setSpacingAfter(0);
    n++;
  }
  return n;
}

/** Re-dim markers if editing has reset their formatting. Safe to run anytime. */
function tidyKeyMarkers() {
  var n = dimKeyMarkers_();
  DocumentApp.getUi().alert('Tidied', n + ' markers dimmed.',
                            DocumentApp.getUi().ButtonSet.OK);
}
