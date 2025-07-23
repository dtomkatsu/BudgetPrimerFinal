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
        """Compile all regex patterns used for parsing."""
        return {
            'program': re.compile(
                r'^\s*\d+\.\s+([A-Z]{2,4}\d*)\s*[-–]\s*(.+)',
                re.IGNORECASE
            ),
            'amount_line': re.compile(
                r'([A-Z]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?\s*$',
                re.IGNORECASE
            ),
            'section': re.compile(
                r'^\s*(OPERATING|(INVESTMENT\s+CAPITAL)(?:\s+([A-Z]{3})\s+([\d,]+[A-Z])\s+([\d,]+[A-Z]))?)',
                re.IGNORECASE
            ),
            'category': re.compile(
                r'^\s*([A-Z])\.\s+(.+?)(?=\s*\([A-Z]+\)|$)',
                re.IGNORECASE
            ),
            'investment_capital': re.compile(
                r'INVESTMENT\s+CAPITAL\s+([A-Z0-9]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?.*$',
                re.IGNORECASE
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
        """Extract budget allocations from content using the original parser's logic."""
        allocations = []
        current_dept = None
        current_program = None
        current_section = None
        current_category = None
        
        # Flag to track if we've reached the end of the main budget document
        end_of_main_budget = False
        
        # Category mapping from original parser
        category_map = {
            'A': 'Economic Development',
            'B': 'Employment', 
            'C': 'Transportation',  # C. TRANSPORTATION FACILITIES
            'D': 'Environment',     # D. ENVIRONMENTAL PROTECTION
            'E': 'Health',          # E. HEALTH
            'F': 'Human Services',  # F. SOCIAL SERVICES
            'G': 'Education',       # G. FORMAL EDUCATION
            'H': 'Culture and Recreation',  # H. CULTURE AND RECREATION
            'I': 'Public Safety',   # I. PUBLIC SAFETY
            'J': 'Individual Rights',  # J. INDIVIDUAL RIGHTS
            'K': 'Government Operations'  # K. GOVERNMENT-WIDE SUPPORT
        }
        
        # Split content into lines for processing
        lines = content.split('\n')
        
        # Find the end of the main budget document (after KAUAI COUNTY)
        for i, line in enumerate(lines):
            if '47.  SUB501 - COUNTY OF KAUAI' in line:
                # Look for the next non-empty line after KAUAI COUNTY
                for j in range(i + 1, min(i + 10, len(lines))):
                    if 'INVESTMENT CAPITAL' in lines[j] and 'COK' in lines[j]:
                        end_line = j + 2  # Include the next line for the second amount
                        lines = lines[:end_line]
                        self.logger.info(f"Truncated document at line {end_line} after KAUAI COUNTY section")
                        break
                break
        
        for i, line in enumerate(lines):
            try:
                line = line.strip()
                if not line:
                    continue
                
                # Check for category header (e.g., "A.  ECONOMIC DEVELOPMENT")
                category_match = self._compiled_patterns['category'].match(line)
                if category_match:
                    category_code = category_match.group(1).upper()
                    current_category = category_map.get(category_code, 'Other')
                    continue
                    
                # Check for program header (e.g., "1. AGS221 - DEPARTMENT NAME")
                program_match = self._compiled_patterns['program'].match(line)
                if program_match:
                    current_dept = program_match.group(1).strip()  # First capturing group is dept code
                    current_program = program_match.group(2).strip()  # Second group is program name
                    current_section = None
                    continue
                
                # First check if this is an INVESTMENT CAPITAL line with amounts
                investment_match = self._compiled_patterns['investment_capital'].match(line)
                if investment_match:
                    current_section = 'INVESTMENT CAPITAL'
                    dept = investment_match.group(1)
                    fy26_amt = (investment_match.group(2) or '0').replace(',', '')
                    fy26_fund = investment_match.group(3) or 'C'  # Default to Capital fund
                    fy27_amt = (investment_match.group(4) or '0').replace(',', '')
                    fy27_fund = investment_match.group(5) or fy26_fund  # Default to same as FY26
                    
                    if fy26_amt and int(fy26_amt) > 0:
                        allocations.append(BudgetAllocation(
                            program_id=current_program or 'UNKNOWN',
                            program_name=current_program or 'Unknown Program',
                            department_code=dept,
                            department_name=dept,
                            section=BudgetSection.CAPITAL_IMPROVEMENT,
                            fund_type=FundType.from_string(fy26_fund),
                            fiscal_year=2026,
                            amount=float(int(fy26_amt)),
                            category=current_category or 'Uncategorized'
                        ))
                        
                    if fy27_amt and int(fy27_amt) > 0:
                        allocations.append(BudgetAllocation(
                            program_id=current_program or 'UNKNOWN',
                            program_name=current_program or 'Unknown Program',
                            department_code=dept,
                            department_name=dept,
                            section=BudgetSection.CAPITAL_IMPROVEMENT,
                            fund_type=FundType.from_string(fy27_fund),
                            fiscal_year=2027,
                            amount=float(int(fy27_amt)),
                            category=current_category or 'Uncategorized'
                        ))
                        
                    # Also check if there are additional amounts on the same line
                    remaining_line = line[investment_match.end():].strip()
                    if remaining_line:
                        # Look for additional amount patterns
                        amount_matches = self._compiled_patterns['amount_line'].findall(remaining_line)
                        for match in amount_matches:
                            dept_code = match[0]
                            fy26_amt = (match[1] or '0').replace(',', '')
                            fy26_fund = match[2] or 'C'
                            fy27_amt = (match[3] or '0').replace(',', '')
                            fy27_fund = match[4] or fy26_fund
                            
                            if fy26_amt and int(fy26_amt) > 0:
                                allocations.append(BudgetAllocation(
                                    program_id='CAPITAL_IMPROVEMENT',
                                    program_name='CAPITAL IMPROVEMENTS',
                                    department_code=dept_code,
                                    department_name=dept_code,
                                    section=BudgetSection.CAPITAL_IMPROVEMENT,
                                    fund_type=FundType.from_string(fy26_fund),
                                    fiscal_year=2026,
                                    amount=float(int(fy26_amt)),
                                    category=current_category or 'Uncategorized'
                                ))
                            
                            if fy27_amt and int(fy27_amt) > 0:
                                allocations.append(BudgetAllocation(
                                    program_id='CAPITAL_IMPROVEMENT',
                                    program_name='CAPITAL IMPROVEMENTS',
                                    department_code=dept_code,
                                    department_name=dept_code,
                                    section=BudgetSection.CAPITAL_IMPROVEMENT,
                                    fund_type=FundType.from_string(fy27_fund),
                                    fiscal_year=2027,
                                    amount=float(int(fy27_amt)),
                                    category=current_category or 'Uncategorized'
                                ))
                    continue  # Skip to next line after processing
                
                # Check for regular section headers (Operating, Capital Improvement)
                section_match = self._compiled_patterns['section'].match(line)
                if section_match:
                    current_section = section_match.group(1).strip()
                    current_fund = None
                    # Check if there are amounts on the same line as the section header
                    if section_match.group(3) and section_match.group(4) and section_match.group(5):
                        dept_code = section_match.group(3).strip()
                        fy26_amount = section_match.group(4).strip()
                        fy27_amount = section_match.group(5).strip()
                        
                        try:
                            fy26_num = int(re.sub(r'[^\d]', '', fy26_amount))
                            fy27_num = int(re.sub(r'[^\d]', '', fy27_amount))
                            fund_type = fy26_amount[-1] if fy26_amount and fy26_amount[-1].isalpha() else 'C'
                            
                            section_enum = BudgetSection.CAPITAL_IMPROVEMENT if 'INVESTMENT' in current_section.upper() else BudgetSection.OPERATING
                            
                            if fy26_num > 0:
                                allocations.append(BudgetAllocation(
                                    program_id=current_program or 'Unknown',
                                    program_name=current_program or 'Unknown Program',
                                    department_code=dept_code,
                                    department_name=dept_code,
                                    section=section_enum,
                                    fund_type=FundType.from_string(fund_type),
                                    fiscal_year=2026,
                                    amount=float(fy26_num),
                                    category=current_category or 'Uncategorized'
                                ))
                            
                            if fy27_num > 0:
                                allocations.append(BudgetAllocation(
                                    program_id=current_program or 'Unknown',
                                    program_name=current_program or 'Unknown Program',
                                    department_code=dept_code,
                                    department_name=dept_code,
                                    section=section_enum,
                                    fund_type=FundType.from_string(fund_type),
                                    fiscal_year=2027,
                                    amount=float(fy27_num),
                                    category=current_category or 'Uncategorized'
                                ))
                            
                        except (ValueError, AttributeError) as e:
                            self.logger.debug(f"Error parsing section header amounts '{fy26_amount}', '{fy27_amount}': {e}")
                    continue
                
                # Check for budget amounts (format: BED 3,893,040A 3,893,040A)
                amount_matches = self._compiled_patterns['amount_line'].findall(line)
                if amount_matches and current_dept and current_program and current_section:
                    for match in amount_matches:
                        if len(match) >= 5:  # New format with fund types
                            dept_code, fy26_amount, fy26_fund, fy27_amount, fy27_fund = match
                            fy26_fund = fy26_fund or ('C' if 'INVESTMENT' in str(current_section).upper() else 'A')
                            fy27_fund = fy27_fund or fy26_fund  # Default to FY26 fund
                        else:  # Fallback to old format
                            dept_code, fy26_amount, fy27_amount = match[:3]
                            fy26_fund = fy27_fund = 'C' if 'INVESTMENT' in str(current_section).upper() else 'A'
                        try:
                            # Extract numeric amounts
                            fy26_num = int(re.sub(r'[^\d]', '', fy26_amount)) if fy26_amount else 0
                            fy27_num = int(re.sub(r'[^\d]', '', fy27_amount)) if fy27_amount and fy27_amount.strip() else 0
                            
                            # Determine fund type based on section if not specified
                            fund_type = fy26_fund if fy26_fund else ('C' if 'INVESTMENT' in str(current_section).upper() else 'A')
                            
                            # Add FY2026 entry
                            if fy26_num > 0:
                                allocations.append(BudgetAllocation(
                                    program_id=current_dept,
                                    program_name=current_program,
                                    department_code=current_dept,
                                    department_name=current_dept,
                                    section=BudgetSection.CAPITAL_IMPROVEMENT if 'INVESTMENT' in current_section else BudgetSection.OPERATING,
                                    fund_type=FundType.from_string(fund_type),
                                    fiscal_year=2026,
                                    amount=float(fy26_num),
                                    category=current_category or 'Uncategorized'
                                ))
                            
                            # Add FY2027 entry
                            if fy27_num > 0:
                                allocations.append(BudgetAllocation(
                                    program_id=current_dept,
                                    program_name=current_program,
                                    department_code=current_dept,
                                    department_name=current_dept,
                                    section=BudgetSection.CAPITAL_IMPROVEMENT if 'INVESTMENT' in current_section else BudgetSection.OPERATING,
                                    fund_type=FundType.from_string(fy27_fund or fund_type),
                                    fiscal_year=2027,
                                    amount=float(fy27_num),
                                    category=current_category or 'Uncategorized'
                                ))
                        except (ValueError, AttributeError) as e:
                            self.logger.debug(f"Error parsing amounts '{fy26_amount}', '{fy27_amount}': {e}")    
            
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
