"""
Budget parser module that exports the default parser for the package.
"""
from .fast_parser import FastBudgetParser

# Export the FastBudgetParser as the default parser
parse_budget_file = FastBudgetParser().parse

__all__ = ['parse_budget_file']
