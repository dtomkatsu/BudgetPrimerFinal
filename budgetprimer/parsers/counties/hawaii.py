"""
County of Hawaiʻi budget parser.

Source: the FY2026-2027 **Proposed Operating Budget** (Bill 135), a 82-page PDF
from the County's Laserfiche portal (records.hawaiicounty.gov). The detailed
schedules are a scanned / OCR'd document — department subtotal lines carry
intermittent OCR corruption in their figures (e.g. the ~$168M Interdepartmental
line reads "168,870,Sbb"), and the roll-up structure double counts, so
department-level totals can't be parsed reliably without shipping wrong numbers.

What IS clean and self-reconciling is the book's own **OPERATING BUDGET BY FUND**
summary table, which lists all 14 funds with two columns — the FY2025-26 adopted
Budget and the FY2026-27 Proposed budget (in thousands). We parse that table and
present Hawaiʻi at the FUND level:
  • FY2026 ← "FY25-26 Budget"  (adopted) — sums to the published $953,413,869
  • FY2027 ← "FY26-27 Proposed"          — sums to the published $966,891,661
Both reconcile within thousands-rounding. Each fund is emitted as one operating
row; the web view labels the operating table "Fund" (operating_row_label) and
the coverage note explains why department detail is absent. Capital improvement
projects are published as a separate volume and are not included here.

Raw file (committed under data/raw/counties/hawaii/):
    fy2026-27: operating Bill 135 (Proposed)
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

# Published control totals (Bill 135 OPERATING BUDGET BY FUND), per year.
HAWAII_OP_TOTAL = {2026: 953413869, 2027: 966891661}

# The 14 funds in the OPERATING BUDGET BY FUND table, matched by a space-removed
# keyword (OCR glues words, e.g. "GeneralFund"). Order matters: the more
# specific "General Excise" must be tried before the bare "general".
HAWAII_FUNDS: List[Tuple[str, str]] = [
    ('generalexcise', 'General Excise Tax Fund'),
    ('general', 'General Fund'),
    ('highway', 'Highway Fund'),
    ('sewer', 'Sewer Fund'),
    ('rentalenforcement', 'Short Term Vacation Rental Enforcement Fund'),
    ('enforcement', 'Short Term Vacation Rental Enforcement Fund'),
    ('cemetery', 'Cemetery Fund'),
    ('bikeway', 'Bikeway Fund'),
    ('beautification', 'Beautification Fund'),
    ('vehicledisposal', 'Vehicle Disposal Fund'),
    ('solidwaste', 'Solid Waste Fund'),
    ('golf', 'Golf Course Fund'),
    ('geothermalroyalty', 'Geothermal Royalty Fund'),
    ('housing', 'Housing Fund'),
    ('geothermalasset', 'Geothermal Asset Fund'),
]

# Column index of each fiscal year in the by-fund table (FY25-26 then FY26-27).
_YEAR_COL = {2026: 0, 2027: 1}

_NUM = re.compile(r'\b\d[\d,]*\b')


def _slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


class HawaiiParser(BaseCountyParser):
    county = 'hawaii'
    source_label = 'FY2026-27 Proposed Operating Budget (Bill 135) · hawaiicounty.gov'
    source_url = ('https://records.hawaiicounty.gov/WebLink/Browse.aspx'
                  '?id=65&dbid=1')
    # The operating "departments" are funds (see module docstring); the web view
    # labels the table accordingly.
    operating_row_label = 'Fund'
    coverage_note = (
        "Operating budget by fund, from the County's published OPERATING BUDGET "
        "BY FUND summary. FY2026 is the FY2025-26 adopted budget; FY2027 is the "
        "FY2026-27 proposed budget. The detailed budget is a scanned/OCR'd "
        "document, so department-level figures are not broken out here. Capital "
        "improvement projects are published as a separate volume and are not "
        "included."
    )

    def parse(self, raw_dir: Path, fiscal_year: int) -> List[CountyAllocation]:
        if fiscal_year not in _YEAR_COL:
            return []
        pdfs = sorted(raw_dir.glob('*operating*.pdf'))
        if not pdfs:
            logger.info(f"Hawaiʻi FY{fiscal_year}: no operating budget PDF")
            return []
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber not installed — cannot parse Hawaiʻi")
            return []

        col = _YEAR_COL[fiscal_year]
        # The OPERATING BUDGET BY FUND table sits on the budget-message pages.
        with pdfplumber.open(pdfs[0]) as pdf:
            text = '\n'.join((pdf.pages[i].extract_text() or '')
                             for i in range(min(8, len(pdf.pages))))

        # Only parse rows inside the table — gate on its column header
        # ("FUND Budget Proposed …") so the budget-message prose above it (which
        # also mentions funds and dollar figures) can't pollute the match.
        seen: Dict[str, int] = {}
        in_table = False
        for ln in text.splitlines():
            low = ln.lower()
            stripped = low.strip()
            if not in_table:
                # The table's column header line, e.g. "FUND Budget Proposed …".
                if stripped.startswith('fund') and 'proposed' in low:
                    in_table = True
                continue
            if stripped.startswith(('total', 'section', 'part ')):
                break
            spaceless = low.replace(' ', '')
            nums = [int(x.replace(',', '')) for x in _NUM.findall(ln)]
            if len(nums) < 2:
                continue
            for kw, name in HAWAII_FUNDS:
                if kw in spaceless and name not in seen:
                    seen[name] = nums[col] * 1000     # table is in thousands
                    break
            if len(seen) == len(set(n for _, n in HAWAII_FUNDS)):
                break

        allocations: List[CountyAllocation] = []
        for name, amount in seen.items():
            if amount == 0:
                continue
            allocations.append(CountyAllocation(
                county=self.county,
                department_code=_slug(name),
                department_name=name,
                section=BudgetSection.OPERATING,
                fund_name=name,
                fund_category=normalize_fund(name),
                fiscal_year=fiscal_year,
                amount=float(amount),
                program_name=None,
                source=f'Hawaiʻi Bill 135 OPERATING BUDGET BY FUND (FY{fiscal_year} col)',
            ))

        parsed = sum(a.amount for a in allocations)
        control = HAWAII_OP_TOTAL.get(fiscal_year)
        pct = f"{(parsed - control) / control * 100:+.3f}% vs published" if control else ''
        logger.info(f"Hawaiʻi FY{fiscal_year} operating: {len(allocations)} funds, "
                    f"${parsed/1e6:.1f}M {pct}")
        if control and abs(parsed - control) > max(2000, control * 0.005):
            logger.warning(f"Hawaiʻi operating parse off (${parsed:,.0f} vs ${control:,})")
        return allocations
