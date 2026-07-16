#!/usr/bin/env python3
"""Pull the primer's prose from the Google Doc into content.md.

    python3 tools/pull_doc.py            # fetch, validate, write content.md
    python3 tools/pull_doc.py --check    # fetch + validate only, don't write
    python3 tools/pull_doc.py --diff     # show what would change

The doc is the writing surface; content.md is the committed snapshot the build
reads, so builds stay reproducible/offline and every prose change lands as a
reviewable git diff. Nothing is written unless the fetched content parses AND
satisfies every key the report needs — a broken doc can never reach the report.

Requires the doc to be shared "Anyone with the link -> Viewer" (the Markdown
export endpoint is then readable without credentials).
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content import Content, ContentError  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
CONTENT = HERE / "content.md"
DOC_ID = "1wOwrX6ISoTvYEp7Ut7HIOmng8PHkp_HEZ9veWihu4TU"
EXPORT = f"https://docs.google.com/document/d/{DOC_ID}/export?format=markdown"


def fetch(url: str = EXPORT) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "budget-primer-sync"})
    with urllib.request.urlopen(req, timeout=30) as r:
        if "text/html" in r.headers.get("Content-Type", ""):
            raise SystemExit(
                "Google returned a sign-in page, not Markdown.\n"
                "Share the doc as 'Anyone with the link -> Viewer' and retry.")
        return r.read().decode("utf-8")


def _header() -> str:
    """The instructions comment at the top of content.md. Docs drops HTML
    comments, so it is re-attached on the way back rather than duplicated
    here — content.md stays its own single source for that text."""
    if not CONTENT.exists():
        return ""
    m = re.match(r"\A(.*?-->\n+)", CONTENT.read_text(), flags=re.S)
    return m.group(1) if m else ""


def normalise(md: str) -> str:
    """Undo the cosmetics Google's Doc <-> Markdown round-trip adds.

    Docs has no concept of our marker syntax, so importing content.md and then
    re-exporting it reshapes the file in predictable ways. Each is reversed
    here; the result is then validated, so anything unanticipated fails loudly
    rather than landing half-converted in content.md.
    """
    md = md.replace("\r\n", "\n").replace(" ", " ")
    # Unescape Google's \. \[ \_ ... — note '_' is \w, so it needs naming.
    md = re.sub(r"\\([^\w\s]|_)", r"\1", md)
    # Bare URLs come back as [url](url); collapse them (after unescaping, so
    # the label and href compare equal).
    md = re.sub(r"\[(https?://[^\]\s]+)\]\(\1\)", r"\1", md)

    # A doc title line sits above the first marker; it is chrome, not content.
    first = re.search(r"^\s*\[\[[A-Za-z0-9._-]+\]\]", md, flags=re.M)
    if first:
        md = md[first.start():]

    # Docs merges a marker into the paragraph that follows it ("[[k]] text"),
    # and pads markers that precede a heading/list with a blank line.
    md = re.sub(r"^(\[\[[A-Za-z0-9._-]+\]\])[ \t]+(?=\S)", r"\1\n", md, flags=re.M)
    md = re.sub(r"^[ \t]*(\[\[[A-Za-z0-9._-]+\]\])[ \t]*\n\n+", r"\1\n", md, flags=re.M)

    # The sources block is soft-wrapped lines inside one Docs paragraph, so it
    # returns as a single line. Split it back at each "[id]: ".
    m = re.search(r"^\[\[sources\]\]\n", md, flags=re.M)
    if m:
        head, block = md[:m.end()], md[m.end():]
        block = re.sub(r"[ \t]+(?=\[[A-Za-z0-9._-]+\]:\s)", "\n", block)
        md = head + block

    md = re.sub(r"[ \t]+$", "", md, flags=re.M)         # trailing hard-break spaces
    md = re.sub(r"\n{3,}", "\n\n", md)
    return _header() + md.strip() + "\n"


def validate(md: str) -> None:
    """Parse as the renderer would. Raises ContentError on anything wrong."""
    tmp = HERE / ".content.pull.tmp"
    tmp.write_text(md)
    try:
        c = Content(tmp)
        for sid in re.findall(r"\[\^([^\]]+)\]", md):
            if sid not in c.sources:
                raise ContentError(
                    f"prose cites [^{sid}] but no such id under [[sources]]")
        print(f"  parsed {len(c._raw)} keys, {len(c.sources)} sources")
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate only, don't write")
    ap.add_argument("--diff", action="store_true", help="show the pending change")
    args = ap.parse_args()

    print(f"fetching {EXPORT}")
    md = normalise(fetch())
    try:
        validate(md)
    except ContentError as e:
        print(f"\nREFUSED — the doc does not satisfy the report:\n  {e}", file=sys.stderr)
        print("content.md left untouched.", file=sys.stderr)
        return 1

    old = CONTENT.read_text() if CONTENT.exists() else ""
    if md == old:
        print("content.md already matches the doc — nothing to do.")
        return 0
    if args.diff or args.check:
        print("".join(difflib.unified_diff(
            old.splitlines(True), md.splitlines(True),
            fromfile="content.md (current)", tofile="content.md (from doc)")) or "(no diff)")
    if args.check:
        return 0
    CONTENT.write_text(md)
    print(f"wrote {CONTENT.relative_to(HERE.parent)} — now run `make html` and review the diff.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
