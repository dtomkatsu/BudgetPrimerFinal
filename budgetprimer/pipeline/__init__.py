"""
Budget data processing pipeline.

This module provides functions for processing and transforming budget data
through various stages of the analysis pipeline, including veto processing.
"""

from .transformer import (
    transform_to_post_veto,
    load_one_time_appropriations,
    _apply_veto_change as apply_veto_changes,
    reconcile_fund_types,
    validate_budget_data
)
from .processor import (
    process_budget_data,
    aggregate_by_category,
    calculate_summary_statistics
)
from .veto_processor import (
    load_veto_changes,
    process_budget_with_vetoes
)

__all__ = [
    # Core processing
    'process_budget_data',
    'aggregate_by_category',
    'calculate_summary_statistics',
    
    # Veto processing
    'transform_to_post_veto',
    'apply_veto_changes',
    'load_veto_changes',
    'process_budget_with_vetoes',
    
    # One-time appropriations
    'load_one_time_appropriations',
    
    # Utility
    'reconcile_fund_types',
    'validate_budget_data'
]
