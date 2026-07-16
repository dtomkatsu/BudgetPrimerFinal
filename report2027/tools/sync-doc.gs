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
 * USE
 * ---
 * Budget Primer -> "Replace doc with report content"
 *   Overwrites this doc with the report's current prose (report -> doc).
 *   Use this for the initial sync, or to reset the doc to what shipped.
 *
 * Then edit the doc normally. To pull your edits back into the report, run
 * `make pull-doc` in the repo — it fetches this doc, validates it, and refuses
 * to write if anything is malformed. Review the git diff, then `make html`.
 *
 * RULES THAT KEEP THE BUILD WORKING
 * ---------------------------------
 * * Keep every "## key" heading exactly as-is. Renaming or deleting one fails
 *   the build loudly (it never silently drops text).
 * * Footnote refs are stable ids like [^act99]; the report numbers them
 *   automatically, so inserting a source never means renumbering by hand.
 * * Every [^id] must have a matching entry under "## sources".
 * * Figures, Table 1 and all dollar amounts are generated from the budget data
 *   — they are not in this doc and cannot be edited here.
 */

var CONTENT_URL =
  'https://raw.githubusercontent.com/dtomkatsu/BudgetPrimerFinal/main/report2027/content.md';

function onOpen() {
  DocumentApp.getUi()
    .createMenu('Budget Primer')
    .addItem('Replace doc with report content', 'replaceDocWithReportContent')
    .addItem('Preview report content (no changes)', 'previewReportContent')
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
  if (md.indexOf('## sources') === -1 || md.indexOf('## basics.p1') === -1) {
    throw new Error('Fetched content does not look like the primer — aborting ' +
                    'so the doc is not clobbered.');
  }
  return md;
}

function previewReportContent() {
  var ui = DocumentApp.getUi();
  try {
    var md = fetchContent_();
    var keys = (md.match(/^## /gm) || []).length;
    ui.alert('Report content looks good',
             keys + ' sections fetched, ' + md.length + ' characters.\n\n' +
             'First lines:\n\n' + md.split('\n').slice(0, 6).join('\n'),
             ui.ButtonSet.OK);
  } catch (e) {
    ui.alert('Preview failed', e.message, ui.ButtonSet.OK);
  }
}

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
    '(' + (md.match(/^## /gm) || []).length + ' sections).\n\n' +
    'Anything currently in this doc is lost, and existing comments will ' +
    'detach. Make a copy first if you need the old version.\n\nContinue?',
    ui.ButtonSet.OK_CANCEL);
  if (ok !== ui.Button.OK) return;

  var docId = DocumentApp.getActiveDocument().getId();
  try {
    // Import the Markdown over the existing doc: Drive converts "## key" to
    // Heading 2, **bold**, [links](), and "- " lists into real Docs formatting,
    // and the Markdown export round-trips it back for `make pull-doc`.
    var blob = Utilities.newBlob(md, 'text/markdown', 'content.md');
    Drive.Files.update({ mimeType: 'application/vnd.google-apps.document' },
                       docId, blob);
  } catch (e) {
    ui.alert('Replace failed',
             e.message + '\n\nIf this mentions "Drive", add the Drive API ' +
             'service in the Apps Script sidebar (step 3 of setup).',
             ui.ButtonSet.OK);
    return;
  }
  ui.alert('Done', 'Reload the doc to see the new content.', ui.ButtonSet.OK);
}
