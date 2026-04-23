"""Historical biennial budget metadata and helpers.

This package collects everything specific to the multi-year (10+ year)
historical comparison feature: the year→bill→act lookup table, future
inflation deflator helpers, etc.

Phase 1 covers the six biennial budget acts from 2015 through 2025.
"""

from .year_bill_table import (
    HISTORICAL_BIENNIAL_BILLS,
    iter_biennial_bills,
    get_bill_for_session,
    fiscal_years_covered,
)

__all__ = [
    "HISTORICAL_BIENNIAL_BILLS",
    "iter_biennial_bills",
    "get_bill_for_session",
    "fiscal_years_covered",
]
