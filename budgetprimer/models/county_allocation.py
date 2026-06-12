"""
County budget allocation data model.

The four counties (Honolulu, Maui, Hawaiʻi, Kauaʻi) publish their own budget
ordinances with fund structures that don't map onto the state's HB300 letter
codes (FundType) — e.g. "Highway Fund", "Sewer Fund", "Bus Transportation
Fund". This module provides a parallel, simpler model: the raw county fund
name is always preserved, and a normalized CountyFundCategory is derived for
cross-county comparison. BudgetSection is shared with the state model.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from .budget_allocation import BudgetSection


class CountyFundCategory(Enum):
    """Normalized fund grouping for county budgets."""
    GENERAL = "General Fund"
    SPECIAL = "Special / Enterprise Funds"
    FEDERAL = "Federal Funds"
    BOND = "Bond / Debt Funds"
    TRUST_OTHER = "Trust & Other Funds"


# Keyword table for normalize_fund(). Checked in order; first match wins, so
# more specific keywords (federal grants, bonds) come before the broad
# special/enterprise bucket.
_FUND_KEYWORDS = [
    (CountyFundCategory.FEDERAL, (
        'federal', 'grant', 'hud', 'fta', 'cdbg', 'community development',
        'section 8', 'rental assistance',
    )),
    (CountyFundCategory.BOND, (
        'bond', 'debt service', 'improvement district', 'capital projects',
    )),
    (CountyFundCategory.GENERAL, (
        'general fund', 'general',
    )),
    (CountyFundCategory.SPECIAL, (
        'highway', 'sewer', 'wastewater', 'solid waste', 'bus', 'transit',
        'transportation', 'water', 'liquor', 'golf', 'special events',
        'hanauma', 'zoo', 'housing', 'affordable', 'bikeway', 'parks',
        'recreation', 'refuse', 'special',
    )),
]


def normalize_fund(fund_name: str) -> CountyFundCategory:
    """Map a raw county fund name to a normalized category."""
    if not fund_name:
        return CountyFundCategory.TRUST_OTHER
    name = fund_name.lower()
    if 'trust' in name:
        return CountyFundCategory.TRUST_OTHER
    for category, keywords in _FUND_KEYWORDS:
        if any(kw in name for kw in keywords):
            return category
    return CountyFundCategory.TRUST_OTHER


COUNTY_NAMES = {
    'honolulu': 'City & County of Honolulu',
    'maui': 'County of Maui',
    'hawaii': 'County of Hawaiʻi',
    'kauai': 'County of Kauaʻi',
}


@dataclass
class CountyAllocation:
    """A single line of a county budget (department × fund × program)."""
    county: str                     # 'honolulu' | 'maui' | 'hawaii' | 'kauai'
    department_code: str            # slug, e.g. 'hpd'
    department_name: str
    section: BudgetSection          # Operating / Capital Improvement
    fund_name: str                  # raw fund name, always preserved
    fund_category: CountyFundCategory
    fiscal_year: int
    amount: float
    program_name: Optional[str] = None   # division/program where available
    positions: Optional[float] = None
    source: str = ""                # dataset id or ordinance number

    def to_dict(self) -> Dict[str, Any]:
        return {
            'county': self.county,
            'department_code': self.department_code,
            'department_name': self.department_name,
            'section': self.section.value,
            'fund_name': self.fund_name,
            'fund_category': self.fund_category.value,
            'fiscal_year': self.fiscal_year,
            'amount': self.amount,
            'program_name': self.program_name,
            'positions': self.positions,
            'source': self.source,
        }
