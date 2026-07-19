# Libraries — assessment

Should the draft editor adopt fabric.js? What other libraries would genuinely
help? Grounded in the editor's actual architecture.

---

## The architectural fact everything hinges on

The editor has **no `<canvas>`**. Its editing surface is an `<iframe>`
(`#out`) showing HTML that the report's **real Python renderer**
(`report2027/tools/render_report.py` + `docsync/layout.py`) generates and the
browser runs via Pyodide. That renderer is the **single source of truth**:

- Prose lives in `content.md` (`[[slot]]`s). Visual objects (shapes, text
  boxes, fills, positions) live in `layout.json`, in **inches** from the page
  corner.
- Python draws BOTH — `layout.py`'s `layer()` / `text_boxes()` /
  `fill_svg_paint()` render the shapes/boxes into the SAME HTML used for the
  edit preview and the final PDF.
- The editor only *overlays interaction* (drag, resize, rotate, select, snap,
  group, guides, layers — ~14 functions, ~1,500 lines, 46 inch-coordinate
  references) on the Python-rendered DOM, and writes results back to
  `layout.json`.
- Output is print-quality **HTML/CSS → PDF** (`@media print`, `@page`,
  selectable text, vector figures).

There is also a hard constraint: the editor is a **single file, no build step,
staged verbatim** by `docsync/stage.py` (load-bearing for Pyodide same-origin
staging). Any *runtime* library must drop in as a CDN `<script>`/ESM import
(as Pyodide already does). This rules out anything heavy or build-dependent.

---

## fabric.js — No

fabric.js is a `<canvas>` object model (rects, text, images, groups,
selection, transform handles, JSON serialization). It expects the canvas to BE
the document. Two ways to adopt it, both bad here:

1. **Replace the surface** (fabric canvas = the document): abandons the
   Pyodide/Python-renderer foundation — the thing that guarantees WYSIWYG
   through the real renderer and produces print-quality HTML→PDF. Canvas
   exports to PNG/SVG or canvas-to-PDF: raster or crude vector, wrong for a
   text-heavy, print-first report (no real text flow, no `@page`, no
   selectable PDF text).

2. **Overlay for shapes only** (fabric just for `layout.json` objects): now
   shapes are drawn **twice** — by fabric while editing, by Python for output
   — with two coordinate systems to keep in sync. Strictly *worse* than
   today's single source (`layout.json` → Python draws both); it reintroduces
   the drift the current design removes.

The hand-rolled interaction layer fabric would replace is deeply tied to the
inch / `layout.json` model and the "renderer is truth" invariant — neither of
which fabric understands. Replacing working code buys nothing and costs the
architecture.

**When fabric WOULD fit:** only if the product pivots to a free-form design
canvas whose output is an image/poster and print-text fidelity is irrelevant —
a different product. Narrow defensible niche: a dedicated per-page "canvas
page" type (a cover or infographic) edited in fabric, exported as SVG, and
embedded into the Python render. Real, but a whole second editing paradigm and
export path for a narrow need — not recommended now.

Same verdict, same reason, for **Konva** and **Paper.js** (canvas engines).

---

## Libraries worth adding (no architecture fight)

Ranked by value / effort.

1. **`@playwright/test` (dev-only) — done.** Formalized into `tests/editor/`
   (36 tests: image compression, sections, sources, undo/redo, drafts/share/
   publish, oauth device-flow, multi-project registry, standalone install
   lifecycle, download/export) and wired into CI
   (`.github/workflows/editor-tests.yml`), alongside `docsync/test_docsync.py`.
   GitHub itself is fully mocked in-memory (`tests/editor/fixtures/
   fake-github.js`) so the suite never touches the real API or pushes a real
   commit. Building it surfaced two real bugs, both fixed: (a) the Cite
   toolbar button's `sel.focus()` blurred the paragraph being edited and tore
   down the citation panel before it could be used; (b) the local dev
   server's live-reload injection (`serve.py`) spliced its `<script>` into
   the *first* `</body>` string in the page instead of the last, which landed
   inside `start.html`'s new-report JS template (itself containing a literal
   `</body>`) and corrupted the whole page's script.

2. **`fflate` — tiny, CDN-friendly** — enables a "Download source"
   (the `content.md` + `layout.json` + touched assets as a `.zip`), the half
   of Export that `STANDALONE.md` left out. Clear value for anyone who wants
   the raw files; zero architectural conflict (it only reads state the editor
   already holds). *Verified 2026-07-18:* fflate **v0.8.3** (published
   2026-05-16), zero runtime dependencies, ships an ESM `module`/`exports`
   build that drops straight in as a CDN import — no build step, which is the
   binding constraint here. Actively maintained (2.9k★, last pushed 2026-05-16,
   not archived). Preferred over **JSZip** (larger, older API); this is the
   "8kB package" its own npm description names, and the `Download ▾` popover
   already has the natural home for a third "Source (.zip)" item.

3. **Native `<dialog>` (not a library)** — the editor still uses raw
   `prompt()`/`confirm()` for new-section, source id, rename, cross-page move,
   token entry, publish. `start.html` already has a proper in-app modal;
   standardizing on `<dialog>` would make those flows consistent and stop
   losing typed input to a dismissed prompt. A UX cleanup, not a library add.
   *Verified 2026-07-18 (MDN):* `<dialog>` + `.showModal()` is **Baseline
   widely available since March 2022** (Safari 15.4 was the last engine to
   land it), so it's safe with zero dependency. Caveats to design around:
   `::backdrop` is supported but style it explicitly, and animating the modal
   in/out needs `transition-behavior: allow-discrete` on `display`. This also
   *directly retires the two `prompt()`-fragility papercuts the test suite
   exposed* — the sequential `prompt()` chains in `+Section` and Cite are
   exactly the "typed input lost to a dismissed prompt" failure a `<dialog>`
   form removes.

4. **`idb-keyval` — tiny, optional** — drafts and the token live in
   `localStorage` today. For offline draft persistence (edits survive a
   closed tab / dropped connection before a network save), a tiny IndexedDB
   wrapper fits the service-worker/offline direction already started in
   `STANDALONE.md`. Plausible next step, not urgent. *Verified 2026-07-18:*
   idb-keyval **v6.3.0**, zero runtime dependencies, ESM `exports`, actively
   maintained (3.2k★, last pushed 2026-07-08). Note the migration cost:
   `localStorage` is synchronous and IndexedDB is not, so the token/draft
   reads scattered through `ensureAuth()`/`resolveDraft()` would each become
   `await`s — worth it only once offline persistence is an actual goal, not
   before.

---

## Libraries to avoid

- **fabric.js / Konva / Paper.js** — canvas engines; wrong model (above).
- **jsPDF + html2canvas** — rasterizes the page into a PDF; strictly worse
  than the existing browser print-to-PDF path (`Download ▾` / `serve.py`'s
  `/__export`), which uses the real print CSS and keeps text selectable.
- **React / Vue / Svelte** — the single-file, no-build, staged-verbatim design
  is intentional and load-bearing; a framework is a large rewrite against the
  grain for no user-visible gain.
- **interact.js / moveable** — could do drag/resize on DOM elements (unlike
  fabric, they don't need a canvas), but the existing hand-rolled layer is
  working and tightly bound to the inch/`layout.json` model and snap/guide/
  group/lock logic. Replacing it is a large rewrite of correct code for
  marginal benefit. (Worth knowing they existed *before* that layer was built;
  not worth swapping now.)
