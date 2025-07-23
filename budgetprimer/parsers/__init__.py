"""
Budget document parsers for different formats.

This module contains parsers for various budget document formats.
"""

from .base_parser import BaseBudgetParser
from .fast_parser import FastBudgetParser

# Export the most commonly used parser as the default
parse_budget_file = FastBudgetParser().parse

__all__ = [
    'BaseBudgetParser',
    'FastBudgetParser',
    'parse_budget_file'
]
