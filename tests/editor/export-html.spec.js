// HTML export fidelity (docsync/editor/edit.html exportHtml/renderClean/
// scopeCss). The editor's iframe holds the renderer's REAL output, not a
// preview of it — so an export that matches what you see is the same render
// minus the editing scaffolding, with everything it referenced pulled inline.
// These tests hold that line: same page count, same text, no data-slot/
// data-el hooks, no external references left dangling.
const { test, expect, gotoEditor } = require('./fixtures/editor-test');

/** Run the export and capture the file instead of writing it to disk. */
async function grabExport(page, which) {
  await page.evaluate(() => {
    window.__dl = null;
    // The export ends in an <a download>.click(); intercept it.
    const realClick = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function () {
      if (this.download) {
        window.__dlName = this.download;
        return fetch(this.href).then(r => r.text()).then(t => { window.__dl = t; });
      }
      return realClick.call(this);
    };
  });
  await page.click('#download');
  await page.click(which);
  await page.waitForFunction(() => window.__dl !== null, null, { timeout: 60_000 });
  return {
    html: await page.evaluate(() => window.__dl),
    name: await page.evaluate(() => window.__dlName),
  };
}

test.describe('HTML export', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('the self-contained file matches the editor, minus the editing hooks', async ({ page }) => {
    // What the editor is showing right now.
    const shown = await page.frameLocator('#out').locator('body').evaluate(b => ({
      pages: b.querySelectorAll('section.page').length,
      text: (b.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 400),
    }));

    const { html, name } = await grabExport(page, '#dl-html');
    expect(name).toMatch(/\.html$/);
    expect(html.startsWith('<!DOCTYPE html>')).toBe(true);

    // Same document: same page count, same words.
    const got = await page.evaluate(h => {
      const d = new DOMParser().parseFromString(h, 'text/html');
      // innerText, not textContent: the cover title is <br>-separated lines,
      // and only innerText reports the line breaks as the spaces a reader
      // sees. Comparing textContent would fail on a document that is right.
      const probe = document.createElement('div');
      probe.style.cssText = 'position:fixed;left:-99999px;top:0;width:1200px';
      probe.innerHTML = d.body.innerHTML;
      document.body.appendChild(probe);
      const text = (probe.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 400);
      probe.remove();
      return {
        pages: d.querySelectorAll('section.page').length,
        text,
        slots: d.querySelectorAll('[data-slot]').length,
        els: d.querySelectorAll('[data-el]').length,
        links: d.querySelectorAll('link[rel~="stylesheet"]').length,
        relImgs: [...d.querySelectorAll('img')]
          .filter(i => !/^(data:|https?:)/i.test(i.getAttribute('src') || '')).length,
      };
    }, html);

    expect(got.pages).toBe(shown.pages);
    expect(got.text.slice(0, 200)).toBe(shown.text.slice(0, 200));
    // The editing scaffolding must NOT ship — it only exists under DOCSYNC_EDIT.
    expect(got.slots).toBe(0);
    expect(got.els).toBe(0);
    // Self-contained: nothing left to fetch from a folder that will not be there.
    expect(got.links).toBe(0);
    expect(got.relImgs).toBe(0);
  });

  test('the editor is still editable after an export', async ({ page }) => {
    await grabExport(page, '#dl-html');
    // renderClean() runs WITHOUT DOCSYNC_EDIT; the editor has to come back
    // with its hooks, or the export silently breaks the session.
    const frame = page.frameLocator('#out');
    await expect(frame.locator('[data-slot]').first()).toBeAttached({ timeout: 30_000 });
    await expect(frame.locator('[data-el]').first()).toBeAttached();
  });

  test('the Squarespace block is a scoped, self-scaling fragment', async ({ page }) => {
    const { html, name } = await grabExport(page, '#dl-sqsp');
    expect(name).toMatch(/-squarespace\.html$/);

    // A fragment: it lives inside someone else's page.
    expect(html).not.toMatch(/<!DOCTYPE/i);
    expect(html).not.toMatch(/<html[\s>]/i);
    expect(html).not.toMatch(/<body[\s>]/i);

    const uid = (html.match(/id="(dsx-[a-z0-9]+)"/) || [])[1];
    expect(uid).toBeTruthy();

    // Every rule is scoped to the wrapper, so the block cannot style the host
    // page and the host page cannot restyle the block.
    const styles = [...html.matchAll(/<style>([\s\S]*?)<\/style>/g)].map(m => m[1]).join('\n');
    expect(styles.length).toBeGreaterThan(50);
    const selectors = styles
      .replace(/@(media|supports|layer|container)[^{]*\{/g, '')   // unwrap at-rules
      .split('}').map(s => s.split('{')[0].trim())
      .filter(s => s && !s.startsWith('@'));
    const unscoped = selectors.filter(s =>
      s.split(',').some(one => one.trim() && !one.includes('#' + uid)));
    expect(unscoped, `unscoped selectors: ${unscoped.slice(0, 5).join(' | ')}`).toEqual([]);

    // Scaled, not reflowed — the design is placed at a fixed page width, so
    // scaling is what keeps it identical in a narrower column.
    expect(html).toContain('dsx-scale');
    expect(html).toMatch(/transform\s*=\s*'scale\(/);
    expect(html).toMatch(/ResizeObserver|addEventListener\('resize'/);
  });

  test('scopeCss rewrites selectors without mangling at-rules', async ({ page }) => {
    const out = await page.evaluate(() => scopeCss(
      'body{margin:0}h1,.a{color:red}@media (max-width:600px){p{font-size:9px}}'
      + '@font-face{font-family:X;src:url(x.woff2)}@keyframes k{to{opacity:1}}',
      '#w'));
    expect(out).toContain('#w{margin:0}');            // body IS the wrapper
    expect(out).toContain('#w h1,#w .a{color:red}');
    expect(out).toContain('@media (max-width:600px){#w p{font-size:9px}}');
    // Naming at-rules must pass through untouched — scoping them breaks them.
    expect(out).toContain('@font-face{font-family:X;src:url(x.woff2)}');
    expect(out).toContain('@keyframes k{to{opacity:1}}');
  });
});
