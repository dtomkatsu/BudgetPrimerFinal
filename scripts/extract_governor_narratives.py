"""Extract per-program 'Program Objective' narratives from the Governor's
budget PDFs, for use as hover tooltips in the HB1800 Draft Comparison tab.

Two sources are scanned in order (first-write wins):

 1. Governor's FY2027 Supplemental Budget PDFs (submitted Dec 2025)
    — data/raw/governor_supplemental_fy27/*.pdf
    — narrative pages titled "Narrative for Supplemental Budget Requests"
    — ONLY programs with requested changes have a narrative
    — ~140 programs covered

 2. Governor's FY2025-27 Executive Biennium Budget PDFs (submitted Dec 2024)
    — data/raw/governor_biennial_fy25-27/*.pdf
    — narrative pages titled "Program Plan Narrative" with
      "A. Statement of Program Objectives" section
    — EVERY program has a narrative (not just ones with changes)
    — fills in the ~138 programs missing from the supplemental

Output: docs/js/program_purposes.json

Narrative page structures (verified across multiple departments):

  Supplemental (S61-A adjacent):
    Narrative for Supplemental Budget Requests
    FY 2027
    Program ID: HMS 301
    Program Structure Level: 06 01 01
    Program Title: CHILD PROTECTIVE SERVICES
    A. Program Objective
      ...1-3 sentences...
    B. Description of Request
    C. Reasons for Request
    D. Significant Changes to Measures of Effectiveness and Program Size

  Biennial (P61-A adjacent):
    Program Plan Narrative
    HMS301: CHILD PROTECTIVE SERVICES            ← header, 5x glitch in most PDFs
    A. Statement of Program Objectives
      ...1-3 sentences...
    B. Description of Request and Compliance with Section 37-68(1)(A)(B)
    C. Description of Activities Performed
    D. Statement of Key Policies Pursued
    E. Identification of Important Program Relationships

We capture section A (Objective) only.  Later sections describe the request
delta or activity detail, which would overflow a reasonable tooltip.

Phase 2 (deferred): committee reports (HSCR/SSCR/CCR) at
https://data.capitol.hawaii.gov/sessions/session2026/commreports/ could
fill in per-change context.  The output JSON carries a `source` field on
each record so a later pass can add entries without any SPA changes.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

import pdfplumber


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "docs" / "js" / "program_purposes.json"

# Max chars for a tooltip-friendly objective.  Most Objectives are 100-300
# chars; a handful (e.g. UOH100) run 3000+.  Cap at 500 and truncate at the
# last sentence boundary before the limit.
OBJECTIVE_CHAR_CAP = 500

# Some biennial/supplemental PDFs have a text-layer glitch that duplicates
# every glyph N times (N observed: 2, 3, 4, 5).  The duplication factor
# varies by PDF and sometimes by page (cropping a 2x PDF can produce 4x
# text).  We handle all flavors with a single per-token GCD collapse:
#
# For a token like "SSCCHHOOOOLL" (2x of "SCHOOL" — the legit double O
# shows as "OOOO"), the run-lengths are [S:2, C:2, H:2, O:4, L:2].  GCD=2.
# Divide every run by 2 → [S:1, C:1, H:1, O:2, L:1] → "SCHOOL".  Likewise
# "EEEDDDNNN444000000:::" (3x of "EDN400:::") gives runs all multiples of
# 3, GCD=3 → "EDN400:".
#
# Tokens with GCD=1 (normal English like "bookkeeper", "committee") are
# left unchanged.  We only attempt collapse on tokens that contain at least
# one run of 4+ identical chars, so clean body text is never touched.
GLITCH_TOKEN_RE = re.compile(r"[A-Za-z0-9&\-:,.']+")
GLITCH_MARKER_RE = re.compile(r'(.)\1{2}')          # 3+ identical = suspicious
PAIR_RE = re.compile(r'([A-Za-z])\1')               # consecutive letter pair


def _collapse_token(token: str) -> str:
    """If every run-length in `token` shares a common divisor > 1, collapse
    by that factor.  Otherwise return the token unchanged.

    Accepts two shapes of glitched tokens:
      * 3x+ glitches ("EEDDNN400", "LLLNNNRRR"): any run of 3+ identical
        chars plus a uniform GCD factor.
      * 2x glitches ("LLNNRR101"): ALL runs are exactly length 2, giving
        GCD=2 without any triple.  Clean English tokens almost never have
        every letter paired (e.g. "MAUI" → [M:1,A:1,U:1,I:1], GCD=1), so
        this pattern is a very strong glitch signal."""
    has_triple = bool(GLITCH_MARKER_RE.search(token))
    # Compute run-lengths once.
    runs: list[tuple[str, int]] = []
    i = 0
    n = len(token)
    while i < n:
        j = i
        while j < n and token[j] == token[i]:
            j += 1
        runs.append((token[i], j - i))
        i = j
    if len(runs) <= 1:
        return token  # single run ("AAAA") — ambiguous, leave alone
    from math import gcd
    from functools import reduce
    g = reduce(gcd, (r[1] for r in runs))
    if g < 2:
        return token  # no uniform factor
    # Accept collapse when either (a) we saw a 3+ run (stronger signal),
    # or (b) EVERY run is exactly the GCD (pure-2x pattern, no lone-char
    # outliers — essentially impossible in clean text).
    if not has_triple and not all(r[1] == g for r in runs):
        return token
    return ''.join(c * (length // g) for c, length in runs)


PUNCT_RUN_RE = re.compile(r"([^\w\s])\1{2,}")


def clean_repeat(text: str) -> str:
    """Collapse per-token char-repeat glitches (2x/3x/4x/5x) using a
    GCD-based run-length reduction.  Also collapse runs of 3+ identical
    non-alphanumeric chars (handles standalone glitched punctuation like
    '&&&&&', '-----', '((((...))))')."""
    text = GLITCH_TOKEN_RE.sub(lambda m: _collapse_token(m.group(0)), text)
    text = PUNCT_RUN_RE.sub(r"\1", text)
    return text


def needs_repeat_cleanup(text: str) -> bool:
    """Return True if the text is likely glitch-duplicated.

    Fires when either (a) any token has a 3+ identical run (catches 3x/4x/5x
    glitches), or (b) the text exhibits heavy letter-pairing — >30% of
    letters are immediately followed by the same letter (catches 2x
    glitches, which lack triples entirely)."""
    if GLITCH_MARKER_RE.search(text):
        return True
    # 2x-glitch detection: count paired-letter density.
    letters = sum(1 for c in text if c.isalpha())
    if letters < 40:
        return False
    pairs = len(PAIR_RE.findall(text))
    return pairs / letters > 0.30


def extract_page_text(page) -> str:
    """Extract narrative-page text, handling (a) the 5x char-repeat glitch
    and (b) two-column body layouts.

    The narrative pages use a single-column HEADER block followed by a
    two-column BODY.  Naive page.extract_text() interleaves the two
    columns, breaking the Objective extraction.  We always split into
    left/right halves using page.crop() bboxes — for genuinely single-
    column pages the right-half crop returns minimal text and the
    concatenation still parses cleanly.
    """
    w, h = page.width, page.height
    midx = w / 2
    left = page.crop((0, 0, midx + 4, h)).extract_text() or ""
    right = page.crop((midx - 4, 0, w, h)).extract_text() or ""

    if needs_repeat_cleanup(left) or needs_repeat_cleanup(right):
        left = clean_repeat(left)
        right = clean_repeat(right)

    return left + "\n" + right


def normalize_objective(raw: str) -> str:
    """Fold line-wraps, collapse whitespace, strip leading bullet cruft,
    and cap at a tooltip-friendly length."""
    s = re.sub(r'\s+', ' ', raw).strip()
    s = re.sub(r'^[\-\*\u2022\s]+', '', s)
    if len(s) > OBJECTIVE_CHAR_CAP:
        head = s[:OBJECTIVE_CHAR_CAP]
        # Truncate at the last sentence-ending punctuation so the tooltip
        # reads as a complete thought.
        m = re.search(r'.*[.!?](?=\s|$)', head, re.DOTALL)
        if m:
            s = m.group(0).strip()
        else:
            s = head.rstrip() + "…"
    return s


# ---------------------------------------------------------------------------
# Source configs
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Source:
    label: str                          # human-readable source name
    tag: str                            # value for `source` field in output
    pdf_dir: pathlib.Path
    narrative_marker: str               # substring that identifies a narrative page
    prog_id_re: re.Pattern[str]         # captures (dept, number)
    title_re: re.Pattern[str] | None    # optional: if None, skip title extraction
    objective_re: re.Pattern[str]       # captures objective body (group 1)


# --- Supplemental (FY2027) -------------------------------------------------
SUPPLEMENTAL = Source(
    label="Governor's Executive Supplemental Budget FY2027",
    tag="governor_supplemental_fy27",
    pdf_dir=REPO_ROOT / "data" / "raw" / "governor_supplemental_fy27",
    narrative_marker="Narrative for Supplemental Budget Requests",
    prog_id_re=re.compile(r'Program\s+ID:\s*([A-Z]{3})\s*(\d+)', re.IGNORECASE),
    title_re=re.compile(r'Program\s+Title:\s*(.+?)(?:\n|$)', re.IGNORECASE),
    # "A. Program Objective" and "A.Program Objective" (TAX has no space)
    objective_re=re.compile(
        r'A\.\s*Program\s+Objective\s*\n(.*?)'
        r'(?=\n\s*B\.\s*Description\s+of\s+Request|\Z)',
        re.DOTALL | re.IGNORECASE,
    ),
)

# --- Biennial (FY2025-27) --------------------------------------------------
# Header line after 5x cleanup looks like:
#    AGR101: FINANCIAL ASSISTANCE FOR AGRICULTURE 01 03 01
# or HTH 840: ENVIRONMENTAL MANAGEMENT 04 01 01
# We capture the "XXX[ ]NNN" at the start of any line that is followed by ":".
# Anchor with optional leading whitespace.
BIENNIAL = Source(
    label="Governor's Executive Biennium Budget FY2025-27",
    tag="governor_biennial_fy25-27",
    pdf_dir=REPO_ROOT / "data" / "raw" / "governor_biennial_fy25-27",
    narrative_marker="Statement of Program Objectives",
    prog_id_re=re.compile(
        r'^[ \t]*([A-Z]{3})\s*(\d{3,4}):',
        re.MULTILINE,
    ),
    # Biennial title comes from the header line itself: "XXX###: TITLE ..."
    title_re=re.compile(
        r'^[ \t]*[A-Z]{3}\s*\d{3,4}:\s*(.+?)(?:\n|$)',
        re.MULTILINE,
    ),
    # "A. Statement of Program Objectives" up to "B. Description of Request".
    # The biennial "B." header continues as "B. Description of Request and
    # Compliance with Section 37-68(1)(A)(B)".
    objective_re=re.compile(
        r'A\.\s*Statement\s+of\s+Program\s+Objectives\s*\n(.*?)'
        r'(?=\n\s*B\.\s*Description\s+of\s+Request|\Z)',
        re.DOTALL | re.IGNORECASE,
    ),
)

# --- Biennial (FY2023-25) — previous biennium, used as fallback -----------
# The FY25-27 biennial PDF has several programs with entirely text-stripped
# narrative pages (most notably LNR 101/102/111/802/907/908), and a few
# others where the narrative page was omitted altogether (e.g. HTH520).  The
# FY23-25 PDFs are older but carry the same "Program Plan Narrative" format
# and for these programs the text layer is intact.  Objectives describe the
# same purpose (what the program does) and rarely change year-to-year, so
# they fill the gaps well.
#
# Format quirks vs FY25-27:
#   * Heading glyphs extract with commas/lowercase instead of periods —
#     "A, statement of Program Objectives" instead of "A. Statement of …".
#   * Several pages have 2x or 7x character-repeat glitches (handled by the
#     updated _collapse_token).
#   * The narrative marker itself may appear with mixed case after glitch
#     cleanup, so we match case-insensitively.
BIENNIAL_PRIOR = Source(
    label="Governor's Executive Biennium Budget FY2023-25",
    tag="governor_biennial_fy23-25",
    pdf_dir=REPO_ROOT / "data" / "raw" / "governor_biennial_fy23-25",
    narrative_marker="statement of Program Objectives",  # lowercase-s form seen here
    prog_id_re=re.compile(
        r'^[ \t]*([A-Z]{3})\s*(\d{3,4}):',
        re.MULTILINE,
    ),
    title_re=re.compile(
        r'^[ \t]*[A-Z]{3}\s*\d{3,4}:\s*(.+?)(?:\n|$)',
        re.MULTILINE,
    ),
    # Flexible A/B section headers — accept either "A." or "A," and accept
    # either "Statement" or "statement" (OCR quirk in FY23-25).
    objective_re=re.compile(
        r'A[,.]?\s*[Ss]tatement\s+of\s+Program\s+Objectives\s*\n(.*?)'
        r'(?=\n\s*B[,.]?\s*Description\s+of\s+Request|\Z)',
        re.DOTALL,
    ),
)

SOURCES: list[Source] = [SUPPLEMENTAL, BIENNIAL, BIENNIAL_PRIOR]


def extract_narrative(txt: str, source: Source) -> dict | None:
    """Parse a narrative page's text per the source config and return
    {prog_id, objective, title}, or None if not a valid narrative record."""
    pid_m = source.prog_id_re.search(txt)
    if not pid_m:
        return None
    prog_id = f"{pid_m.group(1).upper()}{pid_m.group(2)}"

    title = ""
    if source.title_re:
        title_m = source.title_re.search(txt)
        if title_m:
            # Biennial titles include trailing structure numbers like
            # "FINANCIAL ASSISTANCE FOR AGRICULTURE 01 03 01" — strip.
            raw_title = title_m.group(1).strip()
            raw_title = re.sub(r'\s+\d{2}(?:\s+\d{2}){1,3}\s*$', '', raw_title)
            title = raw_title.strip()

    obj_m = source.objective_re.search(txt)
    if not obj_m:
        return None
    objective = normalize_objective(obj_m.group(1))
    if not objective:
        return None

    return {"program_id": prog_id, "objective": objective, "title": title}


def process_pdf(pdf_path: pathlib.Path, source: Source) -> dict[str, dict]:
    """Iterate a single department PDF per source config.  Returns
    {prog_id: record}."""
    stem = pdf_path.stem
    parts = stem.split("_", 1)
    dept_code = (parts[1] if len(parts) == 2 else stem).upper()

    marker_lc = source.narrative_marker.lower()
    records: dict[str, dict] = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw = page.extract_text() or ""
            probe = clean_repeat(raw) if needs_repeat_cleanup(raw) else raw
            # Case-insensitive marker check — FY23-25 PDFs sometimes extract
            # the heading "Statement" as "statement" due to stylized glyphs.
            if marker_lc not in probe.lower():
                continue
            txt = extract_page_text(page)
            rec = extract_narrative(txt, source)
            if not rec:
                continue
            prog_id = rec.pop("program_id")
            if prog_id in records:
                continue  # first page's version wins
            records[prog_id] = {
                "objective": rec["objective"],
                "title": rec["title"],
                "department": dept_code,
                "source": source.tag,
            }
    return records


def process_source(source: Source, all_records: dict[str, dict]) -> dict[str, int]:
    """Scan every PDF in a source directory.  Only insert records for
    programs NOT already in all_records (first source wins).  Returns a
    per-department count of NEWLY added programs from this source."""
    if not source.pdf_dir.exists():
        print(f"[{source.tag}] directory {source.pdf_dir} not found — skipping")
        return {}

    pdf_paths = sorted(source.pdf_dir.glob("*.pdf"))
    if not pdf_paths:
        print(f"[{source.tag}] no PDFs — skipping")
        return {}

    print(f"\n=== {source.label} ===")
    dept_counts: dict[str, int] = {}
    for pdf_path in pdf_paths:
        stem = pdf_path.stem
        parts = stem.split("_", 1)
        dept_label = (parts[1] if len(parts) == 2 else stem).upper()
        print(f"Parsing {pdf_path.name} ...", end=" ", flush=True)
        try:
            records = process_pdf(pdf_path, source)
        except Exception as e:
            print(f"FAILED: {e}")
            dept_counts[dept_label] = 0
            continue

        added = 0
        for pid, rec in records.items():
            if pid not in all_records:
                all_records[pid] = rec
                added += 1
        dept_counts[dept_label] = added
        total = len(records)
        print(f"{added:3d} new (+{total - added:>2d} already covered)")
    return dept_counts


def main() -> int:
    all_records: dict[str, dict] = {}
    per_source_counts: dict[str, dict[str, int]] = {}
    for source in SOURCES:
        counts = process_source(source, all_records)
        per_source_counts[source.tag] = counts

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # Totals by source for quick inspection.
    by_source_totals = {
        tag: sum(c.values()) for tag, c in per_source_counts.items()
    }
    payload = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sources": [s.label for s in SOURCES],
            "program_count": len(all_records),
            "by_source": by_source_totals,
            "per_source_per_department_counts": {
                tag: dict(sorted(c.items())) for tag, c in per_source_counts.items()
            },
        },
        "purposes": dict(sorted(all_records.items())),
    }
    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print()
    print(f"Total unique programs covered: {len(all_records)}")
    for tag, total in by_source_totals.items():
        print(f"  {tag}: {total} new")
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
