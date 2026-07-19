# Canva-parity roadmap

Where the draft editor stands against "make it work like Canva," and what's
left — grounded in the real architecture (a single-file editor overlaying
interaction on the report's Python/Pyodide renderer; `layout.json` in inches;
prose in `content.md` slots; the whole thing staged verbatim, no build step).

---

## Already shipped

- **Text**: click any prose slot or heading to edit; **add** a heading /
  subheading / body text box (Canva's "Add text"); bold/italic/underline,
  bulleted & numbered lists, font/size/weight/case/spacing/colour, alignment.
- **Shapes**: rect / ellipse / line / triangle / arrow, solid visible fill by
  default, recolour (solid or gradient) from the toolbar Fill swatch, 8-handle
  resize, rotate, opacity, shadow, dashes, layer order, lock, group.
- **Text boxes**: draggable, all-side + corner resize (min-height, never
  clips), fill/background, per-box text style.
- **Tables**: draggable, width-resize, edit cells in place, insert/delete rows
  & columns, header band.
- **Images**: upload/replace, crop, auto-compress oversized uploads.
- **Endnotes**: right-click a paragraph to add or cite.
- **The cover title / year** and every section heading are editable.
- **Canvas basics**: undo/redo, duplicate, align/distribute, snap guides &
  rulers, per-page fills, zoom, multi-page rail, offline draft cache,
  save/share/publish.

The editor is at rough Canva parity for **text, shapes, tables, images, and
placement** on a page.

---

## Remaining editability gaps ("edit ALL elements, even designed ones")

Most report text is already an editable slot. Three categories are not yet:

1. **SVG-embedded text** — the budget-process wheel labels (JAN…DEC, the ring
   captions), chart axis/series labels, pie slice labels. These are drawn as
   SVG `<text>`, not HTML, so the click-to-edit textarea doesn't apply.
   *Feasible* — `content.py`'s `slot_attr()` already works on SVG `<text>`, so
   the renderer side is a per-label change; the editor needs a small
   SVG-text inline editor (position a textarea over the glyph run on
   double-click). **Effort: medium**, and it's per-figure. Highest-value
   single target: the process wheel (page 4).

2. **Remaining hardcoded strings** — the page-2 table of contents list
   ("Budget Basics / How Money Is Spent / …"), the folio ("N • BUDGET
   PRIMER"), figure/table number prefixes ("Figure 1.", "Table 1."), and the
   web page's "Budget Tracker ↗" / "Download PDF" header. Each converts to a
   slot exactly like the cover title just did. **Effort: low**, mechanical,
   one slot at a time.

3. **Data-driven numbers** — every dollar amount and chart datum comes from the
   budget JSON and is deliberately *not* editable (editing a number in the
   layout would silently disagree with the source data). **Out of scope by
   design** — the right lever is the data pipeline, not the editor.

---

## Remaining Canva feature additions (ranked by value / effort)

1. **Image adjustments** — filters (brightness / contrast / saturation /
   grayscale) as CSS `filter` on the placed image, stored in `layout.json`.
   Cheap and CSS-native; no service needed. **Small.** (Crop already exists;
   background-removal would need an external service — skip.)

2. **SVG-text editing** — see gap #1. The single biggest "edit everything"
   unlock. **Medium.**

3. **Duplicate / template a page** — "+ Page" adds a blank page today.
   Duplicating an existing page (and a couple of starter layouts) is the Canva
   "new page from template" flow. **Medium.**

4. **Smart alignment guides** — snap-to-other-element guides (centre lines,
   equal spacing) as you drag, beyond the current ruler guides. **Medium.**

5. **More fonts / font upload** — fonts are an allowlist (`FONTS` in
   `layout.py`); adding families is config, uploading a custom font is a
   staging + `@font-face` change. **Small–medium.**

6. **A proper "position / arrange" side panel** — Canva's right-hand panel
   (exact x/y/w/h, alignment, spacing, flip) — the toolbar already has the
   fields; this is a layout/UX consolidation. **Small.**

7. **Comments / live collaboration** — draft/share/publish covers async review;
   inline comments or live cursors are a much larger, backend-touching effort.
   **Large — probably not worth it for this workflow.**

8. **User-editable charts** — the report's figures are code-generated from data;
   a drag-to-edit chart object is a whole second rendering paradigm.
   **Large — recommend keeping charts data-driven.**

---

## Recommendation

The high-value, low-friction next batch is **(1) image filters + (2) the
mechanical hardcoded-string conversions (TOC list, folio, figure labels)**,
then **(3) SVG-text editing starting with the process wheel** if "edit
absolutely everything" is the goal. Comments/live-collab and editable charts
are the two places where the effort stops paying off for a print-first budget
report.
