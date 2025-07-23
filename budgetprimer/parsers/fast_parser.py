"""
Fast parser for budget documents using optimized regex patterns.
"""
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Match
from dataclasses import dataclass
import re
import logging

from .base_parser import BaseBudgetParser
from ..models import (
    BudgetAllocation, 
    BudgetSection, 
    FundType, 
    Program,
    ProgramCategory,
    Department
)


class FastBudgetParser(BaseBudgetParser):
    """Fast parser for budget documents using optimized regex patterns."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, Pattern]:
        """Compile all regex patterns for reuse."""
        return {
            'program': re.compile(
                r'^\s*(?P<program_id>\d+)\.\s*'
                r'(?P<dept_code>[A-Z]{2,4}\d*)[\s-]+'
                r'(?P<program_name>.+?)(?=\s*\d|$)',
                re.IGNORECASE | re.MULTILINE
            ),
            'amount_line': re.compile(
                r'([A-Z]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?\s*$',
                re.IGNORECASE | re.MULTILINE
            ),
            'section': re.compile(
                r'^\s*(?P<section>OPERATING|(INVESTMENT\s+CAPITAL)(?:\s+([A-Z]{3})\s+([\d,]+[A-Z])\s+([\d,]+[A-Z]))?)',
                re.IGNORECASE | re.MULTILINE
            ),
            'category': re.compile(
                r'^\s*([A-Z])\.\s+(.+?)(?=\s*\([A-Z]+\)|$)',
                re.IGNORECASE | re.MULTILINE
            ),
            'investment_capital': re.compile(
                r'INVESTMENT CAPITAL\s+([A-Z0-9]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?.*$',
                re.IGNORECASE | re.MULTILINE
            )
        }
    
    def parse(self, file_path: str, **kwargs) -> List[BudgetAllocation]:
        """Parse a budget document using optimized regex patterns.
        
        Args:
            file_path: Path to the budget document
            **kwargs: Additional parser-specific arguments
            
        Returns:
            List of BudgetAllocation objects
        """
        self.logger.info(f"Starting fast parse of {file_path}")
        
        try:
            # Read the file content
            content = self._read_file(file_path)
            if not content:
                self.logger.error("No content found in file")
                return []
            
            # Extract allocations
            allocations = self._extract_allocations(content)
            
            # Validate the results
            if not self.validate(allocations):
                self.logger.warning("Validation failed for some allocations")
            
            self.logger.info(f"Successfully parsed {len(allocations)} budget allocations")
            return allocations
            
        except Exception as e:
            self.logger.error(f"Error parsing budget document: {str(e)}", exc_info=True)
            raise
    
    def _read_file(self, file_path: str) -> str:
        """Read the content of a file with appropriate encoding detection."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 if utf-8 fails
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    def _extract_allocations(self, content: str) -> List[BudgetAllocation]:
        """Extract budget allocations from content."""
        allocations = []
        current_section = BudgetSection.UNSPECIFIED
        current_category = None
        current_program = None
        
        # Category mapping from original parser
        category_map = {
            'A': 'Economic Development',
            'B': 'Employment', 
            'C': 'Transportation',
            'D': 'Environment',
            'E': 'Health',
            'F': 'Human Services',
            'G': 'Formal Education',
            'H': 'Culture and Recreation',
            'I': 'Public Safety',
            'J': 'Individual Rights',
            'K': 'Government Operations'
        }
        
        # Split content into lines for processing
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            try:
                line = line.strip()
                if not line:
                    continue
                
                # Check for category headers
                category_match = self._compiled_patterns['category'].match(line)
                if category_match:
                    category_code = category_match.group(1).upper()
                    current_category = category_map.get(category_code, 'Other')
                    continue
                
                # Check for program headers
                program_match = self._compiled_patterns['program'].match(line)
                if program_match:
                    current_program = {
                        'program_id': program_match.group('program_id').strip(),
                        'program_name': program_match.group('program_name').strip(),
                        'dept_code': program_match.group('dept_code').strip()
                    }
                    continue
                
                # Check for INVESTMENT CAPITAL with amounts on same line
                investment_match = self._compiled_patterns['investment_capital'].match(line)
                if investment_match:
                    current_section = BudgetSection.CAPITAL_IMPROVEMENT
                    dept = investment_match.group(1)
                    
                    # Process FY26 amount if present
                    if investment_match.group(2):
                        amount = int(investment_match.group(2).replace(',', ''))
                        fund_type = investment_match.group(3) or 'C'  # Default to Capital fund
                        if amount > 0:
                            allocations.append(BudgetAllocation(
                                program_id='CAPITAL_IMPROVEMENT',
                                program_name='CAPITAL IMPROVEMENTS',
                                department_code=dept,
                                department_name=dept,  # Using dept code as name for now
                                section=current_section,
                                fund_type=FundType.from_string(fund_type),
                                fiscal_year=2026,
                                amount=float(amount),
                                category=current_category or 'Uncategorized'
                            ))
                    
                    # Process FY27 amount if present
                    if investment_match.group(4):
                        amount = int(investment_match.group(4).replace(',', ''))
                        fund_type = investment_match.group(5) or (investment_match.group(3) or 'C')
                        if amount > 0:
                            allocations.append(BudgetAllocation(
                                program=Program(
                                    program_id='CAPITAL_IMPROVEMENT',
                                    name='CAPITAL IMPROVEMENTS',
                                    department_code=dept,
                                    description='Capital Improvement Project',
                                    category=ProgramCategory.GOVERNMENT_OPERATIONS
                                ),
                                section=current_section,
                                category=current_category or 'Uncategorized',
                                fund_type=FundType(fund_type),
                                fiscal_year='2027',
                                amount=amount,
                                source_line=line
                            ))
                    continue
                
                # Check for section headers
                section_match = self._compiled_patterns['section'].match(line)
                if section_match:
                    section_name = section_match.group(1).upper()
                    current_section = (
                        BudgetSection.CAPITAL_IMPROVEMENT 
                        if 'CAPITAL' in section_name 
                        else BudgetSection.OPERATING
                    )
                    
                    # Handle amounts on the same line as section header
                    if section_match.group(3):  # Has department code
                        dept = section_match.group(3)
                        # Process FY26 amount if present
                        if section_match.group(4):
                            amount = int(section_match.group(4)[:-1].replace(',', ''))
                            fund_type = section_match.group(4)[-1] or 'C'
                            if amount > 0:
                                allocations.append(BudgetAllocation(
                                    program=Program(
                                        id='CAPITAL_IMPROVEMENT',
                                        name='CAPITAL IMPROVEMENTS',
                                        department=dept
                                    ),
                                    section=current_section,
                                    category=current_category or 'Uncategorized',
                                    fund_type=FundType(fund_type),
                                    fiscal_year='2026',
                                    amount=amount,
                                    source_line=line
                                ))
                        
                        # Process FY27 amount if present
                        if section_match.group(5):
                            amount = int(section_match.group(5)[:-1].replace(',', ''))
                            fund_type = section_match.group(5)[-1] or fund_type
                            if amount > 0:
                                allocations.append(BudgetAllocation(
                                    program=Program(
                                        id='CAPITAL_IMPROVEMENT',
                                        name='CAPITAL IMPROVEMENTS',
                                        department=dept
                                    ),
                                    section=current_section,
                                    category=current_category or 'Uncategorized',
                                    fund_type=FundType(fund_type),
                                    fiscal_year='2027',
                                    amount=amount,
                                    source_line=line
                                ))
                    continue
                
                # Check for amount lines (only if we have a current program and section)
                if current_program and current_section != BudgetSection.UNSPECIFIED:
                    # Find all amount matches in the line
                    for match in self._compiled_patterns['amount_line'].finditer(line):
                        # Process FY26 amount if present
                        if match.group(2):
                            amount = int(match.group(2).replace(',', ''))
                            fund_type = match.group(3) or 'A'  # Default to General Fund
                            if amount > 0:
                                allocations.append(BudgetAllocation(
                                    program_id=current_program['program_id'],
                                    program_name=current_program['program_name'],
                                    department_code=current_program['dept_code'],
                                    department_name=current_program['dept_code'],  # Using dept code as name for now
                                    section=current_section,
                                    fund_type=FundType.from_string(fund_type),
                                    fiscal_year=2026,
                                    amount=float(amount),
                                    category=current_category or 'Uncategorized'
                                ))
                        
                        # Process FY27 amount if present
                        if match.group(4):
                            amount = int(match.group(4).replace(',', ''))
                            fund_type = match.group(5) or (match.group(3) or 'A')
                            if amount > 0:
                                allocations.append(BudgetAllocation(
                                    program=Program(
                                        program_id=current_program['program_id'],
                                        name=current_program['program_name'],
                                        department_code=current_program['dept_code'],
                                        description=current_program.get('program_name', ''),
                                        category=ProgramCategory.GOVERNMENT_OPERATIONS
                                    ),
                                    section=current_section,
                                    category=current_category or 'Uncategorized',
                                    fund_type=FundType(fund_type),
                                    fiscal_year='2027',
                                    amount=amount,
                                    source_line=line
                                ))
            
            except Exception as e:
                self.logger.warning(f"Error processing line {i + 1}: {str(e)}")
                continue
        
        return allocations
    
    def _create_allocation(
            self,
            match: re.Match,
            program: Dict[str, str],
            section: BudgetSection,
            category: Optional[str],
            fiscal_year: str,
            is_fy26: bool
        ) -> List[BudgetAllocation]:
        """
        Create a BudgetAllocation from a regex match.
        This is kept for backward compatibility but most logic is now in _extract_allocations.
        """
        return []
