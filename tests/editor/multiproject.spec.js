// Multi-project registry (docsync/editor/edit.html): loadRegistry() reads
// projects.json beside the editor and shows a #proj picker only when it names
// 2+ ids — one editor, any number of reports. This repo's real projects.json
// has exactly one entry (budget-primer), so the picker never appears in
// production; inject a second id to exercise the switching behavior itself.
const { test, expect, gotoEditor, fillDialog, submitDialog, cancelDialog } = require('./fixtures/editor-test');

async function withTwoProjectRegistry(context) {
  // get()'s cache-buster appends ?cb=<timestamp> — match that suffix too.
  await context.route('**/projects.json*', async route => {
    const res = await route.fetch();
    const real = await res.json();
    const ids = Object.keys(real);
    // Second entry points at the SAME engine/ (base: '') as the first — the
    // switching mechanism (picker, URL, PROJECT var) is what's under test,
    // not a second real report's content.
    real['second-report'] = { name: 'Second Report', base: '', repo: real[ids[0]].repo };
    await route.fulfill({ response: res, json: real });
  });
}

test.describe('multi-project registry', () => {
  test.beforeEach(async ({ context }) => {
    await withTwoProjectRegistry(context);
  });

  test('the picker is hidden with one project, visible with two', async ({ page }) => {
    await gotoEditor(page);
    const sel = page.locator('#proj');
    await expect(sel).toBeVisible();
    const values = await sel.locator('option').evaluateAll(opts => opts.map(o => o.value));
    expect(values.sort()).toEqual(['budget-primer', 'second-report']);
  });

  test('switching projects navigates with ?project= and the picker reflects it', async ({ page }) => {
    await gotoEditor(page);
    await page.locator('#proj').selectOption('second-report');
    await page.waitForURL(/[?&]project=second-report/);
    await page.frameLocator('#out').locator('.page').first().waitFor({ state: 'visible' });

    expect(new URL(page.url()).searchParams.get('project')).toBe('second-report');
    await expect(page.locator('#proj')).toHaveValue('second-report');
  });

  test('an unknown ?project= falls back to the default engine, not an error', async ({ page }) => {
    await gotoEditor(page, '?project=does-not-exist');
    await expect(page.locator('#proj')).toHaveValue('budget-primer');
    await expect(page.locator('#title')).toContainText('budget-primer');
  });

  test('switching with unsaved edits asks for confirmation first', async ({ page }) => {
    await gotoEditor(page);
    // Make a real edit so dirty=true — reuse the +Section flow (already proven
    // in sections.spec.js) via its <dialog> form.
    await page.click('#add');
    await fillDialog(page, { page: 'basics', slug: 'mp-test-section' });
    await submitDialog(page);
    await page.frameLocator('#out').locator('.ds-edit').waitFor({ state: 'visible' });
    await page.keyboard.press('Escape');
    await expect(page.locator('#undo')).toBeEnabled();   // confirms the edit landed, dirty=true

    const urlBefore = page.url();
    await page.locator('#proj').selectOption('second-report');
    await cancelDialog(page);   // decline the "Switch project?" confirm
    await page.waitForTimeout(500);   // give a (wrongly) accepted navigation a chance to happen

    expect(page.url()).toBe(urlBefore);   // declined -> selection reverts, no navigation
    await expect(page.locator('#proj')).toHaveValue('budget-primer');
  });
});
