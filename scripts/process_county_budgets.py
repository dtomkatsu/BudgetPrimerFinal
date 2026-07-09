#!/usr/bin/env python3
"""
County Budget Processing Script

County analog of process_budget.py: parses committed raw county budget files
(see scripts/fetch_county_budgets.py) and produces:
  - Per-county / per-fiscal-year CSVs in data/processed/counties/
  - docs/js/county_budgets.json for the web app.

The JSON holds every available fiscal year so the frontend can offer a year
picker; each county/year block separates the OPERATING budget (departments →
programs → funds) from the CAPITAL improvement program (functions → projects →
funds), since the two are budgeted and published separately. Counties without
a parser yet are marked available: false and shown as "coming soon".

Usage:
    python scripts/process_county_budgets.py --county all --fiscal-years 2026 2027
"""
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from budgetprimer.models.county_allocation import COUNTY_NAMES
from budgetprimer.parsers.counties import COUNTY_PARSERS

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RAW_ROOT = project_root / 'data' / 'raw' / 'counties'
PROCESSED_DIR = project_root / 'data' / 'processed' / 'counties'
JSON_DIR = project_root / 'docs' / 'js'

ALL_COUNTIES = ['honolulu', 'maui', 'hawaii', 'kauai']
DEFAULT_FISCAL_YEARS = [2026, 2027]

OPERATING = 'Operating'
CAPITAL = 'Capital Improvement'


def _fund_breakdown(df: pd.DataFrame) -> Dict[str, float]:
    return {
        k: float(v) for k, v in
        df.groupby('fund_category')['amount'].sum().sort_values(ascending=False).items()
        if v != 0
    }


def _funds_list(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Per-fund detail rows for a program/project, largest first."""
    grouped = df.groupby(['fund_name', 'fund_category'], dropna=False)['amount'].sum()
    funds = [{'fund_name': fn, 'fund_category': fc, 'amount': float(v)}
             for (fn, fc), v in grouped.items() if v != 0]
    funds.sort(key=lambda f: abs(f['amount']), reverse=True)
    return funds


def _build_operating(df: pd.DataFrame) -> Dict[str, Any]:
    """Operating budget: department → program → fund hierarchy."""
    op = df[df['section'] == OPERATING]
    departments: List[Dict[str, Any]] = []
    for code, dept_df in op.groupby('department_code'):
        programs = []
        for pname, p_df in dept_df.groupby(dept_df['program_name'].fillna('(department-wide)')):
            programs.append({
                'program_name': pname,
                'total_budget': float(p_df['amount'].sum()),
                'fund_breakdown': _fund_breakdown(p_df),
                'funds': _funds_list(p_df),
            })
        programs.sort(key=lambda p: abs(p['total_budget']), reverse=True)
        departments.append({
            'code': code,
            'name': dept_df['department_name'].iloc[0],
            'total_budget': float(dept_df['amount'].sum()),
            'fund_breakdown': _fund_breakdown(dept_df),
            'num_programs': len(programs),
            'programs': programs,
        })
    departments.sort(key=lambda d: d['total_budget'], reverse=True)
    return {
        'total': float(op['amount'].sum()),
        'fund_breakdown': _fund_breakdown(op),
        'num_departments': int(op['department_code'].nunique()),
        'num_programs': sum(d['num_programs'] for d in departments),
        'departments': departments,
    }


def _build_cip(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Capital improvement program: function → project → fund hierarchy, plus a
    flat project list for a searchable table. Returns None if no capital data."""
    cap = df[df['section'] == CAPITAL]
    if cap.empty or cap['amount'].sum() == 0:
        return None

    functions: List[Dict[str, Any]] = []
    flat_projects: List[Dict[str, Any]] = []
    for fname, fn_df in cap.groupby('department_name'):
        projects = []
        for pname, p_df in fn_df.groupby(p_key(fn_df)):
            funds = _funds_list(p_df)
            project = {
                'project_name': pname,
                'function': fname,
                'total_budget': float(p_df['amount'].sum()),
                'funds': funds,
                'primary_fund': funds[0]['fund_name'] if funds else None,
                'fund_category': funds[0]['fund_category'] if funds else None,
            }
            projects.append(project)
            flat_projects.append(project)
        projects.sort(key=lambda p: abs(p['total_budget']), reverse=True)
        functions.append({
            'name': fname,
            'code': fn_df['department_code'].iloc[0],
            'total_budget': float(fn_df['amount'].sum()),
            'fund_breakdown': _fund_breakdown(fn_df),
            'num_projects': len(projects),
            'projects': projects,
        })
    functions.sort(key=lambda f: f['total_budget'], reverse=True)
    flat_projects.sort(key=lambda p: abs(p['total_budget']), reverse=True)
    return {
        'total': float(cap['amount'].sum()),
        'fund_breakdown': _fund_breakdown(cap),
        'num_functions': len(functions),
        'num_projects': len(flat_projects),
        'functions': functions,
        'projects': flat_projects,
    }


def p_key(df: pd.DataFrame):
    return df['program_name'].fillna('(unnamed project)')


def _build_county_entry(df: pd.DataFrame, county: str, parser) -> Dict[str, Any]:
    """Build one county/fiscal-year block: operating + cip split."""
    operating = _build_operating(df)
    # Some counties (e.g. Hawaiʻi, from a scanned source) only break operating
    # out by fund, not department — let the parser relabel the operating table.
    operating['row_label'] = getattr(parser, 'operating_row_label', 'Department')
    cip = _build_cip(df)
    return {
        'name': COUNTY_NAMES[county],
        'available': True,
        'total_budget': float(df['amount'].sum()),
        'operating_budget': operating['total'],
        'capital_budget': cip['total'] if cip else 0.0,
        'capital_note': None if cip else 'CIP not yet published for this year',
        'coverage_note': parser.coverage_note or None,
        'fund_breakdown': _fund_breakdown(df),
        'source': {'label': parser.source_label, 'url': parser.source_url},
        'operating': operating,
        'cip': cip,
    }


def _process_year(county: str, fy: int) -> Optional[Dict[str, Any]]:
    """Parse one county/year; write its CSV and return its JSON block (or None
    if no data could be parsed for that year)."""
    if county not in COUNTY_PARSERS:
        return None
    county_parser = COUNTY_PARSERS[county]()
    allocations = county_parser.parse(RAW_ROOT / county, fy)
    if not allocations:
        logger.warning(f"No allocations parsed for {county} FY{fy}")
        return None
    df = pd.DataFrame([a.to_dict() for a in allocations])
    csv_path = PROCESSED_DIR / f'{county}_fy{fy}.csv'
    df.to_csv(csv_path, index=False)
    logger.info(f"Saved {csv_path} ({len(df)} rows, total ${df['amount'].sum()/1e9:.2f}B)")
    return _build_county_entry(df, county, county_parser)


def main():
    parser = argparse.ArgumentParser(description='Process county budget data')
    parser.add_argument('--county', choices=ALL_COUNTIES + ['all'], default='all')
    parser.add_argument('--fiscal-years', type=int, nargs='+', default=DEFAULT_FISCAL_YEARS)
    args = parser.parse_args()

    fiscal_years = sorted(set(args.fiscal_years))
    counties = ALL_COUNTIES if args.county == 'all' else [args.county]

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    JSON_DIR.mkdir(parents=True, exist_ok=True)

    output: Dict[str, Any] = {
        'fiscal_years': fiscal_years,
        'default_fiscal_year': fiscal_years[0],
        'generated_at': datetime.now().isoformat(),
        'years': {},
    }

    for fy in fiscal_years:
        year_block: Dict[str, Any] = {}
        for county in ALL_COUNTIES:
            entry = _process_year(county, fy) if county in counties else None
            year_block[county] = entry or {'name': COUNTY_NAMES[county], 'available': False}
        output['years'][str(fy)] = year_block
        avail = [c for c, v in year_block.items() if v.get('available')]
        logger.info(f"FY{fy}: available — {', '.join(avail) or 'none'}")

    json_path = JSON_DIR / 'county_budgets.json'
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2)
    logger.info(f"Saved {json_path} — fiscal years {fiscal_years}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
