#!/usr/bin/env python3
"""
County Budget Processing Script

County analog of process_budget.py: parses committed raw county budget files
(see scripts/fetch_county_budgets.py) and produces:
  - Per-county CSVs in data/processed/counties/
  - docs/js/county_budgets.json for the web app (all four counties in one
    file; counties without a parser yet are marked available: false and shown
    as "coming soon" in the frontend)

Usage:
    python scripts/process_county_budgets.py --county all --fiscal-year 2026
"""
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

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

OPERATING = 'Operating'
CAPITAL = 'Capital Improvement'


def _fmt_budget(total: float) -> str:
    return f'${total/1e9:.1f}B' if total >= 1e9 else f'${total/1e6:.0f}M'


def _build_county_entry(df: pd.DataFrame, county: str, parser) -> Dict[str, Any]:
    """Build the per-county block of county_budgets.json.

    Mirrors the conventions of _build_departments_json in process_budget.py:
    fund_breakdown dicts, budget display strings, departments sorted by total.
    """
    operating = float(df.loc[df['section'] == OPERATING, 'amount'].sum())
    capital = float(df.loc[df['section'] == CAPITAL, 'amount'].sum())
    total = float(df['amount'].sum())

    fund_breakdown = {
        k: float(v) for k, v in
        df.groupby('fund_category')['amount'].sum().sort_values(ascending=False).items()
    }

    departments: List[Dict[str, Any]] = []
    for code, dept_df in df.groupby('department_code'):
        dept_total = float(dept_df['amount'].sum())
        dept_fund_breakdown = {
            k: float(v) for k, v in
            dept_df.groupby('fund_category')['amount'].sum().sort_values(ascending=False).items()
        }
        # Program/activity level: one entry per program with its own totals and
        # fund detail nested beneath (department → program → fund hierarchy).
        programs = []
        for pname, p_df in dept_df.groupby(
            dept_df['program_name'].fillna('(department-wide)')
        ):
            funds = []
            fund_group = p_df.groupby(
                ['fund_name', 'fund_category', 'section'], dropna=False
            )['amount'].sum().reset_index()
            for _, row in fund_group.iterrows():
                funds.append({
                    'fund_name': row['fund_name'],
                    'fund_category': row['fund_category'],
                    'section': row['section'],
                    'amount': float(row['amount']),
                })
            funds.sort(key=lambda f: abs(f['amount']), reverse=True)
            programs.append({
                'program_name': pname,
                'total_budget': float(p_df['amount'].sum()),
                'operating_budget': float(p_df.loc[p_df['section'] == OPERATING, 'amount'].sum()),
                'capital_budget': float(p_df.loc[p_df['section'] == CAPITAL, 'amount'].sum()),
                'fund_breakdown': {
                    k: float(v) for k, v in
                    p_df.groupby('fund_category')['amount'].sum().sort_values(ascending=False).items()
                },
                'funds': funds,
            })
        programs.sort(key=lambda p: abs(p['total_budget']), reverse=True)

        departments.append({
            'code': code,
            'name': dept_df['department_name'].iloc[0],
            'budget': _fmt_budget(dept_total),
            'operating_budget': float(dept_df.loc[dept_df['section'] == OPERATING, 'amount'].sum()),
            'capital_budget': float(dept_df.loc[dept_df['section'] == CAPITAL, 'amount'].sum()),
            'total_budget': dept_total,
            'fund_breakdown': dept_fund_breakdown,
            'num_programs': len(programs),
            'programs': programs,
        })
    departments.sort(key=lambda d: d['total_budget'], reverse=True)

    return {
        'name': COUNTY_NAMES[county],
        'available': True,
        'total_budget': total,
        'operating_budget': operating,
        'capital_budget': capital,
        'capital_note': 'CIP not yet included' if capital == 0 else None,
        'coverage_note': parser.coverage_note or None,
        'fund_breakdown': fund_breakdown,
        'source': {
            'label': parser.source_label,
            'url': parser.source_url,
        },
        'num_departments': int(df['department_code'].nunique()),
        # program names repeat across departments ("Administration"), so count
        # department × program pairs
        'num_programs': int(df.groupby(
            ['department_code', df['program_name'].fillna('(department-wide)')]
        ).ngroups),
        'num_records': len(df),
        'departments': departments,
    }


def main():
    parser = argparse.ArgumentParser(description='Process county budget data')
    parser.add_argument('--county', choices=ALL_COUNTIES + ['all'], default='all')
    parser.add_argument('--fiscal-year', type=int, default=2026)
    args = parser.parse_args()

    fy = args.fiscal_year
    counties = ALL_COUNTIES if args.county == 'all' else [args.county]

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    JSON_DIR.mkdir(parents=True, exist_ok=True)

    output: Dict[str, Any] = {
        'fiscal_year': fy,
        'generated_at': datetime.now().isoformat(),
        'counties': {},
    }

    for county in ALL_COUNTIES:
        if county not in counties or county not in COUNTY_PARSERS:
            output['counties'][county] = {
                'name': COUNTY_NAMES[county],
                'available': False,
            }
            continue

        county_parser = COUNTY_PARSERS[county]()
        allocations = county_parser.parse(RAW_ROOT / county, fy)
        if not allocations:
            logger.warning(f"No allocations parsed for {county} FY{fy}")
            output['counties'][county] = {
                'name': COUNTY_NAMES[county],
                'available': False,
            }
            continue

        df = pd.DataFrame([a.to_dict() for a in allocations])

        csv_path = PROCESSED_DIR / f'{county}_fy{fy}.csv'
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved {csv_path} ({len(df)} rows, total ${df['amount'].sum()/1e9:.2f}B)")

        output['counties'][county] = _build_county_entry(df, county, county_parser)

    json_path = JSON_DIR / 'county_budgets.json'
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2)
    available = [c for c, v in output['counties'].items() if v.get('available')]
    logger.info(f"Saved {json_path} — available: {', '.join(available) or 'none'}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
