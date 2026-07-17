"""Fragment mode: a whole doc becomes one HTML block inside an existing page.

Slots mode asks a report to name every string it wants; that is the right trade
for an art-directed layout, but it is far too much ceremony for a page that
just wants a doc's prose. Here the doc IS the content: it converts to HTML and
lands between two anchor comments, and everything outside them is untouched.

    <!-- docsync:start -->   ...generated, do not edit...   <!-- docsync:end -->
"""
from __future__ import annotations

import re

from .content import ContentError, md_inline

GENERATED = ("<!-- Generated from the bound Google Doc by docsync. "
             "Edit the doc, not this block. -->")


def to_html(md: str) -> str:
    """Markdown -> HTML. Only the constructs Docs round-trips: headings,
    paragraphs, bullet/number lists, and the inline set md_inline covers."""
    out: list[str] = []
    para: list[str] = []
    items: list[str] = []
    ordered = False

    def flush_para():
        if para:
            out.append(f"<p>{md_inline(' '.join(para))}</p>")
            para.clear()

    def flush_items():
        if items:
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{i}</li>" for i in items)
                       + f"</{tag}>")
            items.clear()

    for line in md.splitlines():
        s = line.strip()
        if not s:
            flush_para(), flush_items()
            continue
        h = re.match(r"^(#{1,6})\s+(.*)$", s)
        if h:
            flush_para(), flush_items()
            out.append(f"<h{len(h.group(1))}>{md_inline(h.group(2))}"
                       f"</h{len(h.group(1))}>")
            continue
        b = re.match(r"^[-*]\s+(.*)$", s)
        n = re.match(r"^\d+[.)]\s+(.*)$", s)
        if b or n:
            flush_para()
            want_ordered = bool(n)
            if items and want_ordered != ordered:
                flush_items()
            ordered = want_ordered
            items.append(md_inline((b or n).group(1)))
            continue
        flush_items()
        para.append(s)
    flush_para(), flush_items()
    return "\n".join(out)


def anchors(name: str) -> tuple[str, str]:
    return f"<!-- {name}:start -->", f"<!-- {name}:end -->"


def inject(page: str, html: str, name: str = "docsync") -> str:
    """Replace whatever sits between the anchors. Missing anchors is a hard
    error — silently appending would put the doc's prose somewhere arbitrary."""
    start, end = anchors(name)
    i, j = page.find(start), page.find(end)
    if i == -1 or j == -1:
        raise ContentError(
            f"target page has no '{start}' / '{end}' anchors — add them where "
            f"the doc's content should appear")
    if j < i:
        raise ContentError(f"'{end}' appears before '{start}' in the target page")
    return (page[:i + len(start)] + "\n" + GENERATED + "\n" + html + "\n"
            + page[j:])


def extract(page: str, name: str = "docsync") -> str:
    """The current generated block, for change detection."""
    start, end = anchors(name)
    i, j = page.find(start), page.find(end)
    if i == -1 or j == -1:
        return ""
    return page[i + len(start):j].strip()
