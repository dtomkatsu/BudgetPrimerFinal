"""Tests for the Hawaiʻi county budget parser (Bill 135, by fund)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from budgetprimer.models.budget_allocation import BudgetSection
from budgetprimer.parsers.counties.hawaii import (
    HAWAII_FUNDS,
    HAWAII_OP_TOTAL,
    HawaiiParser,
)

RAW_DIR = Path(__file__).parent.parent / 'data' / 'raw' / 'counties' / 'hawaii'


class TestFundList:
    def test_fourteen_distinct_funds(self):
        names = {name for _, name in HAWAII_FUNDS}
        assert len(names) == 14

    def test_excise_before_general(self):
        # "General Excise" must be matched before the bare "general" keyword.
        keys = [kw for kw, _ in HAWAII_FUNDS]
        assert keys.index('generalexcise') < keys.index('general')


class TestRowLabel:
    def test_operating_table_relabelled_to_fund(self):
        assert HawaiiParser.operating_row_label == 'Fund'


# Integration: the Bill 135 operating PDF is committed, so these run in CI.
@pytest.mark.parametrize("fy", [2026, 2027])
def test_by_fund_reconciles(fy):
    pytest.importorskip("pdfplumber")
    if not list(RAW_DIR.glob('*operating*.pdf')):
        pytest.skip("Hawaiʻi operating PDF not present")

    allocations = HawaiiParser().parse(RAW_DIR, fy)
    assert len(allocations) == 14
    assert all(a.section == BudgetSection.OPERATING for a in allocations)
    assert all(a.program_name is None for a in allocations)   # fund-level only

    total = sum(a.amount for a in allocations)
    # Within thousands-rounding of the published OPERATING BUDGET BY FUND total.
    assert abs(total - HAWAII_OP_TOTAL[fy]) < 2_000


def test_unsupported_year_returns_empty():
    assert HawaiiParser().parse(RAW_DIR, 2025) == []
