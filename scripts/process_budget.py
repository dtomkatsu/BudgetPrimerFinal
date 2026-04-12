#!/usr/bin/env python3
"""
Budget Data Processing Script — Enhanced Edition

Parses Hawaii State Budget HB 300, produces:
  - Per-FY CSVs with derived metrics (both FY2026 and FY2027)
  - FY26 vs FY27 comparison CSV
  - Veto impact table (when veto file supplied)
  - Enriched JSON for the web app (departments, programs, summary stats)
  - Charts: MOF pie, department bars, CIP pie, FY comparison, fund-type stacked
  - One-time appropriation summary CSV
"""
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use('Agg')  # non-interactive backend

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from budgetprimer import parse_budget_file
from budgetprimer.pipeline import (
    add_derived_metrics,
    build_fy_comparison,
    process_budget_data,
    process_budget_with_vetoes,
)
from budgetprimer.visualization.charts import (
    CIPChart,
    DepartmentChart,
    FYComparisonChart,
    FundTypeStackedChart,
    MeansOfFinanceChart,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('budget_processing.log')],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_chart(chart_cls, df, fy, charts_dir, filename, title=None, **kwargs):
    """Instantiate a chart class, create & save."""
    try:
        chart = chart_cls(fiscal_year=fy, title=title, **kwargs)
        fig = chart.create(df, output_file=charts_dir / filename)
        plt.close(fig)
        logger.info(f"Saved {filename}")
    except Exception as e:
        logger.warning(f"Could not create {filename}: {e}")


def _build_departments_json(
    df_fy: pd.DataFrame,
    programs_by_dept: Dict[str, List[Dict]],
    dept_descriptions: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Build enriched departments.json with per-department fund breakdown and program lists."""
    dept_summary = df_fy.groupby('department_code').agg(
        operating=('amount', lambda x: x[df_fy.loc[x.index, 'section'] == 'Operating'].sum()),
        capital=('amount', lambda x: x[df_fy.loc[x.index, 'section'] == 'Capital Improvement'].sum()),
        one_time=('amount', lambda x: x[df_fy.loc[x.index, 'section'] == 'One-Time'].sum()),
        positions=('positions', lambda x: x.dropna().sum()),
    ).reset_index()

    # Fund breakdown per department
    fund_by_dept = (
        df_fy.groupby(['department_code', 'fund_category'])['amount']
        .sum()
        .reset_index()
    )

    departments = []
    for _, row in dept_summary.iterrows():
        code = row['department_code']
        dept_name = df_fy.loc[df_fy['department_code'] == code, 'department_name'].iloc[0] if len(df_fy[df_fy['department_code'] == code]) > 0 else code
        total = row['operating'] + row['capital'] + row['one_time']

        fund_breakdown = {}
        dept_funds = fund_by_dept[fund_by_dept['department_code'] == code]
        for _, fr in dept_funds.iterrows():
            fund_breakdown[fr['fund_category']] = float(fr['amount'])

        departments.append({
            'id': code.lower(),
            'code': code,
            'name': dept_name,
            'description': dept_descriptions.get(code, ''),
            'budget': f'${total/1e9:.1f}B' if total >= 1e9 else f'${total/1e6:.0f}M',
            'operating_budget': float(row['operating']),
            'capital_budget': float(row['capital']),
            'one_time_appropriations': float(row['one_time']),
            'total_budget': float(total),
            'positions': float(row['positions']) if pd.notna(row['positions']) else None,
            'fund_breakdown': fund_breakdown,
            'programs': programs_by_dept.get(code, []),
            'path': f'/pages/{code.lower()}.html',
        })

    departments.sort(key=lambda d: d['total_budget'], reverse=True)
    return departments


def _build_programs_by_dept(df_fy: pd.DataFrame) -> Dict[str, List[Dict]]:
    """Build per-department program-level data for JSON output."""
    programs: Dict[str, List[Dict]] = {}
    grouped = df_fy.groupby(['department_code', 'program_id', 'program_name', 'section', 'fund_type', 'fund_category'])
    for (dept, pid, pname, section, ft, fcat), group in grouped:
        entry = {
            'program_id': pid,
            'program_name': pname,
            'section': section,
            'fund_type': ft,
            'fund_category': fcat,
            'amount': float(group['amount'].sum()),
            'positions': float(group['positions'].sum()) if group['positions'].notna().any() else None,
        }
        programs.setdefault(dept, []).append(entry)

    # Sort programs within each department by amount descending
    for dept in programs:
        programs[dept].sort(key=lambda p: p['amount'], reverse=True)
    return programs


def _build_summary_stats(df_fy: pd.DataFrame, fy: int, source: str) -> Dict[str, Any]:
    """Build enriched summary_stats.json."""
    total_budget = float(df_fy['amount'].sum())
    operating = float(df_fy.loc[df_fy['section'] == 'Operating', 'amount'].sum())
    capital = float(df_fy.loc[df_fy['section'] == 'Capital Improvement', 'amount'].sum())
    one_time = float(df_fy.loc[df_fy['section'] == 'One-Time', 'amount'].sum())

    fund_breakdown = df_fy.groupby('fund_category')['amount'].sum().to_dict()
    fund_breakdown = {k: float(v) for k, v in sorted(fund_breakdown.items())}

    dept_breakdown = df_fy.groupby('department_name')['amount'].sum().sort_values(ascending=False).to_dict()
    dept_breakdown = {k: float(v) for k, v in dept_breakdown.items()}

    total_positions = float(df_fy['positions'].dropna().sum()) if 'positions' in df_fy.columns else None

    return {
        'fiscal_year': fy,
        'total_budget': total_budget,
        'operating_budget': operating,
        'capital_budget': capital,
        'one_time_appropriations': one_time,
        'total_positions': total_positions,
        'fund_breakdown': fund_breakdown,
        'department_totals': dept_breakdown,
        'num_departments': int(df_fy['department_code'].nunique()),
        'num_programs': int(df_fy['program_id'].nunique()),
        'num_records': len(df_fy),
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'source_file': source,
            'total_records': len(df_fy),
            'fiscal_year': fy,
        },
    }


def _build_veto_impact(
    pre_df: pd.DataFrame,
    post_df: pd.DataFrame,
    fy: int,
) -> pd.DataFrame:
    """Produce a veto-impact table showing pre/post amounts and deltas."""
    id_cols = ['program_id', 'program_name', 'department_code', 'department_name',
               'section', 'fund_type', 'fund_category']
    existing = [c for c in id_cols if c in pre_df.columns and c in post_df.columns]

    merged = pd.merge(
        pre_df[existing + ['amount']],
        post_df[existing + ['amount']],
        on=existing,
        how='outer',
        suffixes=('_pre_veto', '_post_veto'),
    )
    merged['amount_pre_veto'] = merged['amount_pre_veto'].fillna(0)
    merged['amount_post_veto'] = merged['amount_post_veto'].fillna(0)
    merged['veto_delta'] = merged['amount_post_veto'] - merged['amount_pre_veto']
    merged['veto_pct_change'] = (
        merged['veto_delta'] / merged['amount_pre_veto'].replace(0, np.nan) * 100
    ).round(2)

    # Only keep rows where something changed
    changed = merged[merged['veto_delta'].abs() > 0].copy()
    changed = changed.sort_values('veto_delta', ascending=True)
    return changed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Process Hawaii State Budget data')
    parser.add_argument('input_file', help='Path to the budget text file')
    parser.add_argument('--output-dir', default='data/output', help='Output directory')
    parser.add_argument('--fiscal-year', type=int, default=2026)
    parser.add_argument('--section', choices=['operating', 'capital', 'all'], default='all')
    parser.add_argument('--veto-mode', choices=['none', 'apply', 'both'], default='none')
    parser.add_argument('--veto-file', type=Path)
    parser.add_argument('--one-time-appropriations', type=Path,
                        default=Path('data/config/one_time_appropriations_fy2026.csv'))
    parser.add_argument('--top-n', type=int, default=15)
    args = parser.parse_args()

    fy1 = args.fiscal_year
    fy2 = fy1 + 1

    output_dir = Path(args.output_dir)
    processed_dir = Path('data/processed')
    charts_dir = output_dir / 'charts'
    json_dir = Path('docs/js')
    for d in [output_dir, charts_dir, processed_dir, json_dir]:
        d.mkdir(parents=True, exist_ok=True)

    try:
        # ---------------------------------------------------------------
        # 1. Parse
        # ---------------------------------------------------------------
        logger.info(f"Parsing {args.input_file}")
        allocations = parse_budget_file(args.input_file)
        if not allocations:
            logger.error("No allocations found")
            return 1
        logger.info(f"Parsed {len(allocations)} allocations")

        # ---------------------------------------------------------------
        # 2. Process both fiscal years
        # ---------------------------------------------------------------
        result = process_budget_with_vetoes(
            allocations=allocations,
            veto_mode=args.veto_mode,
            veto_file=args.veto_file,
            one_time_appropriations_file=args.one_time_appropriations,
            fiscal_year=None,  # don't filter — we want both FYs
            section=args.section,
        )

        # Process each FY separately for CSV output
        all_allocs = result.get('post_veto_allocations', allocations)
        df_fy1 = process_budget_data(all_allocs, fiscal_year=fy1, section=args.section)
        df_fy2 = process_budget_data(all_allocs, fiscal_year=fy2, section=args.section)
        df_both = process_budget_data(all_allocs, fiscal_year=None, section=args.section)

        # Add derived metrics
        df_fy1 = add_derived_metrics(df_fy1)
        df_fy2 = add_derived_metrics(df_fy2)

        # ---------------------------------------------------------------
        # 3. Save CSVs
        # ---------------------------------------------------------------
        suffix = '_post_veto' if args.veto_mode in ('apply', 'both') else ''

        csv1 = processed_dir / f'budget_allocations_fy{fy1}{suffix}.csv'
        csv2 = processed_dir / f'budget_allocations_fy{fy2}{suffix}.csv'
        df_fy1.to_csv(csv1, index=False)
        df_fy2.to_csv(csv2, index=False)
        logger.info(f"Saved {csv1} ({len(df_fy1)} rows) and {csv2} ({len(df_fy2)} rows)")

        # FY comparison
        fy_comp = build_fy_comparison(all_allocs, fy1=fy1, fy2=fy2, section=args.section)
        fy_comp_csv = processed_dir / f'budget_fy{fy1}_vs_fy{fy2}{suffix}.csv'
        fy_comp.to_csv(fy_comp_csv, index=False)
        logger.info(f"Saved FY comparison: {fy_comp_csv} ({len(fy_comp)} rows)")

        # ---------------------------------------------------------------
        # 4. Veto impact table
        # ---------------------------------------------------------------
        if args.veto_mode in ('apply', 'both') and 'post_veto_df' in result:
            pre_df = result.get('pre_veto_df', df_fy1)
            post_df = result['post_veto_df']
            # Filter to fy1 for comparison
            pre_fy1 = pre_df[pre_df['fiscal_year'] == fy1] if 'fiscal_year' in pre_df.columns else pre_df
            post_fy1 = post_df[post_df['fiscal_year'] == fy1] if 'fiscal_year' in post_df.columns else post_df

            veto_impact = _build_veto_impact(pre_fy1, post_fy1, fy1)
            veto_csv = processed_dir / f'veto_impact_fy{fy1}.csv'
            veto_impact.to_csv(veto_csv, index=False)
            logger.info(f"Saved veto impact: {veto_csv} ({len(veto_impact)} changed items)")

        # ---------------------------------------------------------------
        # 5. Enriched JSON for web app
        # ---------------------------------------------------------------
        # Load department descriptions
        desc_path = processed_dir / 'department_descriptions.json'
        dept_descriptions = {}
        if desc_path.exists():
            with open(desc_path) as f:
                raw_descs = json.load(f)
                if isinstance(raw_descs, dict):
                    for code, info in raw_descs.items():
                        if isinstance(info, dict):
                            dept_descriptions[code] = info.get('description', '')
                        else:
                            dept_descriptions[code] = str(info)
                elif isinstance(raw_descs, list):
                    for entry in raw_descs:
                        code = entry.get('department_code', '')
                        dept_descriptions[code] = entry.get('description', '')

        # Programs by department
        programs_by_dept = _build_programs_by_dept(df_fy1)

        # Departments JSON
        departments = _build_departments_json(df_fy1, programs_by_dept, dept_descriptions)
        with open(json_dir / 'departments.json', 'w') as f:
            json.dump(departments, f, indent=2)
        logger.info(f"Saved enriched departments.json ({len(departments)} departments)")

        # Summary stats JSON
        stats = _build_summary_stats(df_fy1, fy1, str(csv1.name))
        with open(json_dir / 'summary_stats.json', 'w') as f:
            json.dump(stats, f, indent=2)
        logger.info("Saved enriched summary_stats.json")

        # Programs JSON (all programs, for search/filter)
        all_programs = []
        for dept_programs in programs_by_dept.values():
            all_programs.extend(dept_programs)
        with open(json_dir / 'programs.json', 'w') as f:
            json.dump(all_programs, f, indent=2)
        logger.info(f"Saved programs.json ({len(all_programs)} program entries)")

        # FY comparison JSON (for frontend charts)
        fy_comp_json = fy_comp.copy()
        # Replace NaN with None for JSON serialization
        fy_comp_json = fy_comp_json.where(fy_comp_json.notna(), None)
        records = fy_comp_json.to_dict(orient='records')
        # Ensure no NaN/inf values leak through
        for rec in records:
            for k, v in rec.items():
                if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                    rec[k] = None
        with open(json_dir / 'fy_comparison.json', 'w') as f:
            json.dump(records, f, indent=2, default=str)
        logger.info(f"Saved fy_comparison.json ({len(fy_comp_json)} rows)")

        # ---------------------------------------------------------------
        # 6. Charts
        # ---------------------------------------------------------------
        logger.info("Creating charts...")

        # Standard charts for FY1
        _save_chart(MeansOfFinanceChart, df_both, fy1, charts_dir,
                     f'means_of_finance_fy{fy1}{suffix}.png',
                     title=f'Means of Finance (FY{fy1})')
        _save_chart(DepartmentChart, df_both, fy1, charts_dir,
                     f'department_budgets_fy{fy1}{suffix}.png',
                     title=f'Department Budgets (FY{fy1})')
        _save_chart(CIPChart, df_both, fy1, charts_dir,
                     f'cip_funding_fy{fy1}{suffix}.png',
                     title=f'Capital Improvement Funding (FY{fy1})')

        # New: FY comparison chart
        try:
            fy_chart = FYComparisonChart(fy1=fy1, fy2=fy2,
                                          title=f'Department Budgets: FY{fy1} vs FY{fy2}')
            fig = fy_chart.create(df_both, output_file=charts_dir / f'fy{fy1}_vs_fy{fy2}_comparison.png')
            plt.close(fig)
            logger.info(f"Saved FY comparison chart")
        except Exception as e:
            logger.warning(f"Could not create FY comparison chart: {e}")

        # New: Fund-type stacked chart
        _save_chart(FundTypeStackedChart, df_both, fy1, charts_dir,
                     f'fund_type_composition_fy{fy1}{suffix}.png',
                     title=f'Fund-Type Composition by Department (FY{fy1})')

        # If veto mode is both, also make post-veto versions
        if args.veto_mode == 'both' and 'post_veto_df' in result:
            post_df = result['post_veto_df']
            _save_chart(MeansOfFinanceChart, post_df, fy1, charts_dir,
                         f'means_of_finance_fy{fy1}_post_veto.png',
                         title=f'Means of Finance (FY{fy1}) - Post Veto')
            _save_chart(DepartmentChart, post_df, fy1, charts_dir,
                         f'department_budgets_fy{fy1}_post_veto.png',
                         title=f'Department Budgets (FY{fy1}) - Post Veto')

        logger.info("Processing completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
