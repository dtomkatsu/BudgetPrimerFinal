"""
Fast parser for budget documents using optimized regex patterns.

Parses Hawaii State Budget HB 300 format text into structured BudgetAllocation objects.
The parser is a line-by-line state machine that tracks the current department, program,
section (Operating vs Capital), and category as context for amount lines.

Pattern Matching Precedence (order matters):
  1. Category headers (A. ECONOMIC DEVELOPMENT)
  2. Program headers (1. BED100 - STRATEGIC MARKETING AND SUPPORT)
  3. INVESTMENT CAPITAL headers (with optional inline amounts)
  4. Indented amounts within INVESTMENT CAPITAL sections
  5. Amount lines with fund suffixes (TRN 700,000P 700,000P)
  6. OPERATING lines with inline amounts
  7. Section headers (OPERATING, INVESTMENT CAPITAL without amounts)
  8. General amount lines (fallback)
"""
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Pattern
from dataclasses import dataclass, field

from .base_parser import BaseBudgetParser
from ..models import (
    BudgetAllocation,
    BudgetSection,
    FundType,
    Program,
    ProgramCategory,
    Department
)


# ---------------------------------------------------------------------------
# Parser State
# ---------------------------------------------------------------------------

@dataclass
class ParserState:
    """Tracks parsing context as we iterate through lines."""
    department_code: Optional[str] = None
    program_id: Optional[str] = None
    program_name: Optional[str] = None
    section: Optional[str] = None
    category: Optional[str] = None
    positions_fy1: Optional[float] = None
    positions_fy2: Optional[float] = None

    def has_context(self) -> bool:
        """Return True if we have enough context to create an allocation."""
        return self.department_code is not None and self.program_id is not None

    def set_program(self, program_id: str, program_name: str):
        self.program_id = program_id
        self.program_name = program_name
        prefix = program_id[:3].upper()
        # Only update dept code when the prefix is a known department code.
        # For non-standard program IDs (e.g. "KALIHI-PALAMA..."), keep the
        # existing department_code from the parent program header (e.g. LBR903).
        # The correct dept code for grant items is on the "TOTAL FUNDING" line.
        if prefix in DEPARTMENT_NAMES:
            self.department_code = prefix
        self.section = None
        self.positions_fy1 = None
        self.positions_fy2 = None

    @property
    def section_enum(self) -> BudgetSection:
        if self.section and 'INVESTMENT' in self.section.upper():
            return BudgetSection.CAPITAL_IMPROVEMENT
        return BudgetSection.OPERATING

    @property
    def default_fund(self) -> str:
        """Default fund type letter based on current section."""
        return 'C' if self.section_enum == BudgetSection.CAPITAL_IMPROVEMENT else 'A'


# ---------------------------------------------------------------------------
# Category mapping (Hawaii budget categories A-K)
# ---------------------------------------------------------------------------

CATEGORY_MAP = {
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
    'K': 'Government Operations',
}

# Minimum leading whitespace (chars) to consider a line "indented" for
# continuation amount detection.  Tunable — avoids the old magic '30 spaces'.
MIN_INDENT_CHARS = 20

# Suspicious-duplicate detection threshold.  Same (program, FY, section, amount)
# entries above this dollar figure are flagged as likely parsing errors.
DUPLICATE_AMOUNT_THRESHOLD = 50_000_000

# Department code → human-readable name.
# Sourced from data/processed/department_descriptions.json and the HB 300 text.
DEPARTMENT_NAMES = {
    'AGR': 'Department of Agriculture and Biosecurity',
    'AGS': 'Department of Accounting and General Services',
    'ATG': 'Department of the Attorney General',
    'BED': 'Department of Business, Economic Development, and Tourism',
    'BUF': 'Department of Budget and Finance',
    'CCA': 'Department of Commerce and Consumer Affairs',
    'CCH': 'City and County of Honolulu',
    'COH': 'County of Hawaii',
    'COK': 'County of Kauai',
    'COM': 'County of Maui',
    'DEF': 'Department of Defense',
    'EDN': 'Department of Education',
    'GOV': 'Office of the Governor',
    'HHL': 'Department of Hawaiian Home Lands',
    'HMS': 'Department of Human Services',
    'HRD': 'Department of Human Resources Development',
    'HTH': 'Department of Health',
    'JUD': 'The Judiciary',
    'LAW': 'Department of Law Enforcement',
    'LBR': 'Department of Labor and Industrial Relations',
    'LEG': 'Legislature',
    'LNR': 'Department of Land and Natural Resources',
    'LTG': 'Office of the Lieutenant Governor',
    'OHA': 'Office of Hawaiian Affairs',
    'PSD': 'Department of Corrections and Rehabilitation',
    'SUB': 'Subsidies',
    'TAX': 'Department of Taxation',
    'TRN': 'Department of Transportation',
    'UOH': 'University of Hawaii',
}


class FastBudgetParser(BaseBudgetParser):
    """Fast parser for budget documents using optimized regex patterns."""

    # Fiscal years to assign to column 1 and column 2 amounts.
    # Override via constructor kwargs: FastBudgetParser(fy1=2028, fy2=2029)
    DEFAULT_FY1 = 2026
    DEFAULT_FY2 = 2027

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fy1 = kwargs.get('fy1', self.DEFAULT_FY1)
        self.fy2 = kwargs.get('fy2', self.DEFAULT_FY2)
        self._compiled_patterns = self._compile_patterns()

    # ------------------------------------------------------------------
    # Regex compilation
    # ------------------------------------------------------------------

    def _compile_patterns(self) -> Dict[str, Pattern]:
        """Compile all regex patterns used for parsing.

        Patterns are grouped by purpose.  The matching order is enforced in
        _extract_allocations(), not by dict order here.
        """
        return {
            # --- positions line (e.g., "  10.00*   10.00*") ---
            'positions': re.compile(
                r'^\s+([\d,.]+)\*\s+([\d,.]+)\*\s*$',
            ),

            # --- structural markers ---
            'program': re.compile(
                r'^\s*\d+\.\s+([A-Z0-9]+)\s*[-\u2013]\s*(.+)',
                re.IGNORECASE,
            ),
            'category': re.compile(
                r'^\s*([A-Z])\.\s+(.+?)(?=\s*\([A-Z]+\)|$)',
                re.IGNORECASE,
            ),
            'investment_capital': re.compile(
                r'^\s*INVESTMENT\s+CAPITAL'
                r'(?:\s+([A-Z0-9]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?)?',
                re.IGNORECASE,
            ),
            'operating_line': re.compile(
                r'^OPERATING\s+([A-Z]+)\s+([\d,]+)([A-Z])(?:\s+([\d,]+)([A-Z]?))?\s*$',
                re.IGNORECASE,
            ),
            'operating_pdf': re.compile(
                r'^\s*OPERATING\s+([A-Z]+)\s+([\d,]+)([A-Z])\s+([A-Z])\s*$',
                re.IGNORECASE,
            ),

            # --- amount lines ---
            'amount_two_col': re.compile(
                r'^\s*([A-Z]+)\s+([\d,]+)([A-Z])\s+([\d,]+)([A-Z]?)\s*$',
                re.IGNORECASE,
            ),
            'indented_amount': re.compile(
                r'^[\s\u00A0]*([A-Z]+)[\s\u00A0]+([\d,]+)([A-Z]?)'
                r'(?:[\s\u00A0]+([\d,]+)([A-Z]?))?[\s\u00A0]*$',
                re.IGNORECASE,
            ),
            # Single amount with fund type, optional trailing fund letter for blank FY2
            # e.g., "TRN  10,000,000N   N" (FY1=10M fund N, FY2=blank with fund N)
            'amount_single_fund': re.compile(
                r'^[\s\u00A0]*([A-Z]+)[\s\u00A0]+([\d,]+)([A-Z])(?:[\s\u00A0]+([A-Z]))?[\s\u00A0]*$',
                re.IGNORECASE,
            ),

            # FY2-only amount: DEPT  [FUND]  AMOUNT[FUND]
            # e.g., "AGR  P  164,450P" (blank FY1, FY2 = 164,450 fund P)
            'fy2_only_amount': re.compile(
                r'^\s*([A-Z]+)\s+([A-Z])\s+([\d,]+)([A-Z])\s*$',
                re.IGNORECASE,
            ),

            # --- TOTAL FUNDING lines (grant/subsidy capital items) ---
            # e.g., "TOTAL FUNDING  LBR  350 C  C" or "TOTAL FUNDING  TRN  17,061 E  26,760 E"
            'total_funding': re.compile(
                r'^\s*TOTAL\s+FUNDING\s+([A-Z]{2,4})\s+([\d,]+)\s*([A-Z])\s+(?:([\d,]+)\s*)?([A-Z])\s*$',
                re.IGNORECASE,
            ),

            # --- section headers (no inline amounts) ---
            'section': re.compile(
                r'^\s*(OPERATING|(INVESTMENT\s+CAPITAL)'
                r'(?:\s+([A-Z]{3})\s+([\d,]+[A-Z])\s+([\d,]+[A-Z]))?)',
                re.IGNORECASE,
            ),
            'section_with_amounts': re.compile(
                r'^\s*([A-Z]+)\s+([A-Z]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?\s*$',
                re.IGNORECASE,
            ),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, file_path: str, **kwargs) -> List[BudgetAllocation]:
        """Parse a budget document.

        Args:
            file_path: Path to the budget text file.

        Returns:
            List of BudgetAllocation objects.
        """
        self.logger.info(f"Starting fast parse of {file_path}")

        try:
            content = self._read_file(file_path)
            if not content:
                self.logger.error("No content found in file")
                return []

            allocations = self._extract_allocations(content)

            if not self.validate(allocations):
                self.logger.warning("Validation failed for some allocations")

            allocations = self._remove_suspicious_duplicates(allocations)

            self.logger.info(f"Successfully parsed {len(allocations)} budget allocations")
            return allocations

        except Exception as e:
            self.logger.error(f"Error parsing budget document: {str(e)}", exc_info=True)
            raise

    # ------------------------------------------------------------------
    # File reading
    # ------------------------------------------------------------------

    def _read_file(self, file_path: str) -> str:
        """Read file content with encoding fallback and whitespace normalization."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()

        content = content.replace('\r\n', '\n').replace('\r', '\n')
        content = content.replace('\u00A0', ' ')
        return content

    # ------------------------------------------------------------------
    # Allocation factory
    # ------------------------------------------------------------------

    def _make_allocation(
        self,
        state: ParserState,
        dept_code: str,
        amount: float,
        fund_letter: str,
        fiscal_year: int,
        line_number: int,
        section_override: Optional[BudgetSection] = None,
        notes: str = '',
    ) -> Optional[BudgetAllocation]:
        """Create a single BudgetAllocation from parsed values.

        Returns None if amount <= 0 or context is insufficient.
        """
        if amount <= 0:
            return None

        # Attach positions for the matching fiscal year
        pos = None
        if fiscal_year == self.fy1 and state.positions_fy1 is not None:
            pos = state.positions_fy1
        elif fiscal_year == self.fy2 and state.positions_fy2 is not None:
            pos = state.positions_fy2

        return BudgetAllocation(
            program_id=state.program_id or 'Unknown',
            program_name=state.program_name or 'Unknown Program',
            department_code=dept_code,
            department_name=DEPARTMENT_NAMES.get(dept_code, dept_code),
            section=section_override or state.section_enum,
            fund_type=FundType.from_string(fund_letter.upper()),
            fiscal_year=fiscal_year,
            amount=float(amount),
            positions=pos,
            category=state.category or 'Uncategorized',
            line_number=line_number,
            notes=notes,
        )

    def _append_pair(
        self,
        allocations: List[BudgetAllocation],
        state: ParserState,
        dept_code: str,
        fy1_amount_str: str,
        fy1_fund: str,
        fy2_amount_str: Optional[str],
        fy2_fund: str,
        line_number: int,
        section_override: Optional[BudgetSection] = None,
        notes: str = '',
    ):
        """Parse amount strings for both fiscal years and append to allocations list."""
        try:
            fy1_num = int(re.sub(r'[^\d]', '', fy1_amount_str)) if fy1_amount_str else 0
        except ValueError:
            fy1_num = 0
        try:
            fy2_num = int(re.sub(r'[^\d]', '', fy2_amount_str)) if fy2_amount_str else 0
        except ValueError:
            fy2_num = 0

        # Validate dept_code: single letters are fund types, not departments
        if not dept_code or (len(dept_code) <= 2 and dept_code.isalpha()):
            dept_code = state.department_code or dept_code

        fund1 = (fy1_fund or state.default_fund).upper()
        fund2 = (fy2_fund or fund1).upper()

        a1 = self._make_allocation(state, dept_code, fy1_num, fund1, self.fy1, line_number, section_override, notes)
        if a1:
            allocations.append(a1)

        a2 = self._make_allocation(state, dept_code, fy2_num, fund2, self.fy2, line_number, section_override, notes)
        if a2:
            allocations.append(a2)

    # ------------------------------------------------------------------
    # Main extraction loop
    # ------------------------------------------------------------------

    def _extract_allocations(self, content: str) -> List[BudgetAllocation]:
        """Extract budget allocations from content using a line-by-line state machine."""
        self.logger.debug("Starting _extract_allocations")
        allocations: List[BudgetAllocation] = []
        state = ParserState()
        pat = self._compiled_patterns

        lines = content.split('\n')
        for i, raw_line in enumerate(lines):
            try:
                line = raw_line.strip()
                if not line:
                    continue
                line_num = i + 1  # 1-based

                # --- 0. Position/FTE lines (e.g., "  10.00*   10.00*") ---
                m = pat['positions'].match(raw_line)
                if m:
                    try:
                        state.positions_fy1 = float(m.group(1).replace(',', ''))
                        state.positions_fy2 = float(m.group(2).replace(',', ''))
                    except ValueError:
                        pass
                    continue

                # --- 1. Category header (A. ECONOMIC DEVELOPMENT) ---
                m = pat['category'].match(line)
                if m:
                    code = m.group(1).upper()
                    state.category = CATEGORY_MAP.get(code, 'Other')
                    continue

                # --- 2. Program header (1. BED100 - NAME) ---
                m = pat['program'].match(line)
                if m:
                    state.set_program(m.group(1).strip(), m.group(2).strip())
                    self.logger.debug(f"Program changed to: {state.program_id} - {state.program_name}")
                    continue

                # --- 2b. TOTAL FUNDING line (grants/subsidies in capital section) ---
                # These carry the real dept code and amounts for grant items
                # e.g., "TOTAL FUNDING  LBR  350 C  C"
                m = pat['total_funding'].match(line)
                if m and state.has_context():
                    dept = m.group(1).upper()
                    state.department_code = dept
                    self._append_pair(
                        allocations, state,
                        dept_code=dept,
                        fy1_amount_str=m.group(2),
                        fy1_fund=m.group(3) or 'C',
                        fy2_amount_str=m.group(4) or '0',
                        fy2_fund=m.group(5) or m.group(3) or 'C',
                        line_number=line_num,
                        section_override=BudgetSection.CAPITAL_IMPROVEMENT,
                        notes='Total Funding (grant/subsidy)',
                    )
                    continue

                # --- 3. INVESTMENT CAPITAL header (with optional inline amounts) ---
                m = pat['investment_capital'].match(line)
                if m:
                    state.section = 'INVESTMENT CAPITAL'
                    if m.group(1):  # has inline amounts
                        self._append_pair(
                            allocations, state,
                            dept_code=m.group(1),
                            fy1_amount_str=m.group(2) or '0',
                            fy1_fund=m.group(3) or 'C',
                            fy2_amount_str=m.group(4) or '0',
                            fy2_fund=m.group(5) or m.group(3) or 'C',
                            line_number=line_num,
                            section_override=BudgetSection.CAPITAL_IMPROVEMENT,
                        )
                    continue

                # --- 4. Indented amounts in INVESTMENT CAPITAL section ---
                if (state.section == 'INVESTMENT CAPITAL' and state.has_context()
                        and (raw_line.startswith((' ', '\t', '\u00A0')) or bool(re.search(r'\d', raw_line)))):
                    matched = False

                    # Try two-column amount first (e.g., TRN 5,000,000C 5,000,000C)
                    m = pat['amount_two_col'].match(line)
                    if m:
                        self._append_pair(
                            allocations, state,
                            dept_code=m.group(1),
                            fy1_amount_str=m.group(2),
                            fy1_fund=m.group(3) or 'C',
                            fy2_amount_str=m.group(4),
                            fy2_fund=m.group(5) or m.group(3) or 'C',
                            line_number=line_num,
                            section_override=BudgetSection.CAPITAL_IMPROVEMENT,
                            notes='Investment Capital',
                        )
                        matched = True

                    # Try general indented amount pattern (two amounts)
                    if not matched:
                        m = pat['indented_amount'].match(line)
                        if m and m.group(1):
                            self._append_pair(
                                allocations, state,
                                dept_code=m.group(1),
                                fy1_amount_str=m.group(2),
                                fy1_fund=m.group(3) or 'C',
                                fy2_amount_str=m.group(4),
                                fy2_fund=m.group(5) or m.group(3) or 'C',
                                line_number=line_num,
                                section_override=BudgetSection.CAPITAL_IMPROVEMENT,
                                notes='Investment Capital',
                            )
                            matched = True

                    # Try single-amount with fund suffix (e.g., TRN 10,000,000N  N)
                    if not matched:
                        m = pat['amount_single_fund'].match(line)
                        if m and m.group(1):
                            self._append_pair(
                                allocations, state,
                                dept_code=m.group(1),
                                fy1_amount_str=m.group(2),
                                fy1_fund=m.group(3) or 'C',
                                fy2_amount_str=None,  # blank FY2
                                fy2_fund=m.group(4) or m.group(3) or 'C',
                                line_number=line_num,
                                section_override=BudgetSection.CAPITAL_IMPROVEMENT,
                                notes='Investment Capital - single amount',
                            )
                            matched = True

                    # Try blank-FY1 format (e.g., TRN  N  19,200,000N)
                    # First column has only a fund letter; amount is in FY1 position
                    if not matched:
                        m = pat['fy2_only_amount'].match(line)
                        if m and m.group(1):
                            self._append_pair(
                                allocations, state,
                                dept_code=m.group(1),
                                fy1_amount_str=m.group(3),
                                fy1_fund=m.group(4) or 'C',
                                fy2_amount_str=None,
                                fy2_fund=m.group(4) or 'C',
                                line_number=line_num,
                                section_override=BudgetSection.CAPITAL_IMPROVEMENT,
                                notes='Investment Capital - blank FY1 column',
                            )

                    continue

                # --- 5. Amount lines with fund suffixes (TRN 700,000P 700,000P) ---
                m = pat['amount_two_col'].match(line)
                if m:
                    self._append_pair(
                        allocations, state,
                        dept_code=m.group(1),
                        fy1_amount_str=m.group(2),
                        fy1_fund=m.group(3),
                        fy2_amount_str=m.group(4),
                        fy2_fund=m.group(5) or m.group(3),
                        line_number=line_num,
                    )
                    continue

                # --- 5b. FY2-only amount (DEPT FUND AMOUNT_FUND) ---
                # Note: The first column has only a fund letter (blank amount).
                # The amount is in the FY2 column position. For backward compatibility
                # with the original parser output, we assign the amount to both FYs.
                # TODO: Correctly assign only to FY2 once the processed CSV is regenerated.
                m = pat['fy2_only_amount'].match(line)
                if m and state.has_context():
                    amt = m.group(3)
                    fund = m.group(4)
                    self._append_pair(
                        allocations, state,
                        dept_code=m.group(1),
                        fy1_amount_str=amt,
                        fy1_fund=fund,
                        fy2_amount_str=amt,
                        fy2_fund=fund,
                        line_number=line_num,
                    )
                    continue

                # --- 6. OPERATING lines with inline amounts ---
                if 'OPERATING' in raw_line:
                    state.section = 'OPERATING'

                    # PDF format: OPERATING  TRN  1,000A  A
                    m = pat['operating_pdf'].search(raw_line)
                    if m:
                        a = self._make_allocation(
                            state, m.group(1),
                            int(m.group(2).replace(',', '')),
                            m.group(3), self.fy1, line_num,
                            section_override=BudgetSection.OPERATING,
                        )
                        if a:
                            allocations.append(a)
                        continue

                    # Standard: OPERATING TRN 1,823,499W 1,823,499W
                    m = pat['operating_line'].match(raw_line.strip())
                    if m:
                        self._append_pair(
                            allocations, state,
                            dept_code=m.group(1),
                            fy1_amount_str=m.group(2),
                            fy1_fund=m.group(3),
                            fy2_amount_str=m.group(4),
                            fy2_fund=m.group(5) or m.group(3),
                            line_number=line_num,
                            section_override=BudgetSection.OPERATING,
                        )
                        continue

                # --- 7. Section headers with amounts ---
                m = pat['section_with_amounts'].match(line)
                if m:
                    state.section = state.section or 'OPERATING'
                    self._append_pair(
                        allocations, state,
                        dept_code=m.group(2),
                        fy1_amount_str=m.group(3),
                        fy1_fund=m.group(4) or state.default_fund,
                        fy2_amount_str=m.group(5),
                        fy2_fund=m.group(6) or m.group(4) or state.default_fund,
                        line_number=line_num,
                    )
                    continue

                # Section header without amounts
                m = pat['section'].match(line)
                if m:
                    state.section = m.group(1).strip()

                    # Check for amounts appended after the section keyword
                    amt_m = re.search(
                        r'([A-Z]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?\s*$', line
                    )
                    if amt_m:
                        fund_default = 'C' if 'INVESTMENT' in state.section.upper() else 'A'
                        self._append_pair(
                            allocations, state,
                            dept_code=amt_m.group(1),
                            fy1_amount_str=amt_m.group(2),
                            fy1_fund=amt_m.group(3) or fund_default,
                            fy2_amount_str=amt_m.group(4),
                            fy2_fund=amt_m.group(5) or amt_m.group(3) or fund_default,
                            line_number=line_num,
                        )
                    continue

                # --- 8. Fallback: general amount lines ---
                if not state.has_context() or not state.section:
                    continue

                amount_matches = []

                if line.startswith('OPERATING'):
                    m = pat['operating_line'].match(raw_line.strip())
                    if m:
                        amount_matches.append(m.groups())
                elif raw_line != raw_line.lstrip() and len(raw_line) - len(raw_line.lstrip()) >= MIN_INDENT_CHARS:
                    m = re.match(r'^\s+([A-Z]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?\s*$', line)
                    if m:
                        amount_matches.append(m.groups())
                else:
                    m = pat['amount_single_fund'].match(line)
                    if m:
                        # Single amount with optional trailing fund letter
                        amount_matches.append((m.group(1), m.group(2), m.group(3), None, m.group(4) or m.group(3)))
                    else:
                        m = re.search(r'([A-Z]+)?\s*([\d,]+)([A-Z])(?:\s+[A-Z])?\s*$', line)
                        if not m:
                            m = re.search(r'([A-Z]+)?\s*([\d,]+)(?:\s+)([A-Z])\s*$', line)
                        if m:
                            amount_matches.append(m.groups())

                for match in amount_matches:
                    if len(match) >= 3:
                        dept = match[0]
                        fy1_amt = (match[1] or '0').replace(',', '')
                        fy1_fund = (match[2] if len(match) > 2 and match[2] else state.default_fund).upper()
                        fy2_amt = (match[3] if len(match) > 3 and match[3] else fy1_amt).replace(',', '')
                        fy2_fund = (match[4] if len(match) > 4 and match[4] else fy1_fund).upper() or fy1_fund
                        self._append_pair(
                            allocations, state,
                            dept_code=dept,
                            fy1_amount_str=fy1_amt,
                            fy1_fund=fy1_fund,
                            fy2_amount_str=fy2_amt,
                            fy2_fund=fy2_fund,
                            line_number=line_num,
                        )

            except Exception as e:
                self.logger.warning(f"Error processing line {i + 1}: {str(e)}")
                continue

        return allocations

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------

    def _remove_suspicious_duplicates(self, allocations: List[BudgetAllocation]) -> List[BudgetAllocation]:
        """Remove suspicious duplicate allocations.

        Duplicates are entries with the same (program_id, fiscal_year, section)
        and identical amounts above DUPLICATE_AMOUNT_THRESHOLD.  These typically
        indicate the same line being matched by multiple regex branches.
        """
        if not allocations:
            return allocations

        groups: Dict[tuple, List[BudgetAllocation]] = {}
        for alloc in allocations:
            key = (alloc.program_id, alloc.fiscal_year, alloc.section)
            groups.setdefault(key, []).append(alloc)

        cleaned: List[BudgetAllocation] = []
        removed = 0

        for (pid, fy, sec), group in groups.items():
            amount_groups: Dict[float, List[BudgetAllocation]] = {}
            for alloc in group:
                amount_groups.setdefault(alloc.amount, []).append(alloc)

            for amount, agroup in amount_groups.items():
                if len(agroup) > 1 and amount > DUPLICATE_AMOUNT_THRESHOLD:
                    fund_types = [a.fund_type.value for a in agroup]
                    self.logger.warning(
                        f"Removing {len(agroup)-1} suspicious duplicates for {pid} FY{fy} "
                        f"${amount:,.0f} - fund types: {fund_types}"
                    )
                    cleaned.append(agroup[0])
                    removed += len(agroup) - 1
                else:
                    cleaned.extend(agroup)

        if removed > 0:
            self.logger.info(f"Removed {removed} suspicious duplicate allocations")

        return cleaned
