#!/usr/bin/env python3
"""
Compare two budget bill drafts and produce a comparison JSON for the frontend.

Usage:
    python scripts/compare_drafts.py --draft1 HD1 --draft2 SD1
    python scripts/compare_drafts.py --draft1 HD1 --draft2 SD1 --fy 2026
    python scripts/compare_drafts.py file1.txt file2.txt --label1 HD1 --label2 SD1
"""
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from budgetprimer.parsers.fast_parser import FastBudgetParser
from budgetprimer.pipeline.processor import compare_budgets, process_budget_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DRAFTS_DIR = PROJECT_ROOT / 'data' / 'raw' / 'drafts'
JSON_DIR = PROJECT_ROOT / 'docs' / 'js'


def resolve_draft_path(label: str) -> Path:
    """Resolve a draft label (HD1, SD1, introduced) to its file path."""
    meta_path = DRAFTS_DIR / 'metadata.json'
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        drafts = meta.get('drafts', {})
        if label in drafts:
            return DRAFTS_DIR / drafts[label]['filename']

    # Try direct file naming
    for candidate in [
        DRAFTS_DIR / f'HB1800_{label}.txt',
        DRAFTS_DIR / label,
        Path(label),
    ]:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f'Draft "{label}" not found. Run download_bill.py first.')


def compare_drafts(
    file1: Path,
    file2: Path,
    label1: str,
    label2: str,
    fy: int = 2026,
) -> dict:
    """Parse two drafts, compare allocations, return structured result."""
    parser = FastBudgetParser(fy1=fy, fy2=fy + 1)

    logger.info(f'Parsing draft 1: {file1.name}')
    allocs1 = parser.parse(str(file1))
    logger.info(f'  → {len(allocs1)} allocations')

    logger.info(f'Parsing draft 2: {file2.name}')
    allocs2 = parser.parse(str(file2))
    logger.info(f'  → {len(allocs2)} allocations')

    df1 = process_budget_data(allocs1, fiscal_year=fy)
    df2 = process_budget_data(allocs2, fiscal_year=fy)

    logger.info(f'FY{fy}: {len(df1)} records in {label1}, {len(df2)} in {label2}')

    # Aggregate by unique key before comparing to avoid cross-join on duplicates
    id_cols = ['program_id', 'program_name', 'department_code', 'department_name',
               'fund_type', 'fund_category', 'section', 'category']
    existing = [c for c in id_cols if c in df1.columns and c in df2.columns]

    df1_agg = df1.groupby(existing, dropna=False).agg({'amount': 'sum'}).reset_index()
    df2_agg = df2.groupby(existing, dropna=False).agg({'amount': 'sum'}).reset_index()

    comparison = compare_budgets(
        df_before=df1_agg,
        df_after=df2_agg,
        id_cols=existing,
        value_col='amount',
    )

    # Rename columns for clarity
    comparison = comparison.rename(columns={
        'amount_before': f'amount_{label1.lower()}',
        'amount_after': f'amount_{label2.lower()}',
    })

    # Replace NaN/inf for JSON
    comparison = comparison.where(comparison.notna(), None)
    for col in comparison.select_dtypes(include=['float64']).columns:
        comparison[col] = comparison[col].apply(
            lambda v: None if (v is not None and isinstance(v, float) and (np.isnan(v) or np.isinf(v))) else v
        )

    records = comparison.to_dict(orient='records')
    # Final NaN cleanup
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                rec[k] = None

    # Build summary
    changes = [r for r in records if r.get('change') and r['change'] != 0]
    increases = [r for r in changes if (r.get('change') or 0) > 0]
    decreases = [r for r in changes if (r.get('change') or 0) < 0]
    added = [r for r in records if r.get('change_type') == 'added']
    removed = [r for r in records if r.get('change_type') == 'removed']

    total_d1 = sum(r.get(f'amount_{label1.lower()}') or 0 for r in records)
    total_d2 = sum(r.get(f'amount_{label2.lower()}') or 0 for r in records)

    result = {
        'metadata': {
            'draft1': label1,
            'draft2': label2,
            'bill_number': 'HB1800',
            'fiscal_year': fy,
            'generated_at': datetime.now().isoformat(),
            'net_change': total_d2 - total_d1,
        },
        'summary': {
            'total_draft1': total_d1,
            'total_draft2': total_d2,
            'net_change': total_d2 - total_d1,
            'total_items': len(records),
            'items_modified': len(changes),
            'items_increased': len(increases),
            'items_decreased': len(decreases),
            'items_added': len(added),
            'items_removed': len(removed),
        },
        'comparisons': sorted(records, key=lambda r: r.get('change') or 0),
    }

    return result


def main():
    parser = argparse.ArgumentParser(description='Compare two budget bill drafts')
    parser.add_argument('files', nargs='*', help='Two file paths (alternative to --draft1/--draft2)')
    parser.add_argument('--draft1', default='HD1', help='First draft label')
    parser.add_argument('--draft2', default='SD1', help='Second draft label')
    parser.add_argument('--label1', help='Display label for draft 1 (defaults to --draft1)')
    parser.add_argument('--label2', help='Display label for draft 2 (defaults to --draft2)')
    parser.add_argument('--fy', type=int, default=2026, help='Fiscal year to compare')
    parser.add_argument('--output', type=Path, default=JSON_DIR / 'draft_comparison.json',
                        help='Output JSON path')
    args = parser.parse_args()

    if args.files and len(args.files) == 2:
        file1, file2 = Path(args.files[0]), Path(args.files[1])
        label1 = args.label1 or file1.stem
        label2 = args.label2 or file2.stem
    else:
        file1 = resolve_draft_path(args.draft1)
        file2 = resolve_draft_path(args.draft2)
        label1 = args.label1 or args.draft1
        label2 = args.label2 or args.draft2

    result = compare_drafts(file1, file2, label1, label2, args.fy)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    s = result['summary']
    net = result['metadata']['net_change']
    sign = '+' if net > 0 else ''
    logger.info(f'Comparison complete: {s["total_items"]} items')
    logger.info(f'  {s["items_increased"]} increases, {s["items_decreased"]} decreases, '
                f'{s["items_added"]} added, {s["items_removed"]} removed')
    logger.info(f'  Net change: {sign}${net:,.0f}')
    logger.info(f'Saved to {args.output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
