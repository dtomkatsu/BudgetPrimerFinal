// Structural section editing (docsync/editor/edit.html): add/reorder/move/
// delete an [[extra.<page>.<slug>]] overflow section — the feature added in
// the 2026-07-17 session (addExtra/removeExtra/moveExtra/moveSectionToPage).
// Local-mode: no GitHub involved, only in-memory `source` (content.md text)
// and the Pyodide-rendered iframe.
const { test, expect, gotoEditor } = require('./fixtures/editor-test');

/** #add's click handler fires two sequential window.prompt()s: a page number,
 *  then a slug. Answer them in order as they appear. Replaces any prior
 *  'dialog' listener so calling this more than once per test never leaves a
 *  stale, exhausted queue still attached (Playwright dispatches to every
 *  registered listener, not just the newest). */
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

test.describe('section editing', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('adds a new section to a page and it renders', async ({ page }) => {
    queuePrompts(page, ['1', 'auto-test-section']);
    await page.click('#add');

    const frame = page.frameLocator('#out');
    // Adding auto-opens the new section for editing (pendingEdit) — cancel
    // out of that with Escape so it re-renders read-only and picks up the
    // .extra-section / .ds-xtools controls.
    await frame.locator('.ds-edit').waitFor({ state: 'visible' });
    await page.keyboard.press('Escape');

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
    queuePrompts(page, ['1', 'section-a']);
    await page.click('#add');
    await page.frameLocator('#out').locator('.ds-edit').waitFor({ state: 'visible' });
    await page.keyboard.press('Escape');

    queuePrompts(page, ['1', 'section-b']);
    await page.click('#add');
    await page.frameLocator('#out').locator('.ds-edit').waitFor({ state: 'visible' });
    await page.keyboard.press('Escape');

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
    queuePrompts(page, ['1', 'to-delete']);
    await page.click('#add');
    const frame = page.frameLocator('#out');
    await frame.locator('.ds-edit').waitFor({ state: 'visible' });
    await page.keyboard.press('Escape');

    const key = 'extra.basics.to-delete';
    const section = frame.locator(`[data-slot="${key}"]`);
    await expect(section).toHaveCount(1);

    page.off('dialog', page.__promptListener);   // done answering add-section prompts
    page.once('dialog', dialog => dialog.accept());
    await section.locator('.ds-xtools button.del').dispatchEvent('click');

    await expect(frame.locator(`[data-slot="${key}"]`)).toHaveCount(0);
  });
});
