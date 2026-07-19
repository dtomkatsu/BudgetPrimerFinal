// compressImageFile() (docsync/editor/edit.html) resizes oversized image
// uploads before they enter the repo — see commit 6ff6080. These pin exactly
// what was verified by hand when the feature shipped: a big noisy JPEG
// shrinks and keeps its aspect ratio, a small image passes through
// byte-for-byte, an SVG is never rasterized, and a resized PNG keeps alpha.
//
// compressImageFile is a top-level function declaration in a classic (non-
// module) script, so it lands on `window` — callable directly via
// page.evaluate, no UI interaction or upload flow (and therefore no GitHub
// call) needed.
const { test, expect, gotoEditor } = require('./fixtures/editor-test');

test.describe('compressImageFile', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
  });

  test('shrinks an oversized JPEG to fit within 2000px, preserving aspect ratio', async ({ page }) => {
    const result = await page.evaluate(async () => {
      // Build a large noisy (incompressible) JPEG in-browser so the "before"
      // size is realistically big, like a real phone photo.
      const w = 4000, h = 3000;
      const canvas = document.createElement('canvas');
      canvas.width = w; canvas.height = h;
      const ctx = canvas.getContext('2d');
      const imgData = ctx.createImageData(w, h);
      for (let i = 0; i < imgData.data.length; i++) imgData.data[i] = Math.floor(Math.random() * 256);
      ctx.putImageData(imgData, 0, 0);
      const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.95));
      const file = new File([blob], 'phone-photo.jpg', { type: 'image/jpeg' });
      const before = file.size;

      const out = await window.compressImageFile(file);
      const bitmap = await createImageBitmap(out);
      return {
        before, after: out.size, type: out.type,
        width: bitmap.width, height: bitmap.height,
      };
    });

    expect(result.width).toBeLessThanOrEqual(2000);
    expect(result.height).toBeLessThanOrEqual(2000);
    // Original was 4000x3000 (4:3) — the resize must preserve that ratio.
    expect(result.width / result.height).toBeCloseTo(4000 / 3000, 2);
    expect(result.type).toBe('image/jpeg');
    expect(result.after).toBeLessThan(result.before);
  });

  test('leaves an already-small image byte-for-byte unchanged', async ({ page }) => {
    const result = await page.evaluate(async () => {
      const canvas = document.createElement('canvas');
      canvas.width = 400; canvas.height = 300;
      canvas.getContext('2d').fillRect(0, 0, 400, 300);
      const blob = await new Promise(r => canvas.toBlob(r, 'image/png'));
      const file = new File([blob], 'small.png', { type: 'image/png' });

      const out = await window.compressImageFile(file);
      return { same: out === file, beforeSize: file.size, afterSize: out.size };
    });

    expect(result.same).toBe(true);
    expect(result.afterSize).toBe(result.beforeSize);
  });

  test('never rasterizes an SVG', async ({ page }) => {
    const result = await page.evaluate(async () => {
      const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="5000" height="5000"></svg>';
      const file = new File([svg], 'huge.svg', { type: 'image/svg+xml' });
      const out = await window.compressImageFile(file);
      return { same: out === file, type: out.type };
    });

    expect(result.same).toBe(true);
    expect(result.type).toBe('image/svg+xml');
  });

  test('keeps the alpha channel when resizing a PNG', async ({ page }) => {
    const result = await page.evaluate(async () => {
      const w = 3000, h = 2000;
      const canvas = document.createElement('canvas');
      canvas.width = w; canvas.height = h;
      const ctx = canvas.getContext('2d');
      // Half the canvas fully transparent, half opaque red — a resize that
      // drops alpha would turn the transparent half solid.
      ctx.clearRect(0, 0, w / 2, h);
      ctx.fillStyle = 'rgba(255,0,0,1)';
      ctx.fillRect(w / 2, 0, w / 2, h);
      const blob = await new Promise(r => canvas.toBlob(r, 'image/png'));
      const file = new File([blob], 'alpha.png', { type: 'image/png' });

      const out = await window.compressImageFile(file);
      const bitmap = await createImageBitmap(out);
      const oc = document.createElement('canvas');
      oc.width = bitmap.width; oc.height = bitmap.height;
      const octx = oc.getContext('2d');
      octx.drawImage(bitmap, 0, 0);
      const left = octx.getImageData(4, Math.floor(bitmap.height / 2), 1, 1).data;
      const right = octx.getImageData(bitmap.width - 4, Math.floor(bitmap.height / 2), 1, 1).data;
      return { type: out.type, leftAlpha: left[3], rightAlpha: right[3] };
    });

    expect(result.type).toBe('image/png');
    expect(result.leftAlpha).toBe(0);
    expect(result.rightAlpha).toBeGreaterThan(200);
  });

  test('falls back to the original file when the browser cannot decode it', async ({ page }) => {
    const result = await page.evaluate(async () => {
      // Not a real image — createImageBitmap() must reject and the function
      // must hand the original file back rather than throw or block.
      const file = new File([new Uint8Array([1, 2, 3, 4])], 'not-an-image.jpg', { type: 'image/jpeg' });
      const out = await window.compressImageFile(file);
      return { same: out === file };
    });

    expect(result.same).toBe(true);
  });
});
