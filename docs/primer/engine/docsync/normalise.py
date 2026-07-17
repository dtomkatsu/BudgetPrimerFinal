"""Undo the cosmetics Google's Doc <-> Markdown round-trip adds.

Docs has no concept of our marker syntax, so importing a content file and then
re-exporting it reshapes the file in predictable ways. Each is reversed here.
The result is always validated afterwards, so anything unanticipated fails
loudly rather than landing half-converted in a committed file.

Every case handled here was observed from a live doc — see test_docsync.py,
which pins each one. If Google changes its exporter, those tests fail first.
"""
from __future__ import annotations

import re

_MARKER = r"\[\[[A-Za-z0-9._-]+\]\]"


def normalise(md: str, header: str = "") -> str:
    """Google's Markdown export -> the committed file's canonical form.

    `header` is re-attached at the top (Docs drops HTML comments, so a file's
    instructions block cannot survive the round-trip and is carried by the
    caller instead of being duplicated here).
    """
    md = md.replace("\r\n", "\n").replace(" ", " ")
    # '_' is a word char, so it must be named explicitly or \_ survives and
    # reaches the renderer inside {placeholders}.
    md = re.sub(r"\\([^\w\s]|_)", r"\1", md)
    # Bare URLs come back as [url](url); collapse them only when the label and
    # href match, so real labelled links are untouched. Runs after unescaping,
    # or the escaped label never equals the raw href.
    md = re.sub(r"\[(https?://[^\]\s]+)\]\(\1\)", r"\1", md)

    # A doc title line above the first marker is chrome, not content.
    first = re.search(rf"^\s*{_MARKER}", md, flags=re.M)
    if first:
        md = md[first.start():]

    # Docs merges a marker into the paragraph that follows it ("[[k]] text"),
    # and pads markers that precede a heading or list with a blank line.
    md = re.sub(rf"^({_MARKER})[ \t]+(?=\S)", r"\1\n", md, flags=re.M)
    md = re.sub(rf"^[ \t]*({_MARKER})[ \t]*\n\n+", r"\1\n", md, flags=re.M)

    # The sources block is soft-wrapped lines inside one Docs paragraph, so it
    # returns as a single line. Split it back at each "[id]: ".
    m = re.search(r"^\[\[sources\]\]\n", md, flags=re.M)
    if m:
        head, block = md[:m.end()], md[m.end():]
        block = re.sub(r"[ \t]+(?=\[[A-Za-z0-9._-]+\]:\s)", "\n", block)
        md = head + block

    md = re.sub(r"[ \t]+$", "", md, flags=re.M)      # trailing hard-break spaces
    md = re.sub(r"\n{3,}", "\n\n", md)
    return header + md.strip() + "\n"


def leading_comment(text: str) -> str:
    """The instructions comment at the top of a content file, if any."""
    m = re.match(r"\A(.*?-->\n+)", text, flags=re.S)
    return m.group(1) if m else ""
