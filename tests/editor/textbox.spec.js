// Text-box all-side resize (docsync/editor/edit.html + layout.py text_boxes).
// A text box (the "Text" button) is now resizable on every edge and corner,
// like a shape. Height is a MIN-height in the renderer, so a coloured panel can
// be sized on all sides without ever clipping its words. Local mode.
const { test, expect, gotoEditor } = require('./fixtures/editor-test');

async function addTextBox(page) {
  // The Text button now opens a preset popover (Heading/Subheading/Body).
  await page.click('#text');
  await page.click('#textpop .txtpreset[data-k="body"]');
  const box = page.frameLocator('#out').locator('.ds-textbox').first();
  await box.waitFor({ state: 'attached', timeout: 20000 });
  await page.waitForTimeout(1000);
  return box;
}

test.describe('text boxes', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('a selected text box shows all 8 resize handles (incl. vertical + corners)', async ({ page }) => {
    await addTextBox(page);
    const frame = page.frameLocator('#out');
    // Handles live in the page overlay; each direction has its own class.
    for (const dir of ['n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw']) {
      await expect(frame.locator(`.ds-handles .ds-h-${dir}`)).toHaveCount(1);
    }
  });

  test('dragging the south handle sets a min-height on the box', async ({ page }) => {
    const box = await addTextBox(page);
    const frame = page.frameLocator('#out');
    const south = frame.locator('.ds-handles .ds-h-s');
    const from = await south.boundingBox();
    // Drag the bottom edge down ~1 inch (DPI≈96 * fit-scale; a big move is fine).
    await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
    await page.mouse.down();
    await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2 + 160, { steps: 8 });
    await page.mouse.up();
    await page.waitForTimeout(500);

    // The box object now carries an h, and the rendered element has min-height.
    const h = await page.evaluate(() => (layout.boxes[0] || {}).h || null);
    expect(h).toBeGreaterThan(0.4);
    await expect(box).toHaveCSS('min-height', /.+/);
  });
});
