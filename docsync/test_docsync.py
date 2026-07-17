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
      'style="position:absolute;left:1.2in;top:3.4in;width:5.0in"')
check_eq("an override beats the renderer's placement",
         moved.style("c.o", "left:9in;top:9in"),
         "position:absolute;left:1.2in;top:3.4in;width:5.0in")

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
check("back shapes sit behind the text", shaped.layer(7), "z-index:0")
check("front shapes sit above it", shaped.layer(7), "z-index:3")
check_eq("a page with no shapes gets no layer", shaped.layer(2), "")
check("shapes never eat clicks", shaped.layer(7), "pointer-events:none")

if FAILS:
    print("\n\n".join("FAIL: " + f for f in FAILS))
    print(f"\n{len(FAILS)} failed")
    raise SystemExit(1)
print("docsync: all checks passed")
