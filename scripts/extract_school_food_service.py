"""Extract the HIDOE School Food Service revenues/expenditures report into
docs/js/school_food_service.json for the dashboard's School Food Service page.

Source
------
2025.06_School-Food-Service (1).pdf — a one-page, cash-basis report (June 30,
2025). Three stacked blocks (Revenues, Expenditures, Net/Excess-Deficit) for
FY2021-FY2025, each by fund type (General/Federal/Special/All) with
Payroll/Other/Total sub-columns, plus a cash-rollforward section.

Parsing
-------
- Column assignment uses pdfplumber word x-positions bucketed into 12 bands
  (4 funds x payroll/other/total); fragments that share a band are concatenated
  (the PDF splits values like "2" + ",814,983" and "5" + "89").
- The three FY blocks are taken in vertical order (Revenues, Expenditures, Net).
- Cash rollforward: year-end balances are cumulative (start @ 6/30/2020 + each
  year's net), so we extract the two starting balances + encumbered amounts and
  compute the rest from the parsed net totals, validating against the reported
  AVAILABLE CASH.

Validation (asserted before writing): net = revenue - expenditure per fund/year,
and All = General + Federal + Special for revenue and expenditure each year.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import defaultdict

import pdfplumber

REPO_ROOT = pathlib.Path(__file__).parent.parent
DEFAULT_PDF = pathlib.Path.home() / "Downloads" / "2025.06_School-Food-Service (1).pdf"
OUT_PATH = REPO_ROOT / "docs" / "js" / "school_food_service.json"

YEARS = [2021, 2022, 2023, 2024, 2025]
FUNDS = ["General", "Federal", "Special", "All"]
BLOCKS = ["revenue", "expenditure", "net"]

# (fund, component, x-center) — band centers observed in the header/data.
BANDS = [
    ("General", "payroll", 115), ("General", "other", 172), ("General", "total", 220),
    ("Federal", "payroll", 275), ("Federal", "other", 327), ("Federal", "total", 379),
    ("Special", "payroll", 438), ("Special", "other", 487), ("Special", "total", 539),
    ("All", "payroll", 600), ("All", "other", 652), ("All", "total", 703),
]
BAND_TOL = 45


def parse_num(s: str):
    s = s.replace(" ", "").strip()
    if s in ("", "-", "—", "–"):
        return 0
    neg = s.startswith("(") or s.endswith(")")
    s = s.strip("()").replace(",", "")
    if not s or s == "-":
        return 0
    try:
        return -int(s) if neg else int(s)
    except ValueError:
        return None


def nearest_band(x0: float):
    best, bd = BAND_TOL + 1, None
    for fund, comp, cx in BANDS:
        d = abs(x0 - cx)
        if d < best:
            best, bd = d, (fund, comp)
    return bd if best <= BAND_TOL else None


def row_values(words):
    """Assign a data row's words to bands → {(fund,comp): int}."""
    buckets = defaultdict(list)
    for w in words:
        t = w["text"].strip()
        if not any(c.isdigit() for c in t):
            continue
        if re.fullmatch(r"20\d{2}", t):  # the year token
            continue
        bd = nearest_band(w["x0"])
        if bd:
            buckets[bd].append((w["x0"], t))
    out = {}
    for bd, frags in buckets.items():
        frags.sort()
        out[bd] = parse_num("".join(t for _, t in frags))
    return out


def extract(pdf_path: pathlib.Path):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = [w for w in page.extract_words() if w["text"].strip()]
        text = page.extract_text() or ""

    rows = defaultdict(list)
    for w in words:
        rows[round(w["top"])].append(w)

    # The 15 FY data rows (rev/exp/net), top of page, in vertical order.
    fy_tops = sorted(
        top for top, ws in rows.items()
        if top < 340 and " ".join(x["text"] for x in sorted(ws, key=lambda z: z["x0"])).startswith("FY 20")
    )
    assert len(fy_tops) == 15, f"expected 15 FY data rows, got {len(fy_tops)}"

    data = {}  # (block, fy, fund) -> {payroll, other, total}
    for i, top in enumerate(fy_tops):
        block = BLOCKS[i // 5]
        fy = YEARS[i % 5]
        vals = row_values(rows[top])
        for fund in FUNDS:
            data[(block, fy, fund)] = {
                comp: vals.get((fund, comp)) for comp in ("payroll", "other", "total")
            }
    return data, text


def cash_rollforward(text: str, net_total):
    """Federal & Special cash rollforward, using the report's printed year-end
    balances (Federal column left, Special right). available = year-end(2025)
    + encumbered (encumbered is a negative line item). Cross-checked vs PDF."""
    cash_pairs = {}  # fy -> (federal, special) year-end balance
    for m in re.finditer(
        r"CASH @ 06/30/(\d{4})\s+([(\-]?[\d ,]+\)?)\s+CASH @ 06/30/\d{4}\s+([(\-]?[\d ,]+\)?)", text
    ):
        cash_pairs[int(m.group(1))] = (parse_num(m.group(2)), parse_num(m.group(3)))
    enc = [parse_num(m.group(1)) for m in re.finditer(r"LESS: Encumbered Cash\s+([(\-]?[\d ,]+\)?|-)", text)]
    avail = [parse_num(m.group(1)) for m in re.finditer(r"EQUALS: AVAILABLE CASH\s+([(\-]?[\d ,]+\)?)", text)]
    out = {}
    for idx, fund in enumerate(["Federal", "Special"]):
        series = [
            {"fy": fy, "net": net_total[(fy, fund)], "cash_end": cash_pairs[fy][idx]}
            for fy in YEARS
        ]
        encumbered = enc[idx] if idx < len(enc) else 0  # negative = reduction
        available = cash_pairs[2025][idx] + encumbered
        if idx < len(avail):
            assert abs(available - avail[idx]) <= 2, (
                f"{fund} available {available} != reported {avail[idx]}")
        out[fund] = {
            "start_2020": cash_pairs[2020][idx], "encumbered": encumbered,
            "available": available, "series": series,
        }
    return out


def main() -> int:
    pdf_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return 1
    print(f"Parsing {pdf_path.name} ...")
    data, text = extract(pdf_path)

    # Validation: net = rev - exp (totals); All = Gen+Fed+Spec (rev & exp).
    net_total = {}
    for fy in YEARS:
        for fund in FUNDS:
            rev = data[("revenue", fy, fund)]["total"] or 0
            exp = data[("expenditure", fy, fund)]["total"] or 0
            net = data[("net", fy, fund)]["total"] or 0
            assert abs((rev - exp) - net) <= 2, f"net mismatch {fy} {fund}: {rev}-{exp} != {net}"
            net_total[(fy, fund)] = net
        for block in ("revenue", "expenditure"):
            parts = sum(data[(block, fy, f)]["total"] or 0 for f in ("General", "Federal", "Special"))
            allv = data[(block, fy, "All")]["total"] or 0
            assert abs(parts - allv) <= 2, f"{block} {fy}: parts {parts} != All {allv}"

    rows = []
    for fy in YEARS:
        for fund in FUNDS:
            rows.append({
                "fy": fy, "fund": fund,
                "revenue": data[("revenue", fy, fund)],
                "expenditure": data[("expenditure", fy, fund)],
                "net": data[("net", fy, fund)],
            })

    doc = {
        "metadata": {
            "title": "School Food Service",
            "source": "HIDOE School Food Services, June 30, 2025",
            "basis": "cash",
            "fy_range": "FY2021–FY2025",
            "notes": [
                "Prepared on a cash basis; timing of transaction posting affects year-to-year comparability.",
                "General Fund payroll excludes fringe benefits, which are paid directly by the State.",
                "All funds are subject to Federal regulations (7 CFR parts 210 and 245).",
            ],
        },
        "funds": FUNDS,
        "years": YEARS,
        "rows": rows,
        "cash_rollforward": cash_rollforward(text, net_total),
    }
    OUT_PATH.write_text(json.dumps(doc, separators=(",", ":")))
    print(f"Wrote {len(rows)} rows to {OUT_PATH}")
    print(f"  FY2025 All: rev {data[('revenue',2025,'All')]['total']:,} "
          f"exp {data[('expenditure',2025,'All')]['total']:,} net {net_total[(2025,'All')]:,}")
    for f in ("Federal", "Special"):
        cr = doc["cash_rollforward"][f]
        print(f"  {f} available cash @6/30/2025: {cr['available']:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
