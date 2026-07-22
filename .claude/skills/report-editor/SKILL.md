---
name: report-editor
description: How to add or change elements in the Hawaiʻi Budget Primer report so they stay editable in the draft editor — SVGs/graphics/diagrams the user can move & resize, plus text, headings, shapes, images, colours. Use whenever adding, drawing, or restyling anything on a report page in this repo (report2027/), or when the user says an element "should be movable / resizable / editable."
---

# Editing the Budget Primer so elements stay user-editable

This repo's report is rendered by `report2027/tools/render_report.py` and edited
live in the **docsync draft editor**. The editor can move, resize, rotate,
recolour and re-layer elements — but ONLY elements rendered through the right
helper. Raw markup is frozen: the editor has no hook to select it. Your job when
adding anything is to render it so the user can grab it.

## The one rule for SVGs / graphics / diagrams

**Any free-standing SVG, diagram, icon-lockup, badge, or drawn graphic MUST go
through `graphic()`** — never a bare `<svg>` in the markup.

```python
# report2027/tools/render_report.py
{graphic("funding.flow", '<svg viewBox="0 0 200 120" ...>...</svg>', w=2.4)}
```

- `el_id` — unique and **stable** (`<page>.<name>`). It's the key in
  `layout.json`; renaming it orphans wherever the user dragged/sized it.
- The SVG **must carry a `viewBox`** (it scales to fill the wrapper width).
  Use real `fill`/`stroke` colours — inline SVG is recolourable from the editor.
- `w` — default width in inches; it applies only until the user resizes, then
  `layout.json`'s width wins (a rebuild never clobbers their sizing).

The result: the user clicks it, drags to reposition, scales proportionally from
any corner, rotates, and layers it — placement remembered in `layout.json`.

A glyph that belongs *inside* another element (a card-title icon) can also be
made movable — pass `icon_id=` to `card()`, which routes it through `graphic()`.
Small fixed glyphs that shouldn't move stay inline.

## Composing NEW visual elements: separate primitives, grouped — never fused

When the user asks for a new visual (a labelled box, a badge over a shape, a
diagram with a caption), **build it from separate objects and group them** —
do NOT fuse text and background into one element. A fused composite (one div
holding both, or words baked inside an SVG) moves only as a unit and the user
can never pull the text off the shape; a group moves as one **by default** but
Ungroup (⌘⇧G) detaches the pieces. That difference is the point.

The primitives, all authored directly in `report2027/layout.json`:

```jsonc
{
  "shapes": [                       // background panel / accent
    {"id": "funding.note.bg", "page": 9, "kind": "rect",
     "x": 1.0, "y": 7.2, "w": 3.2, "h": 1.1, "fill": "#E8EDE6", "r": 0.12}
  ],
  "boxes": [                        // the words — md is markdown
    {"id": "funding.note", "page": 9, "x": 1.15, "y": 7.35, "w": 2.9,
     "md": "**Note:** special funds are earmarked.", "style": {"size": 11}}
  ],
  "groups": [                       // travel together until the user Ungroups
    ["funding.note.bg", "text.funding.note"]
  ]
}
```

- In `groups` entries (and everywhere the editor names things), a shape is its
  **bare id** (`funding.note.bg`) and a text box is **`text.<id>`**
  (`text.funding.note`).
- Pure art/diagram → `graphic()` in render_report.py; **keep prose OUT of the
  SVG** (labels intrinsic to the art, like axis ticks, are fine — sentences and
  captions are not). Caption → its own text box, grouped with the graphic.
- The report's designed content tiles (`card()`, callouts) are deliberate
  composites — their text lives in content.md and syncs through the pipeline.
  Leave them as they are unless the user explicitly asks to decompose one.

## Making OTHER elements editable

Everything editable shares one hook: **`{L.spacer(el_id)}` before the element +
`{L.attr(el_id)}` on its tag** stamps `data-el` (edit mode only) and applies any
`layout.json` position/size override. The editor then moves/resizes it.

| Want | Use | Handles the user gets |
|---|---|---|
| Free-standing SVG/graphic | `graphic(el_id, svg, w=)` | move, 4-corner proportional resize, rotate |
| Editable prose / heading / caption | `L.attr(el_id)` on the tag + a `data-slot` span (see `C.slot_span`, `C.t`) | click-to-edit text; drag; width resize |
| Photo / raster image | `img_el(el_id, cls, src, alt)` | move, corner resize, rotate, crop, filter, replace |
| Coloured tile with bullets | `card(title, bullets, bg, key=, icon=, icon_id=)` | recolour, move; icon movable if `icon_id` given |
| Rectangle / ellipse / line | added from the editor's Shape button → stored in `layout.json` `shapes` | move, resize, restyle |

`el_id` convention is `<page>.<name>` (e.g. `spent.table1.caption`). Reuse an
existing id only if you mean the same element.

## How placement is stored (layout.json)

`layout.json` is an **overrides layer**: the renderer's design is the default,
and the file only speaks where the user moved/resized/recoloured something. An
empty file = the pristine design. Never hand-place things in it by guessing
inches — let the user drag in the editor, or set a sensible default in
`render_report.py` and let them adjust. `.page` is `overflow:hidden`, so an
element dragged off-page is caught by `Layout.check_bounds()` (a build error),
never silently lost.

## Build, verify, ship

- **`make -C report2027 pub`** is the ONE build command (live server, Save, and
  CI all run it). `report2027/web/index.html` and `docs/primer/` are generated —
  never hand-edit them.
- **Do NOT launch the live server yourself.** "Budget Primer Editor.app" owns
  it (a server started any other way can't reach the keychain, so Push hangs).
  If it needs restarting, ask the user to relaunch the app.
- After adding an editable element, sanity-check the build renders it with its
  `data-el` in edit mode and cleanly (no `data-el`) in publish mode:
  `cd report2027 && DOCSYNC_EDIT=1 python3 tools/render_report.py` then a plain
  `python3 tools/render_report.py`.
- The editor engine (`docsync/`, `serve.py`, `edit.html`) is **vendored from the
  separate `~/primer-editor` repo** — fix editor/tooling bugs THERE first, then
  copy here. Report *content* (pages, prose, the graphics you add) is owned here.
- **Save** commits locally; **Push** sends the branch AND fast-forwards `main`
  (the deploy branch) — every Push publishes to the live site. If a push is
  rejected with "fetch first," CI added a rebuild commit to `main`:
  `git fetch && git merge origin/main`, rebuild, then push both.

## Regression guard

`graphic()` behaviour is covered by `tests/editor/graphic.spec.js` in the
primer-editor repo (inline render, corner-not-width handles, drag-records-
position, resize-writes-width). If you extend the movability system, add or
update a spec there.
