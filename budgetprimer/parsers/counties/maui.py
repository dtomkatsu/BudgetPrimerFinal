"""
County of Maui budget parser.

Source: the FY2026 **Mayor's Proposed Budget** "Program Budget (Combined)" — a
1,072-page PDF. This is the Mayor's *proposed* budget submitted to the Council
in March 2025, NOT the adopted ordinance (unlike Honolulu and Kauaʻi, which use
adopted figures). The web view labels Maui accordingly.

Two clean, self-validating tables anchor the parse:

**Operating** — "Operating Expenditures by Character Type" (Figure 2-8, in
thousands) lists every department with its total operating expenditure; the
table's own "Total Expenditures" row publishes $1,226,165,200. We take each
department's TOTAL column. The proposed book reports operating *fund* splits
only as pie charts, so each department's operating is attributed to its primary
fund (General Fund, except the enterprise departments) — an approximation noted
in the coverage note.

**Capital (CIP)** — the six-year "Project Detail by Department" sheets list each
project with a funding-source code and a FY2026 column (in thousands). Summing
the FY2026 column by project×fund reconciles to the published $461,429,197 (and
to the by-department Figure 5-4 and by-fund-type Figure 5-8 summaries) within
rounding. The per-department tables end with a "FUNDING SOURCE" recap that
repeats every fund row — we stop at it to avoid double counting.

Raw file (NOT committed by default — 29 MB; re-fetch via fetch_county_budgets):
    fy2026: program budget combined (Mayor's Proposed)
"""
from __future__ import annotations
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from budgetprimer.models.budget_allocation import BudgetSection
from budgetprimer.models.county_allocation import CountyAllocation, normalize_fund

from .base import BaseCountyParser

logger = logging.getLogger(__name__)

# Published control totals (Mayor's Proposed FY2026).
MAUI_OP_TOTAL = 1226165200          # Figure 2-8 "Total Expenditures"
MAUI_CIP_TOTAL = 461429197          # Figure 5-4 / 5-8 "TOTAL"

# CIP funding-source code → fund name (from the Capital Budget Summary by Fund
# Type, Figure 5-8). Codes appear on the project-detail sheets.
MAUI_CIP_FUNDS = {
    'GF': 'General Fund',
    'GB': 'General Obligation Bond Fund',
    'FD': 'Federal Fund',
    'GE': 'GET / Revolving Fund',
    'HF': 'Highway Fund',
    'ST': 'State Fund',
    'WF': 'Sewer Fund',
    'WU': 'Water Supply Fund – Unrestricted',
    'WR': 'Water Supply Fund – Restricted/GET',
    'OG': 'Other Grant Fund',
    'SW': 'Solid Waste Fund',
    'PA': 'Park Assessment Fund',
    'EP': 'EP&S Fund',
    'SRF': 'State Revolving Loan Fund',
    'LBF': 'Lapsed Bond Fund',
    'OT': 'Other Fund',
}

# Operating: each department's primary fund. The proposed book only charts the
# operating fund split, so we attribute a department's whole operating budget to
# its primary fund — General Fund except for the enterprise departments.
MAUI_OP_PRIMARY_FUND = {
    'Water Supply': 'Water Supply Fund',
    'Environmental Management': 'Sewer / Solid Waste Fund',
    'Liquor Control': 'Liquor Fund',
}
_OP_DEFAULT_FUND = 'General Fund'

_MONEY = re.compile(r'\(?\$[\d,]+(?:\.\d+)?\)?')
_CIP_ROW = re.compile(r'(.*?)\b([A-Z]{2,3})\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$')
_CBS = re.compile(r'\bCBS-?\d+[A-Z]?\b')
_DEPT_HDR = re.compile(r'^([A-Z][A-Z ʻ&]+) COUNTY OF MAUI$')
_CIP_COLHDR = 'District Project Type CBS No Project Name Fund'
_PAGE_FOOTER = 'MAYOR'  # "FISCAL YEAR 2026 MAYOR'S PROPOSED BUDGET <n>"


def _money_to_dollars(tok: str) -> float:
    """Parse a '$12,708.1' / '($17,072.9)' thousands token → dollars."""
    neg = tok.startswith('(')
    v = float(tok.strip('()$').replace(',', ''))
    return (-v if neg else v) * 1000.0


def _slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def _dept_title(s: str) -> str:
    """Title-case an ALL-CAPS department header, keeping small words lowercase
    (so the CIP page headers match the operating table's casing)."""
    out = s.title()
    for w in (' And ', ' Of ', ' The ', ' For '):
        out = out.replace(w, w.lower())
    return out


class MauiParser(BaseCountyParser):
    county = 'maui'
    source_label = "FY2026 Mayor's Proposed Budget · mauicounty.gov"
    source_url = ('https://www.mauicounty.gov/DocumentCenter/View/152301/'
                  '000---FY-2026-Program-Budget-Combined')
    coverage_note = (
        "FY2026 Mayor's PROPOSED budget (submitted March 2025) — not the adopted "
        "ordinance, unlike Honolulu and Kauaʻi. Operating is shown by department "
        "(from the Operating Expenditures by Character Type summary); the proposed "
        "book reports operating fund splits only as charts, so each department's "
        "operating is attributed to its primary fund. The capital program is "
        "parsed at the project level from the six-year CIP project sheets "
        "(FY2026 column)."
    )

    def parse(self, raw_dir: Path, fiscal_year: int) -> List[CountyAllocation]:
        if fiscal_year != 2026:
            return []                       # only the FY2026 book is published
        pages = self._page_texts(raw_dir, fiscal_year)
        if pages is None:
            return []
        return self._parse_operating(pages, fiscal_year) + \
            self._parse_cip(pages, fiscal_year)

    # -- shared: extract every page's text once (the PDF is large) -------------
    def _page_texts(self, raw_dir: Path, fiscal_year: int) -> Optional[List[str]]:
        pdfs = sorted(raw_dir.glob(f'fy{fiscal_year}_program_budget*.pdf'))
        if not pdfs:
            logger.info(f"Maui FY{fiscal_year}: no program budget PDF")
            return None
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber not installed — cannot parse Maui")
            return None
        with pdfplumber.open(pdfs[0]) as pdf:
            return [(page.extract_text() or '') for page in pdf.pages]

    # -- operating: Figure 2-8 (Operating Expenditures by Character Type) ------
    def _parse_operating(self, pages: List[str], fiscal_year: int) -> List[CountyAllocation]:
        allocations: List[CountyAllocation] = []
        for body in pages:
            if 'Operating Expenditures by Character Type' not in body \
                    or 'SALARIES AND' not in body:
                continue
            intable = False
            for ln in body.splitlines():
                s = ln.strip()
                if s.startswith('DEPARTMENT WAGES'):
                    intable = True
                    continue
                if not intable:
                    continue
                if s.startswith('Total Expenditures'):
                    break
                nums = _MONEY.findall(s)
                if len(nums) < 2 or '$' not in s:
                    continue
                name = s[:s.find('$')].strip().rstrip('123 ').strip()
                total = _money_to_dollars(nums[-1])   # TOTAL is the last column
                if not name or total == 0:
                    continue
                fund = MAUI_OP_PRIMARY_FUND.get(name, _OP_DEFAULT_FUND)
                allocations.append(CountyAllocation(
                    county=self.county,
                    department_code=_slug(name),
                    department_name=name,
                    section=BudgetSection.OPERATING,
                    fund_name=fund,
                    fund_category=normalize_fund(fund),
                    fiscal_year=fiscal_year,
                    amount=total,
                    program_name=None,
                    source="Maui FY2026 Mayor's Proposed (Figure 2-8)",
                ))
            break  # Figure 2-8 appears once

        parsed = sum(a.amount for a in allocations)
        diff = parsed - MAUI_OP_TOTAL
        logger.info(f"Maui FY{fiscal_year} operating: {len(allocations)} departments, "
                    f"${parsed/1e6:.1f}M ({diff:+,.0f} vs published ${MAUI_OP_TOTAL:,})")
        if abs(diff) > MAUI_OP_TOTAL * 0.005:
            logger.warning(f"Maui operating parse off (${parsed:,.0f} vs ${MAUI_OP_TOTAL:,})")
        return allocations

    # -- capital: six-year "Project Detail by Department" sheets ---------------
    def _parse_cip(self, pages: List[str], fiscal_year: int) -> List[CountyAllocation]:
        allocations: List[CountyAllocation] = []
        cur_dept: Optional[str] = None
        cur_project: Optional[str] = None
        pending_name: List[str] = []        # wrapped project-name fragments

        # CIP sheets begin after the operating section; gate on the column header.
        for body in pages:
            lines = body.splitlines()
            for ln in lines[:4]:
                m = _DEPT_HDR.match(ln.strip())
                if m:
                    cur_dept = _dept_title(m.group(1).strip())
            intable = False
            for ln in lines:
                s = ln.strip()
                if _CIP_COLHDR in s:
                    intable = True
                    pending_name = []
                    continue
                if not intable:
                    continue
                if s.startswith(('Total:', 'FUNDING SOURCE', '*Note')):
                    intable = False
                    pending_name = []
                    continue
                m = _CIP_ROW.match(s)
                if not m:
                    # a wrapped project-name fragment (skip page footers)
                    if s and _PAGE_FOOTER not in s and not s.startswith('FISCAL YEAR'):
                        pending_name.append(s)
                    continue
                prefix, code, fy26_s = m.group(1), m.group(2), m.group(3)
                if code not in MAUI_CIP_FUNDS:
                    pending_name = []
                    continue
                fy26 = int(fy26_s.replace(',', '')) * 1000
                cbs = _CBS.search(prefix)
                if cbs:
                    # new project: name = wrapped fragments + text after CBS-####
                    tail = prefix[cbs.end():].strip()
                    cur_project = ' '.join(pending_name + ([tail] if tail else [])).strip()
                    cur_project = re.sub(r'\s+', ' ', cur_project) or '(unnamed project)'
                pending_name = []
                if fy26 == 0 or not cur_dept:
                    continue
                fund = MAUI_CIP_FUNDS[code]
                allocations.append(CountyAllocation(
                    county=self.county,
                    department_code=_slug(cur_dept),
                    department_name=cur_dept,
                    section=BudgetSection.CAPITAL_IMPROVEMENT,
                    fund_name=fund,
                    fund_category=normalize_fund(fund),
                    fiscal_year=fiscal_year,
                    amount=float(fy26),
                    program_name=cur_project or '(unnamed project)',
                    source="Maui FY2026 Mayor's Proposed (CIP project sheets)",
                ))

        parsed = sum(a.amount for a in allocations)
        diff = parsed - MAUI_CIP_TOTAL
        logger.info(f"Maui FY{fiscal_year} CIP: {len(allocations)} project×fund rows, "
                    f"${parsed/1e6:.1f}M ({diff:+,.0f} vs published ${MAUI_CIP_TOTAL:,})")
        if abs(diff) > MAUI_CIP_TOTAL * 0.01:
            logger.warning(f"Maui CIP parse off (${parsed:,.0f} vs ${MAUI_CIP_TOTAL:,})")
        return allocations
