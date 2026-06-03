"""Extract per-program "Governor's Message" detail from the HB1800 CD1 FINAL
worksheet PDF and merge it into the draft_comparison_fy{26,27}.json files.

Source
------
- HB1800 CD1 FINAL WORKSHEETS.pdf  → Two-column comparison worksheet.
  LEFT half  = Conference Draft (CD); carries "LEGISLATURE DOES NOT CONCUR"
               / "LEGISLATURE CONCURS" status.
  RIGHT half = Governor's Message (GM); carries the
               "GOVERNOR'S MESSAGE (mm/dd/yy):" headline and the
               "DETAIL OF GOVERNOR'S MESSAGE:" specific line items
               (e.g. "HAWAII MESONET (FY27: 500,000) $500,000 NON-RECURRING.").

Output (merged in place into docs/js/draft_comparison_fy{26,27}.json)
------
Per program row, keyed by program_id:
  - reason_gov_title   : the "ADD FUNDS FOR …" headline(s)
  - reason_gov         : the specific detail item(s), joined with "; "
  - gov_not_concur     : true when the Legislature declined the request

The SPA's loadDraftComparison() already fetches these files, so the new
fields ride along without any loader change.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import defaultdict

import pdfplumber

REPO_ROOT = pathlib.Path(__file__).parent.parent
DEFAULT_PDF = pathlib.Path.home() / "Downloads" / "HB1800 CD1 FINAL WORKSHEETS.pdf"
JSON_DIR = REPO_ROOT / "docs" / "js"
TARGET_FILES = ["draft_comparison_fy26.json", "draft_comparison_fy27.json"]

PROG_RE = re.compile(r"Program ID:\s*([A-Z]{2,4}\d{2,4})")
# Headline under "GOVERNOR'S MESSAGE (mm/dd/yy):" up to the next separator.
TITLE_RE = re.compile(
    r"GOVERNOR'S MESSAGE\s*\([^)]*\):\s*(.*?)(?:\*{5,}|\Z)", re.S | re.I
)
# Detail block under "DETAIL OF GOVERNOR'S MESSAGE:" up to the next separator
# or the start of the next worksheet block.
DETAIL_RE = re.compile(
    r"DETAIL OF GOVERNOR'S MESSAGE:\s*(.*?)"
    r"(?:\*{5,}|GOVERNOR'S MESSAGE|LEGISLAT|DETAIL OF|\Z)",
    re.S | re.I,
)
# Trailing artifacts that bleed in when no separator follows the detail:
# a standalone amount + fund letter line (e.g. "1,000,000 A").
TRAILING_AMT_RE = re.compile(r"\s*\(?-?[\d,]+\)?\s+[A-Z]\s*$")


def _clean(text: str) -> str:
    """Collapse worksheet whitespace into a single readable line."""
    t = " ".join((text or "").split())
    t = TRAILING_AMT_RE.sub("", t).strip()
    return t


def extract(pdf_path: pathlib.Path) -> dict[str, dict]:
    """Return {program_id: {titles:set, details:list, not_concur:bool, concur:bool}}."""
    out: dict[str, dict] = defaultdict(
        lambda: {"titles": [], "details": [], "not_concur": False, "concur": False}
    )
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full = page.extract_text() or ""
            if "DETAIL OF GOVERNOR" not in full.upper() or "MESSAGE" not in full.upper():
                continue
            pm = PROG_RE.search(full)
            if not pm:
                continue
            pid = pm.group(1)
            w, h = page.width, page.height
            right = page.crop((w / 2, 0, w, h)).extract_text() or ""
            left = page.crop((0, 0, w / 2, h)).extract_text() or ""

            rec = out[pid]
            # Headline(s) — Governor's Message column (right).
            for m in TITLE_RE.finditer(right):
                title = _clean(m.group(1))
                # Stop the headline at the first item/cost line if it ran on.
                title = re.split(r"\bGREEN FEE\b|\bDETAIL OF\b", title, 1, re.I)[0].strip()
                if title and title not in rec["titles"]:
                    rec["titles"].append(title)
            # Detail item(s).
            for m in DETAIL_RE.finditer(right):
                item = _clean(m.group(1))
                if item and item not in rec["details"]:
                    rec["details"].append(item)
            # Concurrence status — Conference Draft column (left).
            up = left.upper()
            if "DOES NOT CONCUR" in up:
                rec["not_concur"] = True
            if re.search(r"LEGISLATURE CONCURS", up):
                rec["concur"] = True
    return out


def merge(records: dict[str, dict]) -> None:
    for fname in TARGET_FILES:
        path = JSON_DIR / fname
        if not path.exists():
            print(f"  skip (missing): {fname}")
            continue
        doc = json.loads(path.read_text())
        n = 0
        for row in doc.get("comparisons", []):
            rec = records.get(row.get("program_id"))
            if not rec or not rec["details"]:
                continue
            row["reason_gov_title"] = "; ".join(rec["titles"])
            row["reason_gov"] = "; ".join(rec["details"])
            row["gov_not_concur"] = bool(rec["not_concur"])
            n += 1
        path.write_text(json.dumps(doc, separators=(",", ":")))
        print(f"  merged into {fname}: {n} rows tagged")


def main() -> int:
    pdf_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return 1
    print(f"Parsing {pdf_path.name} ...")
    records = {pid: r for pid, r in extract(pdf_path).items() if r["details"]}
    print(f"Found Governor's Message detail for {len(records)} programs.")
    merge(records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
