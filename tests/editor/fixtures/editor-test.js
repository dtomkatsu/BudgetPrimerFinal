// Shared fixtures for the draft-editor suite.
//
// Safety net: EVERY test — no exceptions — gets /__save, /__push and /__export
// blocked before it can navigate. Those three endpoints are served by the real
// report2027/tools/serve.py dev server and, unmocked, run actual `git commit` /
// `git push origin HEAD` + `HEAD:main` against this machine's real GitHub
// remote (see serve.py's _save()/_push()). A single spec that forgets to mock
// them would push a test commit to the live repo. Blocking happens here, once,
// so no individual spec file can opt out by omission.
//
// Routes are registered on the BROWSER CONTEXT, not the page: a page-level
// page.route() races the very first requests of an immediately-following
// goto() (Chromium's boot() fires /__ping, the Pyodide fetch, etc. before
// Playwright always finishes wiring page-level interception), so an early
// request can slip through unmocked. Context-level routes are attached before
// any page or navigation exists, so nothing can outrace them.
const base = require('@playwright/test');
const { FakeGitHub } = require('./fake-github');

async function blockDangerousLocalEndpoints(context) {
  await context.route('**/__save', route => route.fulfill({
    json: { ok: true, message: 'blocked in tests — no real save/push happens here', ahead: 0 },
  }));
  await context.route('**/__push', route => route.fulfill({
    json: { ok: true, message: 'blocked in tests — no real save/push happens here', ahead: 0 },
  }));
  await context.route('**/__export', route => route.fulfill({
    status: 200,
    contentType: 'application/pdf',
    body: Buffer.from('%PDF-1.4 fake export for tests'),
  }));
}

/** Wait for Pyodide to finish the first render: the report's page divs land
 *  inside the #out iframe via srcdoc once render() completes. Generous
 *  timeout — a cold Pyodide CDN fetch (~30MB) can take a while in CI. */
async function waitForFirstRender(page) {
  await page.frameLocator('#out').locator('.page').first().waitFor({
    state: 'visible', timeout: 75_000,
  });
}

async function gotoEditor(page, query = '') {
  await page.goto('edit.html' + query);
  await waitForFirstRender(page);
  // Local mode (serve.py answers /__ping) polls its live-reload stream and
  // can pick up one legitimate version bump moments after the first paint,
  // which swaps the iframe's srcdoc wholesale and re-wires every listener.
  // A click racing that swap can land on an element about to be discarded —
  // wait for it to settle before interacting with anything inside #out.
  await page.waitForTimeout(1500);
}

// Plain editor test: real local dev server (serve.py answers /__ping, so the
// app runs in "local" mode — Save/Discard write through /__save, which is
// mocked above). Right for anything that only needs the editing surface
// itself: sections, sources, undo/redo, download's local branch, standalone
// chrome. Never touches GitHub.
const test = base.test.extend({
  context: async ({ context }, use) => {
    await blockDangerousLocalEndpoints(context);
    await use(context);
  },
});

// Hosted editor test: forces local=false (blocks /__ping, exactly what
// detectLocal() treats as "no local server") and installs a fully in-memory
// fake GitHub so Save draft / Share / Publish / sign-in exercise the REAL
// gh()-based code path with zero network egress. Seeds a fake PAT so
// ensureAuth() resolves without a sign-in prompt, unless a test clears it.
const hostedTest = base.test.extend({
  github: async ({}, use) => {
    await use(new FakeGitHub());
  },
  context: async ({ context, github }, use) => {
    await blockDangerousLocalEndpoints(context);
    await context.route('**/__ping', route => route.fulfill({ status: 404, body: 'no local server' }));
    await github.install(context);
    await context.addInitScript(() => {
      window.localStorage.setItem('docsync-pat', 'fake-test-token');
    });
    await use(context);
  },
});

// --- native <dialog> helpers ------------------------------------------------
// prompt()/confirm() were replaced by dsForm/dsConfirm/dsPrompt over a native
// <dialog class="dsdlg"> in the PARENT document (not the iframe). These drive
// them: fill named fields, then submit (OK) or cancel.
async function dialog(page) {
  const d = page.locator('dialog.dsdlg');
  await d.waitFor({ state: 'visible' });
  return d;
}
async function fillDialog(page, values) {
  const d = await dialog(page);
  for (const [name, value] of Object.entries(values)) {
    const f = d.locator(`[name="${name}"]`);
    const tag = await f.evaluate(el => el.tagName);
    if (tag === 'SELECT') await f.selectOption(value);
    else await f.fill(value);
  }
  return d;
}
async function submitDialog(page) {
  const d = await dialog(page);
  await d.locator('.dsdlg-ok').click();
  await d.waitFor({ state: 'hidden' });
}
async function cancelDialog(page) {
  const d = await dialog(page);
  await d.locator('.dsdlg-cancel').click();
  await d.waitFor({ state: 'hidden' });
}
/** Submit a dialog only if one opens within `timeout` — for confirms that are
 *  conditional (e.g. the print-fit-cut warning on Save, which appears only when
 *  content overflows a page). Returns whether a dialog was handled. */
async function submitDialogIfPresent(page, timeout = 3000) {
  const d = page.locator('dialog.dsdlg');
  try { await d.waitFor({ state: 'visible', timeout }); } catch (e) { return false; }
  await d.locator('.dsdlg-ok').click();
  await d.waitFor({ state: 'hidden' });
  return true;
}

module.exports = {
  test, hostedTest, expect: base.expect, gotoEditor, waitForFirstRender,
  blockDangerousLocalEndpoints, dialog, fillDialog, submitDialog, cancelDialog,
  submitDialogIfPresent,
};
