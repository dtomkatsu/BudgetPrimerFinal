"""Year → bill mapping for Hawaii biennial budget acts (2015–2025).

The biennial budget bill is a regular General Appropriations Act passed in
odd-numbered years to fund the next two fiscal years.  The bill *number*
varies year-to-year (it is whatever low-numbered HB the Legislature reserves
for the budget that session), so we maintain an explicit lookup rather than
trying to compute it.

Data source: Hawaii Legislative Reference Bureau Final Reports / Acts
compendia (e.g. https://lrb.hawaii.gov/wp-content/uploads/{YEAR}_Acts.pdf)
cross-referenced with the Capitol bill repository at
https://data.capitol.hawaii.gov/sessions/session{YEAR}/bills/.

The CD1 (Conference Draft 1) is the version transmitted to the Governor.
Line-item vetoes are NOT reflected here — see Phase 2 of the historical
trends plan for veto netting.
"""
from __future__ import annotations

from typing import Iterator, Tuple

# Each entry covers a *biennium* (two fiscal years).  fy_covered is the pair
# of fiscal years funded by the act (FY1, FY2).  Hawaii fiscal years run
# July 1 – June 30; FY2026 = July 1, 2025 – June 30, 2026.
HISTORICAL_BIENNIAL_BILLS: dict[int, dict] = {
    2015: {
        "bill": "HB500",
        "act": "Act 119, SLH 2015",
        "fy_covered": (2016, 2017),
    },
    2017: {
        "bill": "HB100",
        "act": "Act 049, SLH 2017",
        "fy_covered": (2018, 2019),
    },
    2019: {
        "bill": "HB2",
        "act": "Act 005, SLH 2019",
        "fy_covered": (2020, 2021),
    },
    2021: {
        "bill": "HB200",
        "act": "Act 088, SLH 2021",
        "fy_covered": (2022, 2023),
    },
    2023: {
        "bill": "HB300",
        "act": "Act 164, SLH 2023",
        "fy_covered": (2024, 2025),
    },
    2025: {
        "bill": "HB300",
        "act": "Act 250, SLH 2025",
        "fy_covered": (2026, 2027),
    },
}


def iter_biennial_bills() -> Iterator[Tuple[int, dict]]:
    """Yield (session_year, info) pairs in chronological order."""
    for session_year in sorted(HISTORICAL_BIENNIAL_BILLS):
        yield session_year, HISTORICAL_BIENNIAL_BILLS[session_year]


def get_bill_for_session(session_year: int) -> dict:
    """Return the metadata dict for a given session year.

    Raises KeyError if the session is not in the historical table (e.g.
    a supplemental year, or earlier than 2015).
    """
    return HISTORICAL_BIENNIAL_BILLS[session_year]


def fiscal_years_covered() -> list[int]:
    """Return the full sorted list of fiscal years covered by all biennial acts."""
    fys: set[int] = set()
    for info in HISTORICAL_BIENNIAL_BILLS.values():
        fys.update(info["fy_covered"])
    return sorted(fys)
