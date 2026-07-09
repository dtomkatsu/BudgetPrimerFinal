"""
County of Kauaʻi budget parser.

Kauaʻi publishes its budget as two ordinance PDFs per year (operating and
capital). Unlike Honolulu's scanned ordinance, these are digital text PDFs.

**Capital budget (CIP)** — lists projects grouped by fund with three columns:
Appropriation Balance (carryover), Proposed Budget Ordinance (new appropriation),
and Appropriation Balance After Ordinance. The last column is the total
appropriation for the year and is what the ordinance's own Section 1 fund summary
totals; we use it as each project's amount, reconciling to the published "TOTAL
ALL FUNDS" within ~0.1%.

**Operating budget** — published as a ~280-page account-level preparation
worksheet (account = ``FUND-ORG-OBJECT``, e.g. ``001-0101-512.01-01``). Rather
than sum thousands of noisy object lines, we read the worksheet's own subtotal
hierarchy directly: a leading ``*`` is a program/division subtotal, ``**`` a
department total, and ``***`` a fund total. The adopted figure is the rightmost
column (``COUNCIL REVIEW``), read by word x-position. Programs are buffered and
attached to the ``**`` department that closes them; the fund comes from the
account-number prefix. Internally this reconciles exactly — sum of ``*`` = sum of
``**`` = sum of ``***`` = the published all-funds operating total (FY26
$335,329,600; FY27 $355,735,100).

Raw files (committed under data/raw/counties/kauai/):
    fy2026: operating B-2025-905, cip B-2025-906
    fy2027: operating B-2026-917, cip B-2026-918
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

# ---- Operating worksheet parsing -------------------------------------------

# Account number on a detail line: FUND-ORG-OBJECT.SUB-SUB (e.g. 001-0101-512.01-01)
_OP_ACCT_RE = re.compile(r'^(\d{3})-(\d{4})-\d{3}\.\d{2}-\d{2}\b')

# Published total operating appropriation (sum of the *** fund totals), per year.
KAUAI_OP_TOTAL = {2026: 335329600, 2027: 355735100}


def _op_amount(tok: str) -> Optional[int]:
    """Parse a worksheet money token; trailing '-' marks a negative (credit)."""
    t = tok.replace(',', '')
    neg = t.endswith('-')
    t = t.strip('-')
    if not t.isdigit():
        return None
    return -int(t) if neg else int(t)


def _titlecase(s: str) -> str:
    """Title-case an ALL-CAPS ordinance label for display, fixing possessives."""
    return re.sub(r"'S\b", "'s", s.title()) if s else s


def _slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


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
    source_label = 'Operating & Capital Budget Ordinances · kauai.gov'
    source_url = 'https://www.kauai.gov/Government/Departments-Agencies/Finance/Budget-Division'
    coverage_note = (
        "Operating budget by department and program (adopted COUNCIL REVIEW "
        "column of the County operating ordinance worksheet) plus the capital "
        "improvement program from the capital budget ordinance (total "
        "appropriation including carryover balances)."
    )

    def parse(self, raw_dir: Path, fiscal_year: int) -> List[CountyAllocation]:
        return self.parse_operating(raw_dir, fiscal_year) + \
            self.parse_cip(raw_dir, fiscal_year)

    def parse_operating(self, raw_dir: Path, fiscal_year: int) -> List[CountyAllocation]:
        pdfs = sorted(raw_dir.glob(f'fy{fiscal_year}_operating_*.pdf'))
        if not pdfs:
            logger.info(f"Kauaʻi FY{fiscal_year}: no operating ordinance PDF")
            return []
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber not installed — cannot parse Kauaʻi operating")
            return []
        from collections import defaultdict

        pdf_path = pdfs[0]
        fund_names: dict = {}                # '001' -> 'General Fund'
        records: list = []                   # (fund_num, dept_name, program|None, amount)
        cur_fund: Optional[str] = None
        pending: list = []                   # (program_name, amount) since last **

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                rows = defaultdict(list)
                for w in page.extract_words():
                    rows[round(w['top'])].append(w)
                for top in sorted(rows):
                    ws = sorted(rows[top], key=lambda w: w['x0'])
                    # Detail account line tells us which fund we're in.
                    acct = _OP_ACCT_RE.match(' '.join(w['text'] for w in ws).strip())
                    if acct:
                        cur_fund = acct.group(1)
                        continue
                    lead = ws[0]
                    if lead['text'] not in ('*', '**', '***') or lead['x0'] > 60:
                        continue
                    # Name precedes the four right-aligned columns; the adopted
                    # amount is the rightmost (COUNCIL REVIEW), by x1 position.
                    council = None
                    best_x1 = -1.0
                    name_toks: list = []
                    for w in ws[1:]:
                        v = _op_amount(w['text'])
                        if v is None:
                            if council is None:
                                name_toks.append(w['text'])
                        elif w['x1'] > best_x1:
                            best_x1, council = w['x1'], v
                    if council is None:
                        continue
                    name = ' '.join(name_toks).strip()
                    if lead['text'] == '***':
                        if cur_fund:
                            fund_names[cur_fund] = _titlecase(name)
                    elif lead['text'] == '**':
                        if pending:
                            for pn, pv in pending:
                                records.append((cur_fund, name, pn, pv))
                            diff = council - sum(pv for _, pv in pending)
                            if abs(diff) > 1:    # no-silent-failure remainder guard
                                records.append((cur_fund, name, 'Other', diff))
                        else:
                            records.append((cur_fund, name, None, council))
                        pending = []
                    else:  # '*'
                        pending.append((name, council))

        allocations: List[CountyAllocation] = []
        for fund_num, dept_name, prog_name, amount in records:
            fund_name = fund_names.get(fund_num, f'Fund {fund_num}')
            dept_disp = _titlecase(dept_name)
            allocations.append(CountyAllocation(
                county=self.county,
                department_code=_slug(dept_disp),
                department_name=dept_disp,
                section=BudgetSection.OPERATING,
                fund_name=fund_name,
                fund_category=normalize_fund(fund_name),
                fiscal_year=fiscal_year,
                amount=float(amount),
                program_name=_titlecase(prog_name) if prog_name else None,
                source=f'Kauaʻi operating ordinance ({pdf_path.stem})',
            ))

        parsed = sum(a.amount for a in allocations)
        control = KAUAI_OP_TOTAL.get(fiscal_year)
        pct = f"{(parsed - control) / control * 100:+.2f}% vs published" if control else ''
        logger.info(f"Kauaʻi FY{fiscal_year} operating: {len(allocations)} program rows, "
                    f"{len({a.department_code for a in allocations})} departments, "
                    f"${parsed/1e6:.1f}M {pct}")
        if control and abs(parsed - control) > max(1000, control * 0.005):
            logger.warning(f"Kauaʻi operating parse off (${parsed:,.0f} vs ${control:,})")
        return allocations

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
