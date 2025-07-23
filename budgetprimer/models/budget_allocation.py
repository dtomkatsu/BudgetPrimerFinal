"""
Budget allocation data model and fund type handling.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, List, Any
import re
from datetime import datetime


class BudgetSection(Enum):
    """Budget section types."""
    OPERATING = "Operating"
    CAPITAL_IMPROVEMENT = "Capital Improvement"
    UNSPECIFIED = "Unspecified"


class FundType(Enum):
    """Budget fund types based on Hawaii's classification."""
    # General Funds
    GENERAL = 'A'  # General Fund
    
    # Special Funds
    SPECIAL = 'B'  # Special Fund
    TRUST = 'T'    # Trust Fund
    SPECIAL_MANAGEMENT = 'S'  # Special Management Area Fund
    SPECIAL_OUTLAY = 'W'  # Special Outlay Fund
    
    # Federal Funds
    FEDERAL = 'F'  # Federal Funds
    
    # Other Funds
    BOND = 'D'     # General Obligation Bond Fund
    REVENUE_BOND = 'R'  # Revenue Bond Fund
    OTHER = 'X'    # Other Funds
    
    # Default/Unknown
    UNKNOWN = 'U'  # Unknown/Unspecified
    
    @classmethod
    def from_string(cls, value: str) -> FundType:
        """Convert a string representation to a FundType."""
        if not value:
            return cls.UNKNOWN
            
        # Handle single letter codes
        if len(value) == 1:
            for member in cls:
                if member.value == value.upper():
                    return member
        
        # Handle full names
        normalized = value.upper().replace(' ', '_')
        try:
            return cls[normalized]
        except KeyError:
            pass
            
        # Try to match partial names
        for member in cls:
            if member.name.startswith(normalized) or normalized in member.name:
                return member
                
        return cls.UNKNOWN
    
    @property
    def category(self) -> str:
        """Get the fund category (General, Special, Federal, Other)."""
        if self == FundType.GENERAL:
            return "General Fund"
        elif self in [FundType.FEDERAL]:
            return "Federal Funds"
        elif self in [FundType.SPECIAL, FundType.TRUST, 
                     FundType.SPECIAL_MANAGEMENT, FundType.SPECIAL_OUTLAY]:
            return "Special Funds"
        else:
            return "Other Funds"


@dataclass
class BudgetAllocation:
    """Represents a single budget allocation."""
    program_id: str
    program_name: str
    department_code: str
    department_name: str
    section: BudgetSection
    fund_type: FundType
    fiscal_year: int
    amount: float
    positions: Optional[int] = None
    ceiling: Optional[float] = None
    allocation_type: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BudgetAllocation:
        """Create a BudgetAllocation from a dictionary."""
        return cls(
            program_id=data.get('program_id', ''),
            program_name=data.get('program_name', ''),
            department_code=data.get('department_code', ''),
            department_name=data.get('department_name', ''),
            section=BudgetSection(data.get('section', BudgetSection.UNSPECIFIED)),
            fund_type=FundType.from_string(data.get('fund_type', 'U')),
            fiscal_year=int(data.get('fiscal_year', 0)),
            amount=float(data.get('amount', 0)),
            positions=data.get('positions'),
            ceiling=data.get('ceiling'),
            allocation_type=data.get('allocation_type'),
            category=data.get('category'),
            subcategory=data.get('subcategory'),
            notes=data.get('notes', ''),
            metadata=data.get('metadata', {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary."""
        return {
            'program_id': self.program_id,
            'program_name': self.program_name,
            'department_code': self.department_code,
            'department_name': self.department_name,
            'section': self.section.value,
            'fund_type': self.fund_type.value,
            'fiscal_year': self.fiscal_year,
            'amount': self.amount,
            'positions': self.positions,
            'ceiling': self.ceiling,
            'allocation_type': self.allocation_type,
            'category': self.category,
            'subcategory': self.subcategory,
            'notes': self.notes,
            'fund_category': self.fund_type.category,
            **self.metadata
        }
    
    @staticmethod
    def extract_fund_type(amount_str: str) -> FundType:
        """Extract fund type from an amount string.
        
        Args:
            amount_str: String containing amount and optional fund type letter
            
        Returns:
            FundType: The extracted fund type or UNKNOWN if not found
        """
        if not amount_str or not isinstance(amount_str, str):
            return FundType.UNKNOWN
            
        # Look for a single letter (A-Z) at the end of the string after numbers/commas
        match = re.search(r'[\d,]+(?:\(?P<fund_type>[A-Z])\)?$|(?P<fund_type2>[A-Z])$', amount_str.strip())
        if match:
            fund_char = match.group('fund_type') or match.group('fund_type2')
            if fund_char:
                return FundType.from_string(fund_char)
                
        return FundType.UNKNOWN
