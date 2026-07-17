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
import os
from pathlib import Path

PAGE_W_IN, PAGE_H_IN = 8.5, 11.0
KINDS = ("rect", "ellipse", "line")


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


class Layout:
    def __init__(self, path: Path):
        self.path = path
        raw = {}
        if path.exists():
            try:
                raw = json.loads(path.read_text() or "{}")
            except json.JSONDecodeError as e:
                raise LayoutError(f"{path.name}: not valid JSON — {e}")
        self.positions = raw.get("positions") or {}
        self.shapes = raw.get("shapes") or []
        self._validate()

    def _validate(self):
        for el, p in self.positions.items():
            for k in ("x", "y"):
                if k not in p:
                    raise LayoutError(f"position '{el}' has no '{k}'")
                _num(p[k], f"position '{el}'.{k}")
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
            _z(s)          # a bad layer must fail at load, not mid-render
        for el, p in self.positions.items():
            if "z" in p and not isinstance(p["z"], int):
                raise LayoutError(f"position '{el}': z {p['z']!r} is not a layer number")

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
        return s

    def attr(self, el_id: str) -> str:
        """Attributes for an element with no style of its own.

        data-el is stamped only while editing, so the published build carries no
        editing scaffolding; the style appears only when the element has
        actually been moved.
        """
        bits = []
        if os.environ.get("DOCSYNC_EDIT"):
            bits.append(f'data-el="{el_id}"')
        p = self.positions.get(el_id)
        if p:
            bits.append(f'style="{self._style(p)}"')
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

    def style(self, el_id: str, default: str = "") -> str:
        """For elements the renderer already positions itself (the lifecycle
        callouts): the override wins, otherwise the computed placement stands."""
        p = self.positions.get(el_id)
        return self._style(p) if p else default

    def moved(self, el_id: str) -> bool:
        return el_id in self.positions

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
                f'width:{PAGE_W_IN}in;height:{PAGE_H_IN}in;pointer-events:none;'
                f'z-index:{z}" viewBox="0 0 {PAGE_W_IN} {PAGE_H_IN}">{body}</svg>')

    def _shape(self, s: dict) -> str:
        x, y, w, h = (float(s[k]) for k in ("x", "y", "w", "h"))
        fill = s.get("fill", "none")
        stroke = s.get("stroke", "none")
        sw = s.get("sw", 0.02)
        common = (f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
                  f'data-shape="{s["id"]}"')
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
        """
        bad = []
        for el, p in self.positions.items():
            x, y = float(p["x"]), float(p["y"])
            if not (0 <= x <= PAGE_W_IN) or not (0 <= y <= PAGE_H_IN):
                bad.append(f"'{el}' sits at {x}in,{y}in — off the "
                           f"{PAGE_W_IN}x{PAGE_H_IN}in page")
            if p.get("w") and x + float(p["w"]) > PAGE_W_IN + 0.01:
                bad.append(f"'{el}' is {p['w']}in wide at x={x}in — "
                           f"{x + float(p['w']) - PAGE_W_IN:.2f}in past the right edge")
            if p.get("h") and y + float(p["h"]) > PAGE_H_IN + 0.01:
                bad.append(f"'{el}' is {p['h']}in tall at y={y}in — "
                           f"{y + float(p['h']) - PAGE_H_IN:.2f}in past the bottom edge")
        for s in self.shapes:
            x, y, w, h = (float(s[k]) for k in ("x", "y", "w", "h"))
            if x < 0 or y < 0 or x + w > PAGE_W_IN + 0.01 or y + h > PAGE_H_IN + 0.01:
                bad.append(f"shape '{s['id']}' extends past page {s['page']}")
        return bad
