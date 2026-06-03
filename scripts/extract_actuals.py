"""Extract FY2025 actual spending (budgetary basis) by department from the
State of Hawaii Annual Comprehensive Financial Report (ACFR) and write
docs/js/actuals_fy2025.json for the dashboard's "Actuals" tab.

Source
------
acfr2025.pdf → "Schedule of Revenues and Expenditures ‒ Budget and Actual
(Budgetary Basis)" for the five appropriated funds (PDF pages 130–134):
  General Fund, Med-Quest SRF, Administrative Support SRF,
  Natural Resources SRF, Hawaiian Programs SRF.

Each schedule's Expenditures section lists, by department, four columns:
  Original Budget · Final Budget · Actual (Budgetary Basis) · Variance
with amounts in THOUSANDS (parentheses = negative, "-" = zero).

Output
------
Per department (summed across all five funds, converted to dollars):
  department_code, department_name, original_budget, final_budget,
  actual, variance (= final − actual, i.e. positive = under budget),
  pct_variance.
Plus metadata with combined totals and the General-Fund anchor totals.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import defaultdict

import pdfplumber

REPO_ROOT = pathlib.Path(__file__).parent.parent
DEFAULT_PDF = pathlib.Path.home() / "Downloads" / "acfr2025.pdf"
OUT_PATH = REPO_ROOT / "docs" / "js" / "actuals_fy2025.json"

# PDF page indices (0-based) of the five budgetary-comparison schedules.
SCHEDULE_PAGES = [129, 130, 131, 132, 133]

# ACFR department name → dashboard department_code. Names not listed here
# (House, Senate, Judiciary, Legislative Auditor, LRB, OHA, Ombudsman, Ethics,
# ERS) are kept with a null code — the Actuals tab is standalone.
NAME_TO_CODE = {
    "accounting and general services": "AGS",
    "agriculture and biosecurity": "AGR",
    "attorney general": "ATG",
    "budget and finance": "BUF",
    "business, economic development and tourism": "BED",
    "commerce and consumer affairs": "CCA",
    "corrections and rehabilitation": "PSD",
    "defense": "DEF",
    "education": "EDN",
    "governor": "GOV",
    "hawaiian home lands": "HHL",
    "health": "HTH",
    "human resources development": "HRD",
    "human services": "HMS",
    "labor and industrial relations": "LBR",
    "land and natural resources": "LNR",
    "law enforcement": "LAW",
    "lieutenant governor": "LTG",
    "taxation": "TAX",
    "transportation": "TRN",
    "university of hawaii": "UOH",
}

# Canonical display names for some ACFR shorthands.
DISPLAY_FIXUPS = {
    "house of representative": "House of Representatives",
    "ers": "Employees' Retirement System",
}

_VAL_RE = re.compile(r"\(?-?[\d,]+\)?$|^-$")


def parse_val(tok: str) -> int:
    """Parse a thousands value token: '1,234', '(38,732)', '-', '5902'."""
    tok = tok.strip()
    if tok in ("-", "—", "–", ""):
        return 0
    neg = tok.startswith("(") and tok.endswith(")")
    tok = tok.strip("()").replace(",", "").replace("$", "")
    if tok in ("", "-"):
        return 0
    return (-int(tok) if neg else int(tok))


def parse_dept_line(line: str):
    """Return (name, [orig, final, actual, var]) in thousands, or None."""
    toks = [t for t in line.split() if t != "$"]
    if len(toks) < 5:
        return None
    vals = toks[-4:]
    if not all(_VAL_RE.match(v) for v in vals):
        return None
    name = " ".join(toks[:-4]).strip()
    if not name or name.lower().startswith("total"):
        return None
    return name, [parse_val(v) for v in vals]


def parse_schedule(text: str):
    """Yield (dept_name, [orig, final, actual, var]) for the Expenditures block."""
    lines = text.split("\n")
    in_exp = False
    for ln in lines:
        s = ln.strip()
        if s == "Department":
            in_exp = True
            continue
        if not in_exp:
            continue
        if s.startswith("Total expenditures"):
            break
        parsed = parse_dept_line(s)
        if parsed:
            yield parsed


def fund_name(text: str) -> str:
    for ln in text.split("\n")[:4]:
        s = ln.strip()
        if s and s != "State of Hawaii" and "Schedule" not in s:
            return s
    return "?"


def gf_totals(text: str):
    """General-Fund total revenues / total expenditures (dollars) for anchors."""
    # Each total line has 4 columns: Original · Final · Actual · Variance.
    # The "actual" figure is the 3rd value.
    rev = exp = None
    for ln in text.split("\n"):
        s = ln.strip()
        if s.startswith("Total revenues") and rev is None:
            m = re.findall(r"\(?-?[\d,]+\)?", s)
            if len(m) >= 3:
                rev = parse_val(m[2]) * 1000
        if s.startswith("Total expenditures"):
            m = re.findall(r"\(?-?[\d,]+\)?", s)
            if len(m) >= 3:
                exp = parse_val(m[2]) * 1000
    return rev, exp


def main() -> int:
    pdf_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return 1

    depts: dict[str, dict] = defaultdict(
        lambda: {"original_budget": 0, "final_budget": 0, "actual": 0, "name": None}
    )
    funds_used = []
    gf_rev = gf_exp = None

    with pdfplumber.open(pdf_path) as pdf:
        for n, idx in enumerate(SCHEDULE_PAGES):
            text = pdf.pages[idx].extract_text() or ""
            fname = fund_name(text)
            funds_used.append(fname)
            if n == 0:
                gf_rev, gf_exp = gf_totals(text)
            count = 0
            for name, (orig, final, actual, _var) in parse_schedule(text):
                key = name.strip().lower()
                d = depts[key]
                d["name"] = name.strip()
                d["original_budget"] += orig * 1000
                d["final_budget"] += final * 1000
                d["actual"] += actual * 1000
                count += 1
            print(f"  {fname}: {count} department lines")

    records = []
    for key, d in depts.items():
        display = DISPLAY_FIXUPS.get(key, d["name"])
        variance = d["final_budget"] - d["actual"]  # positive = under budget
        final = d["final_budget"]
        records.append({
            "department_code": NAME_TO_CODE.get(key),
            "department_name": display,
            "original_budget": d["original_budget"],
            "final_budget": d["final_budget"],
            "actual": d["actual"],
            "variance": variance,
            "pct_variance": round(variance / final * 100, 2) if final else None,
        })
    records.sort(key=lambda r: r["actual"], reverse=True)

    total_final = sum(r["final_budget"] for r in records)
    total_actual = sum(r["actual"] for r in records)

    doc = {
        "metadata": {
            "fiscal_year": 2025,
            "source": "State of Hawaii ACFR, FY ended June 30, 2025",
            "basis": "budgetary",
            "funds": funds_used,
            "total_final_budget": total_final,
            "total_actual": total_actual,
            "total_variance": total_final - total_actual,
            "general_fund_total_revenues": gf_rev,
            "general_fund_total_expenditures": gf_exp,
        },
        "departments": records,
    }
    OUT_PATH.write_text(json.dumps(doc, separators=(",", ":")))
    print(f"\nWrote {len(records)} departments to {OUT_PATH}")
    print(f"Combined final budget ${total_final:,.0f} | actual ${total_actual:,.0f}")
    print(f"GF anchors — revenues ${gf_rev:,.0f} | expenditures ${gf_exp:,.0f}")
    unmapped = [r["department_name"] for r in records if r["department_code"] is None]
    if unmapped:
        print(f"Null-coded (non-dashboard) departments: {unmapped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
