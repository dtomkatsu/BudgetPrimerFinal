"""Extract per-program adjustment reasons from the HB1800 worksheet PDFs
and merge them into the existing draft_comparison_fy{26,27}.json files.

Sources
-------
- EXEC_HB1800_HD1_SD1_Worksheets.pdf  → Senate adjustments to the
  Governor's supplemental.  Marker: ``Detail Type: S``.  Each
  adjustment block is delimited by a ``SEQ #`` of the form ``\\d{4}-\\d{3}``,
  carries a one-line title under ``SENATE ADJUSTMENT:``, then a more
  procedural ``DETAIL OF SENATE ADJUSTMENT:`` paragraph.

- HB1800 SD-HD DISAGREE.pdf           → Two-column comparison.  Left
  half is HD; right half is SD.  The right half exactly mirrors EXEC's
  Senate content (verified: both have 927 SENATE labels) so we ignore
  it for the Senate stream and use the LEFT half as the canonical
  source for ``HOUSE ADJUSTMENT:`` text.

- HB1800 SD-HD AGREE.pdf              → Skipped.  Totals-only
  reconciliation; no reason text.

Output
------
The reason text is the title line (e.g. ``REDUCE FUNDS FOR FINANCIAL
ASSISTANCE FOR AGRICULTURE (AGR101).``).  Multiple adjustments under
one program are joined with ``; `` so a single tooltip carries the
full Senate (or House) story.

Reasons are merged in place into ``docs/js/draft_comparison_fy{26,27}.json``.
The SPA's existing ``loadDraftComparison()`` already fetches these
files — the new ``reason_sd_change`` / ``reason_hd_change`` fields ride
along without any loader changes.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterator

import pdfplumber

REPO_ROOT = pathlib.Path(__file__).parent.parent
WORKSHEET_DIR = pathlib.Path.home() / "Downloads" / "HB 1800 Budget Worksheets"
EXEC_PDF = WORKSHEET_DIR / "EXEC_HB1800_HD1_SD1_Worksheets.pdf"
DISAGREE_PDF = WORKSHEET_DIR / "HB1800 SD-HD DISAGREE.pdf"
COMPARISON_PATHS = [
    REPO_ROOT / "docs" / "js" / "draft_comparison_fy26.json",
    REPO_ROOT / "docs" / "js" / "draft_comparison_fy27.json",
]

# Each block on a page starts with a SEQ # like "2060-001".  Anchored to
# start-of-line because amounts elsewhere in the page (e.g. position
# numbers like "(#118369)" or position counts "100-001") could otherwise
# false-positive — we want the block delimiter, not arbitrary digits.
SEQ_RE = re.compile(r'^\s*(\d{4}-\d{3})\b', re.MULTILINE)
PROG_RE = re.compile(r'Program ID:\s+([A-Z]{3}\d{3,4})\b')
# The label line is what tells us which chamber owned this SEQ.  Two
# layout variants the regex has to absorb:
#   EXEC  →  "2060-001 SENATE ADJUSTMENT: (212,754) A\nREDUCE FUNDS..."
#   DISAGR → "SENATE ADJUSTMENT:\nREDUCE FUNDS..."
# In both, the title body is the FIRST line after the ``ADJUSTMENT:``
# label and runs until the row of asterisks that delimits the
# ``DETAIL OF`` block.  Negative lookbehind keeps us from matching the
# ``DETAIL OF SENATE ADJUSTMENT:`` header itself, which would otherwise
# steal the detail text as the title.  Unlabelled SEQs (the empty side
# of a DISAGREE page) are correctly skipped.
LBL_RE = re.compile(
    r'(?<!DETAIL OF )(SENATE|HOUSE|GOVERNOR)\s+ADJUSTMENT:[^\n]*\n'
    r'(.+?)(?=\n\s*\*{5,}|\Z)',
    re.DOTALL | re.IGNORECASE,
)


@dataclass
class Reasons:
    """Per-program reason buckets, in insertion order."""
    senate: list[str] = field(default_factory=list)
    house:  list[str] = field(default_factory=list)


_WS_RE = re.compile(r'\s+')


def iter_blocks(text: str) -> Iterator[tuple[str, str, str]]:
    """Yield (seq, chamber, title) for each labelled adjustment block in
    ``text``.  Unlabelled SEQs (the common case for the empty side of a
    DISAGREE page) are skipped — they're a hint that *the other* column
    carries the reason, not a missing-data error.

    Title text routinely wraps across 2–3 PDF lines (the worksheet
    column is narrow), so we collapse all whitespace within the
    captured body into single spaces and trim — yielding one clean
    sentence ending in a period.
    """
    matches = list(SEQ_RE.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.start():end]
        lbl = LBL_RE.search(block)
        if not lbl:
            continue
        chamber = lbl.group(1).upper()
        title = _WS_RE.sub(' ', lbl.group(2)).strip()
        if title:
            yield m.group(1), chamber, title


def collect_program_for_page(text: str, reasons_by_id: dict[str, Reasons],
                             chamber_filter: set[str] | None = None) -> None:
    """Slot each block on a page into the right ``Reasons`` bucket.

    ``chamber_filter`` lets the caller restrict which chambers we
    accept from this slice of text — used to keep DISAGREE's left
    column pure-House and right column pure-Senate, even if a stray
    label leaks across the column boundary.
    """
    prog_match = PROG_RE.search(text)
    if not prog_match:
        return
    pid = prog_match.group(1)
    rec = reasons_by_id.setdefault(pid, Reasons())
    for _seq, chamber, title in iter_blocks(text):
        if chamber_filter and chamber not in chamber_filter:
            continue
        bucket = rec.senate if chamber == 'SENATE' else \
                 rec.house  if chamber == 'HOUSE'  else None
        if bucket is None:
            continue
        # Dedupe: a few programs span pages, so the same SEQ can appear
        # twice with identical text.  Cheap O(n) check is fine — each
        # bucket caps at single-digit length in practice.
        if title not in bucket:
            bucket.append(title)


def parse_exec(reasons_by_id: dict[str, Reasons]) -> int:
    """Walk the EXEC PDF and accumulate Senate reasons.  Returns count
    of (program, SEQ) pairs added — useful for sanity output.
    """
    added = 0
    with pdfplumber.open(EXEC_PDF) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ''
            before = sum(len(r.senate) for r in reasons_by_id.values())
            collect_program_for_page(txt, reasons_by_id, chamber_filter={'SENATE'})
            after = sum(len(r.senate) for r in reasons_by_id.values())
            added += (after - before)
    return added


def parse_disagree_house(reasons_by_id: dict[str, Reasons]) -> int:
    """Walk the DISAGREE PDF, splitting each page into left/right halves
    via ``page.crop()``.  Only the LEFT half feeds the House bucket;
    the right half mirrors EXEC's Senate stream and is ignored here.
    """
    added = 0
    with pdfplumber.open(DISAGREE_PDF) as pdf:
        for page in pdf.pages:
            w, h = page.width, page.height
            left_text = page.crop((0, 0, w / 2, h)).extract_text() or ''
            # The program-ID line lives in the page header band, which
            # ``page.crop`` clips to whichever half it falls in.  In
            # practice the label sits in the left column at our split
            # point, so it's already in ``left_text`` — but if we ever
            # see a layout shift, fall back to the whole-page text for
            # the program lookup.
            if not PROG_RE.search(left_text):
                full = page.extract_text() or ''
                pm = PROG_RE.search(full)
                if pm:
                    left_text = f"Program ID: {pm.group(1)}\n" + left_text
            before = sum(len(r.house) for r in reasons_by_id.values())
            collect_program_for_page(left_text, reasons_by_id, chamber_filter={'HOUSE'})
            after = sum(len(r.house) for r in reasons_by_id.values())
            added += (after - before)
    return added


def to_sentence(titles: list[str]) -> str:
    """Join multiple title lines into one tooltip-friendly sentence.

    Each title typically already ends with a period; we normalize so
    the joined string ends in exactly one period and the separators
    read naturally ("X; Y; Z.").
    """
    if not titles:
        return ''
    cleaned = [t.rstrip().rstrip('.') for t in titles]
    return '; '.join(cleaned) + '.'


def merge_into_comparison(reasons_by_id: dict[str, Reasons],
                          comparison_path: pathlib.Path) -> tuple[int, int]:
    """Write ``reason_sd_change`` / ``reason_hd_change`` into each row of
    the given comparison JSON.  House reasons are only emitted when
    HD ≠ SD — when the chambers landed on the same number, the Senate
    reason carries the whole story and a duplicate House line would
    just clutter the tooltip.
    """
    data = json.loads(comparison_path.read_text())
    sd_added = hd_added = 0
    for row in data['comparisons']:
        rec = reasons_by_id.get(row['program_id'])
        if not rec:
            continue
        sd_text = to_sentence(rec.senate)
        if sd_text:
            row['reason_sd_change'] = sd_text
            sd_added += 1
        hd_diff = abs((row.get('amount_hd1') or 0) - (row.get('amount_sd1') or 0)) > 1
        if rec.house and hd_diff:
            row['reason_hd_change'] = to_sentence(rec.house)
            hd_added += 1
    comparison_path.write_text(json.dumps(data, indent=2))
    return sd_added, hd_added


def main() -> int:
    if not EXEC_PDF.exists():
        print(f"ERROR: {EXEC_PDF} not found", file=sys.stderr)
        return 1
    if not DISAGREE_PDF.exists():
        print(f"ERROR: {DISAGREE_PDF} not found", file=sys.stderr)
        return 1

    reasons: dict[str, Reasons] = {}

    print(f"Parsing EXEC ({EXEC_PDF.name}) ...", flush=True)
    sen_count = parse_exec(reasons)
    print(f"  Senate adjustments captured: {sen_count}")

    print(f"Parsing DISAGREE ({DISAGREE_PDF.name}, House column only) ...", flush=True)
    hou_count = parse_disagree_house(reasons)
    print(f"  House adjustments captured: {hou_count}")

    # Per-bucket program counts before merge
    senate_progs = sum(1 for r in reasons.values() if r.senate)
    house_progs  = sum(1 for r in reasons.values() if r.house)
    print(f"\nDistinct programs with Senate reasons: {senate_progs}")
    print(f"Distinct programs with House reasons:  {house_progs}")
    print(f"Distinct programs total:                {len(reasons)}")

    print("\nMerging into draft_comparison_fy*.json ...")
    for path in COMPARISON_PATHS:
        if not path.exists():
            print(f"  SKIP {path.name} (missing)")
            continue
        sd, hd = merge_into_comparison(reasons, path)
        print(f"  {path.name}: reason_sd_change on {sd} rows, "
              f"reason_hd_change on {hd} rows")

    return 0


if __name__ == '__main__':
    sys.exit(main())
