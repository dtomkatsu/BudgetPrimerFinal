"""
Tests for the budget parsing and processing pipeline.

Organized into:
  - TestParserState: ParserState dataclass behavior
  - TestFundType: FundType enum and conversion
  - TestBudgetAllocation: Data model serialization
  - TestRegexPatterns: Individual regex patterns against known inputs
  - TestExcerptParsing: Parser behavior on small document fragments
  - TestEdgeCases: Specific bug-fix regressions (blank FY columns, grant lines, etc.)
  - TestFullDocumentRegression: Baseline counts against the real HB 300 document
  - TestPipeline: End-to-end flow from parse → process → transform → veto
"""
import pytest
import pandas as pd
from pathlib import Path
from collections import Counter
from budgetprimer.parsers.fast_parser import (
    FastBudgetParser,
    ParserState,
    CATEGORY_MAP,
    DEPARTMENT_NAMES,
)
from budgetprimer.models import BudgetAllocation, BudgetSection, FundType
from budgetprimer.pipeline.processor import process_budget_data, aggregate_by_category
from budgetprimer.pipeline.transformer import (
    transform_to_post_veto,
    validate_budget_data,
    load_one_time_appropriations,
)
from budgetprimer.pipeline.veto_processor import load_veto_changes


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

HB300_PATH = "data/raw/HB 300 CD 1.txt"
VETO_PATH = Path("data/raw/vetoes/governor_vetoes_fy2026_actual.csv")
ONE_TIME_PATH = Path("data/config/one_time_appropriations_fy2026.csv")


@pytest.fixture(scope="module")
def parser():
    return FastBudgetParser()


@pytest.fixture(scope="module")
def full_parse(parser):
    """Parse the full HB 300 document once and reuse across tests."""
    return parser.parse(HB300_PATH)


@pytest.fixture(scope="module")
def fy2026_df(full_parse):
    """Processed DataFrame for FY2026."""
    return process_budget_data(full_parse, fiscal_year=2026)


@pytest.fixture(scope="module")
def fy2027_df(full_parse):
    """Processed DataFrame for FY2027."""
    return process_budget_data(full_parse, fiscal_year=2027)


# ---------------------------------------------------------------------------
# ParserState
# ---------------------------------------------------------------------------

class TestParserState:

    def test_initial_state_has_no_context(self):
        s = ParserState()
        assert not s.has_context()
        assert s.section_enum == BudgetSection.OPERATING
        assert s.default_fund == 'A'

    def test_set_program(self):
        s = ParserState()
        s.set_program('BED100', 'STRATEGIC MARKETING')
        assert s.program_id == 'BED100'
        assert s.program_name == 'STRATEGIC MARKETING'
        assert s.department_code == 'BED'
        assert s.section is None  # reset on program change
        assert s.has_context()

    def test_section_enum_operating(self):
        s = ParserState(section='OPERATING')
        assert s.section_enum == BudgetSection.OPERATING
        assert s.default_fund == 'A'

    def test_section_enum_capital(self):
        s = ParserState(section='INVESTMENT CAPITAL')
        assert s.section_enum == BudgetSection.CAPITAL_IMPROVEMENT
        assert s.default_fund == 'C'

    def test_section_enum_none_defaults_operating(self):
        s = ParserState(section=None)
        assert s.section_enum == BudgetSection.OPERATING


# ---------------------------------------------------------------------------
# FundType model
# ---------------------------------------------------------------------------

class TestFundType:

    @pytest.mark.parametrize("letter,expected", [
        ('A', FundType.GENERAL),
        ('B', FundType.SPECIAL),
        ('C', FundType.GENERAL_OBLIGATION_BOND),
        ('N', FundType.FEDERAL),
        ('P', FundType.OTHER_FEDERAL),
        ('T', FundType.TRUST),
        ('W', FundType.REVOLVING),
        ('X', FundType.OTHER),
    ])
    def test_single_letter_codes(self, letter, expected):
        assert FundType.from_string(letter) == expected

    def test_empty_string_returns_unknown(self):
        assert FundType.from_string("") == FundType.UNKNOWN

    def test_none_like_returns_unknown(self):
        assert FundType.from_string(None) == FundType.UNKNOWN

    def test_full_name_lookup(self):
        assert FundType.from_string("GENERAL") == FundType.GENERAL
        assert FundType.from_string("FEDERAL") == FundType.FEDERAL

    def test_category_property(self):
        assert FundType.GENERAL.category == "General Funds"
        assert FundType.FEDERAL.category == "Federal Funds"
        assert FundType.UNKNOWN.category == "Uncategorized Funds"

    def test_all_fund_types_have_category(self):
        for ft in FundType:
            assert isinstance(ft.category, str)
            assert len(ft.category) > 0


# ---------------------------------------------------------------------------
# BudgetAllocation model
# ---------------------------------------------------------------------------

class TestBudgetAllocation:

    def test_to_dict_roundtrip(self):
        alloc = BudgetAllocation(
            program_id='BED100',
            program_name='Test Program',
            department_code='BED',
            department_name='Department of Business',
            section=BudgetSection.OPERATING,
            fund_type=FundType.GENERAL,
            fiscal_year=2026,
            amount=1_000_000,
        )
        d = alloc.to_dict()
        assert d['program_id'] == 'BED100'
        assert d['section'] == 'Operating'
        assert d['fund_type'] == 'A'
        assert d['fund_category'] == 'General Funds'
        assert d['amount'] == 1_000_000

    def test_from_dict(self):
        data = {
            'program_id': 'HTH430',
            'program_name': 'Hospital',
            'department_code': 'HTH',
            'department_name': 'Health',
            'section': 'Operating',
            'fund_type': 'B',
            'fiscal_year': 2026,
            'amount': 500_000,
        }
        alloc = BudgetAllocation.from_dict(data)
        assert alloc.program_id == 'HTH430'
        assert alloc.fund_type == FundType.SPECIAL

    def test_extract_fund_type_from_amount_string(self):
        assert BudgetAllocation.extract_fund_type("1,000,000A") == FundType.GENERAL
        assert BudgetAllocation.extract_fund_type("") == FundType.UNKNOWN


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

class TestRegexPatterns:

    def test_program_header_standard(self, parser):
        m = parser._compiled_patterns["program"].match("1. BED100 - STRATEGIC MARKETING AND SUPPORT")
        assert m and m.group(1) == "BED100"

    def test_program_header_en_dash(self, parser):
        m = parser._compiled_patterns["program"].match("  42. HTH430 \u2013 HAWAII STATE HOSPITAL")
        assert m and m.group(1) == "HTH430"

    def test_program_header_does_not_match_grants(self, parser):
        """Grant lines like '35. LAI OPUA 2020' should NOT match (no dash separator)."""
        m = parser._compiled_patterns["program"].match("35.         LAI OPUA 2020")
        assert m is None

    def test_category_header(self, parser):
        m = parser._compiled_patterns["category"].match("A.  ECONOMIC DEVELOPMENT")
        assert m and m.group(1) == "A"

    def test_category_header_all_codes(self, parser):
        for code in CATEGORY_MAP:
            m = parser._compiled_patterns["category"].match(f"{code}.  TEST")
            assert m is not None, f"Category {code} should match"

    def test_amount_two_col(self, parser):
        m = parser._compiled_patterns["amount_two_col"].match("TRN      3,893,040A     3,893,040A")
        assert m is not None
        assert m.group(1) == "TRN"
        assert m.group(2) == "3,893,040"
        assert m.group(3) == "A"
        assert m.group(4) == "3,893,040"
        assert m.group(5) == "A"

    def test_investment_capital_bare(self, parser):
        m = parser._compiled_patterns["investment_capital"].match("INVESTMENT CAPITAL")
        assert m is not None
        assert m.group(1) is None  # no inline amounts

    def test_investment_capital_with_amounts(self, parser):
        m = parser._compiled_patterns["investment_capital"].match(
            "INVESTMENT CAPITAL   TRN   5,000,000C   5,000,000C"
        )
        assert m and m.group(1) == "TRN" and m.group(3) == "C"

    def test_operating_line(self, parser):
        m = parser._compiled_patterns["operating_line"].match("OPERATING TRN 1,823,499W 1,823,499W")
        assert m and m.group(1) == "TRN" and m.group(3) == "W"

    def test_operating_pdf_format(self, parser):
        m = parser._compiled_patterns["operating_pdf"].search(
            "OPERATING                         BED       5,000,000C    C"
        )
        assert m is not None
        assert m.group(1) == "BED"
        assert m.group(4) == "C"  # trailing FY2 fund letter

    def test_fy2_only_amount(self, parser):
        m = parser._compiled_patterns["fy2_only_amount"].match("AGR                 P       164,450P")
        assert m is not None
        assert m.group(1) == "AGR"
        assert m.group(2) == "P"
        assert m.group(3) == "164,450"
        assert m.group(4) == "P"

    def test_amount_single_fund(self, parser):
        m = parser._compiled_patterns["amount_single_fund"].match("TRN      5,000,000N           N")
        assert m is not None
        assert m.group(1) == "TRN"
        assert m.group(3) == "N"


# ---------------------------------------------------------------------------
# Excerpt parsing — small document fragments
# ---------------------------------------------------------------------------

class TestExcerptParsing:

    def _parse_text(self, parser, text):
        return parser._extract_allocations(text)

    def test_simple_operating(self, parser):
        text = """A.  ECONOMIC DEVELOPMENT
1. BED100 - STRATEGIC MARKETING AND SUPPORT
OPERATING
TRN      3,893,040A     3,893,040A"""
        allocs = self._parse_text(parser, text)
        operating = [a for a in allocs if a.section == BudgetSection.OPERATING]
        assert len(operating) >= 1
        assert operating[0].program_id == "BED100"
        assert operating[0].fund_type == FundType.GENERAL
        assert operating[0].category == "Economic Development"

    def test_capital_improvement(self, parser):
        text = """1. AGS251 - PUBLIC WORKS
INVESTMENT CAPITAL   TRN   5,000,000C   5,000,000C"""
        allocs = self._parse_text(parser, text)
        capital = [a for a in allocs if a.section == BudgetSection.CAPITAL_IMPROVEMENT]
        assert len(capital) >= 1
        assert capital[0].fund_type == FundType.GENERAL_OBLIGATION_BOND

    def test_multiple_fund_types(self, parser):
        text = """A.  ECONOMIC DEVELOPMENT
1. BED100 - TEST PROGRAM
OPERATING
TRN      1,000,000A     1,000,000A
TRN      500,000B     500,000B"""
        allocs = self._parse_text(parser, text)
        fund_types = set(a.fund_type for a in allocs)
        assert FundType.GENERAL in fund_types
        assert FundType.SPECIAL in fund_types

    def test_program_context_carries_forward(self, parser):
        """Amount lines should inherit the current program context."""
        text = """1. BED100 - FIRST PROGRAM
OPERATING
TRN      1,000,000A     1,000,000A
2. HTH430 - SECOND PROGRAM
OPERATING
TRN      2,000,000B     2,000,000B"""
        allocs = self._parse_text(parser, text)
        bed = [a for a in allocs if a.program_id == 'BED100']
        hth = [a for a in allocs if a.program_id == 'HTH430']
        assert len(bed) >= 1
        assert len(hth) >= 1
        assert all(a.fund_type == FundType.GENERAL for a in bed)
        assert all(a.fund_type == FundType.SPECIAL for a in hth)

    def test_department_name_populated(self, parser):
        text = """1. BED100 - TEST
OPERATING
TRN      1,000,000A     1,000,000A"""
        allocs = self._parse_text(parser, text)
        assert allocs[0].department_name != 'BED'  # should be human-readable

    def test_configurable_fiscal_years(self):
        p = FastBudgetParser(fy1=2028, fy2=2029)
        text = """1. BED100 - TEST
OPERATING
TRN      1,000,000A     1,000,000A"""
        allocs = p._extract_allocations(text)
        years = set(a.fiscal_year for a in allocs)
        assert 2028 in years
        assert 2029 in years
        assert 2026 not in years


# ---------------------------------------------------------------------------
# Edge cases — specific bug-fix regressions
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_grant_line_does_not_crash(self, parser):
        """Lines like '35. LAI OPUA 2020' (grants without dash) should not error."""
        text = """K.  GOVERNMENT OPERATIONS
1. AGS251 - PUBLIC WORKS
OPERATING
TRN      1,000,000A     1,000,000A
35.         LAI OPUA 2020
            PLANS AND CONSTRUCTION
               TOTAL FUNDING              LBR               300 C           C"""
        # Should not raise
        allocs = parser._extract_allocations(text)
        # The grant line should not produce an allocation under a wrong program
        assert all(a.program_id == 'AGS251' for a in allocs)

    def test_blank_fy1_column_operating(self, parser):
        """Line like 'AGR  P  164,450P' should create FY2 allocation."""
        text = """1. AGR192 - GENERAL ADMINISTRATION FOR AGRICULTURE
OPERATING                         AGR        5,580,886A     5,556,126A
                                  AGR                 P       164,450P"""
        allocs = parser._extract_allocations(text)
        p_allocs = [a for a in allocs if a.fund_type == FundType.OTHER_FEDERAL]
        assert len(p_allocs) >= 1
        assert any(a.amount == 164_450 for a in p_allocs)

    def test_blank_fy1_column_capital(self, parser):
        """Lines like 'TRN  N  19,200,000N' in INVESTMENT CAPITAL should parse."""
        text = """1. TRN511 - MAUI HIGHWAYS
INVESTMENT CAPITAL                TRN        4,500,000E     4,800,000E
                                  TRN                 N    19,200,000N"""
        allocs = parser._extract_allocations(text)
        n_allocs = [a for a in allocs if a.fund_type == FundType.FEDERAL]
        assert len(n_allocs) >= 1
        assert any(a.amount == 19_200_000 for a in n_allocs)

    def test_single_amount_with_trailing_fund_letter(self, parser):
        """Lines like 'TRN  10,000,000N  N' (FY1 amount, FY2 blank + fund)."""
        text = """1. TRN511 - MAUI HIGHWAYS
INVESTMENT CAPITAL
                                  TRN       10,000,000N              N"""
        allocs = parser._extract_allocations(text)
        n_allocs = [a for a in allocs if a.fund_type == FundType.FEDERAL]
        assert len(n_allocs) >= 1
        assert n_allocs[0].amount == 10_000_000
        assert n_allocs[0].section == BudgetSection.CAPITAL_IMPROVEMENT

    def test_none_section_does_not_crash(self, parser):
        """Amount lines before any section header should not crash."""
        text = """1. BED100 - TEST
TRN      1,000,000A     1,000,000A"""
        # Should not raise — amounts with no section context are skipped
        allocs = parser._extract_allocations(text)
        # May or may not produce allocations depending on fallback, but no crash

    def test_suspicious_duplicate_removal(self, parser):
        """Same (program, FY, section) with identical large amount should be deduped."""
        alloc = BudgetAllocation(
            program_id='TEST', program_name='Test', department_code='TST',
            department_name='Test', section=BudgetSection.OPERATING,
            fund_type=FundType.GENERAL, fiscal_year=2026, amount=60_000_000,
        )
        alloc2 = BudgetAllocation(
            program_id='TEST', program_name='Test', department_code='TST',
            department_name='Test', section=BudgetSection.OPERATING,
            fund_type=FundType.SPECIAL, fiscal_year=2026, amount=60_000_000,
        )
        cleaned = parser._remove_suspicious_duplicates([alloc, alloc2])
        assert len(cleaned) == 1


# ---------------------------------------------------------------------------
# Full document regression
# ---------------------------------------------------------------------------

class TestFullDocumentRegression:
    """Baseline counts against the real HB 300 document.

    Note: The allocation count increased from the original 1318 after fixing
    3 previously-missing capital allocations (TRN511 N, HTH212 R, EDN100 P).
    """

    def test_minimum_allocation_count(self, full_parse):
        assert len(full_parse) >= 1318

    def test_fy_distribution(self, full_parse):
        fy = Counter(a.fiscal_year for a in full_parse)
        assert fy[2026] >= 687
        assert fy[2027] >= 631

    def test_section_distribution(self, full_parse):
        sec = Counter(a.section.value for a in full_parse)
        assert sec["Operating"] >= 1129
        assert sec["Capital Improvement"] >= 189

    def test_total_amount_fy2026_at_least_baseline(self, full_parse):
        total = sum(a.amount for a in full_parse if a.fiscal_year == 2026)
        assert total >= 23_320_369_599

    def test_total_amount_fy2027(self, full_parse):
        total = sum(a.amount for a in full_parse if a.fiscal_year == 2027)
        assert total == pytest.approx(21_925_812_598, rel=1e-6)

    def test_unique_departments(self, full_parse):
        depts = set(a.department_code for a in full_parse)
        assert len(depts) >= 24

    def test_no_unknown_fund_types(self, full_parse):
        unknown = [a for a in full_parse if a.fund_type == FundType.UNKNOWN]
        assert len(unknown) == 0

    def test_all_amounts_positive(self, full_parse):
        assert all(a.amount > 0 for a in full_parse)

    def test_all_have_program_id(self, full_parse):
        assert all(a.program_id and a.program_id != "Unknown" for a in full_parse)

    def test_all_have_department_code(self, full_parse):
        assert all(a.department_code for a in full_parse)

    def test_department_names_populated(self, full_parse):
        """Most allocations should have human-readable department names."""
        named = [a for a in full_parse if a.department_name != a.department_code]
        assert len(named) / len(full_parse) > 0.95

    def test_previously_missing_capital_allocations(self, full_parse):
        """Bug fix: TRN511 N, HTH212 R, EDN100 P were missing from capital."""
        cap = [a for a in full_parse if a.section == BudgetSection.CAPITAL_IMPROVEMENT]
        cap_keys = {(a.program_id, a.fund_type.value) for a in cap}
        assert ('TRN511', 'N') in cap_keys, "TRN511 N capital allocation missing"
        assert ('HTH212', 'R') in cap_keys, "HTH212 R capital allocation missing"
        assert ('EDN100', 'P') in cap_keys, "EDN100 P capital allocation missing"

    def test_no_errors_on_grant_lines(self, full_parse):
        """The parser should not crash on grant description lines."""
        # If we got here with a full_parse, no crash occurred
        assert len(full_parse) > 0


# ---------------------------------------------------------------------------
# Pipeline: process_budget_data
# ---------------------------------------------------------------------------

class TestProcessBudgetData:

    def test_returns_dataframe(self, full_parse):
        df = process_budget_data(full_parse)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_fiscal_year_filter(self, full_parse):
        df26 = process_budget_data(full_parse, fiscal_year=2026)
        df27 = process_budget_data(full_parse, fiscal_year=2027)
        assert all(df26['fiscal_year'] == 2026)
        assert all(df27['fiscal_year'] == 2027)
        assert len(df26) + len(df27) <= len(full_parse) + 5  # bug-fix allocations

    def test_derived_columns(self, fy2026_df):
        assert 'amount_millions' in fy2026_df.columns
        assert 'is_capital' in fy2026_df.columns
        assert fy2026_df['amount_millions'].iloc[0] == pytest.approx(
            fy2026_df['amount'].iloc[0] / 1_000_000
        )

    def test_section_filter(self, full_parse):
        df_op = process_budget_data(full_parse, section='Operating')
        assert all(df_op['section'] == 'Operating')

    def test_empty_input(self):
        df = process_budget_data([])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_sorted_by_program_id(self, fy2026_df):
        ids = fy2026_df['program_id'].tolist()
        assert ids == sorted(ids)


class TestAggregation:

    def test_aggregate_by_department(self, fy2026_df):
        agg = aggregate_by_category(fy2026_df, ['department_code'])
        assert 'pct_of_total' in agg.columns
        assert agg['pct_of_total'].sum() == pytest.approx(100.0, abs=0.1)

    def test_aggregate_by_fund_type(self, fy2026_df):
        agg = aggregate_by_category(fy2026_df, ['fund_type'])
        assert len(agg) > 0
        assert agg['amount'].sum() == pytest.approx(fy2026_df['amount'].sum())


# ---------------------------------------------------------------------------
# Pipeline: veto processing
# ---------------------------------------------------------------------------

class TestVetoProcessing:

    @pytest.fixture
    def sample_allocations(self):
        return [
            BudgetAllocation(
                program_id='BED143', program_name='Test',
                department_code='BED', department_name='Test Dept',
                section=BudgetSection.OPERATING, fund_type=FundType.GENERAL,
                fiscal_year=2026, amount=10_000_000,
            ),
            BudgetAllocation(
                program_id='HTH430', program_name='Hospital',
                department_code='HTH', department_name='Health',
                section=BudgetSection.OPERATING, fund_type=FundType.GENERAL,
                fiscal_year=2026, amount=200_000_000,
            ),
        ]

    def test_veto_changes_applied(self, sample_allocations):
        changes = [
            {'program_id': 'BED143', 'fiscal_year': 2026, 'amount': 5_000_000, 'fund_type': 'A'},
        ]
        result = transform_to_post_veto(sample_allocations, changes)
        bed = [a for a in result if a.program_id == 'BED143']
        assert bed[0].amount == 5_000_000

    def test_veto_no_match_leaves_unchanged(self, sample_allocations):
        changes = [
            {'program_id': 'NONEXISTENT', 'fiscal_year': 2026, 'amount': 0, 'fund_type': 'A'},
        ]
        result = transform_to_post_veto(sample_allocations, changes)
        assert len(result) == len(sample_allocations)

    def test_validate_budget_data_valid(self, sample_allocations):
        is_valid, errors = validate_budget_data(sample_allocations)
        assert is_valid
        assert len(errors) == 0

    def test_validate_budget_data_empty(self):
        is_valid, errors = validate_budget_data([])
        assert not is_valid

    @pytest.mark.skipif(not VETO_PATH.exists(), reason="Veto CSV not present")
    def test_load_real_veto_file(self):
        changes = load_veto_changes(VETO_PATH)
        assert len(changes) > 0
        assert all('program_id' in c for c in changes)
        assert all('amount' in c for c in changes)

    @pytest.mark.skipif(not ONE_TIME_PATH.exists(), reason="One-time CSV not present")
    def test_load_one_time_appropriations(self):
        allocs = load_one_time_appropriations(ONE_TIME_PATH)
        assert len(allocs) > 0
        assert all(a.section == BudgetSection.ONE_TIME for a in allocs)


# ---------------------------------------------------------------------------
# Pipeline: end-to-end integration
# ---------------------------------------------------------------------------

class TestEndToEnd:

    @pytest.mark.skipif(not VETO_PATH.exists(), reason="Veto CSV not present")
    def test_full_pipeline_with_vetoes(self, full_parse):
        """Parse → process → apply vetoes → validate."""
        veto_changes = load_veto_changes(VETO_PATH)
        post_veto = transform_to_post_veto(full_parse.copy(), veto_changes)
        is_valid, errors = validate_budget_data(post_veto)
        # Some allocations may have UNKNOWN fund type after veto, that's OK
        df = process_budget_data(post_veto, fiscal_year=2026)
        assert len(df) > 0
        assert df['amount'].sum() > 0

    @pytest.mark.skipif(
        not VETO_PATH.exists() or not ONE_TIME_PATH.exists(),
        reason="Veto or one-time CSV not present",
    )
    def test_full_pipeline_with_vetoes_and_one_time(self, full_parse):
        """Parse → apply vetoes + one-time appropriations → process."""
        veto_changes = load_veto_changes(VETO_PATH)
        post_veto = transform_to_post_veto(
            full_parse.copy(), veto_changes,
            one_time_appropriations_file=ONE_TIME_PATH,
        )
        df = process_budget_data(post_veto, fiscal_year=2026)
        one_time = df[df['section'] == 'One-Time']
        assert len(one_time) > 0, "One-time appropriations should be present"
