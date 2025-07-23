"""
Program data model for budget allocations.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class ProgramCategory(Enum):
    """Budget program categories based on lettered sections."""
    ECONOMIC_DEVELOPMENT = 'A'
    EMPLOYMENT = 'B'
    TRANSPORTATION = 'C'
    ENVIRONMENT = 'D'
    HEALTH = 'E'
    HUMAN_SERVICES = 'F'
    EDUCATION = 'G'
    CULTURE_RECREATION = 'H'
    PUBLIC_SAFETY = 'I'
    INDIVIDUAL_RIGHTS = 'J'
    GOVERNMENT_OPERATIONS = 'K'
    UNSPECIFIED = 'Z'


@dataclass
class Program:
    """Represents a budget program or project."""
    program_id: str
    name: str
    description: str = ""
    department_code: Optional[str] = None
    category: ProgramCategory = ProgramCategory.UNSPECIFIED
    subcategory: Optional[str] = None
    is_capital: bool = False
    is_active: bool = True
    metadata: Dict = field(default_factory=dict)
    
    @property
    def category_name(self) -> str:
        """Get the full category name."""
        return self.category.name.replace('_', ' ').title()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'program_id': self.program_id,
            'name': self.name,
            'description': self.description,
            'department_code': self.department_code,
            'category': self.category.value,
            'category_name': self.category_name,
            'subcategory': self.subcategory,
            'is_capital': self.is_capital,
            'is_active': self.is_active,
            **self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Program':
        """Create from dictionary."""
        return cls(
            program_id=data['program_id'],
            name=data['name'],
            description=data.get('description', ''),
            department_code=data.get('department_code'),
            category=ProgramCategory(data.get('category', 'Z')),
            subcategory=data.get('subcategory'),
            is_capital=data.get('is_capital', False),
            is_active=data.get('is_active', True),
            metadata={k: v for k, v in data.items() 
                     if k not in ['program_id', 'name', 'description', 'department_code', 
                                'category', 'subcategory', 'is_capital', 'is_active']}
        )
