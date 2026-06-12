"""Tests for the Honolulu county budget parser and fund normalization."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from budgetprimer.models.budget_allocation import BudgetSection
from budgetprimer.models.county_allocation import CountyFundCategory, normalize_fund
from budgetprimer.parsers.counties.honolulu import HonoluluParser, clean_amount, slugify_department


class TestCleanAmount:
    def test_plain_amount(self):
        assert clean_amount("$   8,200") == 8200.0

    def test_zero_dash(self):
        # Socrata encodes zero as "$   - 0"
        assert clean_amount("$   - 0") == 0.0

    def test_parenthesized_negative(self):
        assert clean_amount("$ (1,234)") == -1234.0

    def test_blank_and_none(self):
        assert clean_amount("") is None
        assert clean_amount(None) is None
        assert clean_amount("$ -") is None

    def test_numeric_passthrough(self):
        assert clean_amount(500) == 500.0
        assert clean_amount(12.5) == 12.5

    def test_garbage(self):
        assert clean_amount("N/A") is None

    def test_millions(self):
        assert clean_amount("$ 12,345,678") == 12345678.0


class TestNormalizeFund:
    def test_general(self):
        assert normalize_fund("General Fund") == CountyFundCategory.GENERAL

    def test_special_enterprise(self):
        assert normalize_fund("Sewer Fund") == CountyFundCategory.SPECIAL
        assert normalize_fund("Highway Fund") == CountyFundCategory.SPECIAL
        assert normalize_fund("Bus Transportation Fund") == CountyFundCategory.SPECIAL
        assert normalize_fund("Special Events Fund") == CountyFundCategory.SPECIAL

    def test_federal(self):
        assert normalize_fund("Federal Grants Fund") == CountyFundCategory.FEDERAL
        assert normalize_fund("Community Development Fund") == CountyFundCategory.FEDERAL
        assert normalize_fund("Section 8") == CountyFundCategory.FEDERAL

    def test_bond(self):
        assert normalize_fund("General Improvement Bond Fund") == CountyFundCategory.BOND

    def test_trust_other(self):
        assert normalize_fund("Real Property Trust Fund") == CountyFundCategory.TRUST_OTHER
        assert normalize_fund("") == CountyFundCategory.TRUST_OTHER
        assert normalize_fund("Mystery Fund") == CountyFundCategory.TRUST_OTHER


class TestSlugify:
    def test_known_departments(self):
        assert slugify_department("Police") == "hpd"
        assert slugify_department("Environmental Services") == "env"

    def test_fallback(self):
        assert slugify_department("Some New Department") == "some-new-department"


class TestHonoluluParser:
    @pytest.fixture
    def raw_dir(self, tmp_path):
        records = [
            # Two object codes in the same dept/division/fund — must aggregate
            {"department_name": "Police", "division_name": "Patrol",
             "fund_name": "General Fund", "object_code_name": "Salaries",
             "fy_2026_proposed_budget": "$   1,000,000"},
            {"department_name": "Police", "division_name": "Patrol",
             "fund_name": "General Fund", "object_code_name": "Equipment",
             "fy_2026_proposed_budget": "$   250,000"},
            # Different fund within the same department
            {"department_name": "Police", "division_name": "Patrol",
             "fund_name": "Federal Grants Fund", "object_code_name": "Grants",
             "fy_2026_proposed_budget": "$   50,000"},
            # Zero-only group should be dropped
            {"department_name": "Fire", "division_name": "Admin",
             "fund_name": "General Fund", "object_code_name": "Nothing",
             "fy_2026_proposed_budget": "$   - 0"},
        ]
        d = tmp_path / "honolulu"
        d.mkdir()
        (d / "fy2026_operating_7sq2-y9vx.json").write_text(json.dumps(records))
        return d

    def test_parse_aggregates_and_maps(self, raw_dir):
        allocations = HonoluluParser().parse(raw_dir, 2026)
        assert len(allocations) == 2  # zero-total Fire group dropped

        general = next(a for a in allocations if a.fund_name == "General Fund")
        assert general.amount == 1_250_000.0
        assert general.department_code == "hpd"
        assert general.program_name == "Patrol"
        assert general.section == BudgetSection.OPERATING
        assert general.fund_category == CountyFundCategory.GENERAL
        assert general.fiscal_year == 2026

        federal = next(a for a in allocations if a.fund_name == "Federal Grants Fund")
        assert federal.fund_category == CountyFundCategory.FEDERAL
        assert federal.amount == 50_000.0

    def test_missing_raw_file(self, tmp_path):
        assert HonoluluParser().parse(tmp_path, 2026) == []

    def test_unknown_fiscal_year(self, raw_dir):
        assert HonoluluParser().parse(raw_dir, 1999) == []
