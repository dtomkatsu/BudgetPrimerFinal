#!/usr/bin/env python3
"""Build report_data.json — single source of truth for the Budget Primer FY2026-27.

Inputs:
  ../docs/js/departments_act175_fy2027.json   (executive budget detail, Act 175 SLH 2026)
  ../docs/js/summary_stats_act175_fy2027.json
  sources/revenue_plans_fb2527.pdf            (COR tax revenue estimates, p.2)
  manual/research.json                        (Jud/Leg/OHA acts, one-time & emergency approps)

Validation mode (--validate) reproduces the published FY2025-26 primer numbers from
the Act 250 FY2026 data to prove the category mappings before trusting FY27 output.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent          # report2027/
REPO = HERE.parent                                     # BudgetPrimerFinal/
DOCS_JS = REPO / "docs" / "js"

# Figure 3 groups the act's functional categories (CATEGORY_MAP in fast_parser.py,
# carried on data/processed/budget_allocations_*_post_veto.csv) into the five slices
# the FY25-26 primer used. Education -> "Formal Education" per CIPChart.
CIP_MAIN = {"Transportation": "Transportation", "Education": "Formal Education",
            "Economic Development": "Economic Development", "Health": "Health"}
CIP_OTHER = "All Others"

# fund_category -> Figure 4 means-of-finance group. The published FY25-26 figure
# counts "Other Federal Funds" (ARPA-type) under Other, not Federal.
FUND_GROUP = {
    "General Funds": "General Funds",
    "Special Funds": "Special Funds",
    "Federal Funds": "Federal Funds",
}
FUND_OTHER = "Other Funds"

# Chart row labels used in Figure 2 of the FY25-26 primer
DEPT_SHORT = {
    "HMS": "Human Services", "BUF": "Budget, Finance", "EDN": "Education",
    "TRN": "Transportation", "HTH": "Health", "UOH": "UH System",
    "BED": "Bus, Econ, Dev, Tour", "ATG": "Attorney General", "LBR": "Labor",
    "AGS": "Accounting, Gen Serv", "LNR": "Land, Natural Res",
    "PSD": "Corrections", "DEF": "Defense", "HHL": "Hwn Home Lands",
    "CCA": "Commerce", "LAW": "Law Enforcement", "AGR": "Agriculture",
    "TAX": "Taxation", "HRD": "Human Resources", "GOV": "Governor",
    "LTG": "Lt. Governor",
}
COUNTY_CODES = {"COM", "COH", "CCH"}  # county CIP grants — footnoted, not charted


def load_departments(act: str, fy: int):
    path = DOCS_JS / f"departments_{act}_fy{fy}.json"
    return json.loads(path.read_text()), path


def tax_revenue_from_pdf(fy: int) -> dict:
    """Parse the COR estimates table (page 2 of the revenue plans PDF)."""
    pdf = HERE / "sources" / "revenue_plans_fb2527.pdf"
    txt = subprocess.run(
        ["pdftotext", "-f", "2", "-l", "2", "-layout", str(pdf), "-"],
        capture_output=True, text=True, check=True).stdout
    lines = [l for l in txt.splitlines() if l.strip()]
    header = next(l for l in lines if "FY 2023" in l)
    years = [int(y) for y in re.findall(r"FY (\d{4})", header)]
    col = years.index(fy)
    rows = {}
    for l in lines:
        m = re.match(r"^([A-Za-z][A-Za-z .,'&*()-]+?)\s{2,}\$?([\d,]+)", l)
        if not m or "FY" in l:
            continue
        nums = [int(n.replace(",", "")) for n in re.findall(r"[\d,]{4,}", l)]
        if len(nums) == len(years):
            rows[m.group(1).strip().rstrip("*").strip()] = nums[col] * 1000
    return rows


def program_categories(fy: int) -> dict:
    """program_id -> functional category, from the post-veto allocations CSV."""
    import csv
    path = REPO / "data" / "processed" / f"budget_allocations_fy{fy}_post_veto.csv"
    cats = {}
    if path.exists():
        for r in csv.DictReader(path.open()):
            if r.get("category"):
                cats[r["program_id"]] = r["category"]
    return cats


def build_budget(act: str, fy: int) -> dict:
    depts, src = load_departments(act, fy)
    prog_cat = program_categories(fy)
    fig2, fig3, fig4 = [], {}, {}
    op_total = cap_total = county_cip = 0.0
    for d in depts:
        code = d["code"]
        if code in COUNTY_CODES:
            county_cip += d.get("capital_budget", 0) or 0
            continue
        op = d.get("operating_budget", 0) or 0
        cap = d.get("capital_budget", 0) or 0
        op_total += op
        cap_total += cap
        fig2.append({"code": code, "label": DEPT_SHORT.get(code, d["name"]),
                     "operating": op, "capital": cap})
        for p in d["programs"]:
            if p["section"] == "Operating":
                g = FUND_GROUP.get(p["fund_category"], FUND_OTHER)
                fig4[g] = fig4.get(g, 0) + p["amount"]
            else:
                raw = prog_cat.get(p["program_id"], "")
                grp = CIP_MAIN.get(raw, CIP_OTHER)
                fig3[grp] = fig3.get(grp, 0) + p["amount"]
    fig2.sort(key=lambda r: r["operating"] + r["capital"], reverse=True)
    # county CIP grants ride in "All Others" (published FY26: 593 = 576 + 17 county)
    if county_cip:
        fig3[CIP_OTHER] = fig3.get(CIP_OTHER, 0) + county_cip
    return {
        "source": src.name, "fiscal_year": fy,
        "executive": {"operating": op_total, "capital": cap_total,
                      "county_cip_grants": county_cip},
        "figure2_departments": fig2,
        "figure3_cip": fig3,
        "figure4_means_of_finance": fig4,
    }


def validate() -> int:
    """Reproduce published FY25-26 primer numbers from Act 250 FY2026 data."""
    b = build_budget("act250", 2026)
    rev = tax_revenue_from_pdf(2026)
    checks = [
        ("Table1 Exec operating $19.88B", b["executive"]["operating"], 19.88e9, 0.01e9),
        ("Table1 Exec CIP $3.38B", b["executive"]["capital"] + b["executive"]["county_cip_grants"], 3.38e9, 0.01e9),
        ("Fig3 Transportation $1,781M", b["figure3_cip"].get("Transportation", 0), 1781e6, 1e6),
        ("Fig3 Formal Education $621M", b["figure3_cip"].get("Formal Education", 0), 621e6, 1e6),
        ("Fig3 Economic Development $307M", b["figure3_cip"].get("Economic Development", 0), 307e6, 1e6),
        ("Fig3 Health $78M", b["figure3_cip"].get("Health", 0), 78e6, 1e6),
        ("Fig4 General Funds $10.5B", b["figure4_means_of_finance"].get("General Funds", 0), 10.5e9, 0.05e9),
        ("Fig4 Special Funds $4.3B", b["figure4_means_of_finance"].get("Special Funds", 0), 4.3e9, 0.05e9),
        ("Fig4 Federal Funds $3.6B", b["figure4_means_of_finance"].get("Federal Funds", 0), 3.6e9, 0.05e9),
        ("Fig5 GET $5.25B", rev.get("General Excise and Use Tax", 0), 5.25e9, 0.01e9),
        ("Fig5 IIT $2.98B", rev.get("Individual Income Tax", 0), 2.98e9, 0.01e9),
        ("Fig5 TAT $0.76B", rev.get("Transient Accommodations Tax", 0), 0.755e9, 0.01e9),
        ("Fig5 Corp $0.45B", rev.get("Corporate Income Tax", 0), 0.446e9, 0.01e9),
    ]
    fails = 0
    for name, got, want, tol in checks:
        ok = abs(got - want) <= tol
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL':4} {name:38} got {got/1e9:,.3f}B want {want/1e9:,.3f}B")
    # print full derived sets for eyeballing category drift
    print("\nFig3 (derived):", {k: round(v / 1e6) for k, v in sorted(b["figure3_cip"].items())})
    print("Fig4 (derived):", {k: round(v / 1e9, 2) for k, v in sorted(b["figure4_means_of_finance"].items())})
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()
    if args.validate:
        sys.exit(validate())

    out = {
        "report": "Hawaiʻi Budget Primer FY2026–27",
        "budget": build_budget("act175", 2027),
        "tax_revenue_fy2027": tax_revenue_from_pdf(2027),
    }
    manual = HERE / "manual" / "research.json"
    if manual.exists():
        out["research"] = json.loads(manual.read_text())
    else:
        out["research"] = None
        print("WARN: manual/research.json missing — Jud/Leg/OHA + one-time/emergency "
              "sections will be empty", file=sys.stderr)
    dest = HERE / "data" / "report_data.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
