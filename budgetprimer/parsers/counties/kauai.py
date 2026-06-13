"""
County of Kauaʻi budget parser.

Kauaʻi publishes its budget as two ordinance PDFs per year (operating and
capital). Unlike Honolulu's scanned ordinance, these are digital text PDFs.

This parser currently covers the **capital budget** (CIP), which lists projects
grouped by fund with three columns — Appropriation Balance (carryover), Proposed
Budget Ordinance (new appropriation), and Appropriation Balance After Ordinance.
The last column is the total appropriation for the year and is what the
ordinance's own Section 1 fund summary totals; we use it as each project's
amount, which reconciles to the published "TOTAL ALL FUNDS" within ~0.1%.

The operating budget is published as a several-hundred-page account-level
preparation worksheet; parsing it to department granularity is a follow-up.

Raw files (committed under data/raw/counties/kauai/):
    fy2026: cip B-2025-906   fy2027: cip B-2026-918
"""
from __future__ import annotations
import logging
import re
from pathlib import Path
from typing import List, Optional

from budgetprimer.models.budget_allocation import BudgetSection
from budgetprimer.models.county_allocation import CountyAllocation, normalize_fund

from .base import BaseCountyParser

logger = logging.getLogger(__name__)

# Short header key (as it appears in the ordinance) → full fund name.
KAUAI_CIP_FUNDS = [
    ('BIKEWAY', 'Bikeway Fund'),
    ('BOND', 'Bond Fund'),
    ('DEVELOPMENT', 'Development Fund'),
    ('G.E. TAX', 'G.E. Tax Fund'),
    ('GENERAL', 'General Fund'),
    ('HIGHWAY', 'Highway Fund'),
    ('PUBLIC ACCESS', 'Public Access, Open Space & Natural Resources Preservation Fund'),
    ('SEWER TRUST', 'Sewer Trust Fund'),
    ('PARKS & PLAYGROUNDS', 'Special Trust Fund for Parks & Playgrounds'),
]
_FUND_NAME = dict(KAUAI_CIP_FUNDS)

# Published "TOTAL ALL FUNDS" per year, for a parse sanity check.
KAUAI_CIP_TOTAL = {2026: 135555648, 2027: 133043449}


def _nums(s: str) -> List[str]:
    return [x for x in re.findall(r'\(?[\d,]+\)?', s) if re.search(r'\d', x)]


def _last_amount(s: str) -> Optional[int]:
    n = _nums(s)
    if not n:
        return None
    return int(n[-1].replace(',', '').replace('(', '-').replace(')', ''))


def _fund_key(text: str) -> Optional[str]:
    up = text.upper()
    for key, _ in KAUAI_CIP_FUNDS:
        if key in up:
            return key
    return None


class KauaiParser(BaseCountyParser):
    county = 'kauai'
    source_label = 'Capital Budget Ordinance · kauai.gov'
    source_url = 'https://www.kauai.gov/Government/Departments-Agencies/Finance/Budget-Division'
    coverage_note = (
        "Capital improvement program only, parsed from the County capital "
        "budget ordinance (total appropriation including carryover balances). "
        "The operating budget is published as a line-item preparation worksheet "
        "and is not yet broken out here."
    )

    def parse(self, raw_dir: Path, fiscal_year: int) -> List[CountyAllocation]:
        return self.parse_cip(raw_dir, fiscal_year)

    def parse_cip(self, raw_dir: Path, fiscal_year: int) -> List[CountyAllocation]:
        pdfs = sorted(raw_dir.glob(f'fy{fiscal_year}_cip_*.pdf'))
        if not pdfs:
            logger.info(f"Kauaʻi FY{fiscal_year}: no CIP ordinance PDF")
            return []
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber not installed — cannot parse Kauaʻi CIP")
            return []

        pdf_path = pdfs[0]
        allocations: List[CountyAllocation] = []
        current_fund: Optional[str] = None
        prev = ''
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[1:]:           # page 1 is the Section 1 summary
                for line in (page.extract_text() or '').splitlines():
                    s = line.strip()
                    if not s:
                        continue
                    # Fund header: all-caps, no digits (may be split across two
                    # lines, e.g. "PUBLIC ACCESS, … RESOURCES / PRESERVATION FUND").
                    if re.match(r"^[A-Z][A-Z .,&'‘’()/-]*$", s) and not re.search(r'\d', s):
                        joined = f'{prev} {s}'.strip() if ('FUND' in s and 'FUND' not in prev) else s
                        key = _fund_key(s) or _fund_key(joined)
                        if key and ('FUND' in s or 'FUND' in joined or '(cont' in s.lower()):
                            current_fund = key
                        prev = s
                        continue
                    if re.match(r'^(SUB)?TOTAL', s) or 'Appropriation' in s or 'Ordinance' in s:
                        prev = s
                        continue
                    # Project row: a project code (W12345, R24005, NEW, …) then
                    # the three appropriation columns; the last is the total.
                    m = re.search(r'\b([A-Z]{1,3}-?\d{2,4}[A-Z0-9-]*|NEW)\b', s)
                    amount = _last_amount(s)
                    if current_fund and m and amount is not None:
                        name = s[:m.start()].strip() or prev.strip()
                        if name and amount != 0:
                            fund_name = _FUND_NAME[current_fund]
                            allocations.append(CountyAllocation(
                                county=self.county,
                                department_code=re.sub(r'[^a-z0-9]+', '-', _FUND_NAME[current_fund].lower()).strip('-'),
                                department_name=fund_name,
                                section=BudgetSection.CAPITAL_IMPROVEMENT,
                                fund_name=fund_name,
                                fund_category=normalize_fund(fund_name),
                                fiscal_year=fiscal_year,
                                amount=float(amount),
                                program_name=name.title() if name.isupper() else name,
                                source=f'Kauaʻi CIP ordinance ({pdf_path.stem})',
                            ))
                    prev = s

        parsed = sum(a.amount for a in allocations)
        control = KAUAI_CIP_TOTAL.get(fiscal_year)
        pct = f"{(parsed - control) / control * 100:+.2f}% vs published" if control else ''
        logger.info(f"Kauaʻi FY{fiscal_year} CIP: {len(allocations)} projects, ${parsed/1e6:.1f}M {pct}")
        if control and abs(parsed - control) / control > 0.03:
            logger.warning(f"Kauaʻi CIP parse off by >3% (${parsed:,.0f} vs ${control:,})")
        return allocations
