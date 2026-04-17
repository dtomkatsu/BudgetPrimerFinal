"""Parse Governor's Supplemental Budget FY2027 PDFs.

Input:  data/raw/governor_supplemental_fy27/*.pdf
Outputs:
  - docs/js/governor_request.json       (S61-A operating + capital program totals)
  - docs/js/governor_projects.json      (S78 per-project capital details)

Schema: matches fy_comparison.json record shape
  { program_id, program_name, department_code, department_name,
    fund_type, fund_category, section, amount_fy2026, amount_fy2027 }

Approach:
- S61-A "Operating Budget Details" pages contain both operating AND capital
  totals for each program, with columns:
    FY26 CURR APPRN | FY26 ADJUST | FY26 REC APPRN |
    FY27 CURR APPRN | FY27 ADJUST | FY27 REC APPRN |
    BIENNIUM CURR | BIENNIUM REC | % CHANGE
- We extract the RECOMMENDED APPRN (REC) columns for FY26 and FY27.
- Use pdfplumber character-level positions to identify columns
  (blank adjustments collapse text but not x-position).
- Skip rollup pages (program_id without a 3-digit suffix).
- Split each page into operating (before "CAPITAL INVESTMENT") and
  capital (after "TOTAL CAPITAL COST") sections; emit fund rows for each.
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

# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------

# Department code → display name (matches existing app data)
DEPARTMENT_NAMES = {
    "AGS": "Department of Accounting & General Services",
    "AGR": "Department of Agriculture",
    "ATG": "Department of the Attorney General",
    "BUF": "Department of Budget & Finance",
    "BED": "Department of Business, Economic Development & Tourism",
    "CCA": "Department of Commerce & Consumer Affairs",
    "CCR": "Department of Corrections and Rehabilitation",
    "PSD": "Department of Corrections and Rehabilitation",  # legacy code
    "DEF": "Department of Defense",
    "EDN": "Department of Education",
    "GOV": "Office of the Governor",
    "HHL": "Department of Hawaiian Home Lands",
    "HTH": "Department of Health",
    "HRD": "Department of Human Resources Development",
    "HMS": "Department of Human Services",
    "LBR": "Department of Labor & Industrial Relations",
    "LNR": "Department of Land & Natural Resources",
    "LAW": "Department of Law Enforcement",
    "LTG": "Office of the Lieutenant Governor",
    "TAX": "Department of Taxation",
    "TRN": "Department of Transportation",
    "UOH": "University of Hawaii",
}

# Fund source label (as it appears in PDF) → (fund_type letter, fund_category)
# Must match existing app schema — see docs/js/fy_comparison.json
FUND_MAP = {
    "GENERAL FUND":              ("A", "General Funds"),
    "GENERAL FUNDS":             ("A", "General Funds"),
    "SPECIAL FUND":              ("B", "Special Funds"),
    "SPECIAL FUNDS":             ("B", "Special Funds"),
    "G.O. BONDS":                ("C", "General Obligation Bond Fund"),
    "GENERAL OBLIGATION BONDS":  ("C", "General Obligation Bond Fund"),
    "REVENUE BOND FUND":         ("E", "Revenue Bond Funds"),
    "REVENUE BOND FUNDS":        ("E", "Revenue Bond Funds"),
    "REVENUE BONDS":             ("E", "Revenue Bond Funds"),
    "G.O.BONDS":                 ("C", "General Obligation Bond Fund"),
    "G.O. REIMBURSABLE BONDS":   ("C", "General Obligation Bond Fund"),
    "G.O.REIMBURSABLE BONDS":    ("C", "General Obligation Bond Fund"),
    "FEDERAL FUND":              ("N", "Federal Funds"),
    "FEDERAL FUNDS":             ("N", "Federal Funds"),
    "OTHER FEDERAL FUND":        ("P", "Other Federal Funds"),
    "OTHER FEDERAL FUNDS":       ("P", "Other Federal Funds"),
    "PRIVATE CONTRIBUTIONS":     ("R", "Private Contributions"),
    "PRIVATE CONTRIB.":          ("R", "Private Contributions"),
    "PRIVATE CONTRIB":           ("R", "Private Contributions"),
    "COUNTY FUND":               ("S", "County Funds"),
    "COUNTY FUNDS":              ("S", "County Funds"),
    "TRUST FUND":                ("T", "Trust Funds"),
    "TRUST FUNDS":               ("T", "Trust Funds"),
    "INTERDEPT. TRANSF":         ("U", "Interdepartmental Transfers"),
    "INTERDEPT TRANSF":          ("U", "Interdepartmental Transfers"),
    "INTERDEPARTMENTAL TRANSFER":("U", "Interdepartmental Transfers"),
    "REVOLVING FUND":            ("W", "Revolving Funds"),
    "REVOLVING FUNDS":           ("W", "Revolving Funds"),
    "OTHER FUND":                ("X", "Other Funds"),
    "OTHER FUNDS":               ("X", "Other Funds"),
}

# Sort fund labels by length desc so "OTHER FEDERAL FUNDS" matches before "FEDERAL FUNDS"
FUND_LABELS_SORTED = sorted(FUND_MAP.keys(), key=len, reverse=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class ColumnMap:
    """x-range (right edge) for each column in the budget table."""
    fy26_curr: float
    fy26_adj: float
    fy26_rec: float
    fy27_curr: float
    fy27_adj: float
    fy27_rec: float
    bien_curr: float
    bien_rec: float

    def assign(self, x1: float) -> str | None:
        """Given a number's right edge x, return which column it belongs to."""
        # Numbers are right-aligned; x1 ≈ column header's right edge + ~15-20px
        # Accept any number whose x1 is within tolerance of a column edge
        TOL = 25.0
        candidates = [
            ("fy26_curr", self.fy26_curr),
            ("fy26_adj",  self.fy26_adj),
            ("fy26_rec",  self.fy26_rec),
            ("fy27_curr", self.fy27_curr),
            ("fy27_adj",  self.fy27_adj),
            ("fy27_rec",  self.fy27_rec),
            ("bien_curr", self.bien_curr),
            ("bien_rec",  self.bien_rec),
        ]
        best = min(candidates, key=lambda c: abs(c[1] + 17 - x1))
        if abs(best[1] + 17 - x1) > TOL:
            return None
        return best[0]


def detect_columns(words: list[dict]) -> ColumnMap | None:
    """Find header row and return x-coordinates of each column's right edge.

    The S61-A header spans multiple visual lines:
      Line A: "FY 2026   FY 2027   BIENNIUM TOTALS"
      Line B: "CURRENT RECOMMEND  CURRENT RECOMMEND  CURRENT RECOMMEND  PERCENT"
      Line C: "PROGRAM COSTS APPRN ADJUSTMENT APPRN   APPRN ADJUSTMENT APPRN  BIENNIUM BIENNIUM CHANGE"

    We collect all words labelled APPRN/ADJUSTMENT/BIENNIUM/CHANGE regardless
    of y-grouping (tolerance), then sort by x to recover column order.
    """
    # Collect all candidate header words (ignore which row they fell into)
    candidates = [
        w for w in words
        if w["text"] in {"APPRN", "ADJUSTMENT", "BIENNIUM", "CHANGE"}
    ]
    # Filter to rows near the top of the page (header is always at top, y<150)
    candidates = [w for w in candidates if w["top"] < 150]

    if not candidates:
        return None

    # Sort by x
    candidates.sort(key=lambda w: w["x0"])
    labels = [w["text"] for w in candidates]

    # Expected pattern (left to right by x):
    #   APPRN, ADJUSTMENT, APPRN, APPRN, ADJUSTMENT, APPRN, BIENNIUM, BIENNIUM, CHANGE
    # Validate
    if labels.count("APPRN") < 4 or labels.count("ADJUSTMENT") < 2 or labels.count("BIENNIUM") < 2 or "CHANGE" not in labels:
        return None

    # Take only the first occurrence of each in positional order
    # Walk through candidates and consume in expected order
    expected = ["APPRN", "ADJUSTMENT", "APPRN", "APPRN", "ADJUSTMENT", "APPRN", "BIENNIUM", "BIENNIUM", "CHANGE"]
    result: list[dict] = []
    idx = 0
    for w in candidates:
        if idx < len(expected) and w["text"] == expected[idx]:
            result.append(w)
            idx += 1
    if len(result) < 9:
        return None

    xs = [w["x1"] for w in result]
    return ColumnMap(
        fy26_curr=xs[0],
        fy26_adj=xs[1],
        fy26_rec=xs[2],
        fy27_curr=xs[3],
        fy27_adj=xs[4],
        fy27_rec=xs[5],
        bien_curr=xs[6],
        bien_rec=xs[7],
    )


def group_by_row(words: list[dict], y_tolerance: float = 2.0) -> list[list[dict]]:
    """Group words into rows based on y-coordinate."""
    rows: list[list[dict]] = []
    current: list[dict] = []
    current_y: float | None = None
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if current_y is None or abs(w["top"] - current_y) <= y_tolerance:
            current.append(w)
            current_y = w["top"] if current_y is None else current_y
        else:
            rows.append(sorted(current, key=lambda w: w["x0"]))
            current = [w]
            current_y = w["top"]
    if current:
        rows.append(sorted(current, key=lambda w: w["x0"]))
    return rows


def _parse_num(text: str) -> float | None:
    """Parse a number like '4,551,872' or '-98,165' or '1.10'.

    Also tolerates trailing decorative characters like '-', '.', '..' which
    appear as visual artifacts in the Governor's PDF tables.
    """
    t = text.strip().replace(",", "").replace("$", "")
    # Strip trailing decorative dashes/dots (not a negative sign)
    t = re.sub(r"[-.\s]+$", "", t)
    if not t or t in {"-", "*", "**"}:
        return None
    if re.fullmatch(r"-?\d+(\.\d+)?", t):
        try:
            return float(t)
        except ValueError:
            return None
    return None


def _coalesce_split_numbers(row_words: list[dict]) -> list[dict]:
    """Merge number fragments split by pdfplumber.

    Patterns seen:
      '2,291,497,' + '122'  ->  '2,291,497,122'
      '1,076,466,906-'      ->  '1,076,466,906'  (handled in _parse_num)

    Heuristic: if a word's text ends with ',' (trailing comma) and the next
    word by x0 starts with digits, merge them.
    """
    if not row_words:
        return row_words
    ws = sorted(row_words, key=lambda w: w["x0"])
    out: list[dict] = []
    i = 0
    while i < len(ws):
        cur = ws[i]
        if (i + 1 < len(ws)
            and cur["text"].endswith(",")
            and re.fullmatch(r"\d+", ws[i + 1]["text"])
            and ws[i + 1]["x0"] - cur["x1"] < 3):
            nxt = ws[i + 1]
            merged = dict(cur)
            merged["text"] = cur["text"] + nxt["text"]
            merged["x1"] = nxt["x1"]
            out.append(merged)
            i += 2
        else:
            out.append(cur)
            i += 1
    return out


def extract_row_values(row_words: list[dict], cols: ColumnMap) -> dict[str, float]:
    """Extract numeric values from a row, assigning each number to a column."""
    row_words = _coalesce_split_numbers(row_words)
    values: dict[str, float] = {}
    for w in row_words:
        val = _parse_num(w["text"])
        if val is None:
            continue
        # Skip position-count markers (they have * or ** in adjacent word)
        # e.g. "24.00*" or "23.00**" — these are already filtered by _parse_num
        # but decimals with asterisks slip through if '*' was attached
        col = cols.assign(w["x1"])
        if col is None:
            continue
        # First write wins for a given column (data rows are small)
        if col not in values:
            values[col] = val
    return values


def match_fund(row_text: str) -> tuple[str, str] | None:
    """Return (fund_type, fund_category) if row starts with a known fund label."""
    # Normalize whitespace
    norm = re.sub(r"\s+", " ", row_text.strip().upper())
    for label in FUND_LABELS_SORTED:
        if norm.startswith(label):
            return FUND_MAP[label]
    return None


def extract_program_header(text: str) -> tuple[str, str] | None:
    """Parse 'PROGRAM ID: XXX-NNN' + 'PROGRAM TITLE: ...' from page text.

    Returns (program_id, program_name) or None if not a leaf detail page.
    program_id is normalized to 'XXXNNN' (no dash).
    """
    # Must have both PROGRAM ID and a 3-digit number
    pid_match = re.search(r"PROGRAM\s+ID:\s*([A-Z]{3})-(\d{3})\b", text)
    if not pid_match:
        return None
    program_id = f"{pid_match.group(1)}{pid_match.group(2)}"
    title_match = re.search(r"PROGRAM\s+TITLE:\s*(.+?)(?:\n|$)", text)
    program_name = title_match.group(1).strip() if title_match else ""
    return program_id, program_name


# ---------------------------------------------------------------------------
# S78 Capital Budget Details parser
# ---------------------------------------------------------------------------

@dataclass
class S78Columns:
    """x-range (right edge) for each column of the S78 capital-project table.

    Layout (6 numeric columns):
        FY 2026:  CURRENT APPRN | ADJUSTMENT | RECOM APPRN
        FY 2027:  CURRENT APPRN | ADJUSTMENT | RECOM APPRN
    """
    fy26_curr: float
    fy26_adj: float
    fy26_rec: float
    fy27_curr: float
    fy27_adj: float
    fy27_rec: float

    def assign(self, x1: float) -> str | None:
        TOL = 25.0
        candidates = [
            ("fy26_curr", self.fy26_curr),
            ("fy26_adj",  self.fy26_adj),
            ("fy26_rec",  self.fy26_rec),
            ("fy27_curr", self.fy27_curr),
            ("fy27_adj",  self.fy27_adj),
            ("fy27_rec",  self.fy27_rec),
        ]
        best = min(candidates, key=lambda c: abs(c[1] + 17 - x1))
        if abs(best[1] + 17 - x1) > TOL:
            return None
        return best[0]


def detect_s78_columns(words: list[dict]) -> S78Columns | None:
    """S78 header: 4× APPRN + 2× ADJUSTMENT near the top of the page."""
    candidates = [
        w for w in words
        if w["text"] in {"APPRN", "ADJUSTMENT"} and w["top"] < 170
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda w: w["x0"])
    expected = ["APPRN", "ADJUSTMENT", "APPRN", "APPRN", "ADJUSTMENT", "APPRN"]
    picked: list[dict] = []
    idx = 0
    for w in candidates:
        if idx < len(expected) and w["text"] == expected[idx]:
            picked.append(w)
            idx += 1
    if len(picked) < 6:
        return None
    xs = [w["x1"] for w in picked]
    return S78Columns(
        fy26_curr=xs[0], fy26_adj=xs[1], fy26_rec=xs[2],
        fy27_curr=xs[3], fy27_adj=xs[4], fy27_rec=xs[5],
    )


# Cost-element / meta rows that are NOT project header lines
_COST_ELEMENTS = {
    "PLANS", "LAND", "DESIGN", "CONSTRUCTION", "EQUIPMENT",
    "LUMP", "TOTAL", "COST", "PROGRAM", "PROJECT",
}

# Scope keywords seen in S78 project-header lines
_SCOPE_KEYWORDS = {
    "NEW", "RENOVATION", "OTHER", "REPLACE", "REPLACEMENT",
    "ADDITION", "IMPROVEMENT", "EXPANSION", "REHABILITATION",
    "REHAB", "CONSTRUCTION", "ACQUISITION", "HEALTH",
}

_PROJECT_NUM_RE = re.compile(r"^[A-Z0-9.]{1,8}$")


def _is_project_header_row(row_words: list[dict]) -> bool:
    """Project-header rows start flush-left with a short alphanumeric code,
    optionally followed by a priority number and scope keyword, then a title.
    Example tokens (first 2-3): 'A38A', '6', 'RENOVATION', ...
                                 'P26116',   'NEW', ...
                                 'Q102',   '03', 'OTHER', ...
    """
    if not row_words:
        return False
    first = row_words[0]["text"]
    if not _PROJECT_NUM_RE.fullmatch(first):
        return False
    if first in _COST_ELEMENTS:
        return False
    # Must have a title after — reject if row is only numbers
    non_numeric = [w for w in row_words[1:] if not re.fullmatch(r"-?[\d,]+", w["text"])]
    if not non_numeric:
        return False
    # Heuristic: look for a scope keyword within the first 4 tokens, or
    # just accept if the 1st token looks like a project code and x0 is small
    # (flush-left, not indented like cost-element rows).
    if row_words[0]["x0"] > 90:  # cost-element rows are indented
        return False
    return True


def _parse_project_header(row_words: list[dict]) -> tuple[str, str, str]:
    """Return (project_number, scope, title)."""
    tokens = [w["text"] for w in row_words]
    project_num = tokens[0]
    i = 1
    # Skip optional priority number (1-2 digits)
    if i < len(tokens) and re.fullmatch(r"\d{1,2}", tokens[i]):
        i += 1
    # Capture scope keyword(s) — greedy up to 3 tokens while still matching
    scope_toks: list[str] = []
    while i < len(tokens) and tokens[i] in _SCOPE_KEYWORDS and len(scope_toks) < 3:
        scope_toks.append(tokens[i])
        i += 1
    # Also accept "LUMP SUM" as part of scope
    if i + 1 < len(tokens) and tokens[i] == "LUMP" and tokens[i + 1] == "SUM":
        scope_toks += ["LUMP", "SUM"]
        i += 2
    scope = " ".join(scope_toks)
    title = " ".join(tokens[i:])
    return project_num, scope, title


def parse_s78(path: pathlib.Path, dept_code: str, dept_name: str) -> Iterator[dict]:
    """Yield per-(project × fund) capital records from S78 pages of one PDF.

    Each project emits one record per fund source. Amounts come from the fund
    row's FY26/FY27 RECOM APPRN columns (which sum to the project TOTAL),
    converted from thousands to dollars.
    """
    # Track carry-over program metadata across continuation pages
    current_project: dict | None = None

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "REPORT S78" not in text:
                continue
            # S78 program ID has no dash: "PROGRAM ID: AGS881 4 of 6"
            pid_match = re.search(r"PROGRAM\s+ID:\s*([A-Z]{3}\d{3})\b", text)
            if not pid_match:
                continue
            program_id = pid_match.group(1)
            title_match = re.search(r"PROGRAM\s+TITLE:\s*(.+?)(?:\n|$)", text)
            program_name = title_match.group(1).strip() if title_match else ""
            words = page.extract_words()
            cols = detect_s78_columns(words)
            if not cols:
                continue

            rows = group_by_row(words)
            # Track page-level project state
            proj: dict | None = None
            in_program_totals = False

            for row in rows:
                row_text_upper = " ".join(w["text"] for w in row).upper()
                if "PROGRAM TOTALS" in row_text_upper:
                    in_program_totals = True
                    proj = None
                    continue
                if in_program_totals:
                    continue
                # Skip pure header/meta rows
                if row_text_upper.startswith(("STATE OF HAWAII", "PROGRAM ID:",
                                              "PROGRAM STRUCTURE", "PROGRAM TITLE:",
                                              "PROJECT PRIORITY", "NUMBER NUMBER",
                                              "NUMBER ", "CURRENT RECOM",
                                              "APPRN ADJUSTMENT")):
                    continue
                # "COST ELEMENT/MOF" sometimes runs onto the same line as the first
                # fund label (e.g. "COST ELEMENT/MOF SPECIAL FUND 2,500 2,500").
                # Strip the prefix so the fund can still be matched rather than
                # skipping the row entirely.
                _CMO_PREFIX = "COST ELEMENT/MOF "
                if row_text_upper.startswith("COST ELEMENT"):
                    if row_text_upper.startswith(_CMO_PREFIX):
                        row_text_upper = row_text_upper[len(_CMO_PREFIX):]
                        # Also strip matching words from the word list so column
                        # assignment still works (the prefix words are far left).
                        skip = len(_CMO_PREFIX.split())
                        row = row[skip:]
                    else:
                        continue  # plain "COST ELEMENT/MOF" header line — skip

                if _is_project_header_row(row):
                    project_num, scope, title = _parse_project_header(row)
                    proj = {
                        "project_id": project_num,
                        "scope": scope,
                        "project_name": title,
                        "program_id": program_id,
                        "program_name": program_name,
                        "department_code": dept_code,
                        "department_name": dept_name,
                    }
                    continue

                # Inside a project — look for fund-source rows
                fund_match = match_fund(row_text_upper)
                if not fund_match or proj is None:
                    continue
                fund_type, fund_category = fund_match
                values = extract_row_values(row, cols)

                def _rec(rec_key: str, curr_key: str, adj_key: str) -> float:
                    if rec_key in values:
                        return values[rec_key]
                    curr = values.get(curr_key, 0.0)
                    if adj_key in values:
                        return curr + values[adj_key]
                    return curr

                amt_fy26 = _rec("fy26_rec", "fy26_curr", "fy26_adj") * 1000.0
                amt_fy27 = _rec("fy27_rec", "fy27_curr", "fy27_adj") * 1000.0
                if amt_fy26 == 0 and amt_fy27 == 0:
                    continue

                yield {
                    **proj,
                    "fund_type": fund_type,
                    "fund_category": fund_category,
                    "amount_fy2026": amt_fy26,
                    "amount_fy2027": amt_fy27,
                }


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_pdf(path: pathlib.Path) -> Iterator[dict]:
    """Yield records from a single department PDF."""
    dept_code = path.stem.split("_")[-1]  # e.g. "09_AGS" -> "AGS"
    # Normalize legacy code
    if dept_code == "SUB":
        dept_code = "BUF"  # Subsidies -> Budget & Finance
    if dept_code == "CCR":
        # HB300/app data uses PSD code for Corrections; normalize
        dept_code = "PSD"
    dept_name = DEPARTMENT_NAMES.get(dept_code, dept_code)

    # Track per-program section state so continuation pages inherit correctly:
    # a program's capital BY-MEANS-OF-FINANCING block can spill onto the next
    # page, which has no "CAPITAL INVESTMENT" marker.
    program_state: dict[str, tuple[str, bool]] = {}

    with pdfplumber.open(path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            # Only S61-A operating detail pages (these contain both op and cap data)
            if "S61-A" not in text:
                continue
            header = extract_program_header(text)
            if not header:
                continue  # Rollup page, skip
            program_id, program_name = header

            words = page.extract_words()
            cols = detect_columns(words)
            if not cols:
                continue

            # Group rows; identify section boundaries
            rows = group_by_row(words)

            # Decide starting state for this page:
            # - If the page has no OPERATING / CAPITAL INVESTMENT markers but we
            #   already tracked this program on a prior page (capital spillover),
            #   resume that state.
            has_op_marker = bool(re.search(r"\bOPERATING\b", text))
            has_cip_marker = "CAPITAL INVESTMENT" in text
            prior = program_state.get(program_id)
            if prior and not has_op_marker and not has_cip_marker:
                current_section, in_capital_funds = prior
            else:
                current_section = "Operating"
                in_capital_funds = False

            for row in rows:
                row_text_upper = " ".join(w["text"] for w in row).upper()
                # Section boundary markers
                if "CAPITAL INVESTMENT" in row_text_upper:
                    current_section = "Capital Improvement"
                    in_capital_funds = False
                    continue
                if "TOTAL CAPITAL COST" in row_text_upper:
                    in_capital_funds = True
                    continue
                if "TOTAL PERM POSITIONS" in row_text_upper or "TOTAL PROGRAM COST" in row_text_upper:
                    # End of table
                    break
                # TOTAL OPERATING COST is informational — we use fund rows instead
                if "TOTAL OPERATING COST" in row_text_upper:
                    continue

                # Is this a fund row?
                fund_match = match_fund(row_text_upper)
                if not fund_match:
                    continue
                fund_type, fund_category = fund_match

                # Skip fund rows in operating section once we're past CAPITAL INVESTMENT
                # and before TOTAL CAPITAL COST (those are CIP category rows, not fund rows)
                if current_section == "Capital Improvement" and not in_capital_funds:
                    # This is within the CAPITAL INVESTMENT block (before TOTAL CAPITAL COST)
                    # Shouldn't happen (CIP rows are PLANS/DESIGN/CONSTRUCTION, not fund names),
                    # but skip just in case
                    continue

                # Extract values
                values = extract_row_values(row, cols)
                # REC APPRN = CURR APPRN + ADJUSTMENT.
                # When REC is zero the column is blank in the PDF, so pdfplumber
                # won't extract a word there.  If fy_adj is present but fy_rec is
                # absent, compute rec = curr + adj (may be 0 when adj cancels curr).
                def _rec(rec_key: str, curr_key: str, adj_key: str) -> float:
                    if rec_key in values:
                        return values[rec_key]
                    curr = values.get(curr_key, 0.0)
                    if adj_key in values:
                        return curr + values[adj_key]
                    return curr

                amount_fy2026 = _rec("fy26_rec", "fy26_curr", "fy26_adj")
                amount_fy2027 = _rec("fy27_rec", "fy27_curr", "fy27_adj")

                # Skip zero/empty rows
                if amount_fy2026 == 0 and amount_fy2027 == 0:
                    continue

                yield {
                    "program_id": program_id,
                    "program_name": program_name,
                    "department_code": dept_code,
                    "department_name": dept_name,
                    "fund_type": fund_type,
                    "fund_category": fund_category,
                    "section": current_section,
                    "amount_fy2026": amount_fy2026,
                    "amount_fy2027": amount_fy2027,
                }

            # Remember this page's ending state so continuation pages for the
            # same program can resume in the correct section.
            program_state[program_id] = (current_section, in_capital_funds)


def main():
    root = pathlib.Path(__file__).parent.parent
    pdf_dir = root / "data" / "raw" / "governor_supplemental_fy27"
    out_path = root / "docs" / "js" / "governor_request.json"
    projects_out_path = root / "docs" / "js" / "governor_projects.json"

    # Aggregate by (program_id, fund_type, section): sum amounts.
    accum: dict[tuple[str, str, str], dict] = {}

    # Capital projects: group by program_id, list of records per program
    projects_by_program: dict[str, list[dict]] = defaultdict(list)

    by_dept: dict[str, int] = defaultdict(int)
    totals = defaultdict(float)

    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        if pdf_path.name.startswith("06_"):  # skip statewide summary if present
            continue
        print(f"Parsing {pdf_path.name}...", end=" ", flush=True)
        page_count = 0
        for rec in parse_pdf(pdf_path):
            page_count += 1
            key = (rec["program_id"], rec["fund_type"], rec["section"])
            if key in accum:
                accum[key]["amount_fy2026"] += rec["amount_fy2026"]
                accum[key]["amount_fy2027"] += rec["amount_fy2027"]
            else:
                accum[key] = rec

        # S78 capital-project details
        dept_code = pdf_path.stem.split("_")[-1]
        if dept_code == "SUB":
            dept_code = "BUF"
        if dept_code == "CCR":
            dept_code = "PSD"
        dept_name = DEPARTMENT_NAMES.get(dept_code, dept_code)
        proj_count = 0
        for prec in parse_s78(pdf_path, dept_code, dept_name):
            projects_by_program[prec["program_id"]].append(prec)
            proj_count += 1
        print(f"{page_count} op/cap rows, {proj_count} project rows")

    all_records = list(accum.values())
    for rec in all_records:
        by_dept[rec["department_code"]] += 1
        totals[f"{rec['section']} FY26"] += rec["amount_fy2026"]
        totals[f"{rec['section']} FY27"] += rec["amount_fy2027"]

    # Write main governor_request.json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(all_records, f, separators=(",", ":"))
    print(f"\nWrote {len(all_records)} records to {out_path}")

    # Write governor_projects.json (mirrors projects_fy26.json shape)
    proj_total_fy26 = sum(p["amount_fy2026"] for ps in projects_by_program.values() for p in ps)
    proj_total_fy27 = sum(p["amount_fy2027"] for ps in projects_by_program.values() for p in ps)
    proj_count_total = sum(len(ps) for ps in projects_by_program.values())
    projects_doc = {
        "metadata": {
            "source": "Governor's Supplemental Budget FY2027 (S78 Capital Budget Details)",
            "bill_number": "Governor's Request",
        },
        "summary": {
            "total_fy2026": proj_total_fy26,
            "total_fy2027": proj_total_fy27,
            "total_projects": proj_count_total,
            "programs_with_projects": len(projects_by_program),
        },
        "projects_by_program": dict(projects_by_program),
    }
    with projects_out_path.open("w") as f:
        json.dump(projects_doc, f, separators=(",", ":"))
    print(f"Wrote {proj_count_total} capital project rows across "
          f"{len(projects_by_program)} programs to {projects_out_path}")

    print(f"\nPer-department counts:")
    for dept, n in sorted(by_dept.items()):
        print(f"  {dept}: {n}")
    print(f"\nGrand totals:")
    for label, amt in sorted(totals.items()):
        print(f"  {label}: ${amt:,.0f}")
    print(f"  Capital Projects (S78) FY26: ${proj_total_fy26:,.0f}")
    print(f"  Capital Projects (S78) FY27: ${proj_total_fy27:,.0f}")


if __name__ == "__main__":
    main()
