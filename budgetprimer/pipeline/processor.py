"""
Budget data processing functions.

This module contains functions for processing and analyzing budget data.
"""
from typing import List, Dict, Any, Tuple, Optional
import logging
import pandas as pd
import numpy as np
from pathlib import Path

from ..models import BudgetAllocation, BudgetSection, FundType, Program, Department

logger = logging.getLogger(__name__)


def process_budget_data(
    allocations: List[BudgetAllocation],
    fiscal_year: Optional[int] = None,
    section: Optional[str] = None
) -> pd.DataFrame:
    """
    Process budget allocations into a structured DataFrame.

    Args:
        allocations: List of budget allocations
        fiscal_year: Optional fiscal year to filter by
        section: Optional budget section to filter by

    Returns:
        Processed DataFrame
    """
    logger.info(f"Processing {len(allocations)} budget allocations")

    # Convert to list of dicts
    data = [alloc.to_dict() for alloc in allocations]

    if not data:
        logger.warning("No budget data to process")
        return pd.DataFrame()

    # Create DataFrame
    df = pd.DataFrame(data)

    # Filter by fiscal year if specified
    if fiscal_year is not None:
        df = df[df['fiscal_year'] == fiscal_year]

    # Filter by section if specified
    if section is not None and section != 'all':
        df = df[df['section'] == section]

    # Convert amount to numeric
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

    # Add derived columns
    df['amount_millions'] = df['amount'] / 1_000_000
    df['is_capital'] = df['section'] == BudgetSection.CAPITAL_IMPROVEMENT.value

    # Sort by program_id to make it easier to review related allocations
    df = df.sort_values(by='program_id')

    logger.info(f"Processed {len(df)} budget records")
    return df


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived analytical columns to the budget DataFrame.

    Adds:
        pct_of_total       – percentage of the grand-total budget
        pct_of_dept        – percentage within the program's department
        dept_rank          – rank within department (1 = largest program)
        overall_rank       – rank across all programs
        cost_per_position  – amount / positions (None when positions unavailable)
    """
    if df.empty:
        return df

    df = df.copy()

    # Percentage of grand total
    grand_total = df['amount'].sum()
    df['pct_of_total'] = (df['amount'] / grand_total * 100).round(2) if grand_total else 0

    # Percentage within department
    dept_totals = df.groupby('department_code')['amount'].transform('sum')
    df['pct_of_dept'] = (df['amount'] / dept_totals.replace(0, np.nan) * 100).round(2)

    # Rank within department (dense ranking, largest = 1)
    df['dept_rank'] = df.groupby('department_code')['amount'].rank(method='dense', ascending=False).astype(int)

    # Overall rank
    df['overall_rank'] = df['amount'].rank(method='dense', ascending=False).astype(int)

    # Cost per position
    if 'positions' in df.columns:
        pos = pd.to_numeric(df['positions'], errors='coerce')
        df['cost_per_position'] = (df['amount'] / pos.replace(0, np.nan)).round(0)
    else:
        df['cost_per_position'] = np.nan

    return df


def build_fy_comparison(
    allocations: List[BudgetAllocation],
    fy1: int = 2026,
    fy2: int = 2027,
    section: Optional[str] = None,
) -> pd.DataFrame:
    """Create a wide-format FY1 vs FY2 comparison table.

    Returns one row per (program_id, fund_type, section) with columns:
        amount_fy1, amount_fy2, delta, pct_change, positions_fy1, positions_fy2
    """
    data = [alloc.to_dict() for alloc in allocations]
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    if section and section != 'all':
        df = df[df['section'] == section]

    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

    id_cols = ['program_id', 'program_name', 'department_code', 'department_name',
               'fund_type', 'fund_category', 'section', 'category']
    existing_id_cols = [c for c in id_cols if c in df.columns]

    df1 = df[df['fiscal_year'] == fy1].copy()
    df2 = df[df['fiscal_year'] == fy2].copy()

    merged = pd.merge(
        df1[existing_id_cols + ['amount', 'positions']],
        df2[existing_id_cols + ['amount', 'positions']],
        on=existing_id_cols,
        how='outer',
        suffixes=(f'_fy{fy1}', f'_fy{fy2}'),
    )

    merged[f'amount_fy{fy1}'] = merged[f'amount_fy{fy1}'].fillna(0)
    merged[f'amount_fy{fy2}'] = merged[f'amount_fy{fy2}'].fillna(0)
    merged['delta'] = merged[f'amount_fy{fy2}'] - merged[f'amount_fy{fy1}']
    merged['pct_change'] = (
        merged['delta'] / merged[f'amount_fy{fy1}'].replace(0, np.nan) * 100
    ).round(2)

    merged = merged.sort_values('delta', ascending=True)
    return merged


def aggregate_by_category(
    df: pd.DataFrame,
    group_cols: List[str],
    agg_col: str = 'amount'
) -> pd.DataFrame:
    """
    Aggregate budget data by specified categories.
    
    Args:
        df: Input DataFrame
        group_cols: Columns to group by
        agg_col: Column to aggregate
        
    Returns:
        Aggregated DataFrame
    """
    if df.empty:
        return pd.DataFrame()
    
    # Ensure the aggregation column exists and is numeric
    if agg_col not in df.columns:
        raise ValueError(f"Column '{agg_col}' not found in DataFrame")
    
    # Ensure all group columns exist
    for col in group_cols:
        if col not in df.columns:
            raise ValueError(f"Group column '{col}' not found in DataFrame")
    
    # Group and aggregate
    agg_df = df.groupby(group_cols, dropna=False, observed=True)[agg_col] \
        .sum() \
        .reset_index() \
        .sort_values(by=agg_col, ascending=False)
    
    # Calculate percentages
    total = agg_df[agg_col].sum()
    if total > 0:
        agg_df['pct_of_total'] = (agg_df[agg_col] / total) * 100
    else:
        agg_df['pct_of_total'] = 0
    
    return agg_df


def calculate_summary_statistics(
    df: pd.DataFrame,
    value_col: str = 'amount',
    group_cols: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Calculate summary statistics for budget data.
    
    Args:
        df: Input DataFrame
        value_col: Column to calculate statistics for
        group_cols: Optional columns to group by
        
    Returns:
        Dictionary of summary statistics
    """
    if df.empty:
        return {}
    
    if value_col not in df.columns:
        raise ValueError(f"Column '{value_col}' not found in DataFrame")
    
    # Ensure the value column is numeric
    if not pd.api.types.is_numeric_dtype(df[value_col]):
        df[value_col] = pd.to_numeric(df[value_col], errors='coerce')
    
    # Calculate overall statistics
    stats = {
        'total': df[value_col].sum(),
        'count': len(df),
        'mean': df[value_col].mean(),
        'median': df[value_col].median(),
        'min': df[value_col].min(),
        'max': df[value_col].max(),
        'std': df[value_col].std(),
        'non_zero_count': (df[value_col] > 0).sum(),
        'zero_count': (df[value_col] == 0).sum(),
    }
    
    # Add grouped statistics if requested
    if group_cols and all(col in df.columns for col in group_cols):
        grouped = df.groupby(group_cols, dropna=False, observed=True)[value_col].agg(['sum', 'count', 'mean', 'median'])
        stats['by_group'] = grouped.to_dict(orient='index')
    
    return stats


def compare_budgets(
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    id_cols: List[str],
    value_col: str = 'amount'
) -> pd.DataFrame:
    """
    Compare two budget DataFrames to identify changes.
    
    Args:
        df_before: DataFrame with 'before' budget data
        df_after: DataFrame with 'after' budget data
        id_cols: Columns to use as unique identifiers
        value_col: Column containing values to compare
        
    Returns:
        DataFrame with comparison results
    """
    # Ensure required columns exist
    for col in id_cols + [value_col]:
        if col not in df_before.columns or col not in df_after.columns:
            raise ValueError(f"Column '{col}' must exist in both DataFrames")
    
    # Merge the DataFrames
    merged = pd.merge(
        df_before,
        df_after,
        on=id_cols,
        how='outer',
        suffixes=('_before', '_after'),
        indicator=True
    )
    
    # Calculate changes
    merged['change'] = merged[f'{value_col}_after'].fillna(0) - merged[f'{value_col}_before'].fillna(0)
    merged['pct_change'] = (
        (merged[f'{value_col}_after'] - merged[f'{value_col}_before']) / 
        merged[f'{value_col}_before'].replace(0, np.nan)
    ) * 100
    
    # Add change type
    merged['change_type'] = merged['_merge'].map({
        'left_only': 'removed',
        'right_only': 'added',
        'both': 'modified'
    })
    
    # Clean up
    merged = merged.drop('_merge', axis=1)
    
    return merged
