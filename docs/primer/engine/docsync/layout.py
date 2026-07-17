"""Layout overrides: positions and shapes, as data.

The report's design lives in the renderer, and that is what keeps it a designed
artifact rather than a blank canvas — twelve pages that stay twelve pages
because only text varies. This module does not change that. It adds a thin
layer on top: where an override exists the renderer honours it, and everywhere
else the code's own design stands.

So a dragged box is one line of JSON, reviewable in a diff and revertable by
deleting it, instead of a hand-edit to layout code. With no overrides the file
is empty and the published HTML is byte-for-byte what it always was.

Coordinates are inches from the page's top-left corner, because `.page` is
`position: relative` and absolutely positioned children resolve against it.

    {
      "positions": { "callout.obligated": {"x": 1.2, "y": 3.4, "w": 5.0,
                                            "reserve": 2.7, "z": 1} },
      "shapes": [ {"id":"s1","page":3,"kind":"rect","x":1,"y":2,"w":3,"h":1,
                   "fill":"#6B9E78","z":"back"} ]
    }
"""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path

# One direction only: content.py imports nothing from this package (it takes its
# styler duck-typed), so there is no cycle. A text box is a markdown block that
# happens to be positioned — block_html already renders exactly that for the
# overflow slots, and a second renderer for the same thing would drift.
from .content import block_html

# Letter portrait, because that is what the Budget Primer is. Any report with a
# different page passes its own size in — this is a default, not a law. It is
# the only thing in this package that ever knew about one particular report.
PAGE_W_IN, PAGE_H_IN = 8.5, 11.0
KINDS = ("rect", "ellipse", "line")

# Fonts a report may ask for, with the weights Google will actually serve. An
# allowlist, not free text: a typo'd family falls back to sans-serif in the PDF
# with nothing to catch it, and an unchecked family name would land inside a
# style="…" attribute, where a stray quote ends the attribute. Canva's picker is
# a fixed list too — this is parity, not a compromise.
FONTS = {
    "Barlow":         [400, 500, 600, 700, 800, 900],
    "Source Sans 3":  [300, 400, 600, 700],
    "Playfair Display": [400, 500, 600, 700, 800, 900],
    "Merriweather":   [300, 400, 700, 900],
    "Lora":           [400, 500, 600, 700],
    "Libre Baskerville": [400, 700],
    "Inter":          [300, 400, 500, 600, 700, 800, 900],
    "Roboto":         [300, 400, 500, 700, 900],
    "Open Sans":      [300, 400, 600, 700, 800],
    "Lato":           [300, 400, 700, 900],
    "Montserrat":     [300, 400, 500, 600, 700, 800, 900],
    "Oswald":         [300, 400, 500, 600, 700],
    "Raleway":        [300, 400, 500, 600, 700, 800, 900],
    "Nunito":         [300, 400, 600, 700, 800, 900],
    "Work Sans":      [300, 400, 500, 600, 700, 800],
    "IBM Plex Sans":  [300, 400, 500, 600, 700],
    "IBM Plex Serif": [300, 400, 500, 600, 700],
    "Space Grotesk":  [300, 400, 500, 600, 700],
    "Bebas Neue":     [400],
    "Anton":          [400],
    "Archivo":        [300, 400, 500, 600, 700, 800, 900],
    "Karla":          [300, 400, 500, 600, 700, 800],
    "Rubik":          [300, 400, 500, 600, 700, 800, 900],
    "Cormorant Garamond": [300, 400, 500, 600, 700],
    "Crimson Text":   [400, 600, 700],
}

# What primer.css already asks Google for. The report needs these whether or not
# anything is overridden, and font_link must reproduce the old hardcoded literal
# from exactly this when nothing is.
BRAND_FONTS = {"Barlow": [800, 900], "Source Sans 3": [300, 400, 600, 700]}
BRAND_ITALICS = {"Source Sans 3": [400]}

# Effects. Each is a function from its parameters to CSS, so validation can
# name the ones that exist and the editor can ask which parameters to show.
#
# Two conventions worth stating once:
#  * 0 degrees is 12 o'clock and it goes clockwise — the same convention
#    arc_path() already uses in the renderer. A second convention for the same
#    idea in one repo is a bug waiting to happen.
#  * Offsets and blurs are in em, so a shadow stays proportional when the type
#    is resized instead of detaching from it.
#  * We store ALPHA, not Canva's "transparency". Storing the inverted quantity
#    invites a 1-x slip at every read; the slider can show whatever it likes.
def _rgba(hexc: str, a: float) -> str:
    h = hexc.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a:g})"


def _xy(offset: float, deg: float) -> tuple[float, float]:
    rad = math.radians(deg)
    return round(offset * math.sin(rad), 3), round(-offset * math.cos(rad), 3)


def _fx_shadow(e: dict) -> str:
    dx, dy = _xy(e.get("offset", 0.06), e.get("direction", 135))
    c = _rgba(e.get("color", "#2F3E46"), e.get("alpha", 0.45))
    return f'text-shadow:{dx}em {dy}em {e.get("blur", 0.04)}em {c}'


def _fx_lift(e: dict) -> str:
    k = e.get("intensity", 0.5)
    return f'text-shadow:0 {round(k * .5, 3)}em {round(k * 1.2, 3)}em rgba(0,0,0,{round(k * .5, 3)})'


def _fx_hollow(e: dict) -> str:
    return (f'color:transparent;-webkit-text-stroke:{e.get("width", 0.02)}em '
            f'{e.get("color", "#52796F")}')


def _fx_splice(e: dict) -> str:
    dx, dy = _xy(e.get("offset", 0.06), e.get("direction", 135))
    return (f'color:transparent;-webkit-text-stroke:{e.get("width", 0.02)}em '
            f'{e.get("color", "#52796F")};'
            f'text-shadow:{dx}em {dy}em 0 {e.get("shadow", "#95B7A2")}')


def _fx_echo(e: dict) -> str:
    dx, dy = _xy(e.get("offset", 0.06), e.get("direction", 135))
    c = e.get("color", "#52796F")
    return (f'text-shadow:{dx}em {dy}em 0 {_rgba(c, .5)},'
            f'{round(dx * 2, 3)}em {round(dy * 2, 3)}em 0 {_rgba(c, .3)}')


def _fx_glitch(e: dict) -> str:
    dx, dy = _xy(e.get("offset", 0.04), e.get("direction", 90))
    return (f'text-shadow:{round(-dx, 3)}em {round(-dy, 3)}em 0 {e.get("color", "#00E5FF")},'
            f'{dx}em {dy}em 0 {e.get("shadow", "#FF00A0")}')


def _fx_neon(e: dict) -> str:
    c = e.get("color", "#6B9E78")
    k = e.get("intensity", 1.0)
    return (f'color:{c};text-shadow:0 0 {round(.08 * k, 3)}em {c},'
            f'0 0 {round(.25 * k, 3)}em {c},0 0 {round(.6 * k, 3)}em {_rgba(c, .7)}')


EFFECTS = {"shadow": _fx_shadow, "lift": _fx_lift, "hollow": _fx_hollow,
           "splice": _fx_splice, "echo": _fx_echo, "glitch": _fx_glitch,
           "neon": _fx_neon}

# Which knobs each effect actually uses — the editor shows only these, so no
# control is ever offered that does nothing.
EFFECT_PARAMS = {
    "shadow": ["offset", "direction", "blur", "alpha", "color"],
    "lift":   ["intensity"],
    "hollow": ["width", "color"],
    "splice": ["width", "offset", "direction", "color", "shadow"],
    "echo":   ["offset", "direction", "color"],
    "glitch": ["offset", "direction", "color", "shadow"],
    "neon":   ["intensity", "color"],
}

ALIGNS = ("left", "center", "right", "justify")
CASES = ("none", "upper", "lower", "title")


def _hex(v, where: str) -> str:
    if not isinstance(v, str) or not re.fullmatch(r"#[0-9a-fA-F]{3,8}", v):
        raise LayoutError(f"{where}: {v!r} is not a hex colour")
    return v


def text_css(st: dict) -> str:
    """One text style -> the CSS declarations it means.

    A module function, not a method, because the editor calls it through Pyodide
    to preview a slider without a full re-render. One implementation of what a
    style means; a JavaScript twin would drift from this one silently and
    forever.

    Returns "" for an empty style, which is what keeps an unstyled report
    byte-identical to the one that shipped before any of this existed.
    """
    if not st:
        return ""
    out = []
    if st.get("font"):
        # Single quotes: this lands inside style="…", so a double quote here
        # would end the attribute and the rest of the style would become stray
        # markup. Family names are allowlisted, so no apostrophe can appear.
        out.append(f"font-family:'{st['font']}'")
    if st.get("size"):
        out.append(f'font-size:{st["size"]}px')
    if st.get("weight"):
        out.append(f'font-weight:{int(st["weight"])}')
    if st.get("italic"):
        out.append("font-style:italic")
    if st.get("underline"):
        out.append("text-decoration:underline")
    if st.get("color"):
        out.append(f'color:{st["color"]}')
    if st.get("tracking") is not None:
        out.append(f'letter-spacing:{st["tracking"]}px')
    if st.get("leading") is not None:
        out.append(f'line-height:{st["leading"]}')
    case = st.get("case")
    if case and case != "none":
        out.append("text-transform:" + {"upper": "uppercase", "lower": "lowercase",
                                        "title": "capitalize"}[case])
    fx = st.get("effect")
    if fx and fx.get("kind"):
        # After colour, deliberately: hollow and splice hollow the glyph out, so
        # they must win over a colour the same style also set.
        out.append(EFFECTS[fx["kind"]](fx))
    if st.get("align"):
        out.append(f'text-align:{st["align"]}')
        # text-align does nothing to an inline box, and the inline slots are
        # spans. Give it a box to align within — but only when alignment was
        # actually asked for, so nothing else grows a width it never had.
        out.append("display:inline-block;width:100%")
    return ";".join(out)


def _check_text(st: dict, where: str) -> None:
    """A bad style must fail here, at load, like a bad layer does — not reach
    the page as a silently ignored declaration."""
    fam = st.get("font")
    if fam is not None:
        if fam not in FONTS:
            raise LayoutError(
                f"{where}: {fam!r} is not a font this report can load. "
                f"One of: {', '.join(sorted(FONTS))}")
        w = st.get("weight")
        if w is not None and int(w) not in FONTS[fam]:
            raise LayoutError(
                f"{where}: {fam} has no weight {w} — it would be faked by the "
                f"browser. One of: {FONTS[fam]}")
    if st.get("align") and st["align"] not in ALIGNS:
        raise LayoutError(f"{where}: align {st['align']!r} must be one of "
                          f"{', '.join(ALIGNS)}")
    if st.get("case") and st["case"] not in CASES:
        raise LayoutError(f"{where}: case {st['case']!r} must be one of "
                          f"{', '.join(CASES)}")
    if st.get("color"):
        _hex(st["color"], where + ".color")
    for k in ("size", "tracking", "leading"):
        if st.get(k) is not None:
            _num(st[k], f"{where}.{k}")
    # `is not None`, not truthiness: an empty effect object is falsy, so a bare
    # "effect": {} would skip every check below and pass as a no-op rather than
    # as the malformed thing it is.
    fx = st.get("effect")
    if fx is not None:
        if not isinstance(fx, dict) or not fx.get("kind"):
            raise LayoutError(f"{where}: effect needs a 'kind'")
        if fx["kind"] not in EFFECTS:
            raise LayoutError(f"{where}: effect {fx['kind']!r} must be one of "
                              f"{', '.join(sorted(EFFECTS))}")
        for c in ("color", "shadow"):
            if fx.get(c):
                _hex(fx[c], f"{where}.effect.{c}")
        a = fx.get("alpha")
        if a is not None and not (0 <= float(a) <= 1):
            raise LayoutError(f"{where}: effect alpha {a} is not a fraction "
                              f"between 0 and 1")
        for k in ("offset", "direction", "blur", "intensity", "width"):
            if fx.get(k) is not None:
                _num(fx[k], f"{where}.effect.{k}")


class LayoutError(RuntimeError):
    """Raised when an override could not produce a sane page."""


def _z(s: dict) -> int:
    """Layer of a shape. Accepts the old back/front words so existing files
    keep working, but everything speaks integers now."""
    z = s.get("z", -1)
    if z == "back":
        return -1
    if z == "front":
        return 2
    try:
        return int(z)
    except (TypeError, ValueError):
        raise LayoutError(f"shape '{s.get('id')}': z {z!r} is not a layer number")


def _num(v, where: str) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        raise LayoutError(f"{where}: {v!r} is not a number")


def _alpha(v, where: str) -> float:
    a = _num(v, where)
    if not 0 <= a <= 1:
        raise LayoutError(f"{where}: {v} is not a fraction between 0 and 1")
    return a


def _check_shadow(sh, where: str) -> None:
    if not isinstance(sh, dict):
        raise LayoutError(f"{where}: expected a shadow object")
    for k in ("offset", "direction", "blur"):
        if sh.get(k) is not None:
            _num(sh[k], f"{where}.{k}")
    if sh.get("alpha") is not None:
        _alpha(sh["alpha"], f"{where}.alpha")
    if sh.get("color"):
        _hex(sh["color"], f"{where}.color")


def shadow_css(sh: dict) -> str:
    """An element shadow -> its box-shadow value. Inches, not em: a box's
    shadow belongs to the page's geometry, not to a font size it does not
    have. Direction shares the clock convention every other angle here uses.
    Module-level so the editor can preview a slider through the same code
    that will render the committed page."""
    dx, dy = _xy(sh.get("offset", 0.04), sh.get("direction", 135))
    c = _rgba(sh.get("color", "#2F3E46"), sh.get("alpha", 0.35))
    return f'{dx}in {dy}in {sh.get("blur", 0.06)}in {c}'


def shape_shadow_css(sh: dict) -> str:
    """The same shadow as a drop-shadow() filter, for SVG shapes — box-shadow
    follows the box, and a shape is not its bounding box.

    The units are the trap. The shape layer's viewBox is in INCHES (1 user
    unit = 1in), and Chrome resolves CSS filter lengths on SVG children as
    user units at 1px = 1 unit — so "0.06in" becomes 96 units: a
    five-and-a-half-INCH blur that swallowed half a page in testing. The inch
    values are therefore written with a px suffix, which lands them as the
    inches they mean."""
    dx, dy = _xy(sh.get("offset", 0.04), sh.get("direction", 135))
    c = _rgba(sh.get("color", "#2F3E46"), sh.get("alpha", 0.35))
    return f'filter:drop-shadow({dx}px {dy}px {sh.get("blur", 0.04)}px {c})'


class Layout:
    def __init__(self, path: Path, page: tuple[float, float] = (PAGE_W_IN, PAGE_H_IN)):
        self.path = path
        self.page_w, self.page_h = page
        raw = {}
        if path.exists():
            try:
                raw = json.loads(path.read_text() or "{}")
            except json.JSONDecodeError as e:
                raise LayoutError(f"{path.name}: not valid JSON — {e}")
        self.positions = raw.get("positions") or {}
        self.shapes = raw.get("shapes") or []
        self.text = raw.get("text") or {}
        self.boxes = raw.get("boxes") or []
        self.fills = raw.get("fill") or {}
        # Editor affordance only: ids the editor refuses to drag. The renderer
        # never reads it, so it cannot move a byte of the published page — it
        # is validated so a hand-edit cannot quietly disable the lock.
        self.locked = raw.get("locked") or []
        self._validate()

    def _validate(self):
        for el, p in self.positions.items():
            for k in ("x", "y"):
                if k not in p:
                    raise LayoutError(f"position '{el}' has no '{k}'")
                _num(p[k], f"position '{el}'.{k}")
            if p.get("rot") is not None:
                _num(p["rot"], f"position '{el}'.rot")
            if p.get("alpha") is not None:
                _alpha(p["alpha"], f"position '{el}'.alpha")
        seen = set()
        for i, s in enumerate(self.shapes):
            where = f"shape #{i + 1}"
            sid = s.get("id")
            if not sid:
                raise LayoutError(f"{where}: needs an 'id'")
            if sid in seen:
                raise LayoutError(f"{where}: duplicate id '{sid}'")
            seen.add(sid)
            if s.get("kind") not in KINDS:
                raise LayoutError(
                    f"{where}: kind {s.get('kind')!r} must be one of {', '.join(KINDS)}")
            if not isinstance(s.get("page"), int):
                raise LayoutError(f"{where}: 'page' must be a page number")
            for k in ("x", "y", "w", "h"):
                _num(s.get(k), f"{where}.{k}")
            # These land verbatim inside SVG attributes: a malformed value
            # does not error, it renders an invisible shape.
            for k in ("fill", "stroke"):
                if s.get(k) not in (None, "none"):
                    _hex(s[k], f"{where}.{k}")
            if s.get("rot") is not None:
                _num(s["rot"], f"{where}.rot")
            if s.get("alpha") is not None:
                _alpha(s["alpha"], f"{where}.alpha")
            if s.get("shadow") is not None:
                _check_shadow(s["shadow"], f"{where}.shadow")
            _z(s)          # a bad layer must fail at load, not mid-render
        for el, p in self.positions.items():
            if "z" in p and not isinstance(p["z"], int):
                raise LayoutError(f"position '{el}': z {p['z']!r} is not a layer number")
        for key, st in self.text.items():
            if not isinstance(st, dict):
                raise LayoutError(f"text '{key}': expected a style object")
            _check_text(st, f"text '{key}'")
        for el, c in self.fills.items():
            _hex(c, f"fill '{el}'")
        if not isinstance(self.locked, list) or any(
                not isinstance(x, str) or not x for x in self.locked):
            raise LayoutError("locked: expected a list of element ids")
        for i, b in enumerate(self.boxes):
            where = f"box #{i + 1}"
            bid = b.get("id")
            if not bid:
                raise LayoutError(f"{where}: needs an 'id'")
            # One namespace with shapes: the editor resolves an id to a thing by
            # searching both, so a collision makes the right-click menu act on
            # whichever it happens to find first.
            if bid in seen:
                raise LayoutError(f"{where}: duplicate id '{bid}' — already a shape")
            seen.add(bid)
            if not isinstance(b.get("page"), int):
                raise LayoutError(f"{where}: 'page' must be a page number")
            for k in ("x", "y", "w"):
                _num(b.get(k), f"{where}.{k}")
            if not str(b.get("md", "")).strip():
                raise LayoutError(f"{where}: has no text — 'md' is empty")
            if "z" in b and not isinstance(b["z"], int):
                raise LayoutError(f"{where}: z {b['z']!r} is not a layer number")
            if b.get("fill"):
                _hex(b["fill"], f"{where}.fill")
            if b.get("rot") is not None:
                _num(b["rot"], f"{where}.rot")
            if b.get("alpha") is not None:
                _alpha(b["alpha"], f"{where}.alpha")
            if b.get("shadow") is not None:
                _check_shadow(b["shadow"], f"{where}.shadow")
            if b.get("style"):
                _check_text(b["style"], f"{where}.style")

    # ---- positions -------------------------------------------------------

    def _style(self, p: dict) -> str:
        s = f'position:absolute;left:{p["x"]}in;top:{p["y"]}in'
        if p.get("w"):
            s += f';width:{p["w"]}in'
        # Height is opt-in. A text box with a fixed height either clips its
        # words or leaves a hole when the prose changes, so only things whose
        # size is their content — images, shapes — should carry one.
        if p.get("h"):
            s += f';height:{p["h"]}in'
        # z is an integer layer: below 0 sits under the text, above 0 over it.
        s += f';z-index:{int(p.get("z", 1))}'
        if p.get("rot"):
            s += f';transform:rotate({p["rot"]}deg)'
        if p.get("alpha") is not None:
            s += f';opacity:{p["alpha"]:g}'
        return s

    def attr(self, el_id: str, extra: str = "") -> str:
        """Attributes for an element with no style of its own.

        data-el is stamped only while editing, so the published build carries no
        editing scaffolding; the style appears only when the element has
        actually been moved. `extra` is for declarations the call site computed
        (a recoloured callout's background) — merged here because an element
        with two style attributes silently keeps only the first.
        """
        bits = []
        if os.environ.get("DOCSYNC_EDIT"):
            bits.append(f'data-el="{el_id}"')
        p = self.positions.get(el_id)
        css = self._style(p) if p else ""
        both = ";".join(x for x in (css, extra) if x)
        if both:
            bits.append(f'style="{both}"')
        return (" " + " ".join(bits)) if bits else ""

    def spacer(self, el_id: str) -> str:
        """Hold the place of an element that has been moved away.

        Positioning something absolutely takes it out of the flow, so whatever
        followed it slides up into the gap — move the logo and the title beneath
        it jumps. That is never what someone dragging one thing means to do, so
        the vacated height stays reserved and its neighbours stay put.

        'reserve' is only recorded for elements that were in the flow to begin
        with; an element that was already absolute (a lifecycle callout)
        reserves nothing, because it never occupied flow space. It is a
        different thing from 'h', which is how tall the element should be drawn.
        """
        p = self.positions.get(el_id)
        if not p or not p.get("reserve"):
            return ""
        return (f'<div class="ds-spacer" style="height:{p["reserve"]}in"'
                f' aria-hidden="true"></div>')

    def tag(self, el_id: str) -> str:
        """Just the data-el hook, for elements that already carry a style of
        their own and must merge the override into it rather than grow a second
        style attribute."""
        return f' data-el="{el_id}"' if os.environ.get("DOCSYNC_EDIT") else ""

    def style(self, el_id: str, default: str = "") -> str:
        """For elements the renderer already positions itself (the lifecycle
        callouts): the override wins, otherwise the computed placement stands."""
        p = self.positions.get(el_id)
        return self._style(p) if p else default

    def moved(self, el_id: str) -> bool:
        return el_id in self.positions

    # ---- text ------------------------------------------------------------

    def text_style(self, key: str) -> str:
        """The CSS for one slot's text, or "" when it was never styled."""
        return text_css(self.text.get(key) or {})

    def text_attr(self, key: str) -> str:
        """ style="…" for a slot, or "" — never style="", which would change
        the bytes of a report nobody has styled."""
        css = self.text_style(key)
        return f' style="{css}"' if css else ""

    def styled(self, key: str) -> bool:
        return bool(self.text.get(key))

    def unknown_text_keys(self, styleable: set) -> list:
        """Styles aimed at slots the report cannot carry a style on.

        The renderer builds a few slots into a string before they reach the page
        (a caption that gets sliced, a label inside SVG). A style on those does
        nothing at all — silently. Better to say so.
        """
        return sorted(k for k in self.text if k not in styleable)

    def font_link(self) -> str:
        """The Google Fonts <link>, covering the brand's fonts plus anything a
        style asks for.

        It was a hardcoded literal. It has to keep producing that exact literal
        when nothing is styled — the head of an unstyled report must not move a
        byte — while also actually requesting a weight someone picks. Today
        Barlow 400 would simply be faked; now it is fetched.
        """
        want: dict[str, set] = {f: set(ws) for f, ws in BRAND_FONTS.items()}
        ital: dict[str, set] = {f: set(ws) for f, ws in BRAND_ITALICS.items()}
        for st in self.text.values():
            fam = st.get("font")
            if not fam:
                continue
            w = int(st.get("weight") or 400)
            (ital if st.get("italic") else want).setdefault(fam, set()).add(w)
            want.setdefault(fam, set())
        parts = []
        for fam in list(BRAND_FONTS) + [f for f in want if f not in BRAND_FONTS]:
            roman, italic = sorted(want.get(fam, set())), sorted(ital.get(fam, set()))
            if not roman and not italic:
                continue
            name = fam.replace(" ", "+")
            if italic:
                axis = ";".join([f"0,{w}" for w in roman] + [f"1,{w}" for w in italic])
                parts.append(f"family={name}:ital,wght@{axis}")
            else:
                parts.append(f"family={name}:wght@{';'.join(str(w) for w in roman)}")
        return ('<link href="https://fonts.googleapis.com/css2?'
                + "&".join(parts) + '&display=swap" rel="stylesheet">')

    # ---- fills -----------------------------------------------------------

    def fill(self, el_id: str, default: str = "") -> str:
        """The colour an element should actually be painted.

        This has to be answered in Python, not patched onto the DOM afterwards,
        and that is not a preference. is_light_bg() reads a tile's luminance at
        build time to decide whether its text is white or charcoal — and the
        footnote pills ride the same class. Recolour a tile in the browser and
        that decision does not re-run: you get white text on a pale tile, which
        is not "wrong colour", it is invisible.
        """
        return self.fills.get(el_id) or default

    def refilled(self, el_id: str) -> bool:
        return el_id in self.fills

    def fill_tag(self, el_id: str) -> str:
        """The editor's right-click hook for recolourable surfaces.

        The editor must not carry a list of what is fillable — that would be
        report knowledge inside a generic tool, and the first new report would
        prove it wrong. The renderer stamps data-fill on exactly the elements
        whose colour it actually consults, so the page itself is the contract.
        Edit mode only, like data-el.
        """
        return f' data-fill="{el_id}"' if os.environ.get("DOCSYNC_EDIT") else ""

    def fill_attr(self, el_id: str) -> str:
        """fill_tag plus the background itself, for surfaces whose colour lives
        in CSS rather than in an inline style the renderer already writes (a
        page section). Emits nothing when unfilled outside edit mode, so the
        published bytes cannot move."""
        bits = []
        if os.environ.get("DOCSYNC_EDIT"):
            bits.append(f'data-fill="{el_id}"')
        if self.refilled(el_id):
            bits.append(f'style="background:{self.fills[el_id]}"')
        return (" " + " ".join(bits)) if bits else ""

    # ---- free-floating text ---------------------------------------------

    def text_boxes(self, page: int) -> str:
        """Text that belongs to the layout rather than to the prose.

        A slot says what the report always says; a box is a note someone put on
        one page. That is why it lives here and not in content.md — and the
        price of that is real: it never reaches the bound Google Doc, so an
        editor working there will never see it.

        No height, deliberately: the same reason a text slot has none. A box
        with a pinned height either clips its words or leaves a hole the moment
        they change. Its bottom is the fit check's problem.
        """
        mine = [b for b in self.boxes if b.get("page") == page]
        if not mine:
            return ""
        out = []
        for b in mine:
            css = (f'position:absolute;left:{b["x"]}in;top:{b["y"]}in;'
                   f'width:{b["w"]}in;z-index:{int(b.get("z", 2))}')
            if b.get("fill"):
                # A background needs breathing room or the words sit on its
                # edge; padding only when filled, so a plain box's text keeps
                # sitting exactly where it was put.
                css += f';background:{b["fill"]};padding:.08in .12in;border-radius:8px'
            if b.get("rot"):
                css += f';transform:rotate({b["rot"]}deg)'
            if b.get("alpha") is not None:
                css += f';opacity:{b["alpha"]:g}'
            if b.get("shadow"):
                css += f';box-shadow:{shadow_css(b["shadow"])}'
            style = text_css(b.get("style") or {})
            tag = f' data-el="text.{b["id"]}"' if os.environ.get("DOCSYNC_EDIT") else ""
            out.append(f'<div class="ds-textbox"{tag} '
                       f'style="{css}{";" + style if style else ""}">'
                       f'{block_html(b["md"])}</div>')
        return "".join(out)

    def box(self, box_id: str) -> dict | None:
        return next((b for b in self.boxes if b.get("id") == box_id), None)

    # ---- shapes ----------------------------------------------------------

    def layer(self, page: int) -> str:
        """Shapes for one page, grouped into one SVG per layer. Empty when there
        are none, so a report without shapes renders exactly as before."""
        mine = [s for s in self.shapes if s.get("page") == page]
        if not mine:
            return ""
        by_z: dict[int, list] = {}
        for s in mine:
            by_z.setdefault(_z(s), []).append(s)
        return "".join(self._svg(by_z[z], z) for z in sorted(by_z))

    def _svg(self, shapes: list, z: int) -> str:
        body = "".join(self._shape(s) for s in shapes)
        return (f'<svg class="shape-layer" style="position:absolute;left:0;top:0;'
                f'width:{self.page_w}in;height:{self.page_h}in;pointer-events:none;'
                f'z-index:{z}" viewBox="0 0 {self.page_w} {self.page_h}">{body}</svg>')

    def _shape(self, s: dict) -> str:
        x, y, w, h = (float(s[k]) for k in ("x", "y", "w", "h"))
        fill = s.get("fill", "none")
        stroke = s.get("stroke", "none")
        sw = s.get("sw", 0.02)
        common = (f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
                  f'data-shape="{s["id"]}"')
        # Rotation turns about the shape's own centre; the viewBox is in
        # inches, so the pivot is plain geometry. Opacity and shadow ride the
        # same node — a wrapping <g> would put a second element between the
        # editor's data-shape lookups and the thing they mean.
        if s.get("rot"):
            common += (f' transform="rotate({s["rot"]} '
                       f'{round(x + w / 2, 4)} {round(y + h / 2, 4)})"')
        if s.get("alpha") is not None:
            common += f' opacity="{s["alpha"]:g}"'
        if s.get("shadow"):
            common += f' style="{shape_shadow_css(s["shadow"])}"'
        if s["kind"] == "rect":
            r = s.get("r", 0)
            return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" {common}/>'
        if s["kind"] == "ellipse":
            return (f'<ellipse cx="{x + w / 2}" cy="{y + h / 2}" rx="{w / 2}" '
                    f'ry="{h / 2}" {common}/>')
        return f'<line x1="{x}" y1="{y}" x2="{x + w}" y2="{y + h}" {common}/>'

    # ---- guardrail -------------------------------------------------------

    def check_bounds(self) -> list[str]:
        """Positions and shapes that fall outside the page.

        `.page` is `overflow: hidden`, so a bad drag does not look broken — the
        content is simply gone. Nothing else would catch that, which is exactly
        why this is a hard failure rather than a warning.

        A rotated element is judged by its rotated bounding box — the corners
        are what get clipped, and at 45 degrees they stand well proud of the
        unrotated frame. That needs a height; where one is not stored (flowed
        prose), the unrotated checks stand and the fit meter owns the rest.
        """
        def rot_aabb(x, y, w, h, deg):
            cx, cy = x + w / 2, y + h / 2
            rad = math.radians(deg)
            hw = abs(w / 2 * math.cos(rad)) + abs(h / 2 * math.sin(rad))
            hh = abs(w / 2 * math.sin(rad)) + abs(h / 2 * math.cos(rad))
            return cx - hw, cy - hh, cx + hw, cy + hh

        bad = []
        for el, p in self.positions.items():
            x, y = float(p["x"]), float(p["y"])
            if not (0 <= x <= self.page_w) or not (0 <= y <= self.page_h):
                bad.append(f"'{el}' sits at {x}in,{y}in — off the "
                           f"{self.page_w}x{self.page_h}in page")
            if p.get("w") and x + float(p["w"]) > self.page_w + 0.01:
                bad.append(f"'{el}' is {p['w']}in wide at x={x}in — "
                           f"{x + float(p['w']) - self.page_w:.2f}in past the right edge")
            if p.get("h") and y + float(p["h"]) > self.page_h + 0.01:
                bad.append(f"'{el}' is {p['h']}in tall at y={y}in — "
                           f"{y + float(p['h']) - self.page_h:.2f}in past the bottom edge")
            if p.get("rot") and p.get("w") and p.get("h"):
                x1, y1, x2, y2 = rot_aabb(x, y, float(p["w"]), float(p["h"]),
                                          float(p["rot"]))
                if x1 < -0.01 or y1 < -0.01 or x2 > self.page_w + 0.01 \
                        or y2 > self.page_h + 0.01:
                    bad.append(f"'{el}' rotated {p['rot']}° swings past the page edge")
        for b in self.boxes:
            x, y, w = (float(b[k]) for k in ("x", "y", "w"))
            if x < 0 or y < 0 or x > self.page_w or y > self.page_h:
                bad.append(f"text box '{b['id']}' sits off page {b['page']}")
            elif x + w > self.page_w + 0.01:
                bad.append(f"text box '{b['id']}' is {w}in wide at x={x}in — "
                           f"{x + w - self.page_w:.2f}in past the right edge")
        for s in self.shapes:
            x, y, w, h = (float(s[k]) for k in ("x", "y", "w", "h"))
            if s.get("rot"):
                x1, y1, x2, y2 = rot_aabb(x, y, w, h, float(s["rot"]))
                if x1 < -0.01 or y1 < -0.01 or x2 > self.page_w + 0.01 \
                        or y2 > self.page_h + 0.01:
                    bad.append(f"shape '{s['id']}' rotated {s['rot']}° swings "
                               f"past page {s['page']}")
            elif x < 0 or y < 0 or x + w > self.page_w + 0.01 or y + h > self.page_h + 0.01:
                bad.append(f"shape '{s['id']}' extends past page {s['page']}")
        return bad
