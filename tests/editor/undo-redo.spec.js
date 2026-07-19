// Undo/redo (docsync/editor/edit.html): pushHistory()/undo()/redo() snapshot
// {source, layout} on every structural edit. Uses the section-add flow as a
// convenient, already-verified mutation to undo/redo against.
const { test, expect, gotoEditor } = require('./fixtures/editor-test');

function queuePrompts(page, answers) {
  if (page.__promptListener) page.off('dialog', page.__promptListener);
  const queue = [...answers];
  page.__promptListener = async dialog => {
    const next = queue.shift();
    if (next === undefined) throw new Error(`unexpected dialog: ${dialog.message()}`);
    await dialog.accept(next);
  };
  page.on('dialog', page.__promptListener);
}

test.describe('undo / redo', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('start disabled, then undo reverts an added section and redo brings it back', async ({ page }) => {
    await expect(page.locator('#undo')).toBeDisabled();
    await expect(page.locator('#redo')).toBeDisabled();

    queuePrompts(page, ['1', 'undo-me']);
    await page.click('#add');
    const frame = page.frameLocator('#out');
    await frame.locator('.ds-edit').waitFor({ state: 'visible' });
    await page.keyboard.press('Escape');

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
