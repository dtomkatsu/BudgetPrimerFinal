// Download / export (docsync/editor/edit.html): $('download') opens a
// popover with PDF/PNG choices; doExport() posts to /__export in local mode
// (mocked by the shared fixture — see STANDALONE.md §C, this never spawns the
// real headless-Chrome PDF/PNG renderer in tests) or falls back to the
// browser's own print() for PDF-only when there's no local server.
const { test, expect, gotoEditor } = require('./fixtures/editor-test');

test.describe('download: local mode (server-rendered PDF/PNG via /__export)', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('the popover offers PNG (and bleed marks) only when a local server is present', async ({ page }) => {
    await page.click('#download');
    await expect(page.locator('#downloadpop')).toBeVisible();
    await expect(page.locator('#dl-png')).toBeEnabled();
    await expect(page.locator('#dl-marks')).toBeEnabled();
  });

  test('PDF downloads a file named for the report', async ({ page }) => {
    await page.click('#download');
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('#dl-pdf'),
    ]);
    expect(download.suggestedFilename()).toBe('Budget-Primer-FY2026-27.pdf');
    await expect(page.locator('#stat')).toContainText('downloaded Budget-Primer-FY2026-27.pdf');
  });

  test('PNG downloads a per-page zip', async ({ page }) => {
    await page.click('#download');
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('#dl-png'),
    ]);
    expect(download.suggestedFilename()).toBe('Budget-Primer-pages.zip');
    await expect(page.locator('#stat')).toContainText('downloaded Budget-Primer-pages.zip');
  });
});

test.describe('download: hosted mode (no local server)', () => {
  test.beforeEach(async ({ context, page }) => {
    await context.route('**/__ping', route => route.fulfill({ status: 404, body: 'no local server' }));
    await gotoEditor(page);
  });

  test('PNG and bleed marks are disabled, with a tooltip explaining why', async ({ page }) => {
    await page.click('#download');
    await expect(page.locator('#dl-png')).toBeDisabled();
    await expect(page.locator('#dl-png')).toHaveAttribute('title', /local live server/);
    await expect(page.locator('#dl-marks')).toBeDisabled();
  });

  test('PDF falls back to the browser\'s own print(), never calling /__export', async ({ page }) => {
    let exportCalled = false;
    await page.route('**/__export', route => { exportCalled = true; route.continue(); });

    // doExport('pdf') calls $('out').contentWindow.print() directly — stub it
    // on the iframe's own window so the test can observe the call without a
    // real (blocking, OS-level) print dialog.
    await page.evaluate(() => {
      document.getElementById('out').contentWindow.print = () => {
        document.getElementById('out').contentWindow.__printed = true;
      };
    });

    await page.click('#download');
    await page.click('#dl-pdf');
    await expect.poll(() => page.evaluate(() =>
      document.getElementById('out').contentWindow.__printed)).toBe(true);
    expect(exportCalled).toBe(false);
  });
});
