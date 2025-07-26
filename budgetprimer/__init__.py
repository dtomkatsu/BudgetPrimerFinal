"""
BudgetPrimerFinal - A streamlined tool for processing and analyzing Hawaii State Budget data.

This package provides tools for parsing, analyzing, and visualizing budget data
from the Hawaii State Budget documents, with a focus on accuracy and performance.
"""

__version__ = "0.1.0"

# Import key components for easier access
from .models.budget_allocation import BudgetAllocation, FundType
from .parsers.budget_parser import parse_budget_file
from .pipeline import (
    process_budget_data, 
    transform_to_post_veto,
    process_budget_with_vetoes,
    load_veto_changes
)

# Set up logging
import logging
from pathlib import Path

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'budgetprimer.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
