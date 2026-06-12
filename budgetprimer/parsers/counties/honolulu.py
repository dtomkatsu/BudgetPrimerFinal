"""
City & County of Honolulu budget parser.

Source: data.honolulu.gov (Socrata). The operating budget is published as a
line-item dataset at object-code granularity (~12.5k rows):

    department_name, division_name, fund_name, object_code_name,
    department (e.g. "OP_DES"), division (e.g. "DES2901"), fund, object_code,
    fy_2023_actual, fy_2024_actual, fy_2025_budget,
    fy_2026_current_services, fy_2026_budget_issues, fy_2026_proposed_budget

Amounts are strings like "$   8,200", zeros appear as "$   - 0", and
negatives as "$  (1,234)". We aggregate to department × division × fund for
output. CIP is not in the open data portal (PDF ordinance only) and is a
planned follow-up.

Datasets (raw JSON committed under data/raw/counties/honolulu/):
    fy2026: 7sq2-y9vx (proposed)   fy2027: puaw-t6sa (proposed)
"""
from __future__ import annotations
import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Optional

from budgetprimer.models.budget_allocation import BudgetSection
from budgetprimer.models.county_allocation import CountyAllocation, normalize_fund

from .base import BaseCountyParser

logger = logging.getLogger(__name__)

# Socrata dataset ids per fiscal year (proposed budgets; swap in adopted
# dataset ids when data.honolulu.gov publishes them).
DATASET_IDS = {
    2026: '7sq2-y9vx',
    2027: 'puaw-t6sa',
}

# Explicit slugs for Honolulu departments; anything unlisted falls back to a
# generic slug of the name.
DEPT_SLUGS = {
    'Police': 'hpd',
    'Honolulu Police Department': 'hpd',
    'Fire': 'hfd',
    'Honolulu Fire Department': 'hfd',
    'Emergency Services': 'hesd',
    'Emergency Management': 'dem',
    'Budget and Fiscal Services': 'bfs',
    'Community Services': 'dcs',
    'Corporation Counsel': 'cor',
    'Customer Services': 'csd',
    'Design and Construction': 'ddc',
    'Enterprise Services': 'des',
    'Environmental Services': 'env',
    'Facility Maintenance': 'dfm',
    'Human Resources': 'dhr',
    'Information Technology': 'dit',
    'Land Management': 'dlm',
    'Mayor': 'mayor',
    'Managing Director': 'md',
    'Medical Examiner': 'med',
    'Parks and Recreation': 'dpr',
    'Planning and Permitting': 'dpp',
    'Prosecuting Attorney': 'pat',
    'Transportation Services': 'dts',
    'City Council': 'council',
    'City Clerk': 'clerk',
    'City Auditor': 'auditor',
    'Council Services': 'councilsvc',
    'Royal Hawaiian Band': 'rhb',
    'Ocean Safety': 'ocean',
}


def slugify_department(name: str) -> str:
    if name in DEPT_SLUGS:
        return DEPT_SLUGS[name]
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def clean_amount(value) -> Optional[float]:
    """Parse Socrata amount strings like "$   8,200", "$   - 0", "$ (1,234)".

    Returns None for blank/unparseable values (callers treat None as 0 when
    aggregating but can distinguish missing data if needed).
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    negative = '(' in s and ')' in s
    s = re.sub(r'[$,()\s]', '', s)
    # Zeros come through as "- 0" → "-0"; bare "-" means blank
    if s in ('', '-'):
        return None
    try:
        amount = float(s)
    except ValueError:
        return None
    if negative:
        amount = -abs(amount)
    return amount


class HonoluluParser(BaseCountyParser):
    county = 'honolulu'
    source_label = 'FY2026 Proposed Operating Budget · data.honolulu.gov'
    source_url = 'https://data.honolulu.gov/d/7sq2-y9vx'
    # The open-data line items cover executive departments only (~$2.3B of the
    # ~$3.9B total operating budget). Debt service, employee benefits/
    # provisions, the legislative branch, and CIP appear only in the budget
    # ordinance PDFs (Ord. 25-38 / 25-39).
    coverage_note = (
        "Executive departments' operating budget only — excludes debt service, "
        "employee benefits and provisions, the legislative branch, and capital "
        "improvements, which are published only in the budget ordinance PDFs."
    )

    def parse(self, raw_dir: Path, fiscal_year: int) -> List[CountyAllocation]:
        dataset_id = DATASET_IDS.get(fiscal_year)
        if not dataset_id:
            logger.warning(f"No Honolulu dataset known for FY{fiscal_year}")
            return []

        raw_file = raw_dir / f'fy{fiscal_year}_operating_{dataset_id}.json'
        if not raw_file.exists():
            logger.warning(f"Missing raw file {raw_file} — run scripts/fetch_county_budgets.py")
            return []

        with open(raw_file) as f:
            records = json.load(f)

        amount_col = f'fy_{fiscal_year}_proposed_budget'

        # Aggregate object-code rows up to department × division × fund
        totals: dict = defaultdict(float)
        names: dict = {}
        skipped = 0
        for rec in records:
            amount = clean_amount(rec.get(amount_col))
            if amount is None:
                skipped += 1
                continue
            dept = (rec.get('department_name') or '').strip()
            division = (rec.get('division_name') or '').strip()
            fund = (rec.get('fund_name') or '').strip()
            if not dept:
                skipped += 1
                continue
            key = (dept, division, fund)
            totals[key] += amount
            names[key] = (dept, division, fund)

        allocations: List[CountyAllocation] = []
        for (dept, division, fund), amount in totals.items():
            if amount == 0:
                continue
            allocations.append(CountyAllocation(
                county=self.county,
                department_code=slugify_department(dept),
                department_name=dept,
                section=BudgetSection.OPERATING,
                fund_name=fund or 'Unspecified',
                fund_category=normalize_fund(fund),
                fiscal_year=fiscal_year,
                amount=amount,
                program_name=division or None,
                source=f'data.honolulu.gov/{dataset_id}',
            ))

        logger.info(
            f"Honolulu FY{fiscal_year}: {len(records)} raw rows → "
            f"{len(allocations)} dept×division×fund allocations "
            f"({skipped} rows without amounts skipped)"
        )
        return allocations
