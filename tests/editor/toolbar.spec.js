// The Canva-style centered contextual strip (docsync/editor/edit.html
// #arrange / #type). Object selected: colour, border, transparency, effects,
// and a Position button holding the geometry machinery. Text being edited:
// the #ty-marks group (B / I / lists) acting on the live selection in the
// iframe — mousedown on the chrome is prevented so the editor never blurs.
// Local mode.
const { test, expect, gotoEditor } = require('./fixtures/editor-test');

async function addRect(page) {
  await page.evaluate(async () => {
    pushHistory();
    layout.shapes.push({ id: 'tb-rect', page: 3, kind: 'rect', x: 1, y: 1,
                         w: 2, h: 1, fill: '#6B9E78', stroke: 'none', sw: 0.02, z: 3 });
    markDirty();
    await render();
    setSel($('out').contentDocument, ['tb-rect']);
  });
  await page.waitForTimeout(300);
}

test.describe('contextual toolbar', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('the strip is centered, not packed left', async ({ page }) => {
    const jc = await page.evaluate(() => getComputedStyle($('arrange')).justifyContent);
    expect(jc).toContain('center');
  });

  test('a shape offers colour, border, transparency, effects and Position', async ({ page }) => {
    await addRect(page);
    for (const id of ['ar-fill', 'ar-border', 'ar-alpha', 'ar-fxbtn', 'ar-pos']) {
      await expect(page.locator('#' + id), id).toBeVisible();
    }
    // The geometry machinery lives behind Position now.
    await expect(page.locator('#ar-pospop')).toBeHidden();
    await page.click('#ar-pos');
    await expect(page.locator('#ar-pospop')).toBeVisible();
    await expect(page.locator('#ar-pospop #ar-x')).toBeAttached();
    await expect(page.locator('#ar-pospop #ar-front')).toBeAttached();
  });

  test('the border popover sets stroke colour and dash', async ({ page }) => {
    await addRect(page);
    await page.click('#ar-border');
    await page.locator('#ar-bswgrid .sw').nth(1).click();   // first palette colour
    await page.waitForTimeout(800);
    let sh = await page.evaluate(() => layout.shapes.find(x => x.id === 'tb-rect'));
    expect(sh.stroke).toBe('#6B9E78');

    await page.click('#ar-border');
    await page.locator('#ar-dashrow button', { hasText: 'Dashed' }).click();
    await page.waitForTimeout(800);
    sh = await page.evaluate(() => layout.shapes.find(x => x.id === 'tb-rect'));
    expect(sh.dash).toEqual([0.08, 0.05]);
  });

  test('the transparency slider writes the shape\'s alpha', async ({ page }) => {
    await addRect(page);
    await page.click('#ar-alpha');
    await page.locator('#ar-alphain').fill('0.5');
    await page.locator('#ar-alphain').dispatchEvent('change');
    await page.waitForTimeout(800);
    const sh = await page.evaluate(() => layout.shapes.find(x => x.id === 'tb-rect'));
    expect(sh.alpha).toBeCloseTo(0.5, 5);
  });

  test('Effects adds and removes a shadow', async ({ page }) => {
    await addRect(page);
    await page.click('#ar-fxbtn');
    await page.locator('#ar-fxpop button', { hasText: 'Add shadow' }).click();
    await page.waitForTimeout(800);
    let sh = await page.evaluate(() => layout.shapes.find(x => x.id === 'tb-rect'));
    expect(sh.shadow).toBeTruthy();
    expect(sh.shadow.blur).toBeGreaterThan(0);

    await page.click('#ar-fxbtn');
    await page.locator('#ar-fxpop button', { hasText: 'Remove shadow' }).click();
    await page.waitForTimeout(800);
    sh = await page.evaluate(() => layout.shapes.find(x => x.id === 'tb-rect'));
    expect(sh.shadow).toBeUndefined();
  });

  test('editing text surfaces B/I in the chrome, acting on the live selection', async ({ page }) => {
    const frame = page.frameLocator('#out');
    await frame.locator('[data-slot="toc.author"]').dblclick({ force: true });
    const host = frame.locator('.ds-edit');
    await host.waitFor({ state: 'visible' });

    await expect(page.locator('#ty-marks')).toBeVisible();
    // toc.author is plain prose, not a block_html target: no list buttons.
    await expect(page.locator('#ty-mul')).toBeHidden();
    // Slot-level italic yields to selection-level marks while editing.
    await expect(page.locator('#ty-i')).toBeHidden();

    await host.evaluate(el => {
      const r = el.ownerDocument.createRange();
      r.selectNodeContents(el);
      const s = el.ownerDocument.getSelection();
      s.removeAllRanges(); s.addRange(r);
    });
    await page.click('#ty-mb');
    expect(await host.locator('b').count()).toBeGreaterThan(0);
    // The editor is still open — the chrome click must not have blurred it.
    await expect(host).toBeVisible();
    await expect(page.locator('#ty-mb')).toHaveClass(/\bon\b/);
  });

  test('the Appleseed logo recolours from the strip and renders inline', async ({ page }) => {
    await page.evaluate(() => setSel($('out').contentDocument, ['cover.logo']));
    await page.waitForTimeout(200);
    const fill = page.locator('#ar-fill');
    await expect(fill).toBeVisible();
    await expect(fill).toHaveAttribute('title', 'Colour');

    await fill.click();
    await page.locator('#side-body .cdot[title="#2F3E46"]').first().click();
    await page.waitForTimeout(1500);

    expect(await page.evaluate(() => layout.fill['cover.logo'])).toBe('#2F3E46');
    // The <img> became an inline svg painted the chosen colour.
    const frame = page.frameLocator('#out');
    const logo = frame.locator('[data-el="cover.logo"] svg.logo-img');
    await expect(logo).toHaveCount(1);
    expect(await logo.evaluate(n => n.style.color)).toBe('rgb(47, 62, 70)');

    // And "Original artwork" puts the plain <img> back.
    await page.evaluate(() => setSel($('out').contentDocument, ['cover.logo']));
    await page.waitForTimeout(300);
    await page.locator('#side-body .cdot.none').click();
    await page.waitForTimeout(1500);
    await expect(frame.locator('[data-el="cover.logo"] img.logo-img')).toHaveCount(1);
  });
});
