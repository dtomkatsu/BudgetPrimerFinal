/**
 * HTML -> layout.json: import a designed web page as an editable document.
 *
 * The renderer's contract runs one way — content.md + layout.json -> Python ->
 * HTML — so there is no path from "here is some rendered HTML" back to "here
 * is a Python template with the right C.t() call sites". Inferring which text
 * is a heading and which colour is *the palette* from finished pixels is not a
 * problem with a correct answer.
 *
 * What IS well defined is the editor's OTHER rendering mode, the one behind
 * the "+ Page" button: a blank page is nothing but L.layer() + L.text_boxes()
 * + L.tables_html(), a flat list of positioned objects in layout.json with no
 * bespoke Python at all. So importing is not parsing — it is TRACING. Every
 * visible thing on the page becomes the same kind of object a person would
 * have made with the Text/Shape/Table buttons, at the inches the browser
 * itself put it.
 *
 * That last part is the trick worth naming: rather than implement a CSS
 * layout engine, load the page in an iframe at the target width and let the
 * browser lay it out, then read the answer back through
 * getBoundingClientRect() — exactly what inchBox() already does for every
 * drag in this editor.
 *
 * Fidelity is deliberately lossy. layout.json has no nesting, so a structural
 * <div> either contributes a background rectangle or nothing at all; its
 * children are what carry meaning. Think "traced starting point you clean up",
 * not "pixel-perfect conversion". The one case that comes back nearly lossless
 * is a document this tool exported itself, which is already boxes and shapes
 * at fixed inch positions underneath.
 */

export const DPI = 96;                     // CSS px per inch, the web's constant

// Tags that never carry visible layout. <nav>/<footer> are deliberately NOT
// here: they are page content, and a person importing a page expects them.
const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'LINK', 'META', 'NOSCRIPT',
  'TEMPLATE', 'HEAD', 'TITLE', 'BASE', 'IFRAME', 'OBJECT', 'EMBED', 'CANVAS']);

// Inline by nature: their presence inside a block does not make that block a
// container. This is what lets <p>text <a>link</a> more</p> stay ONE text box
// instead of fragmenting into three.
const INLINE_TAGS = new Set(['A', 'SPAN', 'B', 'STRONG', 'I', 'EM', 'U', 'S',
  'SMALL', 'SUB', 'SUP', 'CODE', 'BR', 'ABBR', 'CITE', 'Q', 'MARK', 'TIME',
  'LABEL', 'BDI', 'BDO', 'WBR', 'FONT', 'VAR', 'SAMP', 'KBD']);

// Mirrors layout.py's check_icon_svg — imported markup reaches the rendered
// page, so it is gated on the way in as well as on the way out.
const ICON_TAGS_OK = new Set(['g', 'path', 'circle', 'ellipse', 'rect', 'line',
  'polyline', 'polygon', 'defs', 'clipPath', 'mask', 'use', 'title', 'desc',
  'symbol', 'linearGradient', 'radialGradient', 'stop']);
const ICON_BANNED = /<\s*(script|foreignObject|image|iframe|a|animate|animateTransform|set|handler)\b|\bon[a-z]+\s*=|javascript:|<!ENTITY|<!DOCTYPE/i;
export function iconBodyOk(body) {
  if (typeof body !== 'string' || !body.trim() || body.length > 64000) return false;
  if (ICON_BANNED.test(body)) return false;
  return (body.match(/<\s*\/?\s*([A-Za-z][A-Za-z0-9]*)/g) || [])
    .every(m => ICON_TAGS_OK.has(m.replace(/[<\/\s]/g, '')));
}

// Mirrors layout.py's KINDS whitelist for Layout._validate().
const SHAPE_KINDS = new Set(['rect', 'ellipse', 'line', 'triangle', 'arrow', 'icon']);
const VIEWBOX_RE = /^\s*-?[\d.]+(\s+-?[\d.]+){3}\s*$/;

/**
 * Re-check a traced layout right before it is committed — not just here at
 * trace time. Between extractDoc() producing this object and createProject()
 * writing it into a commit, it sits in sessionStorage, a place a devtools
 * session or a future code path could put something else. This is the one
 * gate the commit itself controls, so it fails hard and loud rather than
 * quietly stripping — same philosophy as layout.py's check_icon_svg, whose
 * whitelist this reuses verbatim.
 */
export function assertLayoutSafe(layout) {
  const shapes = (layout && layout.shapes) || [];
  const seen = new Set();
  shapes.forEach((s, i) => {
    const where = `shape #${i + 1}`;
    if (!s.id) throw new Error(`${where}: needs an id`);
    if (seen.has(s.id)) throw new Error(`${where}: duplicate id '${s.id}'`);
    seen.add(s.id);
    if (!SHAPE_KINDS.has(s.kind)) {
      throw new Error(`${where}: kind '${s.kind}' is not allowed`);
    }
    for (const k of ['x', 'y', 'w', 'h']) {
      if (typeof s[k] !== 'number' || !Number.isFinite(s[k])) {
        throw new Error(`${where}.${k}: '${s[k]}' is not a number`);
      }
    }
    if (s.kind === 'icon') {
      if (!iconBodyOk(s.svg)) {
        throw new Error(`${where}: icon markup did not pass the safety check — refusing to import it`);
      }
      if (typeof s.vb !== 'string' || !VIEWBOX_RE.test(s.vb)) {
        throw new Error(`${where}: icon viewBox '${s.vb}' must be four numbers`);
      }
    }
  });
}

const clamp01 = v => Math.min(1, Math.max(0, v));
const round3 = v => Math.round(v * 1000) / 1000;

/** rgb()/rgba() -> #rrggbb, or null when it paints nothing. */
export function cssColorToHex(css) {
  if (!css) return null;
  const m = /^rgba?\(([^)]+)\)$/.exec(css.trim());
  if (!m) return /^#[0-9a-f]{3,8}$/i.test(css.trim()) ? css.trim().toUpperCase() : null;
  const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
  if (p.length >= 4 && p[3] === 0) return null;            // fully transparent
  const h = n => Math.round(n).toString(16).padStart(2, '0');
  return ('#' + h(p[0]) + h(p[1]) + h(p[2])).toUpperCase();
}

/** The alpha of an rgba(), for deciding whether a panel is worth keeping. */
function cssAlpha(css) {
  const m = /^rgba\(([^)]+)\)$/.exec((css || '').trim());
  if (!m) return 1;
  const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
  return p.length >= 4 ? p[3] : 1;
}

/** Is this element drawn at all? Cheap rejects first — a hidden subtree is
 *  the single biggest source of junk objects in an import. */
function invisible(el, cs) {
  if (SKIP_TAGS.has(el.tagName)) return true;
  if (cs.display === 'none' || cs.visibility === 'hidden') return true;
  if (parseFloat(cs.opacity) === 0) return true;
  // NOT aria-hidden: that says "skip me in a screen reader", not "I am not
  // painted". Decorative marks — a logo's leaf, an arrow glyph — carry it as
  // a matter of course, so treating it as invisible drops precisely the
  // artwork most worth importing. (This is why the first pass came back with
  // zero icons: the logo's wrapper was aria-hidden and the walk never
  // reached the <svg> inside it.)
  if (el.hasAttribute('hidden')) return true;
  return false;
}

/** A text LEAF: it has words of its own, and no block-level child that would
 *  carry words separately. That distinction is the whole classifier — get it
 *  wrong one way and every paragraph shatters into spans, wrong the other and
 *  a whole section collapses into one giant box. */
function isTextLeaf(el, win) {
  const own = (el.textContent || '').trim();
  if (!own) return false;
  for (const kid of el.children) {
    if (SKIP_TAGS.has(kid.tagName)) continue;
    const kcs = win.getComputedStyle(kid);
    if (kcs.display === 'none') continue;
    // A GRAPHIC child needs an object of its own, so its parent is a
    // container no matter how much text sits beside it. Without this, a
    // logo lockup (mark + wordmark in one div) reads as a text leaf and the
    // mark is silently dropped — which is exactly what happened to every
    // icon on the first pass.
    if (kid.tagName === 'IMG' || kid.tagName.toLowerCase() === 'svg') {
      const kr = kid.getBoundingClientRect();
      if (kr.width > 4 && kr.height > 4) return false;
    }
    if (INLINE_TAGS.has(kid.tagName)) continue;
    // A block-level child with text of its own means this is a container.
    if (!kcs.display.startsWith('inline') && (kid.textContent || '').trim()) return false;
  }
  return true;
}

/** Does this element paint a background worth keeping as a shape? */
function painted(cs) {
  const bg = cssColorToHex(cs.backgroundColor);
  if (!bg) return null;
  if (cssAlpha(cs.backgroundColor) < 0.08) return null;    // effectively invisible
  return bg;
}

/** A border, if it draws one. Cards on a white page are white — it is the
 *  BORDER that makes them cards, so ignoring it loses the whole component. */
function bordered(cs, dpi) {
  const w = parseFloat(cs.borderTopWidth) || 0;
  if (w < 0.5 || cs.borderTopStyle === 'none') return null;
  const col = cssColorToHex(cs.borderTopColor);
  if (!col || cssAlpha(cs.borderTopColor) < 0.08) return null;
  return { stroke: col, sw: round3(w / dpi) };
}

/** Corner radius in inches — a pill button and a square one are not the same
 *  component, and the shape model already carries `r`. */
function radius(cs, dpi) {
  const r = parseFloat(cs.borderTopLeftRadius) || 0;
  return r > 0.5 ? round3(r / dpi) : 0;
}

/** Inline markup -> the editor's markdown, matching htmlToMd's grammar. The
 *  editor's own serializer is not importable here (it lives inside edit.html),
 *  and only these four constructs survive content.py's md_inline anyway. */
export function inlineMd(el, win) {
  let out = '';
  const view = win || (el.ownerDocument && el.ownerDocument.defaultView);
  el.childNodes.forEach(n => {
    if (n.nodeType === 3) { out += n.nodeValue.replace(/\s+/g, ' '); return; }
    if (n.nodeType !== 1) return;
    // Invisible inline content contributes NOTHING. This is the rule that
    // keeps a carousel's inactive slides out: they are stacked, absolutely
    // positioned, and faded by an opacity:0 on an inner span — so the
    // text-bearing element itself reads as perfectly visible, and only its
    // child gives the game away. Without this, three slides concatenate into
    // one sentence that was never on the page.
    if (view) {
      const cs = view.getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden'
          || parseFloat(cs.opacity) < 0.05) return;
    }
    const t = n.tagName;
    if (t === 'BR') { out += '\n'; return; }
    if (t === 'IMG') { out += `![${n.getAttribute('alt') || ''}](${n.getAttribute('src') || ''})`; return; }
    const inner = inlineMd(n, view);
    if (!inner.trim()) { out += inner; return; }
    if (t === 'B' || t === 'STRONG') out += `**${inner}**`;
    else if (t === 'I' || t === 'EM') out += `*${inner}*`;
    else if (t === 'A') {
      const href = n.getAttribute('href') || '';
      // content.py only linkifies absolute http(s) — anything else would
      // render as literal brackets, so it is better as plain words.
      out += /^https?:\/\//i.test(href) ? `[${inner}](${href})` : inner;
    } else out += inner;
  });
  return out;
}

/** The text style worth carrying over. Deliberately conservative: `font` is
 *  omitted entirely because layout.py validates it against an allowlist of
 *  families the report can actually load, and a source page's font is almost
 *  never on it — a wrong name is a hard build failure, a missing one is the
 *  project's own default. */
function textStyle(cs) {
  const st = {};
  const size = parseFloat(cs.fontSize);
  if (size) st.size = Math.round(size * 10) / 10;
  const w = parseInt(cs.fontWeight, 10);
  if (w && w !== 400) st.weight = w;
  const color = cssColorToHex(cs.color);
  if (color && color !== '#000000') st.color = color;
  if (['center', 'right', 'justify'].includes(cs.textAlign)) st.align = cs.textAlign;
  const lh = parseFloat(cs.lineHeight);
  if (lh && size) st.leading = Math.round((lh / size) * 100) / 100;
  const ls = parseFloat(cs.letterSpacing);
  if (ls) st.tracking = Math.round((ls / (size || 16)) * 1000) / 1000;
  // CSS's names are not layout.py's — it validates against none/upper/lower/
  // title and fails the build on anything else, which is how this mismatch
  // surfaced rather than silently dropping the styling.
  const CASE = { uppercase: 'upper', lowercase: 'lower', capitalize: 'title' };
  if (CASE[cs.textTransform]) st.case = CASE[cs.textTransform];
  return st;
}

/**
 * Walk a laid-out document and emit the flat object model layout.json holds.
 *
 * `root` is usually document.body. `originY` lets a caller slice a tall page
 * into several — everything is measured from it.
 */
export function extractDoc(doc, opts = {}) {
  const win = doc.defaultView;
  const pageId = opts.pageId ?? 1;
  const originX = opts.originX ?? 0;
  const originY = opts.originY ?? 0;
  const dpi = opts.dpi ?? DPI;
  const minPx = opts.minPx ?? 6;          // ignore slivers: rules, spacers, 1px lines
  const root = opts.root || doc.body;

  const boxes = [], shapes = [], tables = [], images = [];
  const stats = { visited: 0, skipped: 0 };
  let n = 0;
  const nid = p => `${p}${++n}`;

  const rootRect = root.getBoundingClientRect();
  const baseX = originX - (rootRect.left + win.scrollX);
  const baseY = originY - (rootRect.top + win.scrollY);

  const inches = el => {
    const r = el.getBoundingClientRect();
    return {
      x: round3((r.left + win.scrollX + baseX) / dpi),
      y: round3((r.top + win.scrollY + baseY) / dpi),
      w: round3(r.width / dpi),
      h: round3(r.height / dpi),
      px: r,
    };
  };

  // z rises with depth so a background lands behind the words drawn over it,
  // which is the whole reason a container's paint is emitted before recursing.
  const walk = (el, depth) => {
    stats.visited++;
    const cs = win.getComputedStyle(el);
    if (invisible(el, cs)) { stats.skipped++; return; }
    const g = inches(el);
    if (g.px.width < minPx || g.px.height < minPx) { stats.skipped++; return; }

    if (el.tagName === 'IMG') {
      const src = el.getAttribute('src');
      if (src) {
        images.push({ src, alt: el.getAttribute('alt') || '' });
        boxes.push({ id: nid('i'), page: pageId, x: g.x, y: g.y, w: g.w,
                     md: `![${el.getAttribute('alt') || ''}](${src})`, z: depth + 1 });
      }
      return;
    }

    if (el.tagName.toLowerCase() === 'svg') {
      // Inline SVG is artwork worth keeping — a logo, an arrow, a leaf mark.
      // It rides the SAME path a picked icon does: inner markup stored in
      // layout.json as kind:"icon", which means it must clear the same
      // whitelist, and gets the same currentColor recolouring for free.
      // Anything that fails the check degrades to a plain rectangle rather
      // than importing markup the renderer would refuse.
      const body = el.innerHTML || '';
      const vb = el.getAttribute('viewBox');
      if (body && vb && /^\s*-?[\d.]+(\s+-?[\d.]+){3}\s*$/.test(vb) && iconBodyOk(body)) {
        shapes.push({ id: nid('g'), page: pageId, kind: 'icon', x: g.x, y: g.y,
                      w: g.w, h: g.h, vb, svg: body,
                      fill: cssColorToHex(cs.color) || '#2F3E46', z: depth + 1 });
      } else {
        const bg = painted(cs);
        if (bg) shapes.push({ id: nid('s'), page: pageId, kind: 'rect', x: g.x, y: g.y,
                              w: g.w, h: g.h, fill: bg, stroke: 'none', sw: 0.02, z: depth });
      }
      return;
    }

    if (el.tagName === 'TABLE') {
      const rows = [...el.querySelectorAll('tr')].map(tr =>
        [...tr.children].map(td => inlineMd(td, win).trim()));
      if (rows.length && rows[0].length) {
        tables.push({ id: nid('t'), page: pageId, x: g.x, y: g.y, w: g.w,
                      header: !!el.querySelector('thead'), rows, z: depth + 1 });
      }
      return;
    }

    if (isTextLeaf(el, win)) {
      const md = inlineMd(el, win).replace(/[ \t]+/g, ' ').trim();
      if (md) {
        // Headroom. The box is measured at the source font's width; the
        // renderer will almost never have that font, and a substitute is
        // usually wider — with no slack the last word wraps or is cut.
        const w = round3(Math.min(g.w * 1.06 + 0.04, opts.pageW || g.w * 1.3));
        const b = { id: nid('b'), page: pageId, x: g.x, y: g.y, w, md, z: depth + 1 };
        const st = textStyle(cs);
        if (Object.keys(st).length) b.style = st;
        // A pill button is a rounded backdrop with words on it — one flat
        // box `fill` would square it off, so the backdrop is its own shape.
        const bg = painted(cs), bd = bordered(cs, dpi), r = radius(cs, dpi);
        if ((bg || bd) && r > 0.01) {
          shapes.push({ id: nid('s'), page: pageId, kind: 'rect', x: g.x, y: g.y,
                        w: g.w, h: g.h, fill: bg || 'none',
                        stroke: bd ? bd.stroke : 'none', sw: bd ? bd.sw : 0.02,
                        r, z: depth });
        } else if (bg) b.fill = bg;
        boxes.push(b);
      }
      return;
    }

    // A container: keep its paint as a backdrop, then let its children speak.
    const bg = painted(cs);
    const bd = bordered(cs, dpi);
    if (bg || bd) {
      shapes.push({ id: nid('s'), page: pageId, kind: 'rect', x: g.x, y: g.y,
                    w: g.w, h: g.h, fill: bg || 'none',
                    stroke: bd ? bd.stroke : 'none', sw: bd ? bd.sw : 0.02,
                    r: radius(cs, dpi), z: depth });
    }
    for (const kid of el.children) walk(kid, depth + 1);
  };

  for (const kid of root.children) walk(kid, 1);

  const rr = root.getBoundingClientRect();
  return {
    boxes, shapes, tables, images, stats,
    widthIn: round3(Math.max(rr.width, root.scrollWidth) / dpi),
    heightIn: round3(Math.max(rr.height, root.scrollHeight) / dpi),
  };
}

/** The imported objects as the two files a project is made of. */
export function toProjectFiles(doc, title) {
  const layout = {
    boxes: doc.boxes, shapes: doc.shapes, tables: doc.tables,
    positions: {}, fill: {},
  };
  const content = `<!--
  Imported from an HTML page. The words live in layout.json as free text
  boxes — the same objects the Text button makes — so this file holds only
  the citation list every project is required to have.
-->

[[title]]
${title}

[[sources]]
[example]: Replace or delete this placeholder source — https://example.com
`;
  return { layout, content };
}
