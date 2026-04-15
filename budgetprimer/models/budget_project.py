"""
Budget project data model for Section 14 capital improvement projects.

Represents an individual named CIP project (e.g., "EAST-WEST CENTER, OAHU")
extracted from Section 14 of the HB1800 bill. These are separate from
BudgetAllocation records, which capture program-level totals from Part II.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from .budget_allocation import FundType


@dataclass
class BudgetProject:
    """Represents a single capital improvement project from Section 14."""
    project_id: str              # "1", "2.1", "3.4"
    project_name: str            # "EAST-WEST CENTER, OAHU"
    scope: str                   # Multi-line description joined with spaces
    program_id: str              # Parent program code (BED101)
    program_name: str            # Parent program name
    department_code: str         # From TOTAL FUNDING line (e.g., "BED")
    category: str                # "Economic Development" (from Section 14 letter header)
    fiscal_year: int
    amount: float                # Already multiplied x1000 (raw bill value is thousands)
    fund_type: FundType
    line_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for JSON serialization."""
        return {
            'project_id': self.project_id,
            'project_name': self.project_name,
            'scope': self.scope,
            'program_id': self.program_id,
            'program_name': self.program_name,
            'department_code': self.department_code,
            'category': self.category,
            'fiscal_year': self.fiscal_year,
            'amount': self.amount,
            'fund_type': self.fund_type.value,
            'fund_category': self.fund_type.category,
            'line_number': self.line_number,
            **self.metadata,
        }
