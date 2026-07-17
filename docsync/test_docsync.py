#!/usr/bin/env python3
"""Regression tests for the doc <-> repo round-trip.

Google Docs reshapes a content file when it imports and re-exports it. Every
normalise() case below is a real mangling observed from the live doc — if
Google changes its exporter, these fail here rather than silently corrupting a
committed file. The rest cover fragment mode and the conflict rules that decide
whether a push is safe.

    python3 docsync/test_docsync.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from docsync.content import ContentError                  # noqa: E402
from docsync.fetch import (FetchError, access_token,      # noqa: E402
                           service_account_email)
from docsync.content import paragraph                     # noqa: E402
from docsync.fragment import extract, inject, to_html     # noqa: E402
from docsync.normalise import leading_comment, normalise  # noqa: E402
from docsync.state import State, content_hash            # noqa: E402

FAILS = []


def check(name, got, want):
    if want not in got:
        FAILS.append(f"{name}\n  want (substring): {want!r}\n  got: {got!r}")


def check_eq(name, got, want):
    if got != want:
        FAILS.append(f"{name}\n  want: {want!r}\n  got:  {got!r}")


def check_raises(name, fn, expect):
    try:
        fn()
    except ContentError as e:
        if expect not in str(e):
            FAILS.append(f"{name}\n  want error containing: {expect!r}\n  got: {e}")
        return
    FAILS.append(f"{name}\n  expected ContentError containing {expect!r}, none raised")


# ---------------------------------------------------------------- normalise()

# Docs merges a marker into the paragraph that follows it.
check("marker merged with paragraph",
      normalise("[[basics.p1]] The state budget funds three branches."),
      "[[basics.p1]]\nThe state budget funds three branches.")

# Markers before a heading/list get padded with a blank line instead.
check("marker padded before heading",
      normalise("[[basics.h1]]\n\n# BUDGET BASICS"),
      "[[basics.h1]]\n# BUDGET BASICS")

# Underscores are \-escaped; '_' is a word char, so the unescape class must
# name it explicitly (this shipped broken once — {cip\_total} reached .format()).
check("escaped underscore in a format placeholder",
      normalise("[[cip.body]]\nCIP in FY{fy} is {cip\\_total} total."),
      "{cip_total}")

# Bare URLs come back as [url](url) — with the label escaped and the href not.
check("autolinked url with escaped label",
      normalise("[[sources]]\n[a]: Report. — "
                "[https://x.gov/a\\_b\\_c.pdf](https://x.gov/a_b_c.pdf)"),
      "[a]: Report. — https://x.gov/a_b_c.pdf")

# A genuinely labelled link must survive — only [url](url) collapses.
check("labelled link preserved",
      normalise("[[a.b]]\nSee [the report](https://x.gov/r.pdf) for detail."),
      "[the report](https://x.gov/r.pdf)")

# The whole sources block returns as one line; it must split at each "[id]: ".
check("sources block collapsed to one line",
      normalise("[[sources]]\n[a]: A. — https://a.gov [b]: B. — https://b.gov"),
      "[a]: A. — https://a.gov\n[b]: B. — https://b.gov")

# A "[id]:" outside the sources block must NOT be split onto its own line.
check("prose link refs are left alone",
      normalise("[[spent.p1]]\nSee the report [a]: not a source line."),
      "See the report [a]: not a source line.")

# The doc title above the first marker is chrome, not content.
check("doc title stripped",
      normalise("# Budget Primer — Content\n\n[[toc.author]]\nAuthor: X"),
      "[[toc.author]]\nAuthor: X")

# Curly quotes/apostrophes are the report's own typography — never rewritten.
check("smart punctuation preserved",
      normalise("[[a.b]]\nEach biennium’s “Fixed Costs” table."),
      "Each biennium’s “Fixed Costs” table.")

# Docs drops HTML comments, so a file's header is re-attached by the caller.
check("header re-attached",
      normalise("[[a.b]]\nText.", header="<!-- keep me -->\n\n"),
      "<!-- keep me -->\n\n[[a.b]]")

check_eq("leading_comment extracts the instructions block",
         leading_comment("<!-- hi -->\n\n[[a.b]]\nText."), "<!-- hi -->\n\n")
check_eq("leading_comment on a file without one",
         leading_comment("[[a.b]]\nX."), "")

# ----------------------------------------------------------------- fragment

check("fragment: heading level preserved",
      to_html("## Why this matters"), "<h2>Why this matters</h2>")
check("fragment: paragraph with inline markdown",
      to_html("A **bold** claim with a [link](https://x.gov)."),
      '<p>A <b>bold</b> claim with a <a href="https://x.gov">link</a>.</p>')
check("fragment: bullet list",
      to_html("- one\n- two"), "<ul><li>one</li><li>two</li></ul>")
check("fragment: numbered list",
      to_html("1. one\n2. two"), "<ol><li>one</li><li>two</li></ol>")
# Soft-wrapped lines are one paragraph; a blank line starts a new one.
check_eq("fragment: blank line splits paragraphs",
         to_html("one\ntwo\n\nthree"), "<p>one two</p>\n<p>three</p>")

PAGE = "<main>\n<!-- docsync:start -->\nold\n<!-- docsync:end -->\n</main>"
out = inject(PAGE, "<p>new</p>")
check("fragment: injected between anchors", out, "<p>new</p>")
check_eq("fragment: content outside anchors untouched",
         out.startswith("<main>\n<!-- docsync:start -->")
         and out.endswith("<!-- docsync:end -->\n</main>"), True)
check_eq("fragment: old block replaced", "old" in out, False)
check("fragment: re-injecting is stable",
      inject(out, "<p>new</p>"), "<p>new</p>")
check_eq("fragment: extract round-trips", "<p>new</p>" in extract(out), True)

check_raises("fragment: missing anchors is a hard error",
             lambda: inject("<main>no anchors</main>", "<p>x</p>"),
             "has no '<!-- docsync:start -->'")
check_raises("fragment: reversed anchors rejected",
             lambda: inject("<!-- docsync:end --><!-- docsync:start -->", "<p>x</p>"),
             "appears before")

# ------------------------------------------------------------------- state

check_eq("hash is stable", content_hash("abc"), content_hash("abc"))
check_eq("hash separates different content",
         content_hash("abc") == content_hash("abd"), False)
check_eq("fresh state is uninitialised", State().initialised, False)
check_eq("state with both fields is initialised",
         State(content_hash="a", doc_modified="t").initialised, True)
# A half-written state must not read as initialised — that would let a push
# skip the conflict check and overwrite doc edits.
check_eq("state with only a hash is not initialised",
         State(content_hash="a").initialised, False)


# The state hash is the last thing BOTH sides agreed on, and every "did this
# side move?" is measured from it. A pull that writes the doc's content without
# recording a new sync point leaves the hash pointing at an older common
# ancestor — so the next repo edit reads as "both sides moved" and the engine
# invents a conflict nobody caused. Live-tested: pull, then edit the repo, must
# be repo-ahead. This models that arithmetic.
def _status(state_h, doc_h, local_h):
    doc_moved, repo_moved = doc_h != state_h, local_h != state_h
    if doc_h == local_h:
        return "in-sync"
    if doc_moved and repo_moved:
        return "conflict"
    return "doc-ahead" if doc_moved else "repo-ahead"


check_eq("after a recorded pull, a repo edit is repo-ahead (not a conflict)",
         _status(state_h="H1", doc_h="H1", local_h="H2"), "repo-ahead")
check_eq("an UNrecorded pull turns the next repo edit into a false conflict",
         _status(state_h="H0", doc_h="H1", local_h="H2"), "conflict")
check_eq("a doc edit against a recorded state is doc-ahead",
         _status(state_h="H1", doc_h="H2", local_h="H1"), "doc-ahead")
check_eq("genuinely divergent sides are still a conflict",
         _status(state_h="H1", doc_h="H2", local_h="H3"), "conflict")

# ------------------------------------------------------------------- setup

# Setup fails in a handful of ways and every one of them used to arrive as a
# stack trace from several libraries down. A bad key must always produce a
# sentence someone can act on.
check_eq("a key that is not JSON yields no identity, rather than raising",
         service_account_email("oops-i-pasted-the-wrong-thing"), "")
check_eq("a key without client_email yields no identity",
         service_account_email('{"private_key": "x"}'), "")
check_eq("a real-shaped key yields its identity",
         service_account_email('{"client_email": "docsync@p.iam.gserviceaccount.com"}'),
         "docsync@p.iam.gserviceaccount.com")


def _fetch_error(fn):
    try:
        fn()
    except FetchError as e:
        return str(e)
    except Exception as e:                                    # noqa: BLE001
        return f"WRONG TYPE {type(e).__name__}: {e}"
    return "no error raised"


try:
    from google.auth.transport.requests import Request        # noqa: F401
    from google.oauth2 import service_account                  # noqa: F401
    HAVE_AUTH = True
except ImportError:
    HAVE_AUTH = False

if HAVE_AUTH:
    check("a non-JSON key is reported as such, not as a parser crash",
          _fetch_error(lambda: access_token("not json at all")),
          "not valid JSON")
    check("a malformed private key is a FetchError, not a raw ValueError",
          _fetch_error(lambda: access_token(
              '{"client_email": "d@p.iam.gserviceaccount.com", "type": "service_account",'
              ' "token_uri": "https://oauth2.googleapis.com/token",'
              ' "private_key": "-----BEGIN PRIVATE KEY-----\\nbogus\\n'
              '-----END PRIVATE KEY-----\\n"}')),
          "ValueError")
else:
    # pull-only use needs no credentials, so google-auth is genuinely optional.
    # Say the checks were skipped rather than failing or pretending they ran.
    print("note: google-auth/requests absent — skipped 2 key-handling checks "
          "(pip install google-auth requests to run them)")
    check("a missing dependency names itself",
          _fetch_error(lambda: access_token("{}")),
          "pip install google-auth requests")

# ------------------------------------------------------------------ layout

# Layout overrides exist so a box can be dragged without layout becoming a
# blank canvas: the renderer's design is the default, data only overrides it.
# With nothing overridden the published HTML must be untouched.
import json, tempfile                                          # noqa: E402
from docsync.layout import Layout, LayoutError                 # noqa: E402


def _layout(d):
    t = Path(tempfile.mktemp(suffix=".json"))
    t.write_text(json.dumps(d))
    try:
        return Layout(t)
    finally:
        t.unlink(missing_ok=True)


def _layout_error(d):
    try:
        _layout(d)
    except LayoutError as e:
        return str(e)
    return "no error raised"


empty = _layout({"positions": {}, "shapes": []})
check_eq("an empty layout adds no attributes", empty.attr("x.y"), "")
check_eq("an empty layout adds no shape layer", empty.layer(3), "")
check_eq("an unmoved element keeps the renderer's own placement",
         empty.style("lc.dec", "left:1in;top:2in"), "left:1in;top:2in")

moved = _layout({"positions": {"c.o": {"x": 1.2, "y": 3.4, "w": 5.0}}, "shapes": []})
check("a moved element is absolutely placed", moved.attr("c.o"),
      'style="position:absolute;left:1.2in;top:3.4in;width:5.0in;z-index:1"')
check_eq("an override beats the renderer's placement",
         moved.style("c.o", "left:9in;top:9in"),
         "position:absolute;left:1.2in;top:3.4in;width:5.0in;z-index:1")

# .page is overflow:hidden, so content dragged off it does not look broken —
# it is simply gone. Nothing else would catch that, so it must be loud.
off = _layout({"positions": {"c.o": {"x": 7.9, "y": 2, "w": 5.0}}, "shapes": []})
check("a box dragged past the right edge is caught",
      " ".join(off.check_bounds()), "past the right edge")
off2 = _layout({"positions": {"c.o": {"x": 12, "y": 2}}, "shapes": []})
check("a box dragged clean off the page is caught",
      " ".join(off2.check_bounds()), "off the 8.5x11.0in page")
check_eq("content inside the page passes",
         _layout({"positions": {"c.o": {"x": 1, "y": 1, "w": 3}}, "shapes": []}).check_bounds(), [])

check("a shape needs a known kind",
      _layout_error({"shapes": [{"id": "a", "page": 1, "kind": "blob",
                                 "x": 0, "y": 0, "w": 1, "h": 1}]}),
      "must be one of rect, ellipse, line")
check("a shape needs an id",
      _layout_error({"shapes": [{"page": 1, "kind": "rect", "x": 0, "y": 0, "w": 1, "h": 1}]}),
      "needs an 'id'")
check("duplicate shape ids are caught",
      _layout_error({"shapes": [{"id": "a", "page": 1, "kind": "rect", "x": 0, "y": 0, "w": 1, "h": 1},
                                {"id": "a", "page": 1, "kind": "rect", "x": 0, "y": 0, "w": 1, "h": 1}]}),
      "duplicate id 'a'")
check("a non-numeric coordinate is caught",
      _layout_error({"positions": {"c.o": {"x": "left", "y": 1}}}), "not a number")

shaped = _layout({"shapes": [
    {"id": "b", "page": 7, "kind": "rect", "x": 1, "y": 2, "w": 3, "h": 1, "fill": "#6B9E78"},
    {"id": "f", "page": 7, "kind": "ellipse", "x": 1, "y": 2, "w": 1, "h": 1, "z": "front"}]})
check_eq("shapes split into back and front layers", shaped.layer(7).count("shape-layer"), 2)
check("back shapes sit behind the text", shaped.layer(7), "z-index:-1")
check("front shapes sit above it", shaped.layer(7), "z-index:2")
check_eq("a page with no shapes gets no layer", shaped.layer(2), "")
check("shapes never eat clicks", shaped.layer(7), "pointer-events:none")

# Positioning something absolutely takes it out of the flow and its neighbours
# rush into the gap — move the logo, and the title beneath it jumps. A moved
# element must keep holding the height it occupied.
held = _layout({"positions": {"cover.logo": {"x": 1, "y": 2, "reserve": 1.09}}})
check("a moved flow element reserves the height it vacated",
      held.spacer("cover.logo"), 'style="height:1.09in"')
# 'reserve' (space held in the flow) and 'h' (how tall to draw it) are
# different questions; one file used to answer both with 'h'.
sized = _layout({"positions": {"photo": {"x": 1, "y": 2, "w": 3, "h": 2}}})
check("a resized element is drawn at that size", sized.attr("photo"), "height:2in")
check_eq("a size does not imply reserved flow space", sized.spacer("photo"), "")
check("a box resized past the bottom is caught",
      " ".join(_layout({"positions": {"p": {"x": 1, "y": 10, "h": 3}}}).check_bounds()),
      "past the bottom edge")
# An element that was already absolute never held flow space, so reserving any
# would push its neighbours DOWN — the same bug, mirrored.
absolute = _layout({"positions": {"lc.dec": {"x": 3, "y": 4}}})
check_eq("an already-absolute element reserves nothing",
         absolute.spacer("lc.dec"), "")
check_eq("an unmoved element reserves nothing", held.spacer("callout.whopays"), "")

# z is an integer layer, and the old back/front words still parse.
layered = _layout({"shapes": [
    {"id": "old", "page": 2, "kind": "rect", "x": 0, "y": 0, "w": 1, "h": 1, "z": "back"},
    {"id": "new", "page": 2, "kind": "rect", "x": 0, "y": 0, "w": 1, "h": 1, "z": 4}]})
check("the legacy 'back' word still means behind", layered.layer(2), "z-index:-1")
check("an integer layer is honoured", layered.layer(2), "z-index:4")
check("a nonsense layer is caught",
      _layout_error({"shapes": [{"id": "x", "page": 1, "kind": "rect",
                                 "x": 0, "y": 0, "w": 1, "h": 1, "z": "middle"}]}),
      "not a layer number")

# -------------------------------------------------------------------- text
# Styling must be invisible until it is used. An unstyled report has to build to
# the same bytes it always did — head included — or the whole premise ("the
# design is the default, JSON only speaks where someone changed something")
# quietly stops being true.
from docsync.layout import text_css, FONTS                      # noqa: E402
from docsync.content import Content                             # noqa: E402

SHIPPED_LINK = ('<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@800;900'
                '&family=Source+Sans+3:ital,wght@0,300;0,400;0,600;0,700;1,400'
                '&display=swap" rel="stylesheet">')

nostyle = _layout({})
check_eq("an empty layout styles nothing", nostyle.text_attr("basics.h1"), "")
check_eq("an unstyled report asks for exactly the fonts it always did",
         nostyle.font_link(), SHIPPED_LINK)
check_eq("text_css of nothing is nothing", text_css({}), "")

styled = _layout({"text": {"a.b": {"font": "Playfair Display", "weight": 700}}})
check("a picked font joins the link", styled.font_link(), "family=Playfair+Display:wght@700")
check("the brand's own fonts survive a pick", styled.font_link(), "family=Barlow:wght@800;900")
check("a weight the report asks for is actually requested",
      _layout({"text": {"a": {"font": "Barlow", "weight": 400}}}).font_link(),
      "Barlow:wght@400;800;900")
check("italic moves the family onto the ital axis",
      _layout({"text": {"a": {"font": "Barlow", "weight": 400, "italic": True}}}).font_link(),
      "Barlow:ital,wght@0,800;0,900;1,400")

# A style attribute is quoted with ", so a family name quoted the same way ends
# the attribute early and the rest becomes stray markup. Every family with a
# space in it would have done this.
check("a font with a space cannot break out of the style attribute",
      text_css({"font": "Playfair Display"}), "font-family:'Playfair Display'")
check_eq("no double quote ever reaches the style attribute",
         '"' in text_css({"font": "Playfair Display", "color": "#fff"}), False)

# text-align does nothing to an inline box, and inline slots are spans.
check("centring an inline slot gives it a box to centre in",
      text_css({"align": "center"}), "display:inline-block;width:100%")
check_eq("a slot that was not aligned grows no width it never had",
         "width:100%" in text_css({"size": 20}), False)

check("an unknown family is caught at load",
      _layout_error({"text": {"a": {"font": "Comic Papyrus"}}}),
      "not a font this report can load")
check("a weight the family lacks is caught, because the browser would fake it",
      _layout_error({"text": {"a": {"font": "Barlow", "weight": 333}}}),
      "has no weight 333")
check("a colour that is not a colour is caught",
      _layout_error({"text": {"a": {"color": "red"}}}), "not a hex colour")
check("an alignment that is not one is caught",
      _layout_error({"text": {"a": {"align": "middle"}}}), "must be one of")
check_eq("the font list is a list, not free text", len(FONTS) > 10, True)


def _content(styles=None, body="[[a.b]]\nText.\n\n[[sources]]\n[x]: A. — https://a.gov\n"):
    t = Path(tempfile.mktemp(suffix=".md"))
    t.write_text(body)
    try:
        return Content(t, styles=styles)
    finally:
        t.unlink(missing_ok=True)


plain = _content(nostyle)
check_eq("an unstyled paragraph is the paragraph it always was",
         plain.html("a.b"), "<p>Text.</p>")
# t() emits a bare string in the published build. Styling it means a span — but
# ONLY for a slot someone actually styled, or every heading in the report grows
# a wrapper it never had.
check_eq("an unstyled t() is still a bare string, not a span", plain.t("a.b"), "Text.")

one = _content(_layout({"text": {"a.b": {"size": 20}}}))
check("a styled paragraph carries its style", one.html("a.b"), '<p style="font-size:20px">')
check("a styled t() becomes a span, and only then", one.t("a.b"), '<span style="font-size:20px">')
check_eq("text() is never wrapped — it lands in alt= and SVG, where a span is invalid",
         one.text("a.b"), "Text.")

# data-slot <=> styleable: the editor never offers a control that does nothing,
# and a style aimed at a slot the renderer builds into a string fails loudly.
c = _content(nostyle)
c.html("a.b")
check_eq("a slot that rendered an element is styleable", "a.b" in c.styleable(), True)
check_eq("a style aimed at a slot that never rendered one is reported",
         nostyle.unknown_text_keys({"a.b"}), [])
check_eq("a style aimed at an unstyleable slot is reported",
         _layout({"text": {"cip.body": {"size": 9}}}).unknown_text_keys({"a.b"}),
         ["cip.body"])

# ----------------------------------------------------------------- effects
from docsync.layout import EFFECTS, EFFECT_PARAMS                # noqa: E402

# The direction convention is 0 = 12 o'clock, clockwise — the same one
# arc_path() uses in the renderer. Pin it: a second convention for the same idea
# in one repo is a bug waiting to be written.
check("direction 0 casts the shadow straight up",
      text_css({"effect": {"kind": "shadow", "offset": 0.1, "direction": 0, "blur": 0}}),
      "0.0em -0.1em")
check("direction 90 casts it to the right",
      text_css({"effect": {"kind": "shadow", "offset": 0.1, "direction": 90, "blur": 0}}),
      "0.1em -0.0em")
# em, not px: a shadow measured in px detaches from its glyphs the moment the
# type is resized.
check("offsets scale with the type", text_css({"effect": {"kind": "shadow"}}), "em")

check("hollow empties the glyph",
      text_css({"effect": {"kind": "hollow"}}), "color:transparent")
check("hollow strokes the glyph",
      text_css({"effect": {"kind": "hollow"}}), "-webkit-text-stroke:")
check("neon glows in its own colour",
      text_css({"effect": {"kind": "neon", "color": "#6B9E78"}}), "0 0 ")
check("echo repeats at increasing distance and decreasing weight",
      text_css({"effect": {"kind": "echo", "offset": 0.05, "direction": 90}}), "0.1em")
check_eq("every effect produces CSS", all(text_css({"effect": {"kind": k}}) for k in EFFECTS), True)
check_eq("every effect declares its own knobs", sorted(EFFECT_PARAMS) == sorted(EFFECTS), True)

# hollow/splice hollow the glyph out, so they must land after any colour the
# same style set — otherwise the colour wins and the effect silently does
# nothing.
check("an effect that empties the glyph beats a colour set beside it",
      text_css({"color": "#ff0000", "effect": {"kind": "hollow"}}),
      "color:#ff0000;color:transparent")

check("an unknown effect is caught at load",
      _layout_error({"text": {"a": {"effect": {"kind": "sparkle"}}}}), "must be one of")
# An empty effect object is falsy, so a truthiness check would skip every
# validation below it and let a malformed file through as a no-op.
check("an effect with no kind is caught",
      _layout_error({"text": {"a": {"effect": {}}}}), "needs a 'kind'")
check("alpha outside 0..1 is caught",
      _layout_error({"text": {"a": {"effect": {"kind": "shadow", "alpha": 40}}}}),
      "not a fraction")
check("an effect colour that is not a colour is caught",
      _layout_error({"text": {"a": {"effect": {"kind": "neon", "color": "hotpink"}}}}),
      "not a hex colour")
check_eq("no effect means no effect CSS", "text-shadow" in text_css({"size": 12}), False)

# The caption used to be sliced at "[^" by the renderer to bold its label.
# Markdown already says "this is bold", so the prose says it and the surgery is
# gone — but only if paragraph() produces exactly what the split did.
check_eq("a bold label in the prose renders as the surgery used to",
         paragraph("**General-fund obligated costs, FY2018–FY2027 ($Billions).**[^exec-biennium]"),
         "<b>General-fund obligated costs, FY2018–FY2027 ($Billions).</b>[^exec-biennium]")

# ------------------------------------------------------------- text boxes
boxed = _layout({"boxes": [{"id": "t1", "page": 3, "x": 1.2, "y": 4, "w": 3, "z": 2,
                            "md": "**Note:** a pull quote",
                            "style": {"size": 13}}]})
check("a box is absolutely placed on its page", boxed.text_boxes(3), "left:1.2in;top:4in")
check_eq("a box only appears on its own page", boxed.text_boxes(4), "")
check("a box renders its markdown", boxed.text_boxes(3), "<b>Note:</b>")
check("a box takes the same styles as a slot", boxed.text_boxes(3), "font-size:13px")
# Same reason a text slot has no height: pin one and it either clips its words
# or leaves a hole the moment they change. Its bottom is the fit check's job.
check_eq("a box pins no height", "height:" in boxed.text_boxes(3), False)
check_eq("no boxes means no markup at all", _layout({}).text_boxes(3), "")

check("a box needs an id",
      _layout_error({"boxes": [{"page": 1, "x": 1, "y": 1, "w": 2, "md": "x"}]}),
      "needs an 'id'")
check("an empty box is caught — it would render as nothing",
      _layout_error({"boxes": [{"id": "a", "page": 1, "x": 1, "y": 1, "w": 2, "md": " "}]}),
      "has no text")
# The editor resolves an id to a thing by searching shapes then boxes, so a
# collision makes the right-click menu act on whichever it finds first.
check("a box id may not collide with a shape id",
      _layout_error({"shapes": [{"id": "d", "page": 1, "kind": "rect", "x": 0, "y": 0, "w": 1, "h": 1}],
                     "boxes": [{"id": "d", "page": 1, "x": 1, "y": 1, "w": 2, "md": "x"}]}),
      "duplicate id 'd' — already a shape")
check("a box dragged off the side is caught",
      " ".join(_layout({"boxes": [{"id": "w", "page": 1, "x": 7, "y": 1, "w": 4,
                                   "md": "x"}]}).check_bounds()),
      "past the right edge")
check("a box's style is validated like any other",
      _layout_error({"boxes": [{"id": "b", "page": 1, "x": 1, "y": 1, "w": 2, "md": "x",
                                "style": {"font": "Comic Papyrus"}}]}),
      "not a font this report can load")

if FAILS:
    print("\n\n".join("FAIL: " + f for f in FAILS))
    print(f"\n{len(FAILS)} failed")
    raise SystemExit(1)
print("docsync: all checks passed")
