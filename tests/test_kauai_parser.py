"""Tests for the Kauaʻi county budget parser (operating worksheet + CIP)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from budgetprimer.models.budget_allocation import BudgetSection
from budgetprimer.parsers.counties.kauai import (
    KAUAI_OP_TOTAL,
    KauaiParser,
    _op_amount,
    _slug,
    _titlecase,
)

RAW_DIR = Path(__file__).parent.parent / 'data' / 'raw' / 'counties' / 'kauai'


class TestOpAmount:
    def test_plain(self):
        assert _op_amount("1,313,466") == 1_313_466

    def test_trailing_minus_is_negative(self):
        # The worksheet shows credits (e.g. cost-recovery) with a trailing '-'.
        assert _op_amount("1,444,886-") == -1_444_886

    def test_non_numeric(self):
        assert _op_amount("ADMINISTRATION") is None
        assert _op_amount("512.01-01") is None


class TestTitlecase:
    def test_possessive(self):
        assert _titlecase("MAYOR'S OFFICE") == "Mayor's Office"

    def test_fund_initials_and_ampersand(self):
        assert _titlecase("G.E. TAX FUND") == "G.E. Tax Fund"
        assert _titlecase("PARKS & RECREATION") == "Parks & Recreation"


class TestSlug:
    def test_basic(self):
        assert _slug("Public Works") == "public-works"
        assert _slug("Mayor's Office") == "mayor-s-office"


# Integration: the operating ordinance PDFs are committed, so we can assert the
# parse reconciles exactly to the published all-funds operating appropriation
# (the sum of the worksheet's own *** fund totals).
@pytest.mark.parametrize("fy", [2026, 2027])
def test_operating_reconciles_to_published_total(fy):
    pytest.importorskip("pdfplumber")
    pdfs = list(RAW_DIR.glob(f'fy{fy}_operating_*.pdf'))
    if not pdfs:
        pytest.skip(f"FY{fy} operating PDF not present")

    allocations = KauaiParser().parse_operating(RAW_DIR, fy)
    assert allocations, "expected operating allocations"
    assert all(a.section == BudgetSection.OPERATING for a in allocations)

    total = sum(a.amount for a in allocations)
    # Exact reconciliation — the subtotal hierarchy is internally consistent.
    assert round(total) == KAUAI_OP_TOTAL[fy]

    # Every program row carries a real department and fund.
    assert all(a.department_name.strip() for a in allocations)
    assert all(a.fund_name and not a.fund_name.startswith("Fund ") for a in allocations)
