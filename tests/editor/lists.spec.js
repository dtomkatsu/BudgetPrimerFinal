// Bulleted + numbered lists (docsync/editor/edit.html + content.py block_html).
// The prose-editing toolbar gets "• List" / "1. List" buttons that toggle the
// markdown line prefixes; the renderer turns them into <ul>/<ol>. Verified
// end-to-end on a +Section overflow block (which renders via block_html).
const { test, expect, gotoEditor, fillDialog, submitDialog } = require('./fixtures/editor-test');

async function addSectionAndEdit(page, slug, text) {
  await page.click('#add');
  await fillDialog(page, { page: 'basics', slug });
  await submitDialog(page);
  const frame = page.frameLocator('#out');
  const ta = frame.locator('.ds-edit');
  await ta.waitFor({ state: 'visible' });
  // Replace the placeholder body with our own lines, selecting all of it.
  await ta.fill(text);
  await ta.selectText();
  return ta;
}

test.describe('lists', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('the numbered-list button renders an <ol>', async ({ page }) => {
    const frame = page.frameLocator('#out');
    const ta = await addSectionAndEdit(page, 'num-list', 'first\nsecond\nthird');
    await frame.locator('.ds-tools button', { hasText: '1. List' }).click();
    // Prefixes now in the textarea…
    await expect(ta).toHaveValue('1. first\n2. second\n3. third');
    // …and after COMMITTING the edit (blur, not Escape which discards), the
    // renderer produces a real <ol>.
    await ta.evaluate(el => el.blur());
    const section = frame.locator('[data-slot="extra.basics.num-list"]');
    await expect(section.locator('ol.extra-numbers')).toHaveCount(1);
    await expect(section.locator('ol.extra-numbers li')).toHaveCount(3);
  });

  test('the bullet-list button renders a <ul>, and toggles back off', async ({ page }) => {
    const frame = page.frameLocator('#out');
    const ta = await addSectionAndEdit(page, 'bul-list', 'apple\nbanana');
    const bulletBtn = frame.locator('.ds-tools button', { hasText: '• List' });

    await bulletBtn.click();
    await expect(ta).toHaveValue('- apple\n- banana');

    // Toggle off — every line already has the prefix, so it strips them.
    await ta.selectText();
    await bulletBtn.click();
    await expect(ta).toHaveValue('apple\nbanana');
  });
});
