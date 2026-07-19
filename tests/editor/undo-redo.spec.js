// Undo/redo (docsync/editor/edit.html): pushHistory()/undo()/redo() snapshot
// {source, layout} on every structural edit. Uses the section-add flow (now a
// native <dialog> form) as a convenient, already-verified mutation.
const { test, expect, gotoEditor, fillDialog, submitDialog } = require('./fixtures/editor-test');

async function addSection(page, slug) {
  await page.click('#add');
  await fillDialog(page, { page: 'basics', slug });
  await submitDialog(page);
  await page.frameLocator('#out').locator('.ds-edit').waitFor({ state: 'visible' });
  await page.keyboard.press('Escape');
}

test.describe('undo / redo', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('start disabled, then undo reverts an added section and redo brings it back', async ({ page }) => {
    await expect(page.locator('#undo')).toBeDisabled();
    await expect(page.locator('#redo')).toBeDisabled();

    await addSection(page, 'undo-me');

    const frame = page.frameLocator('#out');
    const key = 'extra.basics.undo-me';
    await expect(frame.locator(`[data-slot="${key}"]`)).toHaveCount(1);
    await expect(page.locator('#undo')).toBeEnabled();
    await expect(page.locator('#redo')).toBeDisabled();

    await page.click('#undo');
    await expect(frame.locator(`[data-slot="${key}"]`)).toHaveCount(0);
    await expect(page.locator('#redo')).toBeEnabled();

    await page.click('#redo');
    await expect(frame.locator(`[data-slot="${key}"]`)).toHaveCount(1);
    await expect(page.locator('#redo')).toBeDisabled();
  });

  test('undo with nothing to undo is a no-op, not an error', async ({ page }) => {
    // #undo is disabled (no history yet), so Playwright can't click it — use
    // the ⌘Z shortcut, which calls undo() directly and hits its own early
    // "nothing to undo" guard.
    await expect(page.locator('#undo')).toBeDisabled();
    await page.keyboard.press('Control+z');
    await expect(page.locator('#stat')).toContainText('nothing to undo');
  });
});
