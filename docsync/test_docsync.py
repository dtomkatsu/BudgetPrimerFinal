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

if FAILS:
    print("\n\n".join("FAIL: " + f for f in FAILS))
    print(f"\n{len(FAILS)} failed")
    raise SystemExit(1)
print("docsync: all checks passed")
