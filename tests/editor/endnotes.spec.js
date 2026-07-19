// Right-click endnote creation (docsync/editor/edit.html): right-clicking in a
// prose textarea opens a small menu with "Add endnote here…" (creates a source
// and drops a [^id] ref at the caret) and a list of existing sources to cite.
// Local mode; the menu is drawn inside the iframe document.
const { test, expect, gotoEditor, fillDialog, submitDialog } = require('./fixtures/editor-test');

// A multi-line prose block (a +Section overflow slot renders as a <textarea>);
// inline single-line fields like a heading take no footnotes, so they keep the
// native menu. Each test adds its own section and edits it.
let counter = 0;
async function openProse(page) {
  const frame = page.frameLocator('#out');
  await page.click('#add');
  await fillDialog(page, { page: 'basics', slug: 'en-sec-' + (++counter) });
  await submitDialog(page);
  const ta = frame.locator('.ds-edit');
  await ta.waitFor({ state: 'visible' });
  return ta;
}

test.describe('right-click endnotes', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('right-click offers "Add endnote here" and inserts a [^id] ref', async ({ page }) => {
    const frame = page.frameLocator('#out');
    const ta = await openProse(page);
    await ta.click({ button: 'right' });

    const menu = frame.locator('.ds-menu');
    await expect(menu).toBeVisible();
    await menu.locator('button', { hasText: 'Add endnote here' }).click();

    // The shared new-source dialog opens in the parent doc.
    await fillDialog(page, {
      id: 'rc-src', text: 'A right-click source, 2026.', url: 'https://example.com/rc',
    });
    await submitDialog(page);

    // The [^rc-src] ref landed in the prose text.
    await expect(ta).toContainText('[^rc-src]');
  });

  test('the menu lists existing sources to cite without retyping', async ({ page }) => {
    const frame = page.frameLocator('#out');
    // First create a source via right-click.
    let ta = await openProse(page);
    await ta.click({ button: 'right' });
    await frame.locator('.ds-menu button', { hasText: 'Add endnote here' }).click();
    await fillDialog(page, { id: 'existing1', text: 'First source.', url: 'https://example.com/1' });
    await submitDialog(page);
    await expect(ta).toContainText('[^existing1]');

    // Right-click again — the existing source is now offered directly.
    await ta.click({ button: 'right' });
    const cite = frame.locator('.ds-menu button', { hasText: '[existing1]' });
    await expect(cite).toBeVisible();
    await cite.click();
    // A second reference to the same source now sits in the text, as a
    // second footnote chip.
    await expect(ta.locator('.ds-fnchip[data-fn-id="existing1"]')).toHaveCount(2);
  });
});
