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
                r'^\s*\d+\.\s+([A-Z0-9]+)\s*[-–]\s*(.+)',
                re.IGNORECASE
            ),
            # Updated to better handle fund types at the end of amounts (e.g., 700,000P)
            'amount_line': re.compile(
                r'([A-Z]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?\s*$',
                re.IGNORECASE
            ),
            'operating_line': re.compile(
                r'^OPERATING\s+([A-Z]+)\s+([\d,]+)([A-Z])(?:\s+([\d,]+)([A-Z]?))?\s*$',
                re.IGNORECASE
            ),
            'amount_line_with_fund': re.compile(
                r'([A-Z]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?\s*$',
                re.IGNORECASE
            ),
            'section': re.compile(
                r'^\s*(OPERATING|(INVESTMENT\s+CAPITAL)(?:\s+([A-Z]{3})\s+([\d,]+[A-Z])\s+([\d,]+[A-Z]))?)',
                re.IGNORECASE
            ),
            'section_with_amounts': re.compile(
                r'^\s*([A-Z]+)\s+([A-Z]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?\s*$',
                re.IGNORECASE
            ),
            # Pattern to match amount lines with fund type suffixes (e.g., 700,000P)
            'amount_with_fund_suffix': re.compile(
                r'^\s*([A-Z]+)\s+([\d,]+)([A-Z])\s+([\d,]+)([A-Z]?)\s*$',
                re.IGNORECASE
            ),
            'category': re.compile(
                r'^\s*([A-Z])\.\s+(.+?)(?=\s*\([A-Z]+\)|$)',
                re.IGNORECASE
            ),
            'investment_capital': re.compile(
                r'^\s*INVESTMENT\s+CAPITAL(?:\s+([A-Z0-9]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?)?',
                re.IGNORECASE
            ),
            'investment_amount': re.compile(
                r'^\s*([A-Z]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?\s*$',
                re.IGNORECASE
            ),
            'investment_line': re.compile(
                r'^\s*([A-Z]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?\s*$',
                re.IGNORECASE
            ),
            'indented_amount': re.compile(
                r'^[\s\u00A0]*([A-Z]+)[\s\u00A0]+([\d,]+)([A-Z]?)(?:[\s\u00A0]+([\d,]+)([A-Z]?))?[\s\u00A0]*$',
                re.IGNORECASE
            ),
            'indented_single_amount': re.compile(
                r'^[\s\u00A0]*([A-Z]+)[\s\u00A0]+([\d,]+)([A-Z])(?:[\s\u00A0]*[A-Z])?$',
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
            
            # Post-process to remove suspicious duplicates
            allocations = self._remove_suspicious_duplicates(allocations)
        
            self.logger.info(f"Successfully parsed {len(allocations)} budget allocations")
            return allocations
            
        except Exception as e:
            self.logger.error(f"Error parsing budget document: {str(e)}", exc_info=True)
            raise
    
    def _read_file(self, file_path: str) -> str:
        """Read the content of a file with appropriate encoding detection."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 if utf-8 fails
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Normalize line endings and clean up non-breaking spaces
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        # Replace non-breaking spaces with regular spaces
        content = content.replace('\u00A0', ' ')
        return content
    
    def _extract_allocations(self, content: str) -> List[BudgetAllocation]:
        """Extract budget allocations from content using the original parser's logic."""
        self.logger.debug("Starting _extract_allocations")
        allocations = []
        current_dept = None
        current_program = None
        current_program_name = None
        current_section = None
        current_category = None
        
        # Flag to track if we've reached the end of the main budget document
        end_of_main_budget = False
        
        # Category mapping from original parser
        category_map = {
            'A': 'Economic Development',
            'B': 'Employment',
            'C': 'Transportation',
            'D': 'Environment',
            'E': 'Health',
            'F': 'Human Services',
            'G': 'Education',
            'H': 'Culture and Recreation',
            'I': 'Public Safety',
            'J': 'Individual Rights',
            'K': 'Government Operations'
        }
        
        # Split content into lines and process each line
        lines = content.split('\n')
        for i, line in enumerate(lines):
            try:
                # Save original line for indentation check
                original_line = line
                # Strip whitespace for processing
                line = line.strip()
                if not line:
                    continue
                

                
                # Check for category header (e.g., "A.  ECONOMIC DEVELOPMENT")
                category_match = self._compiled_patterns['category'].match(line)
                if category_match:
                    category_code = category_match.group(1).upper()
                    current_category = category_map.get(category_code, 'Other')
                    continue
                    
                # Check for program header (e.g., "1. BED100 - STRATEGIC MARKETING AND SUPPORT")
                program_match = self._compiled_patterns['program'].match(line)
                if program_match:
                    # The program ID is the department code + number (e.g., BED100)
                    program_id = program_match.group(1).strip()
                    program_name = program_match.group(2).strip()
                    
                    # Store the program ID and name separately
                    current_program = program_id  # Just store the ID
                    current_program_name = program_name  # Store the name separately
                    current_dept = program_id[:3]  # First 3 letters are department code
                    current_section = None
                    
                    # Log program change for debugging
                    self.logger.debug(f"Program changed to: {current_program} - {current_program_name}")

                    continue
                
                # First check if this is an INVESTMENT CAPITAL line with amounts
                investment_match = self._compiled_patterns['investment_capital'].match(line)
                if investment_match:
                    current_section = 'INVESTMENT CAPITAL'
                    dept = investment_match.group(1)
                    fy26_amt = (investment_match.group(2) or '0').replace(',', '')
                    fy26_fund = investment_match.group(3) or 'C'  # Default to Capital fund
                    fy27_amt = (investment_match.group(4) or '0').replace(',', '')
                    fy27_fund = (investment_match.group(5) or fy26_fund).upper()  # Ensure uppercase
                    
                    # Use the current program name for capital improvements
                    program_name = current_program_name if 'current_program_name' in locals() and current_program_name else 'Unknown Program'
                    program_id = current_program if current_program else 'UNKNOWN'
                    
                    if fy26_amt and int(fy26_amt) > 0:
                        allocations.append(BudgetAllocation(
                            program_id=program_id,
                            program_name=program_name,
                            department_code=dept,
                            department_name=dept,
                            section=BudgetSection.CAPITAL_IMPROVEMENT,  # Explicitly set section
                            fund_type=FundType.from_string(fy26_fund),
                            fiscal_year=2026,
                            amount=float(int(fy26_amt)),
                            category=current_category or 'Uncategorized',
                            line_number=i + 1  # 1-based line number
                        ))
                        
                    if fy27_amt and int(fy27_amt) > 0:
                        allocations.append(BudgetAllocation(
                            program_id=program_id,
                            program_name=program_name,
                            department_code=dept,
                            department_name=dept,
                            section=BudgetSection.CAPITAL_IMPROVEMENT,  # Explicitly set section
                            fund_type=FundType.from_string(fy27_fund),
                            fiscal_year=2027,
                            amount=float(int(fy27_amt)),
                            category=current_category or 'Uncategorized',
                            line_number=i + 1  # 1-based line number
                        ))
                    
                    # Skip to next line after processing INVESTMENT CAPITAL
                    continue
                
                # Check for indented amounts in INVESTMENT CAPITAL section
                if (current_section == 'INVESTMENT CAPITAL' and current_program and 
                    (original_line.startswith((' ', '\t', '\u00A0')) or bool(re.search(r'\d', original_line)))):

                    
                    # Try the single-amount indented pattern first (for lines like 'TRN      5,000,000N           N')
                    single_amount_match = self._compiled_patterns['indented_single_amount'].match(line)
                    if single_amount_match and single_amount_match.group(1):
                        dept = single_amount_match.group(1)
                        fy26_amt = single_amount_match.group(2).replace(',', '') if single_amount_match.group(2) else '0'
                        fy26_fund = (single_amount_match.group(3) or 'A').upper()
                        
                        if int(fy26_amt) > 0:
                            try:
                                fund_type = FundType.from_string(fy26_fund)
                                allocations.append(BudgetAllocation(
                                    program_id=current_program,
                                    program_name=current_program_name if 'current_program_name' in locals() else current_program,
                                    department_code=dept,
                                    department_name=dept,
                                    section=BudgetSection.CAPITAL_IMPROVEMENT,  # Explicitly set section
                                    fund_type=fund_type,
                                    fiscal_year=2026,
                                    amount=float(int(fy26_amt)),
                                    category=current_category or 'Uncategorized',
                                    line_number=i + 1,
                                    notes=f'Investment Capital - Fund Type: {fy26_fund}'
                                ))
                                self.logger.debug(f"Added investment capital: {current_program} - {fy26_amt}{fy26_fund}")
                            except Exception as e:
                                self.logger.warning(f"Error creating allocation for {current_program} {fy26_amt}{fy26_fund}: {e}")
                        continue  # Skip to next line after processing
                    
                    # Try the general indented amount pattern (for lines with two amounts)
                    indented_match = self._compiled_patterns['indented_amount'].match(line)
                    if indented_match and indented_match.group(1):
                        dept = indented_match.group(1)
                        fy26_amt = indented_match.group(2).replace(',', '') if indented_match.group(2) else '0'
                        fy26_fund = (indented_match.group(3) or 'A').upper()
                        fy27_amt = (indented_match.group(4) or '0').replace(',', '') if indented_match.group(4) else '0'
                        fy27_fund = (indented_match.group(5) or fy26_fund).upper()
                        
                        if int(fy26_amt) > 0:
                            try:
                                fund_type = FundType.from_string(fy26_fund)
                                allocations.append(BudgetAllocation(
                                    program_id=current_program,
                                    program_name=current_program_name if 'current_program_name' in locals() else current_program,
                                    department_code=dept,
                                    department_name=dept,
                                    section=BudgetSection.CAPITAL_IMPROVEMENT,  # Explicitly set section
                                    fund_type=fund_type,
                                    fiscal_year=2026,
                                    amount=float(int(fy26_amt)),
                                    category=current_category or 'Uncategorized',
                                    line_number=i + 1,
                                    notes=f'Investment Capital - Fund Type: {fy26_fund}'
                                ))
                                self.logger.debug(f"Added investment capital: {current_program} - {fy26_amt}{fy26_fund}")
                            except Exception as e:
                                self.logger.warning(f"Error creating allocation for {current_program} {fy26_amt}{fy26_fund}: {e}")
                        
                        if int(fy27_amt) > 0:
                            try:
                                fund_type = FundType.from_string(fy27_fund)
                                allocations.append(BudgetAllocation(
                                    program_id=current_program,
                                    program_name=current_program_name if 'current_program_name' in locals() else current_program,
                                    department_code=dept,
                                    department_name=dept,
                                    section=BudgetSection.CAPITAL_IMPROVEMENT,  # Explicitly set section
                                    fund_type=fund_type,
                                    fiscal_year=2027,
                                    amount=float(int(fy27_amt)),
                                    category=current_category or 'Uncategorized',
                                    line_number=i + 1,
                                    notes=f'Investment Capital - Fund Type: {fy27_fund}'
                                ))
                                self.logger.debug(f"Added investment capital: {current_program} - {fy27_amt}{fy27_fund}")
                            except Exception as e:
                                self.logger.warning(f"Error creating allocation for {current_program} {fy27_amt}{fy27_fund}: {e}")
                        continue  # Skip to next line after processing
                    
                    # Handle investment line pattern (can have one or two amounts)
                    line_match = self._compiled_patterns['investment_line'].match(line)
                    if line_match and line_match.group(1):
                        dept = line_match.group(1)
                        
                        # Process first amount (FY26)
                        if line_match.group(2):  # If first amount exists
                            fy26_amt = line_match.group(2).replace(',', '')
                            fy26_fund = (line_match.group(3) or 'A').upper()
                            
                            if int(fy26_amt) > 0:
                                try:
                                    fund_type = FundType.from_string(fy26_fund)
                                    allocations.append(BudgetAllocation(
                                        program_id=current_program,
                                        program_name=current_program_name if 'current_program_name' in locals() else current_program,
                                        department_code=dept,
                                        department_name=dept,
                                        section=BudgetSection.CAPITAL_IMPROVEMENT,
                                        fund_type=fund_type,
                                        fiscal_year=2026,
                                        amount=float(int(fy26_amt)),
                                        category=current_category or 'Uncategorized',
                                        line_number=i + 1,
                                        notes=f'Investment Capital - Fund Type: {fy26_fund} - Column 1'
                                    ))
                                    self.logger.debug(f"Added FY26 investment: {current_program} - {fy26_amt}{fy26_fund}")
                                except Exception as e:
                                    self.logger.warning(f"Error creating FY26 allocation for {current_program} {fy26_amt}{fy26_fund}: {e}")
                        
                        # Process second amount (FY27) if it exists
                        if line_match.group(4):
                            fy27_amt = line_match.group(4).replace(',', '')
                            fy27_fund = (line_match.group(5) or fy26_fund if line_match.group(3) else 'A').upper()
                            
                            if int(fy27_amt) > 0:
                                try:
                                    fund_type = FundType.from_string(fy27_fund)
                                    allocations.append(BudgetAllocation(
                                        program_id=current_program,
                                        program_name=current_program_name if 'current_program_name' in locals() else current_program,
                                        department_code=dept,
                                        department_name=dept,
                                        section=BudgetSection.CAPITAL_IMPROVEMENT,
                                        fund_type=fund_type,
                                        fiscal_year=2027,
                                        amount=float(int(fy27_amt)),
                                        category=current_category or 'Uncategorized',
                                        line_number=i + 1,
                                        notes=f'Investment Capital - Fund Type: {fy27_fund} - Column 2'
                                    ))
                                    self.logger.debug(f"Added FY27 investment: {current_program} - {fy27_amt}{fy27_fund}")
                                except Exception as e:
                                    self.logger.warning(f"Error creating FY27 allocation for {current_program} {fy27_amt}{fy27_fund}: {e}")
                        
                        continue  # Skip to next line after processing
                    
                    # Skip to next line after processing
                    continue
                
                # Check for amount lines with fund type suffixes (e.g., 700,000P 700,000P)
                amount_suffix_match = self._compiled_patterns['amount_with_fund_suffix'].match(line)
                if amount_suffix_match:
                    dept_code = amount_suffix_match.group(1)
                    fy26_amount = amount_suffix_match.group(2)
                    fy26_fund = amount_suffix_match.group(3).upper()
                    fy27_amount = amount_suffix_match.group(4)
                    fy27_fund = (amount_suffix_match.group(5) or fy26_fund).upper()
                    
                    try:
                        fy26_num = int(re.sub(r'[^\d]', '', fy26_amount))
                        fy27_num = int(re.sub(r'[^\d]', '', fy27_amount))
                        
                        section_enum = BudgetSection.CAPITAL_IMPROVEMENT if current_section and 'INVESTMENT' in current_section.upper() else BudgetSection.OPERATING
                        
                        if fy26_num > 0:
                            program_id = current_program if current_program else 'Unknown'
                            program_name = current_program_name if 'current_program_name' in locals() else 'Unknown Program'
                            
                            allocations.append(BudgetAllocation(
                                program_id=program_id,
                                program_name=program_name,
                                department_code=dept_code,
                                department_name=dept_code,
                                section=BudgetSection.OPERATING if section_enum == BudgetSection.OPERATING else BudgetSection.CAPITAL_IMPROVEMENT,
                                fund_type=FundType.from_string(fy26_fund),
                                fiscal_year=2026,
                                amount=float(fy26_num),
                                category=current_category or 'Uncategorized',
                                line_number=i + 1  # 1-based line number
                            ))
                        
                        if fy27_num > 0 and fy27_fund:
                            # Only add FY27 allocation if there's a fund type specified
                            allocations.append(BudgetAllocation(
                                program_id=program_id,
                                program_name=program_name,
                                department_code=dept_code,
                                department_name=dept_code,
                                section=BudgetSection.OPERATING if section_enum == BudgetSection.OPERATING else BudgetSection.CAPITAL_IMPROVEMENT,
                                fund_type=FundType.from_string(fy27_fund),
                                fiscal_year=2027,
                                amount=float(fy27_num),
                                category=current_category or 'Uncategorized',
                                line_number=i + 1  # 1-based line number
                            ))
                        
                        continue  # Skip to next line after processing
                        
                    except (ValueError, AttributeError) as e:
                        self.logger.debug(f"Error parsing amount with fund suffix '{line}': {e}")
                
                # Check for OPERATING line FIRST (before section header checks)
                if 'OPERATING' in original_line:
                    current_section = 'OPERATING'
                    

                    
                    # Check for OPERATING with amounts on same line (PDF format)
                    # Format: OPERATING [spaces] TRN [spaces] [AMOUNT]A [spaces] A
                    pdf_pattern = r'^\s*OPERATING\s+([A-Z]+)\s+([\d,]+)([A-Z])\s+([A-Z])\s*$'
                    operating_match = re.search(pdf_pattern, original_line)
                    
                    if operating_match:
                        dept = operating_match.group(1)
                        fy26_amt = (operating_match.group(2) or '0').replace(',', '')
                        fy26_fund = (operating_match.group(3) or 'A').upper()
                        
                        # Handle blank FY27 appropriations (indicated by a letter after spaces)
                        fy27_amt = '0'  # Default to 0 for FY27 if blank
                        fy27_fund = fy26_fund  # Default to same fund type as FY26
                        
                        # For PDF format, group 4 contains the FY27 fund type (blank appropriation)
                        if len(operating_match.groups()) >= 4 and operating_match.group(4):
                            fy27_fund = operating_match.group(4).upper()
                        

                        
                        # Create allocation for this operating amount
                        allocation = BudgetAllocation(
                            program_id=current_program,
                            program_name=current_program_name,
                            department_code=dept,
                            department_name=dept,
                            section=BudgetSection.OPERATING,
                            fund_type=FundType.from_string(fy26_fund),
                            fiscal_year=2026,
                            amount=float(int(fy26_amt)),
                            category=current_category or 'Uncategorized',
                            notes='',
                            line_number=i+1
                        )
                        allocations.append(allocation)
                        

                        
                        # Skip the rest of the processing since we found a match
                        continue
                

                
                # Check for section headers (Operating, Capital Improvement)
                section_match = None
                
                # First try the section with amounts pattern
                section_match = self._compiled_patterns['section_with_amounts'].match(line)

                if section_match:
                    current_section = 'OPERATING'  # Default section type
                    current_fund = None
                    # Extract the amounts and funds
                    dept_code = section_match.group(2)
                    fy26_amount = section_match.group(3)
                    fy26_fund = (section_match.group(4) or 'A').upper()
                    fy27_amount = section_match.group(5) or fy26_amount
                    fy27_fund = (section_match.group(6) or fy26_fund).upper()
                    
                    try:
                        fy26_num = int(re.sub(r'[^\d]', '', fy26_amount))
                        fy27_num = int(re.sub(r'[^\d]', '', fy27_amount))
                        
                        section_enum = BudgetSection.CAPITAL_IMPROVEMENT if 'INVESTMENT' in current_section.upper() else BudgetSection.OPERATING
                        
                        if fy26_num > 0:
                            # Use the stored program ID and name
                            program_id = current_program if current_program else 'Unknown'
                            program_name = current_program_name if 'current_program_name' in locals() else 'Unknown Program'
                            
                            allocations.append(BudgetAllocation(
                                program_id=program_id,
                                program_name=program_name,
                                department_code=dept_code,
                                department_name=dept_code,
                                section=BudgetSection.OPERATING if section_enum == BudgetSection.OPERATING else BudgetSection.CAPITAL_IMPROVEMENT,
                                fund_type=FundType.from_string(fy26_fund),
                                fiscal_year=2026,
                                amount=float(fy26_num),
                                category=current_category or 'Uncategorized',
                                line_number=i + 1  # 1-based line number
                            ))
                        
                        if fy27_num > 0:
                            # Use the stored program ID and name
                            program_id = current_program if current_program else 'Unknown'
                            program_name = current_program_name if 'current_program_name' in locals() else 'Unknown Program'
                            
                            allocations.append(BudgetAllocation(
                                program_id=program_id,
                                program_name=program_name,
                                department_code=dept_code,
                                department_name=dept_code,
                                section=BudgetSection.OPERATING if section_enum == BudgetSection.OPERATING else BudgetSection.CAPITAL_IMPROVEMENT,
                                fund_type=FundType.from_string(fy27_fund),
                                fiscal_year=2027,
                                amount=float(fy27_num),
                                category=current_category or 'Uncategorized',
                                line_number=i + 1  # 1-based line number
                            ))
                        
                        # Skip to next line since we've processed this line
                        continue
                        
                    except (ValueError, AttributeError) as e:
                        self.logger.debug(f"Error parsing section header amounts '{fy26_amount}', '{fy27_amount}': {e}")
                
                # Try the regular section pattern if no match yet
                if not section_match:
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
                            fund_type = fy26_amount[-1] if fy26_amount and fy26_amount[-1].isalpha() else 'A'  # Default to 'A' for general funds
                            
                            section_enum = BudgetSection.CAPITAL_IMPROVEMENT if 'INVESTMENT' in current_section.upper() else BudgetSection.OPERATING
                            
                            if fy26_num > 0:
                                allocations.append(BudgetAllocation(
                                    program_id=current_program or 'Unknown',
                                    program_name=current_program or 'Unknown Program',
                                    department_code=dept_code,
                                    department_name=dept_code,
                                    section=BudgetSection.OPERATING,
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
                                    section=BudgetSection.OPERATING,
                                    fund_type=FundType.from_string(fund_type),
                                    fiscal_year=2027,
                                    amount=float(fy27_num),
                                    category=current_category or 'Uncategorized'
                                ))
                            
                        except (ValueError, AttributeError) as e:
                            self.logger.debug(f"Error parsing section header amounts '{fy26_amount}', '{fy27_amount}': {e}")
                    
                    # Check for amounts on the same line as the section header (different format)
                    amount_match = re.search(r'([A-Z]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?\s*$', line)
                    if amount_match:
                        dept_code = amount_match.group(1)
                        fy26_amount = (amount_match.group(2) or '0').replace(',', '')
                        fy26_fund = (amount_match.group(3) or ('C' if 'INVESTMENT' in current_section.upper() else 'A')).upper()
                        fy27_amount = (amount_match.group(4) or fy26_amount).replace(',', '')
                        fy27_fund = (amount_match.group(5) or fy26_fund or 'A').upper()
                        
                        section_enum = BudgetSection.CAPITAL_IMPROVEMENT if 'INVESTMENT' in current_section.upper() else BudgetSection.OPERATING
                        
                        if int(fy26_amount) > 0:
                            allocations.append(BudgetAllocation(
                                program_id=current_program or 'Unknown',
                                program_name=current_program or 'Unknown Program',
                                department_code=dept_code,
                                department_name=dept_code,
                                section=BudgetSection.OPERATING if section_enum == BudgetSection.OPERATING else BudgetSection.CAPITAL_IMPROVEMENT,
                                fund_type=FundType.from_string(fy26_fund),
                                fiscal_year=2026,
                                amount=float(fy26_amount),
                                category=current_category or 'Uncategorized'
                            ))
                        
                        if int(fy27_amount) > 0:
                            allocations.append(BudgetAllocation(
                                program_id=current_program or 'Unknown',
                                program_name=current_program or 'Unknown Program',
                                department_code=dept_code,
                                department_name=dept_code,
                                section=BudgetSection.OPERATING if section_enum == BudgetSection.OPERATING else BudgetSection.CAPITAL_IMPROVEMENT,
                                fund_type=FundType.from_string(fy27_fund),
                                fiscal_year=2027,
                                amount=float(fy27_amount),
                                category=current_category or 'Uncategorized'
                            ))
                    
                    continue
                
                # Handle amount lines (with or without OPERATING prefix)
                amount_matches = []
                
                # Check for OPERATING with amounts on the same line
                if line.startswith('OPERATING'):
                    operating_match = self._compiled_patterns['operating_line'].match(original_line.strip())
                    if operating_match:
                        # This is an OPERATING line with amounts
                        dept = operating_match.group(1)
                        fy26_amt = (operating_match.group(2) or '0').replace(',', '')
                        fy26_fund = (operating_match.group(3) or 'A').upper()
                        fy27_amt = (operating_match.group(4) or '0').replace(',', '') if operating_match.group(4) else '0'
                        fy27_fund = (operating_match.group(5) or fy26_fund).upper()
                        
                        # Add to matches as a tuple that matches our expected format
                        amount_matches.append((dept, fy26_amt, fy26_fund, fy27_amt, fy27_fund))
                # Check if this is an indented line with just amounts
                elif line.strip() and line.startswith(' ' * 30):  # Check for significant indentation
                    # This is an indented continuation line
                    amount_line_match = re.match(r'^\s+([A-Z]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?\s*$', line)
                    if amount_line_match:
                        amount_matches.append(amount_line_match.groups())
                else:
                    # Try to match amount with fund type (e.g., "TRN      5,000,000N           N" or "TRN       700,000S         S")
                    amount_match = re.search(r'([A-Z]+)?\s*([\d,]+)([A-Z])(?:\s+[A-Z])?\s*$', line.strip())
                    if not amount_match:
                        # Try alternative format with fund type at the end after spaces
                        amount_match = re.search(r'([A-Z]+)?\s*([\d,]+)(?:\s+)([A-Z])\s*$', line.strip())
                    if amount_match:
                        amount_matches.append(amount_match.groups())
                
                # If we have matches and we're in a valid context
                if amount_matches and current_dept and current_program and current_section:
                    for match in amount_matches:
                        if len(match) >= 3:  # At least dept, fy26_amount, fy26_fund
                            dept_code = match[0]
                            fy26_amount = (match[1] or '0').replace(',', '')
                            fy26_fund = (match[2] if len(match) > 2 and match[2] else 'A').upper()  # Default to 'A' and ensure uppercase
                            fy27_amount = (match[3] if len(match) > 3 and match[3] else fy26_amount).replace(',', '')
                            fy27_fund = (match[4] if len(match) > 4 and match[4] else fy26_fund).upper() or fy26_fund.upper()
                        try:
                            # Extract numeric amounts
                            fy26_num = int(re.sub(r'[^\d]', '', fy26_amount)) if fy26_amount else 0
                            fy27_num = int(re.sub(r'[^\d]', '', fy27_amount)) if fy27_amount and fy27_amount.strip() else 0
                            
                            # Determine fund type based on section if not specified
                            fund_type = fy26_fund if fy26_fund else ('C' if 'INVESTMENT' in str(current_section).upper() else 'A')
                            
                            # Add FY2026 entry
                            if fy26_num > 0:
                                # Log the allocation for debugging
                                self.logger.debug(f"Adding allocation: {current_program} - {fy26_amount}{fy26_fund} to {dept_code}")
                                allocations.append(BudgetAllocation(
                                    program_id=current_program,  # Use current_program instead of current_dept
                                    program_name=current_program_name,  # Use current_program_name
                                    department_code=dept_code,  # Use the dept_code from the amount line
                                    department_name=dept_code,
                                    section=BudgetSection.CAPITAL_IMPROVEMENT if 'INVESTMENT' in current_section else BudgetSection.OPERATING,
                                    fund_type=FundType.from_string(fund_type),
                                    fiscal_year=2026,
                                    amount=float(fy26_num),
                                    category=current_category or 'Uncategorized'
                                ))
                            
                            # Add FY2027 entry
                            if fy27_num > 0:
                                allocations.append(BudgetAllocation(
                                    program_id=current_program,  # Use current_program instead of current_dept
                                    program_name=current_program_name,  # Use current_program_name
                                    department_code=dept_code,  # Use the dept_code from the amount line
                                    department_name=dept_code,
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
    
    def _remove_suspicious_duplicates(self, allocations: List[BudgetAllocation]) -> List[BudgetAllocation]:
        """
        Remove suspicious duplicate allocations that have the same program_id, fiscal_year, 
        and amount but different fund types. This typically indicates parsing errors.
        """
        if not allocations:
            return allocations
        
        # Group allocations by program_id, fiscal_year, section
        groups = {}
        for alloc in allocations:
            key = (alloc.program_id, alloc.fiscal_year, alloc.section)
            if key not in groups:
                groups[key] = []
            groups[key].append(alloc)
        
        cleaned_allocations = []
        duplicates_removed = 0
        
        for key, group in groups.items():
            program_id, fiscal_year, section = key
            
            # Check for suspicious duplicates (same amount, different fund types)
            amount_groups = {}
            for alloc in group:
                amount = alloc.amount
                if amount not in amount_groups:
                    amount_groups[amount] = []
                amount_groups[amount].append(alloc)
            
            # Process each amount group
            for amount, amount_group in amount_groups.items():
                if len(amount_group) > 1 and amount > 100_000_000:  # Multiple entries with same large amount
                    # This is suspicious - likely a parsing error
                    # Keep only the first one (usually the most reliable fund type)
                    fund_types = [alloc.fund_type.value for alloc in amount_group]
                    self.logger.warning(
                        f"Removing {len(amount_group)-1} suspicious duplicates for {program_id} FY{fiscal_year} "
                        f"${amount:,.0f} - fund types: {fund_types}"
                    )
                    cleaned_allocations.append(amount_group[0])  # Keep only the first one
                    duplicates_removed += len(amount_group) - 1
                else:
                    # No duplicates or amount is small enough to be legitimate
                    cleaned_allocations.extend(amount_group)
        
        if duplicates_removed > 0:
            self.logger.info(f"Removed {duplicates_removed} suspicious duplicate allocations")
        
        return cleaned_allocations
    
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
