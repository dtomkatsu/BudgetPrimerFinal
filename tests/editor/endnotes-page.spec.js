// Per-entry endnotes (report2027/tools/render_report.py endnote_link +
// docsync/editor/edit.html editEndnote): each <li> on the Endnotes page
// (page 12) carries its own data-el="endnote.<id>", so it drags/resizes
// independently like any other designed element, and double-clicking it
// opens a small text/URL form that writes through updateSource() — the same
// function the floating Sources panel's own fields call. Since the page's
// <li> list is rebuilt fresh from content.md's [[sources]] block on every
// render, editing either surface can never leave the other stale. Local mode.
const { test, expect, gotoEditor, fillDialog, submitDialog } = require('./fixtures/editor-test');

const EDITABLE_SLOT = 'toc.author';   // single-click editable, see sources.spec.js

async function addSourceViaUi(page, id, text, url) {
  const frame = page.frameLocator('#out');
  const block = frame.locator(`[data-slot="${EDITABLE_SLOT}"]`);
  await block.click();
  await frame.locator('.ds-tools button', { hasText: 'Cite' }).click();
  await frame.locator('.ds-cite select').selectOption('__new');
  await fillDialog(page, { id, text, url });
  await submitDialog(page);
  await frame.locator('.ds-cite').waitFor({ state: 'detached' });
  await frame.locator('.ds-edit').evaluate(el => el.blur());
  await frame.locator('.ds-edit').waitFor({ state: 'detached' });
  await frame.locator('.page').first().waitFor({ state: 'visible' });
  await page.waitForTimeout(1500);
}

test.describe('endnotes page', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('each endnote entry carries its own data-el and drags independently, numbering unchanged', async ({ page }) => {
    const frame = page.frameLocator('#out');
    await addSourceViaUi(page, 'en-drag-a', 'Source A.', 'https://example.com/a');
    await addSourceViaUi(page, 'en-drag-b', 'Source B.', 'https://example.com/b');

    const li = frame.locator('[data-el="endnote.en-drag-a"]');
    await li.scrollIntoViewIfNeeded();
    await expect(li).toHaveCount(1);
    const otherLi = frame.locator('[data-el="endnote.en-drag-b"]');
    const beforeNum = await otherLi.evaluate(el => el.id);   // "en{n}"

    await li.click();
    const box = await li.boundingBox();
    // A drag's mousedown is deliberately ignored when it lands on the
    // entry's own <a> link (dragify() excludes it so the link stays
    // clickable) — pick a point clearly inside the citation text, just
    // before where the link starts, rather than guessing a fixed offset
    // that could land on either depending on wrap.
    const aBox = await li.locator('a').boundingBox();
    const dragX = aBox ? Math.max(box.x + 2, aBox.x - 15) : box.x + box.width / 2;
    const dragY = aBox ? aBox.y + aBox.height / 2 : box.y + box.height / 2;
    await page.mouse.move(dragX, dragY);
    await page.mouse.down();
    await page.mouse.move(dragX + 50, dragY + 30, { steps: 8 });
    await page.mouse.up();
    await page.waitForTimeout(400);

    const pos = await page.evaluate(() => layout.positions['endnote.en-drag-a']);
    expect(pos).toBeTruthy();
    expect(pos.x).toBeGreaterThan(0);
    // Dragging one entry never renumbers the others — numbering is DOM-order
    // (citation order), not layout position.
    const afterNum = await otherLi.evaluate(el => el.id);
    expect(afterNum).toBe(beforeNum);
  });

  test('editing an endnote in place updates the underlying source (page -> content.md)', async ({ page }) => {
    const frame = page.frameLocator('#out');
    await addSourceViaUi(page, 'en-edit-a', 'Original text.', 'https://example.com/orig');

    const li = frame.locator('[data-el="endnote.en-edit-a"]');
    await li.scrollIntoViewIfNeeded();
    await li.dblclick({ force: true });

    const form = frame.locator('.ds-endnote-edit');
    await form.waitFor({ state: 'visible' });
    const txt = form.locator('.ds-en-text');
    await txt.fill('Updated text.');
    await txt.evaluate(el => el.blur());
    await page.waitForTimeout(600);

    // The underlying [[sources]] line reflects the edit — the single source
    // of truth the page is regenerated from, not a second copy.
    const sourcesText = await page.evaluate(() => readSlot('sources'));
    expect(sourcesText).toContain('Updated text.');
    expect(sourcesText).not.toContain('Original text.');

    // And the re-rendered page shows it too.
    await expect(frame.locator('[data-el="endnote.en-edit-a"]')).toContainText('Updated text.');
  });

  test('editing the same source via the Sources panel is reflected on the endnotes page (sync both ways)', async ({ page }) => {
    const frame = page.frameLocator('#out');
    await addSourceViaUi(page, 'en-edit-b', 'Panel original.', 'https://example.com/panel');

    await page.click('#sources');
    const row = page.locator('#srcpanel .srcrow', { has: page.locator('.srcid', { hasText: '[en-edit-b]' }) });
    await row.locator('.srctext').fill('Panel updated.');
    await row.locator('.srctext').evaluate(el => el.blur());
    await page.waitForTimeout(600);

    const li = frame.locator('[data-el="endnote.en-edit-b"]');
    await li.scrollIntoViewIfNeeded();
    await expect(li).toContainText('Panel updated.');
  });
});
