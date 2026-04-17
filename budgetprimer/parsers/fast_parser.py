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
from typing import Any, Dict, List, Optional, Pattern
from dataclasses import dataclass, field

from .base_parser import BaseBudgetParser
from ..models import (
    BudgetAllocation,
    BudgetProject,
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
            # Program header: e.g. "1. BED100 - STRATEGIC MARKETING"
            # The program ID must look like a real budget code: 2-4 letters + 2-4 digits
            # (e.g. BED100, EDN100, LBR903). This prevents grant project names containing
            # a hyphen (e.g. "32. KALIHI-PALAMA HEALTH CENTER") from being treated as
            # program headers where "KALIHI" would be misread as a program ID.
            'program': re.compile(
                r'^\s*\d+[A-Z]?\.\s+([A-Z]{2,4}\d{2,4})\s*[-\u2013]\s*(.+)',
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
            # Blank-FY1 IC header: "INVESTMENT CAPITAL  DEPT  FUND  AMOUNT_FUND"
            # FY1 column has only a fund letter (no amount); FY2 has the actual amount.
            # e.g. "INVESTMENT CAPITAL  LNR  C  2,000,000C"
            'investment_capital_fy2_only': re.compile(
                r'^\s*INVESTMENT\s+CAPITAL\s+([A-Z]{2,4})\s+([A-Z])\s+([\d,]+)([A-Z])\s*$',
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

            # Bare amendment line: ONLY a number + fund letter, no dept code.
            # HB1800 supplemental format has 3 columns:
            #   Col1 (main line): FY1 appropriation
            #   Col2 (main line): HB300 baseline reference
            #   Col3 (bare next line): THIS bill's actual FY2 amendment
            # e.g., "                        683,779A" overrides the preceding FY2.
            'bare_amendment': re.compile(
                r'^\s{4,}([\d,]+)([A-Z])\s*$',
            ),

            # Two-column bare amendment: overrides BOTH FY1 and FY2.
            # Some supplemental bills put two override values on the same line:
            #   "                        1,186,819A     1,186,819A"
            # The first amount overrides the preceding FY1; the second overrides FY2.
            # Both columns must share the same fund letter.
            'bare_amendment_two_col': re.compile(
                r'^\s{4,}([\d,]+)([A-Z])\s+([\d,]+)([A-Z])\s*$',
            ),

            # --- TOTAL FUNDING lines (grant/subsidy capital items) ---
            # e.g., "TOTAL FUNDING  LBR  350 C  C" or "TOTAL FUNDING  TRN  17,061 E  26,760 E"
            'total_funding': re.compile(
                r'^\s*TOTAL\s+FUNDING\s+([A-Z]{2,4})\s+([\d,]+)\s*([A-Z])\s+(?:([\d,]+)\s*)?([A-Z])\s*$',
                re.IGNORECASE,
            ),

            # --- Section 14 patterns (CIP project list) ---
            # Unnumbered program header (e.g. "BED101 - OFFICE OF INTERNATIONAL AFFAIRS")
            'cip_program': re.compile(
                r'^\s*([A-Z]{2,4}\d{2,4})\s*[-\u2013]\s*(.+?)\s*$',
            ),
            # Project header (e.g. "1.          EAST-WEST CENTER, OAHU" or "2.1  NEW ANIMAL...")
            # Accepts "1." (integer with trailing dot) or "2.1" (decimal subproject).
            'cip_project': re.compile(
                # First char of name can be a letter OR digit — titles like
                # "3RD HAWAII STATE VETERAN'S HOME" or "442ND LEGACY CENTER"
                # are real project names in the bill.
                r'^\s*(\d+(?:\.\d+)?)\.?\s{2,}([A-Z0-9].+?)\s*$',
            ),
            # Section 14 TOTAL FUNDING line — more permissive than the Part II variant.
            # Handles all three forms: FY1 only, FY2 only, and both.
            #   "TOTAL FUNDING  BED  5,000 C    C"      → FY1=5000C, FY2=0C
            #   "TOTAL FUNDING  AGS         C  4,000 C" → FY1=0C,    FY2=4000C
            #   "TOTAL FUNDING  TRN  17,061 E 26,760 E" → FY1=17061E, FY2=26760E
            'cip_total_funding': re.compile(
                r'^\s*TOTAL\s+FUNDING\s+([A-Z]{2,4})\s+'
                r'(?:([\d,]+)\s+)?([A-Z])\s+'       # FY1: optional amount + required fund
                r'(?:([\d,]+)\s+)?([A-Z])\s*$',     # FY2: optional amount + required fund
                re.IGNORECASE,
            ),
            # Section 14 continuation row: a bare "amount fund-letter" appearing
            # directly after a TOTAL FUNDING line. In HB1800 HD1 this represents
            # the bill's amended FY2 appropriation for the same fund; it either
            # overrides the just-emitted FY2 project amount, or (if FY2 was blank)
            # creates the FY2 project entry from scratch.
            # Matched against the stripped line so leading whitespace is ignored;
            # the guards in _extract_allocations (cur_project is None AND a
            # last_cip_emission exists) confine this match to the narrow window
            # between a TOTAL FUNDING emission and the next project header.
            # e.g., "67,000 E" (stripped from "                         67,000 E")
            'cip_continuation_amount': re.compile(
                r'^([\d,]+)\s+([A-Z])$',
            ),
            # Section 14 secondary fund row: "DEPT  [amt] fund  [amt] fund"
            # Appears under a project after its TOTAL FUNDING line to add another
            # fund source. e.g. "TRN   26,064 E   10,100 E" or "TRN  32,394 N  40,400 N"
            # Same shape as cip_total_funding but without the "TOTAL FUNDING" prefix.
            # Matched against the stripped line; confined to the in-project window
            # by the same cur_project/last_cip_emission guards as continuation rows.
            'cip_secondary_fund': re.compile(
                r'^([A-Z]{2,4})\s+'
                r'(?:([\d,]+)\s+)?([A-Z])\s+'
                r'(?:([\d,]+)\s+)?([A-Z])\s*$',
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

        Side effects:
            Populates `self.projects` with List[BudgetProject] from Section 14.
        """
        self.logger.info(f"Starting fast parse of {file_path}")
        self.projects: List[BudgetProject] = []

        try:
            content = self._read_file(file_path)
            if not content:
                self.logger.error("No content found in file")
                return []

            allocations = self._extract_allocations(content)

            if not self.validate(allocations):
                self.logger.warning("Validation failed for some allocations")

            allocations = self._remove_suspicious_duplicates(allocations)

            self.logger.info(
                f"Successfully parsed {len(allocations)} budget allocations "
                f"and {len(self.projects)} Section 14 projects"
            )
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
        in_cip_project_list = False  # Section 14: skip TOTAL FUNDING (already counted in Part II)
        # Tracks the last Section 14 emission so we can (a) apply HD1-style
        # continuation-row FY2 overrides, and (b) dedupe SD1-style duplicate
        # project blocks (same program + same project_id with/without leading
        # whitespace, representing House vs Senate versions stacked as two blocks).
        last_cip_emission: Optional[Dict[str, Any]] = None
        # Deferred dedup: set when a same-title sub-project header fires.
        # Resolved at the next TOTAL FUNDING line by comparing funds.
        pending_fund_dedup: Optional[Dict[str, Any]] = None

        # Section 14 project-parsing state
        cip_program_id: str = ''
        cip_program_name: str = ''
        cip_category: str = ''
        cip_dept_code: str = ''  # Derived from program_id prefix
        cur_project: Optional[Dict] = None  # {project_id, project_name, scope_lines, line_number}

        lines = content.split('\n')
        for i, raw_line in enumerate(lines):
            try:
                # Strip trailing closing-quote that appears on the last amount line
                # of a quoted bill section (e.g. 'COK 13,000,000S  S"').
                # Guard: only strip when the line, after removing the quote, starts with a
                # 2-4 letter department code followed by whitespace (e.g. "COK ", "SUB ").
                # This prevents stripping quotes from CIP item numbers like "K-8  10,500,000 A\""
                # that appear in lapsing-appropriations quoted statutory sections and are NOT
                # appropriations for this bill.
                if raw_line.endswith('"') and len(raw_line) >= 2 and raw_line[-2].isalpha():
                    _candidate = raw_line[:-1]
                    if re.match(r'^[A-Z]{2,4}\s', _candidate.strip(), re.IGNORECASE):
                        raw_line = _candidate
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

                # --- 0b. Bare amendment line (HB1800 supplemental 3-column format) ---
                # Pattern: indented line with ONLY "number + fund letter", no dept code.
                # In HB1800, the 3-column format is:
                #   Main line: OPERATING DEPT  FY1_amt(fund)  reference_FY2_amt(fund)
                #   Next line: (indented)       actual_FY2_amendment(fund)
                # We override the FY2 of the most recently added matching allocation.
                # Check two-column form first (more specific), then single-column.
                m2 = pat['bare_amendment_two_col'].match(raw_line)
                if m2 and state.has_context() and m2.group(2).upper() == m2.group(4).upper():
                    bare_fy1 = int(m2.group(1).replace(',', ''))
                    bare_fy2 = int(m2.group(3).replace(',', ''))
                    bare_fund = m2.group(2).upper()
                    # The bare amendment refers to the preceding IC line's dept.
                    preceding_dept = None
                    for a in reversed(allocations):
                        if a.program_id == state.program_id:
                            preceding_dept = a.department_code
                            break
                    cur_sec = state.section_enum
                    found_fy2 = False
                    for a in reversed(allocations):
                        if (a.program_id == state.program_id
                                and a.fiscal_year == self.fy2
                                and a.fund_type is not None
                                and a.fund_type.value == bare_fund
                                and a.section == cur_sec
                                and (preceding_dept is None
                                     or a.department_code == preceding_dept)):
                            a.amount = bare_fy2
                            found_fy2 = True
                            self.logger.debug(
                                f'L{line_num}: two-col bare amendment FY2 '
                                f'{a.program_id} dept={a.department_code} '
                                f'fund={bare_fund} → {bare_fy2}'
                            )
                            break
                    if not found_fy2 and bare_fy2 > 0 and cur_sec == BudgetSection.CAPITAL_IMPROVEMENT:
                        new_a = self._make_allocation(
                            state,
                            preceding_dept or state.department_code or '',
                            bare_fy2, bare_fund, self.fy2, line_num,
                            section_override=BudgetSection.CAPITAL_IMPROVEMENT,
                            notes='Investment Capital - two-col bare amendment from zero',
                        )
                        if new_a:
                            allocations.append(new_a)
                    found_fy1 = False
                    for a in reversed(allocations):
                        if (a.program_id == state.program_id
                                and a.fiscal_year == self.fy1
                                and a.fund_type is not None
                                and a.fund_type.value == bare_fund
                                and a.section == cur_sec
                                and (preceding_dept is None
                                     or a.department_code == preceding_dept)):
                            a.amount = bare_fy1
                            found_fy1 = True
                            self.logger.debug(
                                f'L{line_num}: two-col bare amendment FY1 '
                                f'{a.program_id} dept={a.department_code} '
                                f'fund={bare_fund} → {bare_fy1}'
                            )
                            break
                    if not found_fy1 and bare_fy1 > 0 and cur_sec == BudgetSection.CAPITAL_IMPROVEMENT:
                        new_a = self._make_allocation(
                            state,
                            preceding_dept or state.department_code or '',
                            bare_fy1, bare_fund, self.fy1, line_num,
                            section_override=BudgetSection.CAPITAL_IMPROVEMENT,
                            notes='Investment Capital - two-col bare amendment FY1 from zero',
                        )
                        if new_a:
                            allocations.append(new_a)
                    continue

                m = pat['bare_amendment'].match(raw_line)
                if m and state.has_context():
                    bare_amt = int(m.group(1).replace(',', ''))
                    bare_fund = m.group(2).upper()
                    # The bare amendment always refers to the IMMEDIATELY PRECEDING
                    # IC line's dept + fund. Find that dept by walking back to the
                    # most recent allocation in this program (any FY).
                    preceding_dept = None
                    for a in reversed(allocations):
                        if a.program_id == state.program_id:
                            preceding_dept = a.department_code
                            break
                    # Walk backwards through allocations to find the most recent
                    # FY2 entry for this program + fund + matching dept AND section to override.
                    # Section must match to avoid CIP bare amendments from trampling Operating
                    # allocations of the same fund/dept when a program has both sections.
                    cur_sec = state.section_enum
                    found_override = False
                    for a in reversed(allocations):
                        if (a.program_id == state.program_id
                                and a.fiscal_year == self.fy2
                                and a.fund_type is not None
                                and a.fund_type.value == bare_fund
                                and a.section == cur_sec
                                and (preceding_dept is None
                                     or a.department_code == preceding_dept)):
                            a.amount = bare_amt
                            found_override = True
                            self.logger.debug(
                                f'L{line_num}: bare amendment overrides FY2 '
                                f'{a.program_id} dept={a.department_code} '
                                f'fund={bare_fund} → {bare_amt}'
                            )
                            break
                    if not found_override and state.section_enum == BudgetSection.CAPITAL_IMPROVEMENT:
                        # FY27 was explicitly 0 (or never stored) in the IC line;
                        # the bare amendment is the real FY27 value — create it now.
                        # Use the dept from the preceding IC line if we found one.
                        new_a = self._make_allocation(
                            state,
                            preceding_dept or state.department_code or '',
                            bare_amt, bare_fund, self.fy2, line_num,
                            section_override=BudgetSection.CAPITAL_IMPROVEMENT,
                            notes='Investment Capital - bare amendment from zero',
                        )
                        if new_a:
                            allocations.append(new_a)
                            self.logger.debug(
                                f'L{line_num}: bare amendment created new CIP FY2 '
                                f'{state.program_id} dept={preceding_dept} '
                                f'fund={bare_fund} = {bare_amt}'
                            )
                    elif not found_override and state.section_enum == BudgetSection.OPERATING and bare_amt > 0:
                        # FY27 was explicitly 0 (or never stored) in the OPERATING line;
                        # e.g. "OPERATING DEPT 400,000A 0A" followed by a bare amendment.
                        # The bare amendment is the real FY27 value — create it now.
                        new_a = self._make_allocation(
                            state,
                            preceding_dept or state.department_code or '',
                            bare_amt, bare_fund, self.fy2, line_num,
                            section_override=BudgetSection.OPERATING,
                            notes='Operating - bare amendment from zero',
                        )
                        if new_a:
                            allocations.append(new_a)
                            self.logger.debug(
                                f'L{line_num}: bare amendment created new OPERATING FY2 '
                                f'{state.program_id} dept={preceding_dept} '
                                f'fund={bare_fund} = {bare_amt}'
                            )
                    continue

                # --- 0c. CIP project list marker (Section 14) ---
                # Section 14 lists capital improvement projects that are already counted
                # in Part II INVESTMENT CAPITAL lines. Skip TOTAL FUNDING lines after this point.
                if 'CAPITAL IMPROVEMENT PROJECTS AUTHORIZED' in line:
                    in_cip_project_list = True
                    self.logger.debug("Entered CIP project list section (Section 14); skipping TOTAL FUNDING lines")
                    continue

                # --- 0d. Section 14 project parsing ---
                # When inside the CIP project list, parse project-level structure into
                # self.projects. Do NOT emit BudgetAllocation records here (those come
                # from Part II).
                if in_cip_project_list:
                    # Category header (A. ECONOMIC DEVELOPMENT)
                    mc = pat['category'].match(line)
                    if mc:
                        code = mc.group(1).upper()
                        cip_category = CATEGORY_MAP.get(code, 'Other')
                        continue

                    # Unnumbered program header (BED101 - OFFICE OF INTERNATIONAL AFFAIRS)
                    mp = pat['cip_program'].match(line)
                    if mp and mp.group(1)[:3].upper() in DEPARTMENT_NAMES:
                        cip_program_id = mp.group(1).strip().upper()
                        cip_program_name = mp.group(2).strip()
                        cip_dept_code = cip_program_id[:3].upper()
                        cur_project = None  # Flush in-progress project
                        last_cip_emission = None  # emission context is per-program
                        pending_fund_dedup = None
                        continue

                    # TOTAL FUNDING line — emit project(s) for cur_project
                    mt = pat['cip_total_funding'].match(line)
                    if mt and cur_project and cip_program_id:
                        dept = mt.group(1).upper()
                        fy1_num = int(re.sub(r'[^\d]', '', mt.group(2))) if mt.group(2) else 0
                        fy2_num = int(re.sub(r'[^\d]', '', mt.group(4))) if mt.group(4) else 0
                        fy1_fund = (mt.group(3) or 'C').upper()
                        fy2_fund = (mt.group(5) or fy1_fund).upper()
                        # Resolve deferred same-title dedup. Senate duplicate
                        # blocks share the prev emission's FY1 fund + FY1
                        # amount (the "keep FY1, modify FY2" pattern).
                        # Distinct-but-same-titled projects typically differ
                        # on FY1 amount (e.g. UOH100 #23.1 vs #24: 0 vs 4M).
                        fy1_amount_new = float(fy1_num) * 1000.0
                        if (pending_fund_dedup is not None
                                and pending_fund_dedup['program_id'] == cip_program_id
                                and pending_fund_dedup['prev_fy1_fund'] == fy1_fund
                                and pending_fund_dedup['prev_fy2_fund'] == fy2_fund
                                and pending_fund_dedup['prev_fy1_amount'] == fy1_amount_new):
                            stale = pending_fund_dedup['stale_refs']
                            if stale:
                                self.projects = [p for p in self.projects if id(p) not in stale]
                            self.logger.debug(
                                f"L{line_num}: CIP same-title dedup fired "
                                f"{cip_program_id} #{cur_project['project_id']} "
                                f"(funds {fy1_fund}/{fy2_fund}, fy1={fy1_amount_new:,.0f})"
                            )
                        pending_fund_dedup = None
                        scope_text = ' '.join(
                            s.strip() for s in cur_project['scope_lines'] if s.strip()
                        )
                        # Emit FY1 project (amounts are in thousands → multiply by 1000)
                        fy1_proj_ref = None
                        fy2_proj_ref = None
                        if fy1_num > 0:
                            self.projects.append(BudgetProject(
                                project_id=cur_project['project_id'],
                                project_name=cur_project['project_name'],
                                scope=scope_text,
                                program_id=cip_program_id,
                                program_name=cip_program_name,
                                department_code=dept,
                                category=cip_category or 'Uncategorized',
                                fiscal_year=self.fy1,
                                amount=float(fy1_num) * 1000.0,
                                fund_type=FundType.from_string(fy1_fund),
                                line_number=line_num,
                            ))
                            fy1_proj_ref = self.projects[-1]
                        if fy2_num > 0:
                            self.projects.append(BudgetProject(
                                project_id=cur_project['project_id'],
                                project_name=cur_project['project_name'],
                                scope=scope_text,
                                program_id=cip_program_id,
                                program_name=cip_program_name,
                                department_code=dept,
                                category=cip_category or 'Uncategorized',
                                fiscal_year=self.fy2,
                                amount=float(fy2_num) * 1000.0,
                                fund_type=FundType.from_string(fy2_fund),
                                line_number=line_num,
                            ))
                            fy2_proj_ref = self.projects[-1]
                        # Record the emission so a subsequent continuation row
                        # (HD1 pattern), secondary fund row, or duplicate project
                        # block (SD1 pattern) can amend or replace it.
                        # fy1_proj/fy2_proj track the *most recent* fund emission
                        # (used as the target for continuation-row overrides).
                        # all_refs tracks every BudgetProject emitted under this
                        # project header so the SD1 duplicate-block dedup can
                        # remove every fund source, not just the primary.
                        all_refs = [r for r in (fy1_proj_ref, fy2_proj_ref) if r is not None]
                        last_cip_emission = {
                            'program_id': cip_program_id,
                            'program_name': cip_program_name,
                            'project_id': cur_project['project_id'],
                            'project_id_norm': cur_project['project_id'].strip(),
                            'project_name': cur_project['project_name'],
                            'project_name_key': cur_project['project_name'].strip().upper(),
                            'scope': scope_text,
                            'category': cip_category or 'Uncategorized',
                            'dept': dept,
                            'fy1_fund': fy1_fund,
                            'fy2_fund': fy2_fund,
                            'fy1_proj': fy1_proj_ref,
                            'fy2_proj': fy2_proj_ref,
                            'all_refs': all_refs,
                            # Immutable primary-emission snapshot used by the
                            # deferred same-title dedup. Secondary-fund rows
                            # mutate fy1_fund/fy2_fund/fy1_proj/fy2_proj above
                            # to retarget continuation rows, but the dedup
                            # needs the ORIGINAL TOTAL FUNDING values.
                            'fy1_fund_primary': fy1_fund,
                            'fy2_fund_primary': fy2_fund,
                            'fy1_amount_primary': float(fy1_num) * 1000.0,
                        }
                        cur_project = None
                        continue

                    # Section 14 secondary fund row — another fund source under
                    # the current project (same DEPT, no "TOTAL FUNDING" prefix).
                    # e.g. "TRN  26,064 E  10,100 E". Emits FY1/FY2 projects and
                    # refreshes last_cip_emission so subsequent continuation rows
                    # target THIS fund (not the primary TOTAL FUNDING fund).
                    if last_cip_emission is not None and cur_project is None:
                        msf = pat['cip_secondary_fund'].match(line)
                        if msf and msf.group(1).upper() == last_cip_emission.get('dept', '').upper():
                            sf_fy1_num = int(re.sub(r'[^\d]', '', msf.group(2))) if msf.group(2) else 0
                            sf_fy2_num = int(re.sub(r'[^\d]', '', msf.group(4))) if msf.group(4) else 0
                            sf_fy1_fund = (msf.group(3) or 'C').upper()
                            sf_fy2_fund = (msf.group(5) or sf_fy1_fund).upper()
                            sf_fy1_ref = None
                            sf_fy2_ref = None
                            if sf_fy1_num > 0:
                                self.projects.append(BudgetProject(
                                    project_id=last_cip_emission['project_id'],
                                    project_name=last_cip_emission['project_name'],
                                    scope=last_cip_emission['scope'],
                                    program_id=last_cip_emission['program_id'],
                                    program_name=last_cip_emission['program_name'],
                                    department_code=last_cip_emission['dept'],
                                    category=last_cip_emission['category'],
                                    fiscal_year=self.fy1,
                                    amount=float(sf_fy1_num) * 1000.0,
                                    fund_type=FundType.from_string(sf_fy1_fund),
                                    line_number=line_num,
                                ))
                                sf_fy1_ref = self.projects[-1]
                                last_cip_emission['all_refs'].append(sf_fy1_ref)
                            if sf_fy2_num > 0:
                                self.projects.append(BudgetProject(
                                    project_id=last_cip_emission['project_id'],
                                    project_name=last_cip_emission['project_name'],
                                    scope=last_cip_emission['scope'],
                                    program_id=last_cip_emission['program_id'],
                                    program_name=last_cip_emission['program_name'],
                                    department_code=last_cip_emission['dept'],
                                    category=last_cip_emission['category'],
                                    fiscal_year=self.fy2,
                                    amount=float(sf_fy2_num) * 1000.0,
                                    fund_type=FundType.from_string(sf_fy2_fund),
                                    line_number=line_num,
                                ))
                                sf_fy2_ref = self.projects[-1]
                                last_cip_emission['all_refs'].append(sf_fy2_ref)
                            # Refresh continuation-target pointers to the most
                            # recently emitted fund. A continuation row coming
                            # next will override THIS fund's FY2.
                            last_cip_emission['fy1_fund'] = sf_fy1_fund
                            last_cip_emission['fy2_fund'] = sf_fy2_fund
                            last_cip_emission['fy1_proj'] = sf_fy1_ref
                            last_cip_emission['fy2_proj'] = sf_fy2_ref
                            self.logger.debug(
                                f"L{line_num}: CIP secondary fund "
                                f"{last_cip_emission['program_id']} "
                                f"proj={last_cip_emission['project_id']} "
                                f"fund={sf_fy1_fund}  "
                                f"fy1={sf_fy1_num*1000:,.0f} fy2={sf_fy2_num*1000:,.0f}"
                            )
                            continue

                    # Section 14 continuation row (HD1 pattern):
                    # deeply-indented bare amount directly amends the just-emitted
                    # FY2 project. If the prior FY2 was 0/blank, creates a new FY2
                    # entry from the last emission's context.
                    mcc = pat['cip_continuation_amount'].match(line)
                    if mcc and last_cip_emission is not None and cur_project is None:
                        try:
                            amt_thousands = int(mcc.group(1).replace(',', ''))
                        except ValueError:
                            amt_thousands = 0
                        cont_fund = mcc.group(2).upper()
                        new_amt = float(amt_thousands) * 1000.0
                        fy2_proj = last_cip_emission.get('fy2_proj')
                        if (fy2_proj is not None
                                and fy2_proj.fund_type is not None
                                and fy2_proj.fund_type.value == cont_fund):
                            # Override existing FY2 amount
                            fy2_proj.amount = new_amt
                            self.logger.debug(
                                f"L{line_num}: CIP FY2 continuation override "
                                f"{fy2_proj.program_id} proj={fy2_proj.project_id} "
                                f"fund={cont_fund} → {new_amt:,.0f}"
                            )
                        elif (fy2_proj is None and amt_thousands > 0
                                and cont_fund == last_cip_emission.get('fy1_fund')
                                and cont_fund == last_cip_emission.get('fy2_fund')):
                            # FY2 was blank on main row AND the continuation fund
                            # matches the row's fund — create new FY2 project.
                            # (If the funds differ, the continuation row is
                            # amending a *secondary* fund row that this parser
                            # doesn't yet capture in Section 14; skip to avoid
                            # creating a ghost project under the wrong fund.)
                            new_proj = BudgetProject(
                                project_id=last_cip_emission['project_id'],
                                project_name=last_cip_emission['project_name'],
                                scope=last_cip_emission['scope'],
                                program_id=last_cip_emission['program_id'],
                                program_name=last_cip_emission['program_name'],
                                department_code=last_cip_emission['dept'],
                                category=last_cip_emission['category'],
                                fiscal_year=self.fy2,
                                amount=new_amt,
                                fund_type=FundType.from_string(cont_fund),
                                line_number=line_num,
                            )
                            self.projects.append(new_proj)
                            last_cip_emission['fy2_proj'] = new_proj
                            last_cip_emission.setdefault('all_refs', []).append(new_proj)
                            self.logger.debug(
                                f"L{line_num}: CIP FY2 continuation created "
                                f"{new_proj.program_id} proj={new_proj.project_id} "
                                f"fund={cont_fund} = {new_amt:,.0f}"
                            )
                        continue

                    # Project header (1. EAST-WEST CENTER, OAHU or 2.1  NEW ...)
                    # Check after cip_program to avoid matching "BED101 - NAME" as a number.
                    mj = pat['cip_project'].match(line)
                    # Guard: the matched first group must look like a project number
                    # (purely digits/dot), NOT a department code.
                    if mj and re.fullmatch(r'\d+(?:\.\d+)?', mj.group(1)):
                        new_pid_norm = mj.group(1).strip()
                        new_pname_key = mj.group(2).strip().upper()
                        # SD1-style duplicate-block dedup: within the same program,
                        # the Senate amendment re-emits the House version with
                        # either (a) the same project number but a slightly
                        # tweaked title (e.g. BED160 #29 with/without "STATEWIDE"),
                        # or (b) the same title but a renumbered project_id
                        # (e.g. TRN102 " 2." becomes "1."). We fire dedup on
                        # EITHER matching project_id OR matching title — or when
                        # one title is a prefix of the other (covers the "title
                        # with trailing location qualifier" case).
                        prev_pid = last_cip_emission['project_id_norm'] if last_cip_emission else ''
                        prev_pname = last_cip_emission['project_name_key'] if last_cip_emission else ''
                        # Dedup strategy:
                        #   - Exact id-match → fire immediately (strongest
                        #     signal; House/Senate re-emit same block with
                        #     same number).
                        #   - Same title but different id (including sub-
                        #     projects) → DEFER. Too ambiguous at this point:
                        #     BED113 #2/#2.1 and UOH100 #23.1/#24/#25 share
                        #     titles but are distinct. Resolve at the next
                        #     TOTAL FUNDING by requiring both fund-match AND
                        #     FY1-amount-match (Senate duplicate blocks
                        #     preserve the FY1 figure; distinct projects
                        #     typically differ).
                        if (last_cip_emission is not None
                                and last_cip_emission['program_id'] == cip_program_id
                                and prev_pid == new_pid_norm):
                            stale_refs = {id(p) for p in last_cip_emission.get('all_refs', [])
                                          if p is not None}
                            if stale_refs:
                                self.projects = [p for p in self.projects if id(p) not in stale_refs]
                            self.logger.debug(
                                f"L{line_num}: CIP duplicate project "
                                f"{cip_program_id} #{new_pid_norm} — removed prior "
                                f"emission (id-match)"
                            )
                            last_cip_emission = None
                        elif (last_cip_emission is not None
                              and last_cip_emission['program_id'] == cip_program_id
                              and prev_pname == new_pname_key
                              and prev_pid != new_pid_norm):
                            # Same title, different id: defer to TOTAL FUNDING.
                            pending_fund_dedup = {
                                'prev_fy1_fund': last_cip_emission.get('fy1_fund_primary'),
                                'prev_fy2_fund': last_cip_emission.get('fy2_fund_primary'),
                                'prev_fy1_amount': last_cip_emission.get('fy1_amount_primary', 0),
                                'stale_refs': {id(p) for p in last_cip_emission.get('all_refs', [])
                                               if p is not None},
                                'program_id': cip_program_id,
                            }
                        cur_project = {
                            'project_id': mj.group(1),
                            'project_name': mj.group(2).strip(),
                            'scope_lines': [],
                            'line_number': line_num,
                        }
                        continue

                    # Any other non-empty line inside a project → scope continuation
                    if cur_project is not None and line:
                        cur_project['scope_lines'].append(line)
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
                # SKIP in CIP project list section (Section 14), as these are project breakdowns
                # of funds already counted in Part II INVESTMENT CAPITAL lines.
                m = pat['total_funding'].match(line)
                if m and state.has_context() and not in_cip_project_list:
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
                # Try blank-FY1 variant first (more specific): "IC  DEPT  FUND  AMOUNT_FUND"
                m_ic2 = pat['investment_capital_fy2_only'].match(line)
                if m_ic2:
                    state.section = 'INVESTMENT CAPITAL'
                    self._append_pair(
                        allocations, state,
                        dept_code=m_ic2.group(1),
                        fy1_amount_str=None,
                        fy1_fund=m_ic2.group(4) or 'C',
                        fy2_amount_str=m_ic2.group(3),
                        fy2_fund=m_ic2.group(4) or 'C',
                        line_number=line_num,
                        section_override=BudgetSection.CAPITAL_IMPROVEMENT,
                        notes='Investment Capital - blank FY1 header',
                    )
                    continue

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
                    # First column has only a fund letter (no amount); amount is in FY2 position.
                    if not matched:
                        m = pat['fy2_only_amount'].match(line)
                        if m and m.group(1):
                            self._append_pair(
                                allocations, state,
                                dept_code=m.group(1),
                                fy1_amount_str=None,
                                fy1_fund=m.group(4) or 'C',
                                fy2_amount_str=m.group(3),
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
                # The first column has only a fund letter (blank FY1 amount).
                # The amount belongs only to FY2; FY1 gets zero/None.
                m = pat['fy2_only_amount'].match(line)
                if m and state.has_context():
                    amt = m.group(3)
                    fund = m.group(4)
                    self._append_pair(
                        allocations, state,
                        dept_code=m.group(1),
                        fy1_amount_str=None,
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
                    fund_default = 'C' if 'INVESTMENT' in state.section.upper() else 'A'

                    # First try blank-FY1 format: "SECTION  DEPT  FUND  AMOUNT_FUND"
                    # (Amount belongs to FY2, FY1 is blank.)
                    blank_fy1 = re.search(
                        r'([A-Z]{2,4})\s+([A-Z])\s+([\d,]+)([A-Z])\s*$', line
                    )
                    if blank_fy1:
                        self._append_pair(
                            allocations, state,
                            dept_code=blank_fy1.group(1),
                            fy1_amount_str=None,
                            fy1_fund=blank_fy1.group(4) or blank_fy1.group(2) or fund_default,
                            fy2_amount_str=blank_fy1.group(3),
                            fy2_fund=blank_fy1.group(4) or fund_default,
                            line_number=line_num,
                        )
                        continue

                    # Check for amounts appended after the section keyword
                    amt_m = re.search(
                        r'([A-Z]+)\s+([\d,]+)([A-Z]?)(?:\s+([\d,]+)([A-Z]?))?\s*$', line
                    )
                    if amt_m:
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
