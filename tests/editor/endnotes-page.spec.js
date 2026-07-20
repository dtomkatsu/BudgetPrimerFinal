// Per-entry endnotes (report2027/tools/render_report.py endnote_link +
// docsync/editor/edit.html editEndnote): each <li> on the Endnotes page
// (page 12) carries its own data-el="endnote.<id>", so it drags/resizes
// independently like any other designed element, and double-clicking it
// opens a small text/URL form that writes through updateSource() — the same
// function the floating Sources panel's own fields call. Since the page's
// <li> list is rebuilt fresh from content.md's [[sources]] block on every
// render, editing either surface can never leave the other stale. Local mode.
const { test, expect, gotoEditor, fillDialog, submitDialog } = require('./fixtures/editor-test');

const EDITABLE_SLOT = 'toc.author';   // double-click to edit, see sources.spec.js

async function addSourceViaUi(page, id, text, url) {
  const frame = page.frameLocator('#out');
  const block = frame.locator(`[data-slot="${EDITABLE_SLOT}"]`);
  await block.dblclick({ force: true });
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

  test('dragging an endnote past another reorders the list, and everything renumbers', async ({ page }) => {
    const frame = page.frameLocator('#out');
    await addSourceViaUi(page, 'en-drag-a', 'Source A.', 'https://example.com/a');
    await addSourceViaUi(page, 'en-drag-b', 'Source B.', 'https://example.com/b');

    // Both new sources are cited from the same slot, so they land at the end
    // of the list in citation order. Drag the LAST one up onto the first
    // entry and it should become #1.
    const ids = await page.evaluate(() =>
      [...document.querySelector('#out').contentDocument
        .querySelectorAll('[data-el^="endnote."]')].map(li => li.dataset.el.slice(8)));
    expect(ids.length).toBeGreaterThan(2);
    const moving = ids[ids.length - 1];
    expect(ids[0]).not.toBe(moving);

    // Grab the entry by its own URL link — the surface that makes up most of
    // an endnote, and that a drag has to be able to start from.
    const dragged = await page.evaluate((movingId) => {
      const d = document.querySelector('#out').contentDocument;
      const src = d.querySelector(`[data-el="endnote.${movingId}"]`);
      const dst = d.querySelector('[data-el^="endnote."]');
      const a = src.querySelector('a') || src;
      const ar = a.getBoundingClientRect(), t = dst.getBoundingClientRect();
      const sx = ar.left + 10, sy = ar.top + ar.height / 2;
      const tx = t.left + 10, ty = t.top + 1;
      const ev = (type, cx, cy, tgt) => tgt.dispatchEvent(new MouseEvent(type,
        { bubbles: true, cancelable: true, clientX: cx, clientY: cy, button: 0, view: d.defaultView }));
      ev('mousedown', sx, sy, a);
      for (let i = 1; i <= 8; i++) ev('mousemove', sx + (tx - sx) * i / 8, sy + (ty - sy) * i / 8, d);
      ev('mouseup', tx, ty, d);
      return true;
    }, moving);
    expect(dragged).toBe(true);
    await page.waitForTimeout(1200);

    // The order override is recorded, with the dragged entry now leading...
    const order = await page.evaluate(() => layout.endnotes);
    expect(order).toBeTruthy();
    expect(order[0]).toBe(moving);
    // ...the rendered list agrees...
    const after = await page.evaluate(() =>
      [...document.querySelector('#out').contentDocument
        .querySelectorAll('[data-el^="endnote."]')].map(li => li.dataset.el.slice(8)));
    expect(after[0]).toBe(moving);
    // ...and it never parks: an endnote stays in the list flow, so no
    // absolute position is written for it.
    const pos = await page.evaluate(m => (layout.positions || {})['endnote.' + m], moving);
    expect(pos).toBeUndefined();
  });

  test('an endnote that never moves leaves no order override', async ({ page }) => {
    const order = await page.evaluate(() => layout.endnotes);
    expect(order === undefined || order.length === 0).toBe(true);
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
