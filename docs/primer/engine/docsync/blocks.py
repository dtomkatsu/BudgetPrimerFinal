"""Reusable, editor-aware building blocks ANY report renderer can import.

These grew up inside the Budget Primer's renderer and were trapped there — a
new report scaffolded beside it got plain prose and nothing else. Extracted
here they travel with the engine: `graphic()` for a movable/resizable inline
SVG, `card()` for a coloured tile whose title/bullets can optionally be pulled
apart in the editor, and the `is_light_bg()` contrast test they share.

Deliberately zero-stylesheet: every visual rule is inlined on the markup, so a
minimal scaffolded renderer with no CSS of its own gets the same result as the
fully art-directed primer. The classes that ARE emitted (`ds-graphic`,
`ds-detachable`) are the draft editor's behavioural hooks — corner-resize
handles, independent grab inside a movable — not styling.

Usage, from a project renderer:

    from docsync.blocks import graphic, card

    graphic(L, "page1.diagram", '<svg viewBox="0 0 100 60">…</svg>', w=2.0)
    card(C, L, "page1.card.title", "page1.card.bullets", "#52796F",
         detachable=True, min_h=1.8)

The primer's own render_report.py keeps a thin wrapper (its `graphic()`
delegates here), so there is one implementation to maintain.
"""
from __future__ import annotations

import re

from .layout import fill_css, fill_repr


def is_light_bg(hexc) -> bool:
    """True when a fill is light enough to need dark (not white) text.

    An 8-digit fill carries alpha: a half-transparent dark tile shows the white
    page through it and reads light, so the colour is composited over white
    before the luminance test."""
    h = str(hexc).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    if len(h) == 8:
        a = int(h[6:8], 16) / 255
        r, g, b = (v * a + 255 * (1 - a) for v in (r, g, b))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) > 130


def _fit_svg(svg: str) -> str:
    """Make the SVG fill its wrapper (the wrapper carries the width; the
    viewBox keeps the aspect). Styles go inline so no stylesheet is needed —
    only when the tag has none of its own, which is left alone."""
    if re.match(r"\s*<svg[^>]*\bstyle=", svg):
        return svg
    return re.sub(r"<svg\b", '<svg style="display:block;width:100%;height:auto"',
                  svg, count=1)


def graphic(L, el_id: str, svg: str, w: float = 1.5, cls: str = "") -> str:
    """A free-standing SVG the editor can MOVE, RESIZE (proportionally, from
    any corner) and ROTATE like an image — its placement lives in layout.json
    under el_id, so a drag or a resize sticks across rebuilds.

    This is the ONE way to add an SVG a report editor should be able to
    reposition: a bare <svg> in the markup is frozen, invisible to the editor.
    Give every graphic a unique, stable el_id; the SVG MUST carry a viewBox
    (it scales to fill the wrapper); `w` is its default width in inches, which
    applies only until the user resizes — after that layout.json's width wins,
    so a rebuild never overwrites their sizing."""
    klass = ("ds-graphic " + cls).strip()
    sized = L.positions.get(el_id, {}).get("w")
    base = "display:inline-block;vertical-align:middle;line-height:0"
    if w and not sized:
        base += f";width:{w}in"
    return (f"{L.spacer(el_id)}"
            f'<span class="{klass}"{L.attr(el_id, base)}>{_fit_svg(svg)}</span>')


def card(C, L, title_key: str, bullets_key: str, bg, light=None,
         icon: str = "", icon_id: str = "", detachable: bool = False,
         min_h: float | None = None, ink: str = "#2F3E46",
         radius: int = 16) -> str:
    """A coloured tile with a bold title and a bullet list — inline-styled, so
    it looks right in a renderer with no stylesheet.

    title_key / bullets_key are content.md slots (the text stays editable
    prose). The tile itself is movable/recolourable under `card.<bullets_key>`.
    detachable=True renders the title and bullets as their OWN movable objects
    (ds-detachable) laid out inside the tile by default — seed a default group
    in layout.json (["card.<key>", "<title_key>", "<bullets_key>"]) so the
    three move as one until the user Ungroups and pulls a piece out. min_h
    keeps the tile a visible panel after its text is dragged elsewhere.
    An icon (inline SVG string) sits left of the title; give icon_id to make
    the glyph its own movable graphic."""
    el_id = f"card.{bullets_key}"
    if L.refilled(el_id):
        bg = L.fill(el_id)
        light = None                       # re-judge contrast on the new colour
    if light is None:
        light = is_light_bg(fill_repr(bg))
    color = ink if light else "#fff"
    override = L.style(el_id, "")
    style = (f"background:{fill_css(bg)};color:{color};"
             f"border-radius:{radius}px;padding:16px 18px")
    if override:
        style += ";" + override
    if detachable and min_h:
        style += f";min-height:{min_h}in"

    h4_style = "font-size:15px;margin:0 0 8px"
    ico = ""
    if icon:
        ico = (graphic(L, icon_id, icon, w=0.42, cls="card-ico")
               if icon_id else f'<span style="display:inline-block;width:0.42in;'
                               f'vertical-align:middle;line-height:0">{_fit_svg(icon)}</span>')
        h4_style = "display:flex;align-items:center;gap:13px;font-size:20px;line-height:1.13;margin:0 0 12px"

    lis = "".join(f'<li style="font-weight:600;margin:4px 0">{b}</li>'
                  for b in C.list(bullets_key))
    ul = f'<ul{C.ul_attr(bullets_key)} style="margin:0;padding-left:17px">{lis}</ul>'
    title = C.t(title_key)

    if detachable:
        head = (f'{L.spacer(title_key)}<h4 class="ds-detachable"'
                f'{L.attr(title_key, h4_style)}>{ico}{title}</h4>')
        body = (f'{L.spacer(bullets_key)}<div class="ds-detachable"'
                f'{L.attr(bullets_key)}>{ul}</div>')
    else:
        head = f'<h4 style="{h4_style}">{ico}{title}</h4>'
        body = ul
    tag = L.tag(el_id) + L.fill_tag(el_id)
    return (f'{L.spacer(el_id)}<div{tag} style="{style}">{head}{body}</div>')
