"""Tests for the Maui county budget parser (FY2026 Mayor's Proposed)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from budgetprimer.models.budget_allocation import BudgetSection
from budgetprimer.models.county_allocation import CountyFundCategory
from budgetprimer.parsers.counties.maui import (
    MAUI_CIP_FUNDS,
    MAUI_CIP_TOTAL,
    MAUI_OP_TOTAL,
    MauiParser,
    _dept_title,
    _money_to_dollars,
)

RAW_DIR = Path(__file__).parent.parent / 'data' / 'raw' / 'counties' / 'maui'


class TestMoneyToDollars:
    def test_thousands_decimal(self):
        assert _money_to_dollars("$12,708.1") == pytest.approx(12_708_100)

    def test_parenthesized_negative(self):
        assert _money_to_dollars("($17,072.9)") == pytest.approx(-17_072_900)

    def test_grand_total(self):
        assert _money_to_dollars("$1,226,165.2") == pytest.approx(1_226_165_200)


class TestDeptTitle:
    def test_small_words_lowercased(self):
        assert _dept_title("FIRE AND PUBLIC SAFETY") == "Fire and Public Safety"
        assert _dept_title("OFFICE OF THE MAYOR") == "Office of the Mayor"


class TestFundMap:
    def test_known_codes_cover_figure_5_8(self):
        # The 16 fund-type codes seen on the CIP project sheets.
        for code in ('GF', 'GB', 'FD', 'GE', 'HF', 'ST', 'WF', 'WU', 'WR',
                     'OG', 'SW', 'PA', 'EP', 'SRF', 'LBF', 'OT'):
            assert code in MAUI_CIP_FUNDS


# Integration: requires the 29 MB program-budget PDF. Skips cleanly when it is
# absent (e.g. a checkout that hasn't run fetch_county_budgets).
@pytest.fixture(scope="module")
def maui_allocations():
    pytest.importorskip("pdfplumber")
    if not list(RAW_DIR.glob('fy2026_program_budget*.pdf')):
        pytest.skip("Maui program budget PDF not present")
    return MauiParser().parse(RAW_DIR, 2026)


def test_operating_reconciles(maui_allocations):
    op = [a for a in maui_allocations if a.section == BudgetSection.OPERATING]
    assert len(op) == 24
    total = sum(a.amount for a in op)
    # Within source rounding (Figure 2-8 is in thousands).
    assert abs(total - MAUI_OP_TOTAL) < 5_000


def test_cip_reconciles(maui_allocations):
    cip = [a for a in maui_allocations if a.section == BudgetSection.CAPITAL_IMPROVEMENT]
    total = sum(a.amount for a in cip)
    assert abs(total - MAUI_CIP_TOTAL) < 5_000           # $1000s rounding
    assert all(a.program_name and a.program_name != '(unnamed project)' for a in cip)
    assert all(a.fund_category in CountyFundCategory for a in cip)


def test_only_fy2026_published():
    assert MauiParser().parse(RAW_DIR, 2027) == []
