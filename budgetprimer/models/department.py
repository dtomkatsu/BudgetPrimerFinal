"""
Department data model for budget allocations.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class Department:
    """Represents a government department or agency."""
    code: str
    name: str
    description: str = ""
    parent_code: Optional[str] = None
    is_active: bool = True
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'parent_code': self.parent_code,
            'is_active': self.is_active,
            **self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Department':
        """Create from dictionary."""
        return cls(
            code=data['code'],
            name=data['name'],
            description=data.get('description', ''),
            parent_code=data.get('parent_code'),
            is_active=data.get('is_active', True),
            metadata={k: v for k, v in data.items() 
                     if k not in ['code', 'name', 'description', 'parent_code', 'is_active']}
        )
