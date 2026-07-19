// Offline draft cache (docsync/editor/edit.html): unsaved edits are autosaved
// to IndexedDB via idb-keyval (debounced, hosted mode only) and auto-restored
// on the next boot, so a closed tab or a refresh before a network Save does not
// lose work. Hosted mode — page.reload() keeps the same origin, so the same
// IndexedDB and the fake-GitHub context routes survive the reload.
const { hostedTest: test, expect, gotoEditor, waitForFirstRender,
        fillDialog, submitDialog, submitDialogIfPresent } = require('./fixtures/editor-test');

async function addSection(page, slug) {
  await page.click('#add');
  await fillDialog(page, { page: 'basics', slug });
  await submitDialog(page);
  await page.frameLocator('#out').locator('.ds-edit').waitFor({ state: 'visible' });
  await page.keyboard.press('Escape');
}

test.describe('offline draft cache', () => {
  test('an unsaved section survives a reload and is auto-restored', async ({ page }) => {
    await gotoEditor(page);
    await addSection(page, 'cache-survivor');
    const key = 'extra.basics.cache-survivor';
    await expect(page.frameLocator('#out').locator(`[data-slot="${key}"]`)).toHaveCount(1);

    // Let the debounced (800ms) autosave land in IndexedDB before reloading.
    await page.waitForTimeout(1200);
    await page.reload();
    await waitForFirstRender(page);

    // The unsaved section is back — restored from IndexedDB, not from GitHub
    // (nothing was ever saved to the branch).
    await expect(page.frameLocator('#out').locator(`[data-slot="${key}"]`)).toHaveCount(1);
    await expect(page.locator('#stat')).toContainText('restored unsaved edits');
  });

  test('after Save the cache is cleared, so a reload does NOT re-restore', async ({ page }) => {
    await gotoEditor(page);
    await addSection(page, 'saved-then-gone');
    // Saving a section that overflows the page raises a print-fit <dialog>
    // confirm — accept it so the Save actually goes through.
    await page.click('#save');
    await submitDialogIfPresent(page);
    await expect(page.locator('#stat')).toContainText('draft saved', { timeout: 15000 });

    await page.waitForTimeout(1200);   // outlast any pending autosave debounce
    await page.reload();
    await waitForFirstRender(page);

    // The section is on the draft branch (fetched normally), but the "restored
    // unsaved edits" notice must NOT appear — the cache was cleared on Save.
    await expect(page.locator('#stat')).not.toContainText('restored unsaved edits');
  });

  test('the cache does not fire in local mode (files on disk are the truth)', async ({ page, context }) => {
    // Undo the hosted fixture's /__ping block for this one test so the app runs
    // in local mode, then confirm nothing was written to the draft cache.
    await context.unroute('**/__ping');
    await gotoEditor(page);
    await addSection(page, 'local-no-cache');
    await page.waitForTimeout(1200);

    const cached = await page.evaluate(async () => {
      try {
        const { get } = await import('https://cdn.jsdelivr.net/npm/idb-keyval@6.3.0/dist/index.js');
        return (await get('draft-cache:budget-primer')) || null;
      } catch (e) { return 'import-failed'; }
    });
    expect(cached).toBeNull();
  });
});
