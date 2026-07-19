// Tables (docsync/editor/edit.html + layout.py tables_html): a placed,
// draggable, editable grid. The "Table" button creates one; cells edit in
// place on double-click; right-click a cell for rows & columns. Local mode.
const { test, expect, gotoEditor } = require('./fixtures/editor-test');

async function addTable(page) {
  // Create on a CONTENT page — the cover (page 1) has a full-bleed overlay
  // that would sit over the cells. Scroll a content page into view first so
  // visiblePageId() targets it.
  const frame = page.frameLocator('#out');
  await frame.locator('section.page').nth(3).scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  await page.click('#table');
  const tbl = frame.locator('table.ds-table[data-el]').first();
  await tbl.waitFor({ state: 'attached', timeout: 20000 });
  await tbl.scrollIntoViewIfNeeded();
  await page.waitForTimeout(1000);
  return tbl;
}

test.describe('tables', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('the Table button creates a header table with rows and cells', async ({ page }) => {
    const tbl = await addTable(page);
    await expect(tbl.locator('th')).toHaveCount(2);        // header row
    await expect(tbl.locator('tr')).toHaveCount(3);        // 1 header + 2 body
    // Selected on create, so it's deletable from the toolbar.
    await expect(page.locator('#ar-del')).toBeEnabled();
  });

  test('double-clicking a cell edits it in place', async ({ page }) => {
    const tbl = await addTable(page);
    const frame = page.frameLocator('#out');
    // Edit a body cell (row 1, col 0).
    const cell = tbl.locator('td[data-cell="1,0"]');
    await cell.dblclick();
    const editor = frame.locator('.ds-cell-edit');
    await editor.waitFor({ state: 'visible' });
    await editor.fill('Human Services');
    await editor.evaluate(el => el.blur());

    // The cell text (and the underlying model) now hold the new value.
    await expect(page.evaluate(() => layout.tables[0].rows[1][0])).resolves.toBe('Human Services');
    await expect(frame.locator('table.ds-table td', { hasText: 'Human Services' })).toHaveCount(1);
  });

  test('right-click inserts a row via the rows & columns menu', async ({ page }) => {
    const tbl = await addTable(page);
    const frame = page.frameLocator('#out');
    const before = await page.evaluate(() => layout.tables[0].rows.length);

    await tbl.locator('td[data-cell="1,0"]').click({ button: 'right' });
    const menu = frame.locator('.ds-menu');
    await expect(menu).toBeVisible();
    await menu.locator('button', { hasText: 'Insert row below' }).click();

    await expect(page.evaluate(() => layout.tables[0].rows.length)).resolves.toBe(before + 1);
  });

  test('right-click inserts a column across every row', async ({ page }) => {
    const tbl = await addTable(page);
    const frame = page.frameLocator('#out');

    await tbl.locator('th[data-cell="0,0"]').click({ button: 'right' });
    await frame.locator('.ds-menu button', { hasText: 'Insert column right' }).click();

    const widths = await page.evaluate(() => layout.tables[0].rows.map(r => r.length));
    expect(widths.every(w => w === 3)).toBe(true);   // every row gained a cell
  });
});
