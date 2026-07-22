---
name: report-editor
description: How to build or change ANY report served by the docsync draft editor so its elements stay user-editable — movable/resizable SVGs and graphics, detachable cards, text, shapes, images, groups, citations. Use when adding, drawing, or restyling anything in a report bound in docsync.yml, or when the user says an element "should be movable / resizable / editable." In this repo that means report2027/.
---

# Building reports the draft editor can edit

Reports bound in `docsync.yml` render through their own `render_report.py` and
are edited live in the **docsync draft editor** (`docsync/editor/edit.html`).
The editor can move, resize, rotate, recolour, group and re-layer elements —
but ONLY elements rendered through the right hook. Raw markup is frozen: the
editor has no handle to select it. When you add anything, render it so the
user can grab it.

## The shared building blocks: `docsync.blocks`

Every project can import the engine's helpers — they are staged into the
browser engine automatically:

```python
from docsync.blocks import graphic, card, is_light_bg

# A movable/resizable/rotatable inline SVG. viewBox REQUIRED; w = default
# width in inches (until the user resizes; then layout.json wins).
{graphic(L, "page1.diagram", '<svg viewBox="0 0 200 120">…</svg>', w=2.4)}

# A coloured tile: bold title + bullets, both content.md slots. detachable=True
# renders title/bullets as their own movables (seed a default group, below).
{card(C, L, "page1.card.title", "page1.card.bullets", "#52796F",
      detachable=True, min_h=1.8)}
```

- `L` is the project's `Layout`, `C` its `Content` — every renderer has both.
- `el_id`s must be unique and STABLE (`<page>.<name>`): they key layout.json;
  renaming one orphans wherever the user dragged it.
- Helpers are zero-stylesheet (styles inlined), so they work in a minimal
  scaffolded renderer with no CSS of its own.
- A project MAY keep bespoke equivalents (the Budget Primer's `card()` is
  CSS-styled); the *behavioural* hooks (`ds-graphic`, `ds-detachable`,
  `data-el`/`data-slot`) are what the editor reads either way.

## The one rule for SVGs / graphics

**Any free-standing SVG, diagram, icon-lockup, badge, or drawn graphic MUST go
through `graphic()`** — never a bare `<svg>` in the markup. Glyphs that live
inside another element and shouldn't move on their own stay inline.

## Making other elements editable

Everything editable shares one hook: `{L.spacer(el_id)}` before the element +
`{L.attr(el_id)}` on its tag stamps `data-el` (edit mode only) and applies any
layout.json position/size override.

| Want | Use | The user gets |
|---|---|---|
| Free-standing SVG/graphic | `blocks.graphic(L, id, svg, w=)` | move, 4-corner proportional resize, rotate |
| Coloured tile with text | `blocks.card(C, L, …, detachable=)` | recolour, move; pieces pull apart if detachable |
| Editable prose / heading | `L.attr(el_id)` on the tag + a slot (`C.t`, `C.slot_span`) | click-to-edit text; drag; width resize |
| Photo / raster image | an `<img>` with `L.attr` (see the primer's `img_el`) | move, corner resize, rotate, crop, replace |
| Rect / ellipse / line / text box / table | user adds from the editor; stored in layout.json | move, resize, restyle |

## Composing NEW visuals: separate primitives, grouped — never fused

Build a labelled box from a layout.json `shapes` rect + a `boxes` text box +
a `groups` entry (`["<shapeId>", "text.<boxId>"]`): it moves as one until the
user hits Ungroup (⌘⇧G) and detaches the text. Never bake sentences inside an
SVG or fuse text + background into one div. For a `card(detachable=True)`,
seed the default group `["card.<bullets_key>", "<title_key>", "<bullets_key>"]`.

## layout.json is an OVERRIDES layer

The renderer's design is the default; layout.json only speaks where the user
moved/resized/recoloured something (`positions`, `shapes`, `boxes`, `tables`,
`groups`, `endnote_order`). An empty file = the pristine design. Don't
hand-place by guessing inches — set a sensible default in the renderer and let
the user drag.

## Moving cited text (footnotes travel with it)

A citation is the literal token `[^source-id]`. Move the sentence WITH its
token — into another slot or a text box's `md` — and endnotes renumber by
first appearance in the new reading order automatically. Mid-move states are
edit-tolerant, publish-strict: an uncited source, a typo'd token (renders a
red ? naming the missing id), and an emptied bullet list all RENDER in edit
mode and REFUSE at publish. Never retype a token by hand — copy it exactly.

## Editing the editor itself (`edit.html`)

Its whole stylesheet is one JS **template literal**: a backtick or `${…}` in a
CSS comment ends the literal early and kills the ENTIRE script — the editor
hangs at "loading the render engine…" with no console error. After ANY
`edit.html` change run a boot test (`npx playwright test boot-errors.spec.js`)
or at least `node --check` its inline script (`tools/test_render.py` does).
An isolated DOM check that a feature works is NOT proof the file still boots.

## Build & serve rules

- Each binding in `docsync.yml` names its ONE build command; run that, never
  hand-edit generated output (the rendered HTML, the staged `<dir>/engine/`).
- Re-stage after engine changes: `python3 -m docsync.stage --id <id>`.
- Never start or kill a dev server the USER owns (a server launched outside
  their login session cannot reach the keychain, so Push breaks) — ask them to
  relaunch their launcher app instead. Test servers on other ports are fine.
- If an editor origin wedges ("localhost won't load", server healthy), the
  escape hatch is `<origin>/reset.html` — it unregisters the service worker,
  drops caches, and reopens the editor.

## Where code lives

The engine (`docsync/`, `edit.html`, `serve.py`, this skill) is canonical in
the **primer-editor** repo; report repos vendor copies. Fix engine bugs there
first, then copy over. Report content (its pages, prose, its renderer's
bespoke design) is owned by each report's repo and never flows back.

---

# Budget Primer specifics (this repo)

- **Build:** `make -C report2027 pub` is the ONE build command (live server,
  Save, CI). `report2027/web/index.html` and `docs/primer/` are generated —
  never hand-edit.
- **Serve:** "Budget Primer Editor.app" owns the live server on :8010. Never
  start/kill it from Claude — ask the user to relaunch the app.
- **Deploy:** Save commits locally; Push sends the current branch AND
  fast-forwards `main` — every Push publishes to the live site. "fetch first"
  rejection = CI added a rebuild commit: `git fetch && git merge origin/main`,
  rebuild, push both.
- **Vendoring:** engine files (docsync/, edit.html, serve.py) come FROM
  `~/primer-editor` — fix there first, copy here. This report's renderer,
  content and design are owned here.
- **Bespoke card():** this report's `card()` in render_report.py is CSS-styled
  (.card in primer.css) and predates docsync.blocks — keep using it here. It
  supports `icon=`/`icon_id=` (movable header glyph) and
  `detachable=True, min_h=` (title/bullets pull apart; seed the default group
  in layout.json: `["card.<key>", "<base>.title", "<key>"]`). `graphic()` here
  delegates to docsync.blocks.
- **Cache:** bump `CACHE_VERSION` in `docs/primer/sw.js` after any
  primer.css/shell change, or returning browsers keep the old stylesheet.
- **Escape hatch:** http://localhost:8010/reset.html un-wedges a stuck editor
  origin (stale service worker / cache).
