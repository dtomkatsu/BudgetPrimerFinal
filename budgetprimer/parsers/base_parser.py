"""
Base parser class for budget documents.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import logging

from ..models import BudgetAllocation, Department, Program


class BaseBudgetParser(ABC):
    """Abstract base class for budget document parsers."""
    
    def __init__(self, **kwargs):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.kwargs = kwargs
    
    @abstractmethod
    def parse(self, file_path: Union[str, Path], **kwargs) -> List[BudgetAllocation]:
        """Parse a budget document and return a list of budget allocations.
        
        Args:
            file_path: Path to the budget document
            **kwargs: Additional parser-specific arguments
            
        Returns:
            List of BudgetAllocation objects
        """
        pass
    
    def validate(self, allocations: List[BudgetAllocation]) -> bool:
        """Validate the parsed budget allocations.
        
        Args:
            allocations: List of parsed budget allocations
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        if not allocations:
            self.logger.warning("No budget allocations found")
            return False
            
        # Check for required fields
        required_fields = ['program_id', 'program_name', 'department_code', 'fiscal_year', 'amount']
        for i, alloc in enumerate(allocations):
            for field in required_fields:
                if not getattr(alloc, field, None):
                    self.logger.warning(f"Missing required field '{field}' in allocation {i}")
                    return False
        
        return True
    
    def extract_departments(self, allocations: List[BudgetAllocation]) -> List[Department]:
        """Extract unique departments from budget allocations.
        
        Args:
            allocations: List of budget allocations
            
        Returns:
            List of Department objects
        """
        dept_map = {}
        for alloc in allocations:
            if alloc.department_code and alloc.department_code not in dept_map:
                dept_map[alloc.department_code] = Department(
                    code=alloc.department_code,
                    name=alloc.department_name or alloc.department_code
                )
        return list(dept_map.values())
    
    def extract_programs(self, allocations: List[BudgetAllocation]) -> List[Program]:
        """Extract unique programs from budget allocations.
        
        Args:
            allocations: List of budget allocations
            
        Returns:
            List of Program objects
        """
        program_map = {}
        for alloc in allocations:
            if alloc.program_id and alloc.program_id not in program_map:
                program_map[alloc.program_id] = Program(
                    program_id=alloc.program_id,
                    name=alloc.program_name,
                    department_code=alloc.department_code,
                    is_capital=alloc.section == 'Capital Improvement'
                )
        return list(program_map.values())
    
    def to_dataframe(self, allocations: List[BudgetAllocation]):
        """Convert budget allocations to a pandas DataFrame.
        
        Args:
            allocations: List of budget allocations
            
        Returns:
            pandas.DataFrame: DataFrame containing the budget allocations
        """
        import pandas as pd
        return pd.DataFrame([alloc.to_dict() for alloc in allocations])
