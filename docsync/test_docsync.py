#!/usr/bin/env python3
"""Regression tests for the doc <-> repo round-trip.

Google Docs reshapes a content file when it imports and re-exports it. Every
normalise() case below is a real mangling observed from the live doc — if
Google changes its exporter, these fail here rather than silently corrupting a
committed file. The rest cover fragment mode and the conflict rules that decide
whether a push is safe.

    python3 docsync/test_docsync.py
"""
import os
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
from docsync.layout import (Layout, LayoutError, shadow_css,   # noqa: E402
                            fill_css, fill_repr, fill_svg_paint)


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


def _layout_error_at(fn):
    """For failures that fire at render, not load — page_order needs the page
    count, which only the renderer knows."""
    try:
        fn()
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
      held.spacer("cover.logo"), 'height:1.09in;flex:0 0 auto')
# A moved element in a FLEX row (a branch photo beside its card) must reserve
# its WIDTH too, or the sibling stretches across the gap.
held_w = _layout({"positions": {"branch.photo.x": {"x": 1, "y": 2, "w": 2.15,
                                                   "reserve": 1.6}}})
check("a moved flex element reserves its width and height",
      held_w.spacer("branch.photo.x"), 'width:2.15in;height:1.6in;flex:0 0 auto')
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

# A prose block is a movable unit: moved, the whole slot travels in one
# wrapper. Unmoved and published, the bytes are the bare paragraphs above —
# already proven by "an unstyled paragraph is the paragraph it always was".
moved_para = _content(_layout({"positions": {"para.a.b": {"x": 1, "y": 2, "w": 4,
                                                          "reserve": 0.5}}}))
check("a moved prose block travels in one positioned wrapper",
      moved_para.html("a.b"),
      '<div style="position:absolute;left:1in;top:2in;width:4in;z-index:1"><p>Text.</p></div>')
check("its vacated flow space stays held", moved_para.html("a.b"),
      '<div class="ds-spacer" style="width:4in;height:0.5in;flex:0 0 auto"')
os.environ["DOCSYNC_EDIT"] = "1"
try:
    check("in edit mode the wrapper is the editor's drag handle",
          _content(nostyle).html("a.b"), '<div data-el="para.a.b"><p')
finally:
    del os.environ["DOCSYNC_EDIT"]

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

# ------------------------------------------------------------------ fills
# attr() merges extra declarations into the position style: an element with two
# style attributes silently keeps only the first, so a recoloured-and-moved
# callout must come out as ONE attribute carrying both.
both = _layout({"positions": {"c.o": {"x": 1, "y": 2}}})
check("attr merges a computed background into the move",
      both.attr("c.o", "background:#2F3E46"),
      'style="position:absolute;left:1in;top:2in;z-index:1;background:#2F3E46"')
check_eq("extra alone still emits a style", empty.attr("c.o", "background:#2F3E46"),
         ' style="background:#2F3E46"')
check_eq("no move, no extra, no attribute", empty.attr("c.o"), "")

# The generic fill hooks: outside edit mode an unfilled surface must emit
# NOTHING (the published bytes cannot move), and the editor's data-fill hook
# exists only while editing — like data-el.
check_eq("fill_attr is silent when unfilled", empty.fill_attr("page.3"), "")
check_eq("fill_tag is silent outside edit mode", empty.fill_tag("card.a"), "")
pg = _layout({"fill": {"page.3": "#E8EDE6"}})
check_eq("a filled page carries its background",
         pg.fill_attr("page.3"), ' style="background:#E8EDE6"')
os.environ["DOCSYNC_EDIT"] = "1"
try:
    check_eq("edit mode stamps the right-click hook",
             empty.fill_tag("card.a"), ' data-fill="card.a"')
    check_eq("edit mode stamps hook and background together",
             pg.fill_attr("page.3"), ' data-fill="page.3" style="background:#E8EDE6"')
finally:
    del os.environ["DOCSYNC_EDIT"]

check("a shape colour that is not a colour is caught",
      _layout_error({"shapes": [{"id": "a", "page": 1, "kind": "rect",
                                 "x": 0, "y": 0, "w": 1, "h": 1, "fill": "sage"}]}),
      "not a hex colour")
check_eq("'none' stays a legal shape fill",
         _layout({"shapes": [{"id": "a", "page": 1, "kind": "rect", "x": 0, "y": 0,
                              "w": 1, "h": 1, "fill": "none"}]}).layer(1).count('fill="none"'), 1)

# A text box may carry a panel colour; only then does it grow padding, so a
# plain box's words sit exactly where they were put.
bfill = _layout({"boxes": [{"id": "t1", "page": 3, "x": 1, "y": 2, "w": 3,
                            "md": "note", "fill": "#D6E0D2"}]})
check("a filled text box paints and pads", bfill.text_boxes(3),
      "background:#D6E0D2;padding:.08in .12in")
bplain = _layout({"boxes": [{"id": "t1", "page": 3, "x": 1, "y": 2, "w": 3, "md": "note"}]})
check_eq("an unfilled text box grows no padding",
         "padding" in bplain.text_boxes(3), False)
check("a box colour that is not a colour is caught",
      _layout_error({"boxes": [{"id": "t1", "page": 3, "x": 1, "y": 2, "w": 3,
                                "md": "note", "fill": "teal"}]}),
      "not a hex colour")

# ------------------------------------------------- rotation, opacity, shadow
rotp = _layout({"positions": {"c.o": {"x": 1, "y": 2, "rot": 15, "alpha": 0.8}}})
check("a rotated element turns in place", rotp.attr("c.o"), "transform:rotate(15deg)")
check("a faded element carries its opacity", rotp.attr("c.o"), "opacity:0.8")
rots = _layout({"shapes": [{"id": "a", "page": 1, "kind": "rect", "x": 1, "y": 1,
                            "w": 2, "h": 1, "rot": 30, "alpha": 0.5,
                            "shadow": {"offset": 0.05, "blur": 0.08}}]})
check("a shape rotates about its own centre", rots.layer(1), 'transform="rotate(30 2.0 1.5)"')
check("shape opacity is an attribute", rots.layer(1), 'opacity="0.5"')
check("a shape shadow is a drop-shadow filter", rots.layer(1), "drop-shadow(")
rotb = _layout({"boxes": [{"id": "t1", "page": 3, "x": 1, "y": 2, "w": 3, "md": "hi",
                           "rot": -10, "shadow": {"blur": 0.1, "alpha": 0.5}}]})
check("a box shadow is box-shadow", rotb.text_boxes(3), "box-shadow:")
check("a box rotates too", rotb.text_boxes(3), "rotate(-10deg)")
check("an opacity above one is caught",
      _layout_error({"positions": {"c.o": {"x": 1, "y": 2, "alpha": 1.5}}}),
      "not a fraction")
scaled = _layout({"positions": {"logo": {"x": 1, "y": 2, "scale": 1.4}}})
check("a scaled graphic carries its factor", scaled.attr("logo"), "scale(1.4)")
check_eq("a scale of exactly 1 emits nothing",
         "scale" in _layout({"positions": {"c.o": {"x": 1, "y": 2, "scale": 1}}}).attr("c.o"),
         False)
check("rotation and scale share one transform, in order",
      _layout({"positions": {"g": {"x": 1, "y": 2, "rot": 20, "scale": 1.5}}}).attr("g"),
      "transform:rotate(20deg) scale(1.5)")
check("a non-positive scale is caught",
      _layout_error({"positions": {"g": {"x": 1, "y": 2, "scale": 0}}}),
      "scale must be positive")
check("a shadow that is not an object is caught",
      _layout_error({"boxes": [{"id": "t1", "page": 3, "x": 1, "y": 2, "w": 3,
                                "md": "hi", "shadow": "big"}]}),
      "expected a shadow object")

# Rotation swings corners past edges the unrotated frame never reached: a
# 4x1in shape at 45° stands ~1.77in proud of its own top edge.
spin = _layout({"shapes": [{"id": "a", "page": 1, "kind": "rect",
                            "x": 2, "y": 0.2, "w": 4, "h": 1, "rot": 45}]})
check("a rotated shape is judged by its rotated box",
      " ".join(spin.check_bounds()), "swings past")
flat = _layout({"shapes": [{"id": "a", "page": 1, "kind": "rect",
                            "x": 2, "y": 0.2, "w": 4, "h": 1}]})
check_eq("unrotated, the same shape is fine", flat.check_bounds(), [])
check_eq("shadow_css is inches and rgba",
         shadow_css({"offset": 0.1, "direction": 90, "blur": 0.05,
                     "alpha": 0.4, "color": "#2F3E46"}),
         "0.1in -0.0in 0.05in rgba(47,62,70,0.4)")

# ------------------------------------------------ shape styling & new kinds
styled_sh = _layout({"shapes": [
    {"id": "t", "page": 2, "kind": "triangle", "x": 1, "y": 1, "w": 2, "h": 1,
     "fill": "#6B9E78"},
    {"id": "a", "page": 2, "kind": "arrow", "x": 4, "y": 1, "w": 2, "h": 0.8,
     "fill": "#52796F"},
    {"id": "l", "page": 2, "kind": "line", "x": 1, "y": 3, "w": 3, "h": 0,
     "stroke": "#2F3E46", "ends": "end", "dash": [0.08, 0.05]}]})
lay2 = styled_sh.layer(2)
check("a triangle is a polygon with its apex centred", lay2, 'points="2,1 3,2 1,2"')
check("an arrow closes seven points", lay2, "5.24,1.224 5.24,1")
check("a dashed line carries its dash", lay2, 'stroke-dasharray="0.08 0.05"')
check("an ended line points its marker", lay2, 'marker-end="url(#ds-arr-2--1)"')
check("the layer defines the arrowhead once", lay2, 'id="ds-arr-2--1"')
check_eq("markers inherit the line's own colour", lay2.count('fill="context-stroke"'), 1)
check("a dash that is not lengths is caught",
      _layout_error({"shapes": [{"id": "l", "page": 1, "kind": "line", "x": 0,
                                 "y": 0, "w": 1, "h": 0, "dash": [0]}]}),
      "positive")
check("unknown line ends are caught",
      _layout_error({"shapes": [{"id": "l", "page": 1, "kind": "line", "x": 0,
                                 "y": 0, "w": 1, "h": 0, "ends": "sideways"}]}),
      "must be one of none, start, end, both")
check("a negative corner radius is caught",
      _layout_error({"shapes": [{"id": "r", "page": 1, "kind": "rect", "x": 0,
                                 "y": 0, "w": 1, "h": 1, "r": -0.1}]}),
      "cannot be negative")

# ---------------------------------------------------------------- images
imged = _layout({"positions": {"p": {"x": 1, "y": 1, "rot": 10, "flip": "h"}},
                 "img": {"p": {"radius": 0.12, "src": "assets/new.jpg",
                               "filter": {"bright": 1.1, "gray": 0.3},
                               "crop": {"imgW": 6.0, "dx": 1.2, "dy": 0.4}}}})
check("rotate and flip share one transform declaration",
      imged.attr("p"), "transform:rotate(10deg) scale(-1,1)")
check_eq("a replaced image shows its replacement",
         imged.img_src("p", "assets/old.jpg"), "assets/new.jpg")
check_eq("an unreplaced image keeps the designed file",
         imged.img_src("q", "assets/old.jpg"), "assets/old.jpg")
check("radius and filters come out as one style", imged.img_css("p"),
      "border-radius:0.12in;filter:brightness(1.1) grayscale(0.3)")
check_eq("no overrides, no style", imged.img_css("q"), "")
check_eq("the crop window's geometry round-trips",
         imged.cropped("p"), {"imgW": 6.0, "dx": 1.2, "dy": 0.4})
check("an unknown flip is caught",
      _layout_error({"positions": {"p": {"x": 1, "y": 1, "flip": "x"}}}),
      "must be h, v or hv")
check("a crop missing its geometry is caught",
      _layout_error({"img": {"p": {"crop": {"imgW": 5}}}}), "needs imgW, dx and dy")
check("a negative filter is caught",
      _layout_error({"img": {"p": {"filter": {"sat": -1}}}}), "cannot be negative")

# --------------------------------------------------------------- page order
# The load-bearing case: no override means the identity order, so the report
# builds byte for byte as before.
check_eq("no page override is the identity order",
         empty.page_order(12), list(range(1, 13)))
reordered = _layout({"pages": {"blanks": [{"id": "b1"}],
                               "order": [1, 2, "b1", 3, 5, 12]}})
check_eq("order interleaves blanks and hides by omission",
         reordered.page_order(12), [1, 2, "b1", 3, 5, 12])
check_eq("blanks are named", reordered.blank_ids(), ["b1"])
check("a designed page beyond the report is caught at render",
      _layout_error_at(lambda: _layout({"pages": {"order": [1, 2, 99]}}).page_order(12)),
      "pages 1–12, not 99")
check("an order naming an undeclared blank is caught",
      _layout_error({"pages": {"order": [1, "ghost"]}}),
      "not a blank this file declares")
check("a duplicate page in the order is caught",
      _layout_error({"pages": {"order": [1, 2, 2]}}), "appears twice")
check("a shape may live on a blank page",
      _layout({"pages": {"blanks": [{"id": "b1"}]},
               "shapes": [{"id": "s", "page": "b1", "kind": "rect",
                           "x": 1, "y": 1, "w": 1, "h": 1}]}).layer("b1"),
      "shape-layer")

# The lock list is an editor affordance the renderer never reads — but a
# malformed one must still fail at load, not quietly stop locking anything.
check_eq("locked ids load", _layout({"locked": ["cover.logo", "s1-rect"]}).locked,
         ["cover.logo", "s1-rect"])
check("a lock list that is not ids is caught",
      _layout_error({"locked": [{"id": "x"}]}), "list of element ids")
check_eq("no lock list means nothing locked", empty.locked, [])

# Groups are an editor affordance too — select and move as one — and the
# renderer never reads them, but a malformed one still fails at load.
check_eq("groups load as lists of member ids",
         _layout({"groups": [["a", "b"], ["c", "d", "e"]]}).groups,
         [["a", "b"], ["c", "d", "e"]])
check("a group of one is not a group",
      _layout_error({"groups": [["solo"]]}), "two or more element ids")
check("an element cannot be in two groups",
      _layout_error({"groups": [["a", "b"], ["b", "c"]]}), "at most one")
check_eq("a group never reaches the rendered page",
         _layout({"groups": [["a", "b"]]}).layer(3), "")

# Ruler guides are editor-only — the renderer never emits one, so an empty
# guides block cannot move a byte, but a malformed one still fails at load.
check_eq("guides load as inches", _layout({"guides": {"x": [1.2, 4.25], "y": [3.0]}}).guides,
         {"x": [1.2, 4.25], "y": [3.0]})
check("a guide off the page is caught",
      _layout_error({"guides": {"x": [9.9]}}), "off the 8.5in page")
check("a guide that is not a number is caught",
      _layout_error({"guides": {"y": ["top"]}}), "not a number")
check_eq("a guide never reaches the rendered page",
         _layout({"guides": {"x": [1.2]}}).layer(3), "")

filled = _layout({"fill": {"card.a": "#2F3E46"}})
check_eq("a fill overrides the designed colour", filled.fill("card.a", "#6B9E78"), "#2F3E46")
check_eq("an unfilled element keeps the colour the report chose",
         filled.fill("card.b", "#6B9E78"), "#6B9E78")
check_eq("refilled() knows which is which", (filled.refilled("card.a"), filled.refilled("card.b")),
         (True, False))
check("a fill that is not a colour is caught",
      _layout_error({"fill": {"card.a": "burnt sienna"}}), "not a hex colour")

# The reason colour cannot be painted onto the DOM: is_light_bg() picks white or
# charcoal text from a tile's luminance AT BUILD TIME, and the footnote pills
# ride the same class. One card is hand-judged light=True by the renderer — a
# judgment about the colour it chose. Recolour it and that judgment is about a
# colour that is no longer there.
def _is_light(hexc):                                  # mirrors render_report.py
    h = hexc.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) > 130


check_eq("the pale tile the renderer hand-judges really is light", _is_light("#CAD2C5"), True)
check_eq("recoloured to charcoal it is not — so its text must reverse",
         _is_light("#2F3E46"), False)


def _is_light_a(hexc):                                # 8-digit, composited over white
    h = hexc.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if len(h) == 8:
        a = int(h[6:8], 16) / 255
        r, g, b = (v * a + 255 * (1 - a) for v in (r, g, b))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) > 130


check_eq("an opaque charcoal fill reads dark", _is_light_a("#2F3E46FF"), False)
check_eq("the same charcoal at 25% shows the page and reads light",
         _is_light_a("#2F3E4640"), True)

# --- gradient fills --------------------------------------------------------
# A fill may be a hex (byte-identity) or a gradient object; shape, box and the
# fill{} surfaces all accept both. The three helpers must keep a hex verbatim so
# a solid fill never moves a byte, and must turn a gradient into CSS / an SVG
# paint+defs / one contrast colour.
_LIN = {"type": "linear", "angle": 90,
        "stops": [{"color": "#FFFFFF", "at": 0}, {"color": "#2F3E46", "at": 1}]}
_RAD = {"type": "radial",
        "stops": [{"color": "#6B9E78", "at": 0}, {"color": "#354F52", "at": 1}]}

check_eq("a gradient fill loads on a shape",
         _layout({"shapes": [{"id": "g", "page": 5, "kind": "rect",
                              "x": 1, "y": 1, "w": 2, "h": 2, "fill": _LIN}]}).shapes[0]["fill"]["type"],
         "linear")
check_eq("a gradient fill loads on a fill surface",
         _layout({"fill": {"card.a": _RAD}}).fill("card.a", "#fff")["type"], "radial")
check("a gradient needs two or more stops",
      _layout_error({"fill": {"card.a": {"type": "linear",
                                         "stops": [{"color": "#fff", "at": 0}]}}}),
      "two or more stops")
check("a gradient needs a known type",
      _layout_error({"fill": {"card.a": {"type": "conic",
                                         "stops": [{"color": "#fff", "at": 0},
                                                   {"color": "#000", "at": 1}]}}}),
      "'linear' or 'radial'")
check("a gradient stop needs a hex colour",
      _layout_error({"fill": {"card.a": {"type": "linear",
                                         "stops": [{"color": "teal", "at": 0},
                                                   {"color": "#000", "at": 1}]}}}),
      "not a hex colour")
check("a gradient stop position stays within 0..1",
      _layout_error({"fill": {"card.a": {"type": "linear",
                                         "stops": [{"color": "#fff", "at": 0},
                                                   {"color": "#000", "at": 2}]}}}),
      "between 0 and 1")

# The byte-identity guarantee: a SOLID fill emits exactly what it did before —
# no gradient <defs>, hex verbatim in CSS and SVG.
_solidshape = _layout({"shapes": [{"id": "s", "page": 5, "kind": "rect",
                                   "x": 1, "y": 1, "w": 2, "h": 2, "fill": "#6B9E78"}]})
check("a solid shape emits its hex verbatim", _solidshape.layer(5), 'fill="#6B9E78"')
check_eq("a solid shape draws no gradient def", "linearGradient" in _solidshape.layer(5), False)
check_eq("fill_css keeps a hex verbatim", fill_css("#E8EDE6"), "#E8EDE6")
check_eq("fill_repr keeps a hex verbatim", fill_repr("#123456"), "#123456")

# A gradient shape references a def; the def is emitted once in the layer.
_gradshape = _layout({"shapes": [{"id": "gg", "page": 5, "kind": "rect",
                                  "x": 1, "y": 1, "w": 2, "h": 2, "fill": _LIN}]})
check("a gradient shape paints from a def", _gradshape.layer(5), 'fill="url(#ds-fill-gg)"')
check("the gradient def is emitted", _gradshape.layer(5), '<linearGradient id="ds-fill-gg"')
check("fill_css writes a CSS linear-gradient", fill_css(_LIN), "linear-gradient(90deg,")
check("fill_css writes a CSS radial-gradient", fill_css(_RAD), "radial-gradient(circle,")
check_eq("fill_repr returns a six-digit hex for a gradient", len(fill_repr(_LIN)), 7)
check_eq("contrast still resolves on a gradient (it returns a bool)",
         isinstance(_is_light(fill_repr(_LIN)), bool), True)
# 90deg = to the right: the last stop sits at x=1.
check("a 90deg gradient runs left to right", fill_svg_paint(_LIN, "d")[1], 'x1="0.0"')
check("its last stop is on the right", fill_svg_paint(_LIN, "d")[1], 'x2="1.0"')
# An 8-digit stop splits into colour + opacity for SVG.
check("an 8-digit stop splits its alpha",
      fill_svg_paint({"type": "linear", "stops": [{"color": "#2F3E4680", "at": 0},
                                                  {"color": "#fff", "at": 1}]}, "d")[1],
      'stop-color="#2F3E46" stop-opacity="0.5')

# ------------------------------------------------------------------- icons
# An icon's geometry is copied into layout.json from an open-source set, so
# markup from the internet reaches the rendered page. layout.py is the only
# gate the RENDERER controls (layout.json can be hand-edited), so it checks
# rather than trusts — and fails loudly instead of stripping, which would
# leave a half-drawn icon nobody could explain.
from docsync.layout import check_icon_svg, icon_color                # noqa: E402


def check_icon_raises(name, body, expect):
    try:
        check_icon_svg(body, "shape #1")
    except LayoutError as e:
        if expect not in str(e):
            FAILS.append(f"{name}\n  want error containing: {expect!r}\n  got: {e}")
        return
    FAILS.append(f"{name}\n  expected LayoutError containing {expect!r}, none raised")


_ICON = '<g fill="none" stroke="currentColor"><path d="M3 10a2 2 0 0 1 .7-1.5"/></g>'
check_eq("a plain drawing passes", check_icon_svg(_ICON, "s"), _ICON)
check_icon_raises("a script tag is refused", "<script>alert(1)</script>", "not allowed")
check_icon_raises("an event handler is refused", '<path onload="x" d="M0 0"/>', "not allowed")
check_icon_raises("a remote image is refused", '<image href="http://e/x.png"/>', "not allowed")
check_icon_raises("a javascript: link is refused", '<a href="javascript:1">x</a>', "not allowed")
check_icon_raises("foreignObject is refused", "<foreignObject><b>x</b></foreignObject>",
                  "not allowed")
check_icon_raises("an unknown tag is refused", "<video/>", "not one of the allowed")
check_icon_raises("empty markup is refused", "  ", "needs its 'svg'")
check_icon_raises("absurd markup is refused", '<path d="' + "M0 0" * 20000 + '"/>',
                  "refusing it")

# currentColor is the whole reason these sets recolour cleanly: one CSS
# property repaints the glyph. A gradient cannot BE a colour, so it lends its
# first stop rather than failing — the icon still lands in the palette.
check_eq("a solid fill is the icon's colour", icon_color("#B23A48"), "#B23A48")
check_eq("a gradient lends its first stop",
         icon_color({"type": "linear", "stops": [{"color": "#123456", "at": 0}]}), "#123456")
check_eq("no fill falls back to the report's ink", icon_color(None), "#2F3E46")

if FAILS:
    print("\n\n".join("FAIL: " + f for f in FAILS))
    print(f"\n{len(FAILS)} failed")
    raise SystemExit(1)
print("docsync: all checks passed")
