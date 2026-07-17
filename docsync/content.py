"""Prose layer for the Budget Primer.

The primer's authored text lives in content.md ([[key]] slots), which is kept
in sync with the Google Doc via `make pull-doc`. This module parses that file,
converts inline Markdown to the exact HTML the report expects, and resolves
footnote refs.

Footnotes: prose carries stable IDs ([^act99]). Numbering is assigned in order of
first appearance across the assembled document, so a source can be inserted or
removed in the doc without renumbering anything by hand.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

_KEY_RE = re.compile(r"^\[\[([A-Za-z0-9._-]+)\]\]\s*$", re.M)
_HEADING_RE = re.compile(r"^#{1,6}\s+", re.M)   # doc headings are styling, not content
_SOURCE_RE = re.compile(r"^\[([^\]]+)\]:\s*(.*?)\s+—\s+(\S+)\s*$", re.M)


class ContentError(RuntimeError):
    """Raised when content.md is missing a key or a source — never fail silently."""


def _strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def parse_content(path: Path) -> dict:
    """content.md -> {key: raw markdown block}. Blocks keep their line breaks."""
    text = _strip_comments(path.read_text())
    out, matches = {}, list(_KEY_RE.finditer(text))
    if not matches:
        raise ContentError(f"{path.name}: no '[[key]]' markers found")
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        key = m.group(1)
        if key in out:
            raise ContentError(f"{path.name}: duplicate key '[[{key}]]'")
        out[key] = text[m.end():end].strip("\n").strip()
    return out


def parse_sources(block: str) -> dict:
    """[[sources]] block -> {id: (text, url)} preserving declaration order."""
    src = {}
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _SOURCE_RE.match(line)
        if not m:
            raise ContentError(
                f"source line is not '[id]: text — https://url':\n  {line}")
        sid, txt, url = m.group(1), m.group(2).strip(), m.group(3).strip()
        if sid in src:
            raise ContentError(f"duplicate source id '[{sid}]'")
        src[sid] = (txt, url)
    if not src:
        raise ContentError("[[sources]] section is empty")
    return src


def md_inline(s: str) -> str:
    """Inline Markdown -> the report's HTML. Deliberately minimal: only the
    constructs the primer actually uses, emitting <b>/<i>/<a> (not <strong>).

    Prose '&' is escaped to '&amp;'; URLs are pulled out first so query strings
    (?a=1&b=2) keep their raw ampersands, matching the report's existing markup.
    """
    urls: list[str] = []

    def stash(m):
        urls.append(m.group(2))
        return f"\x00LINK{len(urls) - 1}\x00{m.group(1)}\x01"

    s = re.sub(r"\[([^\]^][^\]]*)\]\((https?://[^)\s]+)\)", stash, s)
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s, flags=re.S)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", s, flags=re.S)
    s = re.sub(r"\x00LINK(\d+)\x00(.*?)\x01",
               lambda m: f'<a href="{urls[int(m.group(1))]}">{m.group(2)}</a>', s, flags=re.S)
    return s


def bullets(block: str) -> list[str]:
    """'- item' lines -> [html, ...]. Errors if the block isn't a list."""
    items = [md_inline(l.strip()[2:].strip())
             for l in _unhead(block).splitlines() if l.strip().startswith("- ")]
    if not items:
        raise ContentError(f"expected a '- ' bullet list, got:\n  {block[:80]}")
    return items


def _unhead(block: str) -> str:
    return _HEADING_RE.sub("", block)


def paragraph(block: str) -> str:
    """A prose block -> one HTML string (soft line wraps collapse to spaces)."""
    return md_inline(" ".join(l.strip() for l in _unhead(block).splitlines() if l.strip()))


def block_html(block: str) -> str:
    """Generic renderer for overflow slots: headings, bullet lists and
    paragraphs in source order. '##' -> section heading, '###' -> subheading,
    matching the report's existing styles."""
    out: list[str] = []
    para: list[str] = []
    items: list[str] = []

    def flush_para():
        if para:
            out.append(f"<p>{md_inline(' '.join(para))}</p>")
            para.clear()

    def flush_items():
        if items:
            out.append('<ul class="extra-bullets">'
                       + "".join(f"<li>{i}</li>" for i in items) + "</ul>")
            items.clear()

    for line in block.splitlines():
        s = line.strip()
        if not s:
            flush_para(); flush_items()
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            flush_para(); flush_items()
            txt = md_inline(m.group(2))
            out.append(f'<h2 class="sub">{txt}</h2>' if len(m.group(1)) <= 2
                       else f'<h3 class="sub2">{txt}</h3>')
            continue
        if s.startswith("- "):
            flush_para()
            items.append(md_inline(s[2:].strip()))
            continue
        flush_items()
        para.append(s)
    flush_para(); flush_items()
    return "".join(out)


def paragraphs(block: str) -> list[str]:
    """A block -> one HTML string per blank-line-separated paragraph, so an
    editor can add a paragraph inside a slot and have it flow into the report."""
    chunks = [c for c in re.split(r"\n\s*\n", _unhead(block).strip()) if c.strip()]
    return [md_inline(" ".join(l.strip() for l in c.splitlines() if l.strip()))
            for c in chunks]


class Footnotes:
    """Assigns numbers to [^id] refs in order of first appearance."""

    def __init__(self, sources: dict):
        self.sources = sources
        self.order: list[str] = []          # ids, in first-appearance order

    def _number(self, sid: str) -> int:
        if sid not in self.sources:
            raise ContentError(
                f"footnote [^{sid}] has no entry under [[sources]] in content.md")
        if sid not in self.order:
            self.order.append(sid)
        return self.order.index(sid) + 1

    def resolve(self, html: str) -> str:
        """Replace [^id] runs with <sup>N</sup> (adjacent refs share one <sup>,
        thin-space separated, matching the primer's multi-ref style)."""
        def run(m):
            ids = re.findall(r"\[\^([^\]]+)\]", m.group(0))
            return "<sup>" + "&thinsp;".join(str(self._number(i)) for i in ids) + "</sup>"
        return re.sub(r"(?:\[\^[^\]]+\])+", run, html)

    def unused(self) -> list[str]:
        return [s for s in self.sources if s not in self.order]

    def endnotes(self) -> list[tuple[str, str]]:
        """(text, url) in numbered order — feeds the Endnotes page."""
        return [self.sources[sid] for sid in self.order]


class Content:
    """Key lookup with a loud failure when a key is missing."""

    def __init__(self, path: Path):
        self.path = path
        self._raw = parse_content(path)
        if "sources" not in self._raw:
            raise ContentError(f"{path.name}: missing the '[[sources]]' section")
        self.sources = parse_sources(self._raw.pop("sources"))
        self.fn = Footnotes(self.sources)
        self._used: set[str] = set()

    def raw(self, key: str) -> str:
        if key not in self._raw:
            raise ContentError(
                f"{self.path.name}: missing '[[{key}]]'.\n"
                f"  The Google Doc must keep every [[key]] marker intact.")
        self._used.add(key)
        return self._raw[key]

    def __call__(self, key: str) -> str:
        """Prose block -> HTML paragraph text (footnote refs left for resolve())."""
        return paragraph(self.raw(key))

    def text(self, key: str) -> str:
        """Raw single-line value (titles, labels) with no Markdown conversion."""
        return " ".join(l.strip() for l in _unhead(self.raw(key)).splitlines() if l.strip())

    def html(self, key: str, cls: str | None = None) -> str:
        """Slot -> one or more <p> elements (multi-paragraph slots supported).

        DOCSYNC_EDIT stamps the slot name on each paragraph so the draft editor
        can map a click back to the text that produced it. Off by default: the
        published HTML carries no editing scaffolding.
        """
        attr = f' class="{cls}"' if cls else ""
        slot = f' data-slot="{key}"' if os.environ.get("DOCSYNC_EDIT") else ""
        return "".join(f"<p{attr}{slot}>{h}</p>" for h in paragraphs(self.raw(key)))

    def list(self, key: str) -> list[str]:
        return bullets(self.raw(key))

    def lines(self, key: str) -> list[str]:
        return [l.strip() for l in _unhead(self.raw(key)).splitlines() if l.strip()]

    def extras(self, page: str) -> str:
        """Render every overflow slot for a page — keys named
        [[extra.<page>.<slug>]] — in content.md order. This is what lets an
        editor add a whole new prose section from the Google Doc alone:
        no renderer change, the slot just appears at the end of that page."""
        prefix = f"extra.{page}."
        return "".join(block_html(self.raw(k))
                       for k in self._raw if k.startswith(prefix))

    def unused_keys(self) -> list[str]:
        return sorted(set(self._raw) - self._used)
