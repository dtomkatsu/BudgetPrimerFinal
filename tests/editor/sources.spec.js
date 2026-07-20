// Sources panel (docsync/editor/edit.html): add a citation via the "Cite"
// toolbar button while editing a paragraph, then edit/rename/reorder/delete
// it from the Sources panel (openSources/renderSources/addSource/
// updateSource/renameSource/moveSource/deleteSource). Local-mode, no GitHub.
const { test, expect, gotoEditor, fillDialog, submitDialog } = require('./fixtures/editor-test');

// toc.author (the "Author: …" byline). Like every movable text in the
// report it now sits inside a [data-el] object, so a single click selects
// it for dragging and a DOUBLE click opens the words — the same split
// headings and callouts use (see wire()'s [data-slot] wiring).
const EDITABLE_SLOT = 'toc.author';

/** Click into an editable prose block, open the Cite panel, and add a
 *  brand-new source through the real "+ new source…" flow — now one <dialog>
 *  form (id + citation text + URL), the only UI path that creates a source. */
async function addSourceViaUi(page, id, text, url) {
  const frame = page.frameLocator('#out');
  const block = frame.locator(`[data-slot="${EDITABLE_SLOT}"]`);
  await block.dblclick({ force: true });
  await frame.locator('.ds-tools button', { hasText: 'Cite' }).click();
  await frame.locator('.ds-cite select').selectOption('__new');
  // The dsForm dialog opens in the parent doc; fill all three fields at once.
  await fillDialog(page, { id, text, url });
  await submitDialog(page);
  await frame.locator('.ds-cite').waitFor({ state: 'detached' });
  // Blur (not Escape) to COMMIT the edit — Escape's finish(false) would
  // discard the [^id] reference spliceAt() just inserted, leaving the source
  // added but never actually cited.
  await frame.locator('.ds-edit').evaluate(el => el.blur());
  // finish()'s render() reassigns the iframe's srcdoc wholesale: the OLD
  // document (and .ds-edit with it) is gone the instant that starts, well
  // before the NEW document has loaded and re-wired its click handlers.
  // Waiting only for .ds-edit to detach is a false-positive "done" signal —
  // wait for the new document to actually paint before the caller acts on it
  // again (e.g. a second addSourceViaUi() clicking the same slot).
  await frame.locator('.ds-edit').waitFor({ state: 'detached' });
  await frame.locator('.page').first().waitFor({ state: 'visible' });
  // As in gotoEditor(): local mode's live-reload can still pick up one more
  // version bump shortly after a render, which is a second, invisible-to-
  // Playwright-visibility-checks srcdoc swap. Settle before the caller acts
  // inside #out again.
  await page.waitForTimeout(1500);
}

test.describe('sources panel', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('adding a source via Cite shows it in the Sources panel as cited', async ({ page }) => {
    await addSourceViaUi(page, 'test-src-1', 'A Test Source, 2026.', 'https://example.com/a');

    await page.click('#sources');
    const row = page.locator('#srcpanel .srcrow', { has: page.locator('.srcid', { hasText: '[test-src-1]' }) });
    await expect(row).toBeVisible();
    await expect(row.locator('.srcuse')).toContainText('cited 1');
    await expect(row.locator('.srctext')).toHaveValue('A Test Source, 2026.');
    await expect(row.locator('input').nth(1)).toHaveValue('https://example.com/a');
    // Cited: the panel must refuse to delete it out from under the citation.
    await expect(row.locator('.srcdel')).toBeDisabled();
  });

  test('editing the text/url fields commits via updateSource', async ({ page }) => {
    await addSourceViaUi(page, 'test-src-2', 'Original text.', 'https://example.com/orig');
    await page.click('#sources');
    const row = page.locator('#srcpanel .srcrow', { has: page.locator('.srcid', { hasText: '[test-src-2]' }) });

    await row.locator('.srctext').fill('Updated text.');
    await row.locator('.srctext').blur();
    await expect(page.locator('#undo')).toBeEnabled();

    // openSources() always tears down and rebuilds the panel from scratch —
    // re-clicking #sources confirms the edit round-tripped through `source`
    // (the underlying content.md text), not just the input's DOM value.
    await page.click('#sources');
    const rowAfter = page.locator('#srcpanel .srcrow', { has: page.locator('.srcid', { hasText: '[test-src-2]' }) });
    await expect(rowAfter.locator('.srctext')).toHaveValue('Updated text.');
  });

  test('renaming a source id updates it everywhere', async ({ page }) => {
    await addSourceViaUi(page, 'old-id', 'Some source.', 'https://example.com/x');
    await page.click('#sources');
    const row = page.locator('#srcpanel .srcrow', { has: page.locator('.srcid', { hasText: '[old-id]' }) });

    await row.locator('.srcren', { hasText: 'rename' }).click();
    await fillDialog(page, { id: 'new-id' });
    await submitDialog(page);

    const renamed = page.locator('#srcpanel .srcrow', { has: page.locator('.srcid', { hasText: '[new-id]' }) });
    await expect(renamed).toBeVisible();
    await expect(page.locator('#srcpanel .srcrow', { has: page.locator('.srcid', { hasText: '[old-id]' }) })).toHaveCount(0);
    // Still cited — the rename must have followed through to the [^old-id] ref in prose.
    await expect(renamed.locator('.srcuse')).toContainText('cited 1');
  });

  test('reorders two sources with ↑/↓', async ({ page }) => {
    await addSourceViaUi(page, 'src-a', 'Source A.', 'https://example.com/a');
    await addSourceViaUi(page, 'src-b', 'Source B.', 'https://example.com/b');
    await page.click('#sources');

    const ids = () => page.locator('#srcpanel .srcid').allTextContents();
    const before = (await ids()).map(t => t.split(']')[0] + ']');
    const bIdx = before.findIndex(t => t === '[src-b]');
    expect(bIdx).toBeGreaterThan(0);

    const rowB = page.locator('#srcpanel .srcrow', { has: page.locator('.srcid', { hasText: '[src-b]' }) });
    await rowB.locator('.srcren', { hasText: '↑' }).click();

    const after = (await ids()).map(t => t.split(']')[0] + ']');
    expect(after.indexOf('[src-b]')).toBeLessThan(bIdx);
  });

  test('deleteSource() removes an uncited source from the underlying text', async ({ page }) => {
    // Every UI-created source is cited on creation (Cite always inserts the
    // [^id] ref) — deleteSource() itself has no such restriction, only the
    // panel's button does (disabled above). Exercise the function directly,
    // the same way image-compression.spec.js reaches compressImageFile():
    // it's a top-level function declaration in a classic script, so `window.
    // deleteSource` etc. are real page functions, not test-only scaffolding.
    // `source` itself is a page-level `let`, so it's *not* on `window` — but
    // it IS reachable as a bare identifier, the same as typing it into the
    // DevTools console for this page.
    await page.evaluate(() => {
      window.pushHistory();
      window.addSource('uncited-src', 'Never cited.', 'https://example.com/z');
      window.markDirty();
    });
    let hasSource = await page.evaluate(() => source.includes('[uncited-src]:'));
    expect(hasSource).toBe(true);

    await page.evaluate(() => {
      window.pushHistory();
      window.deleteSource('uncited-src');
      window.markDirty();
    });
    hasSource = await page.evaluate(() => source.includes('[uncited-src]:'));
    expect(hasSource).toBe(false);
  });
});
