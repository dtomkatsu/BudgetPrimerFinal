// Movable/resizable designed headings (report2027/tools/render_report.py +
// docsync/layout.py Layout.attr/spacer). Section headings (e.g. "BUDGET
// BASICS") now carry the same data-el position-override hook already used for
// logos and images: a single click selects the heading as a draggable/
// resizable object (like any other element), while double-clicking its actual
// text still opens the inline text editor — the same split already proven for
// prose paragraphs and callout titles. Local mode.
const { test, expect, gotoEditor } = require('./fixtures/editor-test');

test.describe('movable headings', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('a single click selects the heading as a movable object, not text-edit', async ({ page }) => {
    const frame = page.frameLocator('#out');
    await frame.locator('section.page').nth(2).scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);

    const h1 = frame.locator('[data-el="basics.h1"]');
    await expect(h1).toHaveCount(1);
    await h1.click();

    await expect(frame.locator('.ds-edit')).toHaveCount(0);   // no text editor opened
    await expect(page.locator('#arrange')).toBeVisible();
    await expect(page.locator('#ar-count')).toHaveText('basics.h1');
    // Width-only handles (a heading reflows on width, like any prose slot) —
    // no corners, so it keeps the dangling rotate handle.
    await expect(frame.locator('.ds-handles .ds-h-e')).toHaveCount(1);
    await expect(frame.locator('.ds-handles .ds-h-w')).toHaveCount(1);
    await expect(frame.locator('.ds-handles .ds-rot')).toHaveCount(1);
  });

  test('dragging the heading records a position, and the flow below it stays put', async ({ page }) => {
    const frame = page.frameLocator('#out');
    await frame.locator('section.page').nth(2).scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);

    const h1 = frame.locator('[data-el="basics.h1"]');
    await h1.click();
    const box = await h1.boundingBox();
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width / 2 + 60, box.y + box.height / 2 + 40, { steps: 8 });
    await page.mouse.up();
    await page.waitForTimeout(400);

    const pos = await page.evaluate(() => layout.positions['basics.h1']);
    expect(pos).toBeTruthy();
    expect(pos.x).toBeGreaterThan(0);
    // A spacer holds the vacated flow slot so the prose that followed the
    // heading doesn't jump up into the gap. (Other spacers may already exist
    // on the page for unrelated moved elements — just confirm one shows up.)
    expect(pos.reserve).toBeGreaterThan(0);
    expect(await frame.locator('.ds-spacer').count()).toBeGreaterThanOrEqual(1);
  });

  test('a resize handle sets a width override', async ({ page }) => {
    const frame = page.frameLocator('#out');
    await frame.locator('section.page').nth(2).scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);

    const h1 = frame.locator('[data-el="basics.h1"]');
    await h1.click();
    const handle = frame.locator('.ds-handles .ds-h-e');
    const hb = await handle.boundingBox();
    await page.mouse.move(hb.x + hb.width / 2, hb.y + hb.height / 2);
    await page.mouse.down();
    await page.mouse.move(hb.x - 80, hb.y + hb.height / 2, { steps: 8 });
    await page.mouse.up();
    await page.waitForTimeout(400);

    const pos = await page.evaluate(() => layout.positions['basics.h1']);
    expect(pos.w).toBeGreaterThan(0);
  });

  test('double-clicking the heading text still opens the inline text editor', async ({ page }) => {
    const frame = page.frameLocator('#out');
    await frame.locator('section.page').nth(2).scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);

    const text = frame.locator('[data-slot="basics.h1"]');
    await text.dblclick({ force: true });
    const ta = frame.locator('.ds-edit');
    await ta.waitFor({ state: 'visible' });
    await expect(ta).toHaveText(/BUDGET BASICS/i);
  });

  test('an unmoved heading publishes with no position scaffolding (published bytes unchanged)', async ({ page }) => {
    // Sanity: moving is opt-in — a heading nobody touched must render exactly
    // as it always did (verified at the Python level in the render script;
    // here we just confirm the editor never writes a position without a drag).
    const pos = await page.evaluate(() => (layout.positions || {})['basics.h1']);
    expect(pos).toBeUndefined();
  });

  // Standalone lines of text — the byline, the copyright, a figure caption —
  // are placed things too, not just headings. They were the last text in the
  // report a click could edit but not move.
  for (const id of ['toc.author', 'toc.copyright', 'process.fig1.caption']) {
    test(`${id} is a movable object, not just editable text`, async ({ page }) => {
      const frame = page.frameLocator('#out');
      const el = frame.locator(`[data-el="${id}"]`);
      await expect(el).toHaveCount(1);
      await el.scrollIntoViewIfNeeded();
      await el.click();
      await expect(frame.locator('.ds-edit')).toHaveCount(0);   // selects, not text-edit
      await expect(page.locator('#ar-count')).toHaveText(id);

      const box = await el.boundingBox();
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.down();
      await page.mouse.move(box.x + box.width / 2 + 40, box.y + box.height / 2 + 30, { steps: 8 });
      await page.mouse.up();
      await page.waitForTimeout(400);

      // y, not x: a full-width line (the copyright) has no horizontal room —
      // placer clamps it back to 0 — so vertical is the axis that always
      // proves the drag landed.
      const pos = await page.evaluate(k => layout.positions[k], id);
      expect(pos).toBeTruthy();
      expect(pos.y).toBeGreaterThan(0);
    });
  }
});
