// Structural section editing (docsync/editor/edit.html): add/reorder/move/
// delete an [[extra.<page>.<slug>]] overflow section. The +Section and delete
// flows now go through native <dialog> modals (dsForm/dsConfirm), not
// prompt()/confirm(). Local-mode: no GitHub, only in-memory `source` and the
// Pyodide-rendered iframe.
const { test, expect, gotoEditor, fillDialog, submitDialog } = require('./fixtures/editor-test');

/** Add a section through the +Section dialog: pick a page and name it in one
 *  form, submit, then Escape out of the auto-opened editor so it re-renders
 *  read-only with its .extra-section / .ds-xtools controls. */
async function addSection(page, slug, pageValue = 'basics') {
  await page.click('#add');
  await fillDialog(page, { page: pageValue, slug });
  await submitDialog(page);
  await page.frameLocator('#out').locator('.ds-edit').waitFor({ state: 'visible' });
  await page.keyboard.press('Escape');
}

test.describe('section editing', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('adds a new section to a page and it renders', async ({ page }) => {
    await addSection(page, 'auto-test-section');

    const frame = page.frameLocator('#out');
    // toHaveCount, not toBeVisible: a section landing past the print-fit cut
    // is genuinely clipped by its (print-accurate) .page container — that's
    // real behavior, not a broken render, so visibility isn't the right check.
    const section = frame.locator('[data-slot="extra.basics.auto-test-section"]');
    await expect(section).toHaveCount(1);
    await expect(section).toContainText('New section');
    await expect(page.locator('#undo')).toBeEnabled();
    await expect(page.locator('#save')).toBeEnabled();
  });

  test('reorders two sections on the same page with ↑/↓', async ({ page }) => {
    await addSection(page, 'section-a');
    await addSection(page, 'section-b');

    const frame = page.frameLocator('#out');
    const extras = frame.locator('.extra-section[data-extra="1"]');
    await expect(extras).toHaveCount(2);
    await expect(extras.nth(0)).toHaveAttribute('data-slot', 'extra.basics.section-a');
    await expect(extras.nth(1)).toHaveAttribute('data-slot', 'extra.basics.section-b');

    // .ds-xtools only shows on :hover of its .extra-section, and the report
    // page can render below the fold of the (CSS-scaled) preview iframe — both
    // make a real mouse hover/click unreliable here. dispatchEvent fires the
    // listener directly on the node, skipping hit-testing and CSS visibility.
    await extras.nth(1).locator('.ds-xtools button', { hasText: '↑' }).dispatchEvent('click');
    const extrasAfter = frame.locator('.extra-section[data-extra="1"]');
    await expect(extrasAfter.nth(0)).toHaveAttribute('data-slot', 'extra.basics.section-b');
    await expect(extrasAfter.nth(1)).toHaveAttribute('data-slot', 'extra.basics.section-a');
  });

  test('deletes a section via the ✕ control after confirming', async ({ page }) => {
    await addSection(page, 'to-delete');

    const frame = page.frameLocator('#out');
    const key = 'extra.basics.to-delete';
    const section = frame.locator(`[data-slot="${key}"]`);
    await expect(section).toHaveCount(1);

    // The ✕ opens a dsConfirm dialog (in the parent doc); accept it.
    await section.locator('.ds-xtools button.del').dispatchEvent('click');
    await submitDialog(page);

    await expect(frame.locator(`[data-slot="${key}"]`)).toHaveCount(0);
  });
});
