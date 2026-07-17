/**
 * Budget Primer — optional in-doc convenience menu.
 *
 * THIS IS NOT THE SYNC ENGINE. docsync (GitHub Actions, see docsync/SETUP.md)
 * is the engine of record: it syncs every binding in docsync.yml both ways on
 * a schedule, under a service account, whether or not anyone is at a laptop.
 *
 * This script is a nicety for someone editing the doc who wants an immediate
 * nudge instead of waiting for the next scheduled run, plus the marker
 * cosmetics the engine has no way to apply (Drive's Markdown import cannot
 * style individual paragraphs).
 *
 * Because it runs as YOU and not the service account, its safety check reads
 * PropertiesService, which CI cannot see. Two mechanisms tracking the same
 * thing can disagree, so prefer the engine and treat this as a shortcut:
 *
 *   Update from report (safe)  — same conflict rules, applied client-side
 *   Tidy [[key]] markers       — re-dim markers after editing resets them
 *   Force replace              — discard doc edits; the engine's --force
 *
 * SETUP (only if you want the menu)
 * --------------------------------
 * 1. Open the doc -> Extensions -> Apps Script.
 * 2. Paste this whole file and Save.
 * 3. Sidebar "+" next to Services -> add "Drive API" -> Add.
 * 4. Reload the doc; a "Budget Primer" menu appears.
 *
 * EDITING RULES (these are what the build enforces, engine or not)
 * ---------------------------------------------------------------
 * * Keep every [[key]] marker exactly as-is. Renaming or deleting one fails
 *   the build loudly — it never silently drops text.
 * * A slot can hold more than one paragraph: leave a blank line between them.
 * * To add a whole new subsection, use an overflow slot:
 *     [[extra.<page>.<your-slug>]]
 *   where <page> is one of: basics, process, spent, categories, cip, onetime,
 *   funding, taxes, whopays. Headings, paragraphs and "- " bullets all work,
 *   and it renders at the end of that page with no code change.
 * * Footnote refs are stable ids like [^act99]; the report numbers them.
 *   Every [^id] needs an entry under [[sources]].
 * * Figures, Table 1 and all dollar amounts come from the budget data — they
 *   are not in this doc and cannot be edited here.
 */

var CONTENT_URL =
  'https://raw.githubusercontent.com/dtomkatsu/BudgetPrimerFinal/main/report2027/content.md';

function onOpen() {
  DocumentApp.getUi()
    .createMenu('Budget Primer')
    .addItem('Update from report (safe)', 'updateFromReport')
    .addItem('Enable instant sync (doc edits -> site in ~2 min)', 'enableInstantSync')
    .addItem('Disable instant sync', 'disableInstantSync')
    .addItem('Sync now', 'syncNow')
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

// ---------------------------------------------------------------------------
// instant sync: doc edit -> repository_dispatch -> the docsync workflow pulls
// ---------------------------------------------------------------------------
// Docs cannot tell us an edit happened — it has no onChange/onEdit trigger
// (those are Sheets and Forms only), and a time-based trigger is the finest
// grain on offer. So poll the modified time once a minute and dispatch when it
// settles. ~2 min from last keystroke to live site; for seconds, the draft
// preview renders this doc directly and needs none of this.

var GH_REPO = 'dtomkatsu/BudgetPrimerFinal';
// Triggers and web-app requests have no active document, so the id is pinned.
var DOC_ID = '1wOwrX6ISoTvYEp7Ut7HIOmng8PHkp_HEZ9veWihu4TU';

function enableInstantSync() {
  var ui = DocumentApp.getUi();
  var props = PropertiesService.getScriptProperties();
  if (!props.getProperty('GH_TOKEN')) {
    var r = ui.prompt('GitHub token needed once',
      'Paste a fine-grained personal access token for ' + GH_REPO + '\n' +
      '(github.com -> Settings -> Developer settings -> Fine-grained tokens;\n' +
      'Only this repository; Permissions: Contents -> Read and write).\n\n' +
      'It is stored in this script\'s properties, visible only to you.',
      ui.ButtonSet.OK_CANCEL);
    if (r.getSelectedButton() !== ui.Button.OK || !r.getResponseText().trim()) return;
    props.setProperty('GH_TOKEN', r.getResponseText().trim());
  }
  removeTriggers_('pollDocChange');
  ScriptApp.newTrigger('pollDocChange').timeBased().everyMinutes(1).create();
  PropertiesService.getScriptProperties().deleteProperty('SEEN_MOD');
  ui.alert('Instant sync on',
    'The doc is checked once a minute. Edits reach the site about two '
    + 'minutes after you stop typing.\n\n'
    + 'For seconds-level feedback while you write, keep the draft preview '
    + 'open — it renders the real page from this doc as you go.',
    ui.ButtonSet.OK);
}

function disableInstantSync() {
  var n = removeTriggers_('pollDocChange');
  DocumentApp.getUi().alert('Instant sync off',
    n ? 'Trigger removed.' : 'It was not on.',
    DocumentApp.getUi().ButtonSet.OK);
}

/**
 * Fire a pull once the doc has been quiet for a minute.
 *
 * Docs has no edit trigger — onChange/onEdit exist for Sheets and Forms only,
 * so an edit cannot summon anything. Polling the modified time is the closest
 * legal thing, and the minute of quiet falls out of it for free: a change is
 * noticed on one tick and dispatched on the next, so a run happens after the
 * typing stops rather than in the middle of it.
 */
function pollDocChange() {
  var props = PropertiesService.getScriptProperties();
  if (!props.getProperty('GH_TOKEN')) return;
  var mod = String(DriveApp.getFileById(DOC_ID).getLastUpdated().getTime());
  var seen = props.getProperty('SEEN_MOD');
  var fired = props.getProperty('FIRED_MOD');

  if (mod !== seen) {
    props.setProperty('SEEN_MOD', mod);      // still moving; wait for quiet
    return;
  }
  if (mod === fired) return;                 // quiet, and already dispatched
  firePull_();
  props.setProperty('FIRED_MOD', mod);
}

function firePull_() {
  var token = PropertiesService.getScriptProperties().getProperty('GH_TOKEN');
  if (!token) return;
  var res = UrlFetchApp.fetch('https://api.github.com/repos/' + GH_REPO + '/dispatches', {
    method: 'post',
    contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + token,
               Accept: 'application/vnd.github+json' },
    payload: JSON.stringify({ event_type: 'docsync-pull' }),
    muteHttpExceptions: true,
  });
  // 204 is success. A 401/403 means the token expired or lacks Contents:write,
  // and a silent no-op would look exactly like "sync is just slow".
  if (res.getResponseCode() >= 300) {
    console.log('dispatch failed ' + res.getResponseCode() + ': '
                + res.getContentText().slice(0, 200));
  }
}

/** Fire a pull right now, without waiting for the poll. */
function syncNow() {
  var ui = DocumentApp.getUi();
  if (!PropertiesService.getScriptProperties().getProperty('GH_TOKEN')) {
    ui.alert('No GitHub token', 'Run "Enable instant sync" first.', ui.ButtonSet.OK);
    return;
  }
  firePull_();
  ui.alert('Sync requested',
    'The workflow was asked to pull this doc. Give it a minute or two.',
    ui.ButtonSet.OK);
}

function removeTriggers_(handler) {
  var n = 0;
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === handler) { ScriptApp.deleteTrigger(t); n++; }
  });
  return n;
}

// ---------------------------------------------------------------------------
// live preview feed: GET this script's /exec URL -> the doc as Markdown
// ---------------------------------------------------------------------------
// The preview page renders the report in-browser from the doc's CURRENT text.
// It cannot read the export endpoint directly (no CORS), so this tiny web app
// is the doc's CORS-friendly window. Deploy once: Deploy -> New deployment ->
// Web app -> execute as Me, access "Anyone" -> copy the /exec URL into the
// preview page's settings. Serving text only; the doc is link-visible anyway.

function doGet() {
  var res = UrlFetchApp.fetch(
    'https://docs.google.com/document/d/' + DOC_ID + '/export?format=markdown',
    { headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() } });
  return ContentService.createTextOutput(res.getContentText())
                       .setMimeType(ContentService.MimeType.TEXT);
}
