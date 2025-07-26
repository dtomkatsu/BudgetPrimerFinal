"""
Budget data transformation functions.

This module contains functions for transforming budget data between different
formats and states (e.g., pre-veto to post-veto).
"""
from typing import List, Dict, Any, Optional, Tuple
import logging
import pandas as pd
from pathlib import Path

from ..models import BudgetAllocation, FundType

logger = logging.getLogger(__name__)


def transform_to_post_veto(
    pre_veto_data: List[BudgetAllocation],
    veto_changes: List[Dict[str, Any]]
) -> List[BudgetAllocation]:
    """
    Transform pre-veto budget data to post-veto by applying veto changes.
    
    Args:
        pre_veto_data: List of pre-veto budget allocations
        veto_changes: List of veto changes to apply
        
    Returns:
        List of post-veto budget allocations
    """
    logger.info("Starting transformation to post-veto data")
    
    # Create a copy of the pre-veto data
    post_veto_data = [alloc for alloc in pre_veto_data]
    
    # Apply each veto change
    for change in veto_changes:
        post_veto_data = _apply_veto_change(post_veto_data, change)
    
    logger.info(f"Applied {len(veto_changes)} veto changes to {len(post_veto_data)} allocations")
    return post_veto_data


def _apply_veto_change(
    allocations: List[BudgetAllocation],
    change: Dict[str, Any]
) -> List[BudgetAllocation]:
    """Apply a single veto change to the budget allocations."""
    program_id = change.get('program_id')
    fiscal_year = str(change.get('fiscal_year', ''))
    
    # Get the fund type from the change (default to 'A' if not specified)
    change_fund_type = change.get('fund_type', 'A')
    
    # Find matching allocations (must match program_id, fiscal_year, and fund_type)
    matches = [
        (i, alloc) for i, alloc in enumerate(allocations)
        if (alloc.program_id == program_id and 
            str(alloc.fiscal_year) == fiscal_year and
            alloc.fund_type.value == change_fund_type)
    ]
    
    if not matches:
        logger.warning(f"No matching allocation found for program {program_id}, FY{fiscal_year}")
        return allocations
    
    # Apply the change to each matching allocation
    for idx, alloc in matches:
        # Create a copy of the allocation
        new_alloc = BudgetAllocation(**alloc.__dict__)
        
        # Apply changes
        if 'amount' in change:
            new_alloc.amount = change['amount']
        if 'fund_type' in change:
            new_alloc.fund_type = FundType.from_string(change['fund_type'])
        if 'positions' in change:
            new_alloc.positions = change['positions']
        if 'notes' in change:
            new_alloc.notes = change['notes']
        
        # Update the allocation in the list
        allocations[idx] = new_alloc
    
    return allocations


def reconcile_fund_types(
    allocations: List[BudgetAllocation],
    fund_type_map: Optional[Dict[str, str]] = None
) -> List[BudgetAllocation]:
    """
    Reconcile fund types across budget allocations.
    
    Args:
        allocations: List of budget allocations
        fund_type_map: Optional mapping of program IDs to fund types
        
    Returns:
        List of allocations with reconciled fund types
    """
    if not fund_type_map:
        fund_type_map = {}
    
    result = []
    
    for alloc in allocations:
        # Create a copy of the allocation
        new_alloc = BudgetAllocation(**alloc.__dict__)
        
        # Check if we have a mapping for this program
        if alloc.program_id in fund_type_map:
            new_alloc.fund_type = FundType.from_string(fund_type_map[alloc.program_id])
        
        result.append(new_alloc)
    
    return result


def validate_budget_data(
    allocations: List[BudgetAllocation],
    require_fund_type: bool = True
) -> Tuple[bool, List[str]]:
    """
    Validate budget data for consistency and completeness.
    
    Args:
        allocations: List of budget allocations to validate
        require_fund_type: Whether to require a valid fund type
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not allocations:
        return False, ["No budget allocations provided"]
    
    required_fields = [
        'program_id', 'program_name', 'department_code', 
        'fiscal_year', 'amount', 'section'
    ]
    
    for i, alloc in enumerate(allocations):
        # Check required fields
        for field in required_fields:
            if not getattr(alloc, field, None):
                errors.append(f"Allocation {i}: Missing required field '{field}'")
        
        # Check fund type if required
        if require_fund_type and (not alloc.fund_type or alloc.fund_type == FundType.UNKNOWN):
            errors.append(
                f"Allocation {i} (Program {alloc.program_id}, FY{alloc.fiscal_year}): "
                f"Missing or invalid fund type"
            )
        
        # Check amount is non-negative
        if alloc.amount < 0:
            errors.append(
                f"Allocation {i} (Program {alloc.program_id}, FY{alloc.fiscal_year}): "
                f"Negative amount: {alloc.amount}"
            )
    
    return len(errors) == 0, errors
