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

2. **`fflate` — done.** A "Source — files & images (.zip)" item in the
   `Download ▾` popover (`downloadSource()`), bundling `content.md` +
   `layout.json` + any session-uploaded images. fflate **v0.8.3** loads as an
   ESM `import()` from the same CDN as Pyodide — no build step, no server, no
   token; it only reads state the editor already holds, so it works in local
   and hosted mode alike. Preferred over **JSZip** (larger, older API). Pinned
   by `download.spec.js` (asserts a real `PK`-signature zip carrying both
   authored files).

3. **Native `<dialog>` — done.** All ~20 `prompt()`/`confirm()`/`alert()`
   call sites now go through `dsForm`/`dsConfirm`/`dsPrompt`/`dsAlert`, a set
   of Promise-returning helpers over a focus-trapped `<dialog>` in the parent
   document (Baseline since March 2022, zero dependency). The win the test
   suite predicted is realized: `+Section` and Cite's "+ new source" are now
   single multi-field forms with inline validation, so a dismissed field no
   longer discards everything already typed (the old sequential-`prompt()` +
   `alert()` failure). A `modalOpen` flag stops an opening dialog from firing
   the in-iframe edit's blur/`finish()`. Pinned by `dialogs.spec.js` (cancel
   is a clean no-op, a validation error keeps the form and its input open, Esc
   cancels) plus the sections/sources/drafts/multiproject specs driving the
   real modals.

4. **`idb-keyval` — done.** Unsaved edits autosave (debounced) to IndexedDB
   via idb-keyval **v6.3.0** and auto-restore on the next boot, so a closed
   tab or a refresh before a network Save no longer loses work; the cache is
   cleared on Save/Publish/Discard. Hosted mode only — local mode's files on
   disk are already the truth. Deliberately ONLY the draft cache moved to
   IndexedDB; the token/user stay in `localStorage`, so `ensureAuth()`/
   `resolveDraft()` keep their synchronous reads (the sync→async migration cost
   noted below is thus avoided). Pinned by `offline-cache.spec.js`.

   *Original assessment, for the record:* drafts and the token live in
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

---

## ProseMirror / Tiptap — No for the prose editors, with one real niche

Assessed 2026-07-19, after slot/box/cell editing moved from a raw `<textarea>`
of markdown to a `contenteditable` surface (`mdToHtml`/`htmlToMd` +
`buildTools` in `edit.html`). That change is what makes the question live: the
editor now *is* a small rich-text editor, so the obvious move is to stop
hand-rolling one.

### The objections that don't hold

Worth clearing these first, because they are the usual reflexes and both are
wrong here:

- **"Too heavy."** Measured, not guessed: ProseMirror core (view, model,
  state, transform, keymap, history, commands) is **~65KB gzipped** from
  esm.sh. Next to the ~30MB Pyodide runtime this editor already downloads,
  that is noise.
- **"No build step."** Every `prosemirror-*` package and `@tiptap/core` ships
  `"type": "module"` with an ESM `module` entry and resolves through esm.sh as
  a plain `import()` — the same mechanism `fflate` and `idb-keyval` already
  use here. Offline is a solved problem too: `sw.js` already precaches
  Pyodide, so it could cache these.

So the decision turns on fit, not cost.

### Why it's still wrong for the prose editors

**Python is the renderer, and its markdown is a deliberately small custom
subset.** `content.py`'s `md_inline()` handles exactly four things — images,
`https?://` links, `**bold**`, `*italic*` — plus `[^id]` footnotes resolved
document-wide, and `block_html()` adds only flat `- `/`N. ` lists and
`#`/`##` headings. `prosemirror-markdown` parses CommonMark via markdown-it,
which is a strictly larger grammar.

That gap is not cosmetic — it breaks the one guarantee this editor exists to
provide. Probed against the current serializer, all of these are correctly
left as **literal text**, because that is exactly what Python will render:

| typed | current editor | why |
|---|---|---|
| `_under_` | literal `_under_` | `md_inline` only matches `*`, never `_` |
| `` `code` `` | literal | no code spans in the grammar |
| `> quote` | literal | no blockquotes |
| `[rel](assets/x.png)` | literal | links must be `https?://` |
| `- a` / `  - nested` | flat two-item list | `block_html` has no nesting |

Under ProseMirror's default markdown these would each become *real* editor
structure — italic, code, a blockquote, a link, a nested list — and then
render as literal text in the PDF. The editor would confidently show
something the report cannot produce. Restricting a PM schema and a markdown-it
instance back down to exactly this subset is possible, but it is
*re-implementing the work that already exists*, on top of a dependency, and
leaves two grammars to keep in sync with `content.py` instead of one.

**What we'd actually be buying is small.** Probed on the real editor, the
structural editing PM is famous for getting right is already correct here,
because Chromium's own `contenteditable` does it and `htmlToMd` normalizes the
result:

- Enter mid-`<li>` splits the list properly → `- alpha` / `- X` / `- beta`.
- Backspace merging a paragraph into one ending in a footnote chip keeps the
  chip intact → `one[^zz]two`. Chromium leaves a junk `<span style=…>` behind,
  but the serializer's unknown-wrapper fallback drops it on commit, so nothing
  reaches `content.md`.

### The two things that are genuinely weak (and are cheap to fix without PM)

1. **No paste handling at all** — there is no `paste` listener, so pasting
   from Word or Google Docs is pure browser default. Nothing corrupts
   (`htmlToMd` keeps text + `b`/`i`/`a`/`img` and strips the rest at commit),
   but pasted headings, tables and nested lists flatten *silently and
   invisibly* until the edit is committed. The fix is ~15 lines and is
   strictly better than what PM gives by default: intercept `paste`, run the
   clipboard HTML through `htmlToMd` → `mdToHtml`, and insert that — so what
   lands on the page is, by construction, exactly what will render.

2. **`document.execCommand` is deprecated** — used in three places (bold,
   italic, `insertLineBreak`). This is the one real long-term risk, and it is
   the strongest pro-PM argument. It is bounded, though: Chromium is the only
   engine this tool targets (the PDF path already hardcodes a Chrome binary),
   and if it ever breaks, replacing two toggles with hand-rolled `Range`
   splitting is tens of lines, not a rewrite.

### Where it WOULD be appropriate

Two places, neither of them today:

1. **Text boxes (`editBox`), if they ever need formatting the report's prose
   doesn't have.** They are the strongest candidate for a specific reason: a
   text box's content lives in **`layout.json`, not `content.md`** — it is the
   editor's own data, not the report's authored prose, and it never reaches
   the bound Google Doc. So it is the one surface whose storage format could
   change without touching the authored text. If boxes ever need per-run
   colour/size, alignment, or nested lists (i.e. real design-tool text), the
   coherent move is to store **ProseMirror JSON** for box content and teach
   `layout.py` to render that to HTML — replacing `block_html` for boxes only.
   That contains the blast radius to one feature and keeps `content.md`'s
   grammar untouched. Until boxes actually need that, it is a large change for
   formatting nobody has asked for.

2. **Multi-user simultaneous editing.** If two people ever need to edit one
   draft at once, `prosemirror-collab` plus its transaction/rebase model is
   the industry answer and hand-rolling operational transforms is not a
   reasonable undertaking. Note this would be a much deeper change than the
   editor alone — the save path is a git commit to a draft branch, not a
   shared document server.

**Verdict: don't adopt now.** Add the paste handler instead — it closes the
one real gap, for ~15 lines and no dependency. Revisit ProseMirror if text
boxes grow real design-tool typography, or if collaborative editing is ever
wanted; and treat `execCommand` breaking in Chromium as the trigger to
reconsider rather than a reason to pre-empt.

Same verdict for **Quill / Slate / Lexical**, and for the same root reason:
they all own the document model, and here Python owns it.
