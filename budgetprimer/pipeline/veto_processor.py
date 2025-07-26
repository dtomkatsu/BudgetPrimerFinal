"""
Veto processing functionality for budget data.

This module provides functions for loading and applying veto changes to budget allocations.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import csv
import logging

from ..models import BudgetAllocation, FundType

logger = logging.getLogger(__name__)

def load_veto_changes(veto_file: Path) -> List[Dict[str, Any]]:
    """
    Load veto changes from a CSV file.
    
    Expected CSV format:
        Program,Type,FY 2026 Amount,FY 2027 Amount
        BED143,Operating,,2,701,795A
        HTH430,Operating,147,045,865A,
    
    Args:
        veto_file: Path to the veto CSV file
        
    Returns:
        List of veto changes in the format expected by transform_to_post_veto
    """
    changes = []
    
    try:
        with open(veto_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                program_id = row.get('Program', '').strip()
                if not program_id:
                    continue
                    
                # Process FY 2026 amount if present
                fy26_amt = row.get('FY 2026 Amount', '').strip()
                if fy26_amt:
                    amount_str = fy26_amt.rstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                    amount = int(amount_str.replace(',', '')) if amount_str else 0
                    fund_type = fy26_amt[-1] if fy26_amt and fy26_amt[-1].isalpha() else 'A'
                    
                    changes.append({
                        'program_id': program_id,
                        'fiscal_year': 2026,
                        'amount': amount,
                        'fund_type': fund_type,
                        'notes': f'Veto change for {program_id} FY2026'
                    })
                
                # Process FY 2027 amount if present
                fy27_amt = row.get('FY 2027 Amount', '').strip()
                if fy27_amt:
                    amount_str = fy27_amt.rstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                    amount = int(amount_str.replace(',', '')) if amount_str else 0
                    fund_type = fy27_amt[-1] if fy27_amt and fy27_amt[-1].isalpha() else 'A'
                    
                    changes.append({
                        'program_id': program_id,
                        'fiscal_year': 2027,
                        'amount': amount,
                        'fund_type': fund_type,
                        'notes': f'Veto change for {program_id} FY2027'
                    })
        
        logger.info(f"Loaded {len(changes)} veto changes from {veto_file}")
        return changes
        
    except Exception as e:
        logger.error(f"Error loading veto changes from {veto_file}: {str(e)}")
        return []


def process_budget_with_vetoes(
    allocations: List[BudgetAllocation],
    veto_mode: str = "none",
    veto_file: Optional[Path] = None,
    fiscal_year: Optional[int] = None,
    section: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process budget data with optional veto application.
    
    Args:
        allocations: List of budget allocations
        veto_mode: One of 'none', 'apply', or 'both'
        veto_file: Path to veto CSV file (required if veto_mode is 'apply' or 'both')
        fiscal_year: Optional fiscal year to filter by
        section: Optional section to filter by
        
    Returns:
        Dictionary containing:
        - pre_veto_df: DataFrame of original allocations
        - post_veto_df: DataFrame with vetoes applied (if veto_mode is 'apply' or 'both')
        - pre_veto_allocations: Original allocations (if veto_mode is 'both')
        - post_veto_allocations: Allocations with vetoes applied (if veto_mode is 'both')
    """
    from .processor import process_budget_data
    from .transformer import transform_to_post_veto
    
    result = {}
    
    # Process pre-veto data
    pre_veto_allocations = allocations.copy()
    pre_veto_df = process_budget_data(
        pre_veto_allocations,
        fiscal_year=fiscal_year,
        section=section
    )
    result['pre_veto_df'] = pre_veto_df
    
    if veto_mode in ('apply', 'both') and veto_file and veto_file.exists():
        # Load and apply veto changes
        veto_changes = load_veto_changes(veto_file)
        if not veto_changes:
            logger.warning(f"No veto changes loaded from {veto_file}")
            return result
            
        post_veto_allocations = transform_to_post_veto(
            pre_veto_allocations.copy(),
            veto_changes
        )
        
        # Process post-veto data
        post_veto_df = process_budget_data(
            post_veto_allocations,
            fiscal_year=fiscal_year,
            section=section
        )
        
        result['post_veto_df'] = post_veto_df
        
        if veto_mode == 'both':
            result.update({
                'pre_veto_allocations': pre_veto_allocations,
                'post_veto_allocations': post_veto_allocations
            })
    
    return result
