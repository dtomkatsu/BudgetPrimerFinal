// Local Save vs explicit Push (docsync/editor/edit.html Save/Push buttons,
// report2027/tools/serve.py _save/_push). Save writes content.md/layout.json
// to disk and commits LOCALLY — it never pushes on its own, so it can never
// surprise-trigger GitHub Actions (build.yml watches pushes to main) or send
// something to the shared repo before you meant to. Push is the separate,
// explicit action that sends whatever is committed locally to GitHub.
//
// /__save and /__push are mocked (fixtures/editor-test.js) so this never
// touches the real repo. /__ping is mocked HERE, per test, to a fixed `ahead`
// — the real server's own 1.5s poll (detectLocal) keeps running against
// whatever /__ping resolves to, and a genuinely-zero real value would
// otherwise race a test's own setPushState() call back to disabled between
// the call and the next assertion. Mocking makes the poll agree with the
// scenario instead of fighting it. These tests are about the CLIENT'S state
// machine, not serve.py's actual git plumbing.
const { test, hostedTest, expect, gotoEditor, submitDialogIfPresent } = require('./fixtures/editor-test');

/** Navigate with /__ping pinned to a fixed `ahead`, registered before the
 *  page ever loads — detectLocal()'s first ping (which decides `local` and
 *  the button's initial state) must see the same value the 1.5s poll will
 *  keep reporting for the rest of the test. */
async function gotoWithAhead(page, context, ahead) {
  await context.route('**/__ping', route => route.fulfill({ json: { ok: true, v: 1, ahead } }));
  await gotoEditor(page);
}

test.describe('local Save vs Push', () => {
  test('Push is visible in local mode, disabled with nothing to push', async ({ page, context }) => {
    await gotoWithAhead(page, context, 0);
    await expect(page.locator('#push')).toBeVisible();
    await expect(page.locator('#push')).toBeDisabled();   // nothing to push yet
  });

  // Regression: detectLocal() sets share/publish's `hidden` PROPERTY in local
  // mode, but a CSS rule (#bar button's display:inline-flex) can render a
  // "hidden" element anyway — see the hosted-mode describe block below for
  // the full explanation. toBeHidden() checks the real rendered box, which a
  // `.hidden` DOM-property read would not have caught.
  test('Share and Publish are genuinely hidden in local mode, not just marked', async ({ page, context }) => {
    await gotoWithAhead(page, context, 0);
    await expect(page.locator('#share')).toBeHidden();
    await expect(page.locator('#publish')).toBeHidden();
  });


  test('Save writes locally and does not claim anything was pushed', async ({ page, context }) => {
    await gotoWithAhead(page, context, 0);
    await page.evaluate(() => { source = original + '\n'; markDirty(); });
    await expect(page.locator('#save')).toBeEnabled();
    await page.click('#save');
    await submitDialogIfPresent(page);
    // Not "the word push appears anywhere" (the safety mock's OWN message
    // mentions push) — specifically, no claim of a completed push.
    await expect(page.locator('#stat')).not.toContainText('pushed');
    await expect(page.locator('#save')).toBeDisabled();      // dirty cleared
  });

  test('Save response drives the Push button state via setPushState', async ({ page, context }) => {
    // Pin the poll to 2 throughout: the assertions below drive setPushState
    // directly (simulating what /__save's own response would carry, since
    // that endpoint is a fixed stub), and the poll must not contradict them.
    await gotoWithAhead(page, context, 2);
    await page.evaluate(() => setPushState(2));
    await expect(page.locator('#push')).toBeEnabled();
    await expect(page.locator('#push')).toHaveClass(/\bpending\b/);
    await expect(page.locator('#push')).toHaveText('Push (2)');
  });

  test('reaching zero ahead disables the button again', async ({ page, context }) => {
    await gotoWithAhead(page, context, 0);
    await page.evaluate(() => setPushState(0));
    await expect(page.locator('#push')).toBeDisabled();
    await expect(page.locator('#push')).not.toHaveClass(/\bpending\b/);
    await expect(page.locator('#push')).toHaveText('Push');
  });

  test('clicking Push calls /__push and reflects the response', async ({ page, context }) => {
    await gotoWithAhead(page, context, 1);
    await context.route('**/__push', route => route.fulfill({
      json: { ok: true, message: 'pushed — GitHub Pages deploys in about a minute', ahead: 0 },
    }));
    await expect(page.locator('#push')).toBeEnabled();
    await page.click('#push');
    await expect(page.locator('#stat')).toContainText('pushed', { timeout: 5000 });
    await expect(page.locator('#push')).toBeDisabled();
  });

  test('a rejected push surfaces the error and stays enabled to retry', async ({ page, context }) => {
    await gotoWithAhead(page, context, 1);
    await context.route('**/__push', route => route.fulfill({
      json: { ok: false, error: 'push rejected — the remote has commits this machine doesn\'t '
        + '(often build.yml\'s own rebuild). Ask Claude to reconcile it.', ahead: 1 },
    }));
    await expect(page.locator('#push')).toBeEnabled();
    await page.click('#push');
    await expect(page.locator('#stat')).toContainText('push failed');
    await expect(page.locator('#stat')).toContainText('reconcile');
    await expect(page.locator('#push')).toBeEnabled();   // still there to retry
  });

  test('setPushState ignores a non-numeric ahead (a mocked/blocked response)', async ({ page, context }) => {
    // The test-safety mock (blockDangerousLocalEndpoints) returns ahead: 0
    // explicitly, but any caller passing undefined must not crash or blank
    // the button — this is what keeps every OTHER local-mode spec safe from
    // the Save mock's response shape.
    await gotoWithAhead(page, context, 3);
    await page.evaluate(() => setPushState(3));
    await expect(page.locator('#push')).toHaveText('Push (3)');
    await page.evaluate(() => setPushState(undefined));
    await expect(page.locator('#push')).toHaveText('Push (3)');   // unchanged
  });
});

hostedTest.describe('hosted mode: local-only controls truly hidden, not just marked', () => {
  // Regression: [hidden] alone does not hide a #bar button — #bar button's
  // own display:inline-flex rule outranks the attribute's (non-!important)
  // display:none, so a button relying on ONLY the attribute rendered anyway.
  // toBeHidden() (not a `.hidden` DOM-property read) is what actually catches
  // this, since it checks the rendered box the same way the bug hid in it —
  // Share/Publish had this exact bug for a long time with no test to catch
  // it, since nothing asserted their LOCAL-mode hidden state; Push inherited
  // it on arrival, which is what surfaced it.
  hostedTest('Push stays hidden in hosted mode (no local dev server)', async ({ page }) => {
    await gotoEditor(page);
    await expect(page.locator('#push')).toBeHidden();
    await expect(page.locator('#share')).toBeVisible();     // the hosted-only controls
    await expect(page.locator('#publish')).toBeVisible();
  });
});
