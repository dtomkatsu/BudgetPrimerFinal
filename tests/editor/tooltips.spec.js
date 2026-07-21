// Hover tooltips (docsync/editor/edit.html wireTooltips/mkBtn-family aria-label
// conversion). Icon-only buttons (lock, duplicate, delete…) used to rely on the
// native `title` attribute, which never appears on a DISABLED button — the
// common state for Duplicate/Lock/Delete before anything is selected — and is
// slow and OS-styled the rest of the time. Now every icon-only action button
// carries `aria-label` instead, and a small delegated #tt chip shows a short
// label (the part of aria-label before " — ") on hover, in both the chrome
// (this document) and the draft iframe (the floating mini toolbar).
const { test, expect, gotoEditor } = require('./fixtures/editor-test');

test.describe('hover tooltips', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('a disabled chrome button still shows its tooltip', async ({ page }) => {
    // Nothing selected yet, so ar-dup/ar-lock are disabled — exactly the case
    // native title never covered.
    await expect(page.locator('#ar-dup')).toBeDisabled();
    await page.hover('#ar-dup');
    const tip = page.locator('#tt');
    await expect(tip).toBeVisible({ timeout: 2000 });
    await expect(tip).toHaveText('Duplicate (⌘D)');
  });

  test('the short label drops the " — " explanation', async ({ page }) => {
    await page.hover('#ar-lock');
    const tip = page.locator('#tt');
    await expect(tip).toBeVisible({ timeout: 2000 });
    await expect(tip).toHaveText('Lock');
    expect(await tip.textContent()).not.toContain('—');
  });

  test('moving to a different button swaps the label without a stale one lingering', async ({ page }) => {
    await page.hover('#ar-dup');
    await expect(page.locator('#tt')).toHaveText('Duplicate (⌘D)', { timeout: 2000 });
    await page.hover('#ar-del');
    await expect(page.locator('#tt')).toHaveText(/^Delete/, { timeout: 2000 });
  });

  test('moving off a button hides the tooltip', async ({ page }) => {
    await page.hover('#ar-dup');
    await expect(page.locator('#tt')).toBeVisible({ timeout: 2000 });
    await page.hover('#stat');
    await expect(page.locator('#tt')).toBeHidden();
  });

  test('mousedown dismisses it immediately', async ({ page }) => {
    // Enabled, not disabled: a disabled control suppresses mousedown itself
    // (browser default, not this feature's concern), so there is nothing to
    // dismiss-on-click for — the case worth guarding is a real action button.
    await page.evaluate(() => setSel($('out').contentDocument, ['cover.logo']));
    await expect(page.locator('#ar-dup')).toBeEnabled();
    await page.hover('#ar-dup');
    await expect(page.locator('#tt')).toBeVisible({ timeout: 2000 });
    await page.mouse.down();
    await expect(page.locator('#tt')).toBeHidden();
    await page.mouse.up();
  });

  test('the floating mini toolbar (inside the draft) shows tooltips too', async ({ page }) => {
    const frame = page.frameLocator('#out');
    await page.evaluate(() => setSel($('out').contentDocument, ['cover.logo']));
    await page.waitForTimeout(200);
    const dup = frame.locator('.ds-mini button[aria-label^="Duplicate"]');
    await expect(dup).toHaveCount(1);
    await dup.hover();
    const tip = frame.locator('#tt');
    await expect(tip).toBeVisible({ timeout: 2000 });
    await expect(tip).toHaveText(/^Duplicate/);
  });

  test('every icon-only chrome button still exposes an accessible name', async ({ page }) => {
    // The rename from title -> aria-label must not have dropped any labels —
    // that would silently make a button invisible to a screen reader.
    const unlabelled = await page.evaluate(() =>
      [...document.querySelectorAll('#bar button, #arrange button')]
        .filter(b => !b.textContent.trim() && !b.getAttribute('aria-label'))
        .map(b => b.id || b.className));
    expect(unlabelled).toEqual([]);
  });
});
