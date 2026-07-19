// Editable cover title (report2027/content.md cover.title + render_report.py):
// the previously-hardcoded <h1 class="cover-title"> is now a data-slot, so the
// flagship "designed" element edits like any heading. Its stacked lines are one
// multi-line slot (newlines -> <br>). Local mode; editor opens on the cover.
const { test, expect, gotoEditor } = require('./fixtures/editor-test');

test.describe('editable cover title', () => {
  test('the cover title is an editable slot and commits an edit', async ({ page }) => {
    await gotoEditor(page);
    const frame = page.frameLocator('#out');

    const title = frame.locator('h1.cover-title[data-slot="cover.title"]');
    await expect(title).toHaveCount(1);
    await expect(title).toContainText('HAWAI');

    // Click opens the multi-line editor seeded with the raw slot lines.
    await title.click();
    const ta = frame.locator('.ds-edit');
    await ta.waitFor({ state: 'visible' });
    await expect(ta).toHaveValue(/HAWAI[\s\S]*BUDGET[\s\S]*PRIMER/);

    // Edit all three lines and commit (blur).
    await ta.fill('HAWAII\nSTATE\nBUDGET');
    await ta.evaluate(el => el.blur());

    // The rendered title reflects the edit, still stacked with <br>.
    const after = frame.locator('h1.cover-title[data-slot="cover.title"]');
    await expect(after).toContainText('STATE');
    const brs = await after.evaluate(el => el.querySelectorAll('br').length);
    expect(brs).toBe(2);   // three lines -> two <br>
  });

  test('the cover year is editable too', async ({ page }) => {
    await gotoEditor(page);
    const frame = page.frameLocator('#out');
    await expect(frame.locator('.cover-year [data-slot="cover.year"]')).toHaveCount(1);
  });
});
