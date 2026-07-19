# Standalone app — scope

Today the editor is a page you're handed a link to: `.../primer/edit.html`,
tied to one project's `engine/` unless you know to add `?project=`. This scopes
turning it into something you'd *open* — an app, with its own front door,
its own files, and a way to get a finished document out. Three explicit asks:
**new files**, **export**, **resize document**. Grounded in what's there today,
then what's missing, then a plan.

> **Status: all four pieces are implemented** (`start.html`/`index.html` naming
> collision caught along the way — see §5). Recap:
> - **B (installable shell):** `manifest.webmanifest` + `sw.js`, registered from
>   both app pages. Three-tier caching (Pyodide CDN forever, app shell
>   stale-while-revalidate, report data/GitHub network-only) — and the real
>   published report (`index.html`) is explicitly excluded, so a reader who
>   never opened the editor is never affected, and one who did never gets a
>   stale copy of what they came here to read.
> - **A (landing page):** `docs/primer/start.html` — a card grid over
>   `projects.json`, "+ New report" opens a modal. Named `start.html`, not
>   `index.html`: that name was already the actual published report.
> - **C (export):** an "Export" button that calls `print()` on the rendered
>   iframe (not the parent page), reusing the print CSS `make pdf` already
>   relies on — no server, no headless Chrome.
> - **D (resize + new-from-template):** page size is chosen **once, at
>   creation**, not as a retrofit on an existing report — see §5 for why the
>   existing Budget Primer's own resize stays explicitly out of scope. A new
>   report picks Letter/A4/Legal in the creation modal; the choice is baked
>   into that project's own generated CSS and manifest, with zero legacy
>   content to re-anchor.
>
> Verified end-to-end in a headless browser: landing page → New Report
> (Git Data API commit sequence, atomic) → redirect → the scaffolded project
> actually boots and renders through Pyodide with the chosen page size,
> editable sections, and the shared Sources panel — plus the full prior
> regression suite (sections/sources/undo/drafts/sign-in/multi-project)
> still green.

---

## 1. What "opening an app" is missing today

- **No front door.** There's no `index.html` for the editor itself — you land
  directly on one project (or the one named by `?project=`). Nothing says
  "here are your documents, pick one or start one."
- **No install / offline.** No web-app manifest, no service worker. It's a
  browser tab, not something you add to a dock or home screen; it needs the
  network for Pyodide (loaded from a CDN, ~30MB) and the GitHub API every time.
- **No document creation.** A "project" in `projects.json` requires a human to
  hand-build an `engine/` directory (a Python renderer, a `content.md`, a
  manifest) and add a registry line. There's no in-app "New" that produces a
  working, empty report.
- **No export.** The only way to get a PDF is `make pdf` on a machine with the
  repo cloned and headless Chrome installed — a developer command, not
  something the person using the web page can do. There's a print-fit
  *warning* (the "page N will be cut off" indicator) but no Download/Export
  button anywhere in the UI.
- **No document resize.** Page size (`8.5in × 11in`) is set in the manifest
  (`page.w`/`page.h`, driving the editor's own JS geometry) but is **also**
  hardcoded separately in `primer.css` (`.page` width/height and the `@page`
  print rule) — two sources of truth that happen to agree today. There is no
  UI to change it, and no code path that would keep both in sync if there were.

---

## 2. Goals

- **A landing page.** Open the app, see your documents (owned + shared),
  create or open one — not "here's a link to a specific report."
- **Feels like an app.** Installable (Add to Home Screen / dock), a name and
  icon, sensible behavior offline (or a clear "you're offline" rather than a
  silent hang).
- **New document, from the app.** Start a blank (or templated) report without
  hand-authoring a Python package.
- **Export.** Download a PDF (and ideally the raw `content.md`/assets) from
  the browser, no local toolchain.
- **Resize the document.** Change page dimensions (Letter/A4/Legal, or
  custom) from the UI, with one source of truth that the renderer, the
  editor's geometry, and the print CSS all read from.
- **Keep everything already built.** Projects registry, drafts/Share/Publish,
  sign-in, undo/redo, sections/sources — all of this is the app's *editing*
  layer; standalone-ness wraps around it, it doesn't replace it.

---

## 3. The four pieces

### A. A landing page / document picker
A new `docs/primer/index.html` (or repurpose the bare-registry list) that:
lists `projects.json` entries as cards (name, maybe a thumbnail), "Open" goes
to `edit.html?project=<id>`, "New" starts the create flow (D). Becomes the
thing you bookmark/install instead of a specific report's editor URL.

- *Effort:* small. It's mostly `projects.json` rendered as a grid instead of
  a `<select>`, plus a New button. No new save/auth logic — reuses `ensureAuth`.

### B. Installable, offline-aware shell
A `manifest.webmanifest` (name, icons, `display: standalone`) + a minimal
service worker that caches the app shell (HTML/CSS/JS, the Pyodide runtime)
so a repeat visit is instant and a dropped connection degrades to "you're
offline, reconnect to save" instead of a silent hang. Editing already needs
the network for GitHub anyway — this isn't full offline editing, just a fast,
installable shell.

- *Effort:* small–medium. Pyodide + wasm caching needs care (~30MB — cache it
  once, don't refetch every load); this is the highest-value, lowest-risk
  piece and worth doing regardless of the rest.

### C. Export (PDF, and the source files)
Move `make pdf`'s logic into the browser: the editor already renders the full
`index.html` locally via Pyodide for every edit, so a `window.print()` (with
the existing print CSS) gets a same-content PDF via the browser's own
print-to-PDF — no server, no headless Chrome. Chrome/Edge's print dialog even
supports "Save as PDF" directly; a "Download PDF" button just opens `print()`
against the rendered iframe with the right media-print styles active, and
possibly the `window.print()` fires *inside* the iframe context. A "Download
source" button zips (or lists) `content.md` + `layout.json` + touched assets
for anyone who wants the raw files.

- *Effort:* small for a "trigger print()" button (CSS already exists);
  medium if pixel-parity with the `make pdf` headless-Chrome output matters
  enough to verify carefully (fonts, page breaks) — browser print and headless
  Chrome print-to-PDF are the same engine family but not guaranteed identical
  down to the pixel.

### D. Resize the document + new-from-template
Two related capabilities:

1. **Change page size for the current report.** A page-size control (Letter /
   A4 / Legal / custom W×H) that writes ONE value the renderer, the editor's
   own geometry, and the print CSS all read from — closing the two-sources-of-
   truth gap above. Concretely: move `8.5in`/`11in` out of `primer.css`'s
   literals into CSS custom properties (`--page-w`, `--page-h`) set from the
   manifest at render time (the Python renderer already stamps template
   values in; this is one more), and have the editor's `PAGE_W_IN`/`PAGE_H_IN`
   read the same manifest field they already read today. A resize is then a
   manifest edit (through the UI) rather than a code change — but every
   existing absolute-positioned box/shape in `layout.json` would need
   re-anchoring (percentage or margin-relative, not raw inches) or a resize
   silently mis-places everything already placed. That re-anchoring is the
   real work here, not the UI control.
2. **New document from a template.** "New" (from A) needs *something* to
   scaffold: a minimal `engine/` — a starter `content.md` with a few `[[slot]]`
   examples, a trivial `render_report.py`, a manifest with a chosen page size
   — committed to a fresh repo (or a fresh top-level folder in an existing
   one) via the GitHub API, using the same auth/commit machinery Save already
   has. Effectively "fork a blank-report template repo," not a from-scratch
   generator.

- *Effort:* (1) is medium-to-large — the CSS/manifest plumbing is small, the
  layout re-anchoring is the real cost and needs its own design pass; a
  simpler first cut is Letter-vs-A4 only (both close enough in aspect ratio
  that re-anchoring is forgiving) before general custom sizes. (2) is
  medium — mostly wiring a template repo through the existing commit helper.

---

## 4. Recommended order

1. **B (installable shell)** first — cheapest, safe, immediately makes it
   *feel* like an app, and every later piece benefits from the caching.
2. **A (landing page)** next — needs nothing new, mostly surfaces what
   `projects.json` already holds; makes "open the app" a real front door.
3. **C (export, print-to-PDF only)** — high value, low risk, no server. Skip
   the "download source zip" half unless someone asks for it.
4. **D.1 (page-size control, Letter/A4 only)** — do this before D.2; a
   template needs *a* page size, so the source of truth should exist first.
   Scope re-anchoring carefully; this is the one piece worth its own design
   review before writing code.
5. **D.2 (new-from-template)** — last, since it depends on D.1's manifest
   plumbing existing, and is the least urgent (one new report is rare next to
   many edits on existing ones).

None of this touches the drafts/Share/Publish/sign-in/sections/sources work
already shipped — it wraps a front door and an output around it.

---

## 5. Implementation notes (what actually shipped, and why)

**`start.html`, not `index.html`.** `docs/primer/index.html` turned out to
already be the actual published, publicly-readable report (built by CI from
`content.md`) — not a spare slot. The landing page lives at `start.html`
instead; `manifest.webmanifest`'s `start_url` points there.

**Page size is a creation-time choice, not a retrofit.** Genuinely resizing
the *existing* Budget Primer report was ruled out for this pass: its renderer
is ~900 lines of pixel-precise SVG figure layout built for Letter (chart
viewBoxes, label positions, table geometry), and I have not verified how deep
that coupling goes beyond `primer.css`'s two literal `8.5in`/`11in`s. Retrofitting
that safely is real, separate, careful work — not something to fold into a
"resize" button without its own review. What ships instead is real and useful:
**a brand-new report** picks its page size once, in the creation modal
(Letter/A4/Legal), baked into that project's own generated renderer and CSS —
zero legacy content, so there's nothing to mis-place.

**A blank project's renderer is genuinely minimal**, not a copy of the Budget
Primer's: it reads `content.md` via the shared, already-generic
`docsync.content.Content` (confirmed to carry zero Budget Primer-specific
logic), assembles any number of `[[extra.page1.*]]` sections — the same
overflow mechanism "+ Section" already uses — and emits basic page/print CSS
parameterized by the chosen size. `docsync/layout.py` is copied in too (its
own header already documents Letter as "a default, not a law" — any report
passes its own size in) because `boot()` unconditionally imports
`docsync.layout` for the font/effect-picker UI, even for a report with no
visual layer yet.

**`EXTRA_PAGES` (the page list "+ Section" offers) moved from a hardcoded
constant to a manifest field** (`"pages": [["id","Label"], …]`), with the
Budget Primer's own list as the default when a manifest declares none — so
existing reports need no changes, but a new report's "+ Section" correctly
offers only the page(s) it actually has, instead of nine Budget-Primer page
names that would mean nothing on a blank report.

**A real gap, disclosed rather than silently left:** every project has a
"true source" location (a working directory, same convention as the Budget
Primer's own `report2027/`) *and* a staged copy under `docs/primer/<base>/
engine/` that the editor fetches before any draft exists — this is the
existing architecture, not something introduced here (`build.yml`
already does this dance for the Budget Primer, watching `report2027/**` and
re-staging on every push to `main`). "New Report" writes both copies
identically at creation time, so a fresh project is immediately viewable and
editable. What it does **not** do is extend `build.yml` to keep re-staging a
NEW project's copy after subsequent publishes — that's a real, bounded
follow-up, not done here. In practice this rarely bites: anyone actively
editing a report always reads live from GitHub the moment they have a draft
(resumed or fresh), which is most of a new report's early activity; the gap
only shows for a first-time visitor loading a project with no draft in
progress, after a publish that outpaced the staging step.
