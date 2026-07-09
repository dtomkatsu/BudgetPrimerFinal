#!/usr/bin/env python3
"""
Generate Act 175 (HB1800 supplemental, SLH 2026) per-fiscal-year department
datasets for the "By Department" tab, WITHOUT overwriting the live Act 250
`departments.json` / `summary_stats.json`.

Act 175 == HB1800 CD1 (the Governor signed with no line-item vetoes). We parse
the enrolled CD1 text with the SAME code path the HB1800 tab uses
(FastBudgetParser → process_budget_data), then reuse process_budget.py's JSON
builders so the output is byte-for-byte the same shape the front-end already
consumes for departments.json.

Outputs (to docs/js/):
  departments_act175_fy2026.json      summary_stats_act175_fy2026.json
  departments_act175_fy2027.json      summary_stats_act175_fy2027.json

Usage:
  python scripts/generate_act175_departments.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from budgetprimer.parsers.fast_parser import FastBudgetParser
from budgetprimer.pipeline import add_derived_metrics, process_budget_data

# Reuse the exact JSON builders that produced the Act 250 departments.json.
_pb_path = PROJECT_ROOT / "scripts" / "process_budget.py"
_spec = importlib.util.spec_from_file_location("process_budget", _pb_path)
process_budget = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(process_budget)

CD1_TEXT = PROJECT_ROOT / "data" / "raw" / "drafts" / "HB1800_CD1.txt"
JSON_DIR = PROJECT_ROOT / "docs" / "js"
DESC_PATH = PROJECT_ROOT / "data" / "processed" / "department_descriptions.json"

ACT = "Act 175, SLH 2026"
BILL = "HB1800"

# The original biennium (Act 250, SLH 2025) FY2026 & FY2027 so the "· Act 250"
# dropdown entries also have full program detail — and, crucially, include the
# county grant pass-through codes (CCH/COH/COK) that the filtered front-end
# departmentsData drops, so every pane reconciles with historical_trends.json
# (FY2026 $23.320B, FY2027 $22.090B). Sourced from the already-parsed post-veto
# CSVs.
ACT250_CSVS = {
    2026: PROJECT_ROOT / "data" / "processed" / "budget_allocations_fy2026_post_veto.csv",
    2027: PROJECT_ROOT / "data" / "processed" / "budget_allocations_fy2027_post_veto.csv",
}


def _load_descriptions() -> dict:
    descs: dict[str, str] = {}
    if DESC_PATH.exists():
        raw = json.loads(DESC_PATH.read_text())
        if isinstance(raw, dict):
            for code, info in raw.items():
                descs[code] = info.get("description", "") if isinstance(info, dict) else str(info)
        elif isinstance(raw, list):
            for entry in raw:
                descs[entry.get("department_code", "")] = entry.get("description", "")
    return descs


def main() -> int:
    if not CD1_TEXT.exists():
        print(f"ERROR: missing {CD1_TEXT}", file=sys.stderr)
        return 1

    # Same parser + biennium the HB1800 tab uses to produce its CD1 numbers.
    parser = FastBudgetParser(fy1=2026, fy2=2027)
    allocs = parser.parse(str(CD1_TEXT))
    print(f"Parsed {len(allocs)} Act 175 (CD1) allocations from {CD1_TEXT.name}")

    descriptions = _load_descriptions()

    for fy in (2026, 2027):
        df = process_budget_data(allocs, fiscal_year=fy, section="all")
        df = add_derived_metrics(df)

        programs_by_dept = process_budget._build_programs_by_dept(df)
        departments = process_budget._build_departments_json(df, programs_by_dept, descriptions)
        stats = process_budget._build_summary_stats(df, fy, f"{BILL} CD1 ({ACT})")
        # Provenance so the front-end / future maintainers know the source.
        stats["metadata"]["act"] = ACT
        stats["metadata"]["bill"] = BILL

        dept_out = JSON_DIR / f"departments_act175_fy{fy}.json"
        stats_out = JSON_DIR / f"summary_stats_act175_fy{fy}.json"
        dept_out.write_text(json.dumps(departments, indent=2))
        stats_out.write_text(json.dumps(stats, indent=2))

        total = sum(d["total_budget"] for d in departments)
        print(
            f"FY{fy}: {len(departments)} depts, total ${total/1e9:.3f}B "
            f"(op ${stats['operating_budget']/1e9:.3f}B / cap ${stats['capital_budget']/1e9:.3f}B) "
            f"→ {dept_out.name}, {stats_out.name}"
        )

    # ---- FY2026 & FY2027 · Act 250 (original biennium) detail from CSV -------
    for fy, csv in ACT250_CSVS.items():
        if not csv.exists():
            print(f"NOTE: {csv.name} missing — FY{fy}·Act 250 will fall back to totals-only")
            continue
        df = pd.read_csv(csv)
        programs_by_dept = process_budget._build_programs_by_dept(df)
        departments = process_budget._build_departments_json(df, programs_by_dept, descriptions)
        stats = process_budget._build_summary_stats(df, fy, csv.name)
        stats["metadata"]["act"] = "Act 250, SLH 2025"
        stats["metadata"]["bill"] = "HB300"
        (JSON_DIR / f"departments_act250_fy{fy}.json").write_text(json.dumps(departments, indent=2))
        (JSON_DIR / f"summary_stats_act250_fy{fy}.json").write_text(json.dumps(stats, indent=2))
        total = sum(d["total_budget"] for d in departments)
        print(f"FY{fy} · Act 250: {len(departments)} depts, total ${total/1e9:.3f}B → departments_act250_fy{fy}.json")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
