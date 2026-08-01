"""Reusable, editor-aware building blocks ANY report renderer can import.

These grew up inside the Budget Primer's renderer and were trapped there — a
new report scaffolded beside it got plain prose and nothing else. Extracted
here they travel with the engine: `graphic()` for a movable/resizable inline
SVG, `card()` for a coloured tile whose title/bullets can optionally be pulled
apart in the editor, `pdf_button()` for the reader-facing "Download PDF" (with
the `print_css()` that makes its output correct), and the `is_light_bg()`
contrast test they share.

Deliberately zero-stylesheet: every visual rule is inlined on the markup, so a
minimal scaffolded renderer with no CSS of its own gets the same result as the
fully art-directed primer. The classes that ARE emitted (`ds-graphic`,
`ds-detachable`) are the draft editor's behavioural hooks — corner-resize
handles, independent grab inside a movable — not styling.

Usage, from a project renderer:

    from docsync.blocks import graphic, card, pdf_button

    graphic(L, "page1.diagram", '<svg viewBox="0 0 100 60">…</svg>', w=2.0)
    card(C, L, "page1.card.title", "page1.card.bullets", "#52796F",
         detachable=True, min_h=1.8)

    # Once, just inside <body> — a reader-facing download that stays in step
    # with the page, plus the print rules that make the PDF come out right.
    pdf_button(L, bg="#52796F")

The primer's own render_report.py keeps a thin wrapper (its `graphic()`
delegates here), so there is one implementation to maintain.
"""
from __future__ import annotations

import os
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


def _in(v) -> str:
    """An inch measurement, without a pointless trailing zero.

    The same size arrives as an int from a renderer's own page=(8.5, 11) and as
    a float from layout.json's {"h": 11}, and "11in" vs "11.0in" in the CSS is
    a diff in generated output that means nothing."""
    return f"{float(v):g}in"


def print_css(L, pad: str = "", link_ink: str = "") -> str:
    """The rules that make a report PRINT as the sheets it was designed as.

    Without these a report prints as what it technically is — a scrolling web
    page — and every "Download PDF" is wrong in the same four ways: the sheet
    carries the browser's own margins on top of the page's, the drop shadow and
    the 24px gutter between pages print as grey bands, nothing forces a break
    at a page boundary so sheet 2 starts halfway down sheet 1, and Chrome drops
    every background colour unless told not to. The renderer that art-directs a
    document cannot be relied on to remember all four, so they live here.

    Emitted as a <style> in the body, which is valid and applies document-wide
    — the same trick layout.py's page_style() uses, and for the same reason: it
    can ride along with a call the renderer is already making.

    `pad` overrides the page's padding for print only, for a report whose
    screen padding is deliberately different from its print margins (the Budget
    Primer's is). Left empty the screen padding stands, which is what a report
    designed at its real size wants. `link_ink` re-colours and underlines links
    for print, off by default: a document whose links are already styled as
    citations does not want them underlined too.
    """
    w = getattr(L, "page_w", 8.5)
    h = getattr(L, "page_h", 11.0)
    # A pageless layout ({"h": null}) is one continuous surface: it gets a
    # width and lets the sheet run, with no fixed height and no forced breaks.
    pageless = bool(getattr(L, "page", None)) and L.page[1] is None
    sheet = f"{_in(w)} auto" if pageless else f"{_in(w)} {_in(h)}"
    box = ["margin:0", "box-shadow:none", "max-width:none"]
    if not pageless:
        # Exact sheets, so N pages print as exactly N sheets. .page is
        # overflow:hidden by convention, so a page whose content genuinely
        # exceeds its height is clipped rather than spilling a near-blank
        # extra sheet — the editor's own "page cut in print" warning is what
        # catches that, before it reaches a PDF.
        box += [f"height:{_in(h)}", "page-break-after:always"]
    pagerule = ";".join(box) + (f";padding:{pad}" if pad else "")
    links = f"a{{color:{link_ink};text-decoration:underline}}" if link_ink else ""
    return (
        f"<style>@page{{size:{sheet};margin:0}}@media print{{"
        # Must hang off a selector — a bare declaration inside @media is
        # invalid and gets dropped silently.
        "*,*::before,*::after{-webkit-print-color-adjust:exact !important;"
        "print-color-adjust:exact !important}"
        "body{background:#fff}"
        # The engine-wide opt-out for on-screen chrome: toolbars, download
        # buttons, tooltips — anything that is part of the web page but not
        # part of the document.
        ".noprint{display:none !important}"
        f".page{{{pagerule}}}"
        ".page:last-child{page-break-after:auto}"
        f"{links}}}</style>")


def pdf_button(L, label: str = "Download PDF", *, bg: str = "#2F3E46",
               ink: str = "#FFFFFF", top: str = "18px", right: str = "18px",
               pad: str = "", link_ink: str = "", css: bool = True) -> str:
    """A screen-only "Download PDF" control, pinned to the upper-right corner.

    Prints through the browser (window.print() -> "Save as PDF") rather than
    linking to a PDF file, which is the Budget Primer's approach and the reason
    it holds up: the download is generated from the page the reader is looking
    at, so it can never go stale, it needs no build step or committed binary,
    it works from any host, and the text stays selectable vector with its links
    live. A pre-rendered PDF beside the page is one content edit away from
    quietly shipping last month's document.

    Carries print_css() with it by default, because a button that produces a
    badly formatted PDF is worse than no button — the two halves are one
    capability. Call once per document; pass css=False for a second button.

    Drawn in the editor too, and it WORKS there: it was hidden at first, then
    drawn but inert — and an inert button that looks clickable reads as broken,
    which is exactly what got reported. In the editor a click posts a message
    up to the parent chrome, which runs the same server-side Chrome export as
    File > Download > PDF — so the button downloads the current draft, unsaved
    edits and all, rather than window.print()-ing the artboard iframe with its
    selection handles and edit affordances baked in.
    """
    sheet = print_css(L, pad=pad, link_ink=link_ink) if css else ""
    edit = bool(os.environ.get("DOCSYNC_EDIT"))
    act = ('onclick="parent.postMessage({ds:\'export-pdf\'},\'*\')" '
           'title="Download this draft as a PDF"' if edit else
           'onclick="window.print()" '
           'title="Opens your browser\'s print dialog — choose Save as PDF"')
    # The ds- class prefix is the editor's "this control stays live" hook:
    # deafenStickyChrome() sets pointer-events:none on every fixed/sticky child
    # of <body> so a report's standing chrome cannot eat canvas clicks — which
    # silently made this button unclickable on the artboard. Real clicks passed
    # straight through it; only synthetic dispatch (which ignores
    # pointer-events) still fired, which is how the breakage got past a test.
    klass = "ds-pdfbtn noprint" if edit else "noprint"
    return sheet + (
        f'<button type="button" class="{klass}" {act} '
        f'style="position:fixed;top:{top};right:{right};z-index:60;'
        f'background:{bg};color:{ink};border:0;border-radius:8px;'
        f'padding:9px 15px;font-family:inherit;font-size:14px;font-weight:700;'
        f'cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.18)">'
        f'↓&nbsp;{label}</button>')


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
    # position:relative from birth: the tile is the coordinate frame for any
    # movable laid out inside it (a detached title or bullets, an icon
    # graphic), and a frame must exist BEFORE anything is saved against it.
    # When the tile was static its pieces pinned against the page; the first
    # move of the tile then made it their containing block and every saved
    # coordinate re-based against it — the text landed displaced by exactly
    # the tile's offset, clipped or white-on-white: "the words disappeared".
    # The override appends after this, so a moved tile's position:absolute
    # still wins (later declaration takes the property).
    style = (f"background:{fill_css(bg)};color:{color};position:relative;"
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
