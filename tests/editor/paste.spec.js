// Paste sanitizing (docsync/editor/edit.html pasteClean). Pasting from Word
// or Google Docs used to drop their whole markup into the page; none of it
// survived htmlToMd at commit, so the structure vanished silently minutes
// later. Now the clipboard is normalized through the report's OWN grammar on
// the way in, so what lands on the page is what will render. Local mode.
const { test, expect, gotoEditor, fillDialog, submitDialog } = require('./fixtures/editor-test');

let counter = 0;

/** A +Section overflow slot: block_html's grammar, so lists and headings are
 *  real there — the richest paste target the report has. */
async function openSection(page) {
  await page.click('#add');
  await fillDialog(page, { page: 'basics', slug: 'paste-' + (++counter) });
  await submitDialog(page);
  const ta = page.frameLocator('#out').locator('.ds-edit');
  await ta.waitFor({ state: 'visible' });
  return ta;
}

/** Fire a real paste through the editor's own handler. Playwright cannot
 *  populate the OS clipboard with text/html, and a synthetic ClipboardEvent
 *  is untrusted so it never triggers the browser's own paste — but it does
 *  reach an explicit listener, which is exactly the code under test. */
async function pasteHtml(page, html, selectAll = false) {
  await page.evaluate(({ html, selectAll }) => {
    const d = document.querySelector('#out').contentDocument;
    const host = d.querySelector('.ds-edit');
    host.focus();
    const r = d.createRange();
    r.selectNodeContents(host);
    if (!selectAll) r.collapse(false);          // caret at the end
    const s = d.getSelection(); s.removeAllRanges(); s.addRange(r);
    const dt = new DataTransfer();
    dt.setData('text/html', html);
    dt.setData('text/plain', html.replace(/<[^>]+>/g, ''));
    host.dispatchEvent(new ClipboardEvent('paste', {
      clipboardData: dt, bubbles: true, cancelable: true,
    }));
  }, { html, selectAll });
  await page.waitForTimeout(150);
}

const md = page => page.evaluate(() => {
  const host = document.querySelector('#out').contentDocument.querySelector('.ds-edit');
  return htmlToMd(host, { allowLists: true });
});

test.describe('paste', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('keeps the formatting the report supports', async ({ page }) => {
    const ta = await openSection(page);
    await ta.evaluate(el => { el.innerHTML = '<p></p>'; });
    await pasteHtml(page, '<p>plain <b>bold</b> and <i>ital</i> and ' +
      '<a href="https://example.com/x">a link</a></p>', true);

    expect(await md(page)).toBe('plain **bold** and *ital* and [a link](https://example.com/x)');
  });

  test('strips styling the report cannot render, keeping the words', async ({ page }) => {
    const ta = await openSection(page);
    await ta.evaluate(el => { el.innerHTML = '<p></p>'; });
    // The shape Word and Google Docs actually paste: nested style carriers.
    await pasteHtml(page,
      '<p class="MsoNormal"><span style="font-family:Calibri;color:#FF0000;font-size:14pt">' +
      'red <b>and bold</b></span></p>', true);

    const out = await md(page);
    expect(out).toContain('red');
    expect(out).toContain('**and bold**');   // supported formatting survives
    expect(out).not.toContain('style');      // the rest does not
    expect(out).not.toContain('span');
  });

  test('a pasted list stays a list, and a pasted heading stays a heading', async ({ page }) => {
    const ta = await openSection(page);
    await ta.evaluate(el => { el.innerHTML = '<p></p>'; });
    await pasteHtml(page, '<h2>A heading</h2><ul><li>one</li><li>two</li></ul>', true);

    expect(await md(page)).toBe('## A heading\n\n- one\n- two');
  });

  test('structure the renderer has no grammar for flattens on the way IN, not silently at commit', async ({ page }) => {
    const ta = await openSection(page);
    await ta.evaluate(el => { el.innerHTML = '<p></p>'; });
    // A table and a nested list: content.py can render neither.
    await pasteHtml(page,
      '<table><tr><td>cell A</td><td>cell B</td></tr></table>' +
      '<ul><li>outer<ul><li>inner</li></ul></li></ul>', true);

    const shown = await ta.evaluate(el => el.innerHTML);
    expect(shown).not.toContain('<table');
    // What the editor SHOWS already equals what a commit would keep — the
    // whole point: no structure disappears later.
    const committed = await md(page);
    const reshown = await page.evaluate(m => {
      const div = document.createElement('div');
      div.innerHTML = mdToHtml(m, { allowLists: true });
      return htmlToMd(div, { allowLists: true });
    }, committed);
    expect(reshown).toBe(committed);
    expect(committed).toContain('cell A');
    expect(committed).toContain('inner');
  });

  test('a plain-text slot takes the text literally — pasted stars stay stars', async ({ page }) => {
    const frame = page.frameLocator('#out');
    // cover.title is not run through md_inline, so it gets no markdown.
    await frame.locator('[data-slot="cover.title"]').dblclick({ force: true });
    await frame.locator('.ds-edit').waitFor({ state: 'visible' });
    await pasteHtml(page, '<p>**not bold**</p>', true);

    const text = await frame.locator('.ds-edit').evaluate(el => el.textContent);
    expect(text).toContain('**not bold**');
    expect(await frame.locator('.ds-edit b').count()).toBe(0);
  });
});
