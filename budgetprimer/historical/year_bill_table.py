"""Year → bill mapping for Hawaii biennial budget acts (2015–2025).

The biennial budget bill is a regular General Appropriations Act passed in
odd-numbered years to fund the next two fiscal years.  The bill *number*
varies year-to-year (it is whatever low-numbered HB the Legislature reserves
for the budget that session), so we maintain an explicit lookup rather than
trying to compute it.

## A note on the "GM" (Governor's Message) files on the Capitol data site

Hawaii's data.capitol.hawaii.gov site has a separate family of files named
GM####_.PDF.  A GM PDF is NOT a distinct bill — it is a bundle containing
(1) a one-page transmittal cover letter from the Governor notifying the
Legislature that a specific measure has been signed, followed by (2) the
full enrolled bill text.  The text inside a GM bundle is the same HB/SB
CD1 we already download.  Parsing CD1 HTM is the correct approach for
line-item appropriation analysis; the only thing the GM bundle adds is
the approval date and any line-item-veto notations on the final page.

## Multi-bill sessions

Most biennia appropriate operating + capital in a single omnibus bill.
The 2019 session was an exception: HB2 CD1 contained ONLY operating
appropriations, while capital improvements (CIP) were enacted separately
in HB1259 CD1.  The schema below supports a list of bills per session to
handle this cleanly.

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
# of fiscal years funded by the session's appropriations (FY1, FY2).  Hawaii
# fiscal years run July 1 – June 30; FY2026 = July 1, 2025 – June 30, 2026.
#
# "bills" is an ordered list.  Most sessions pass a single omnibus bill
# (scope="combined") carrying both operating and capital.  2019 split into
# HB2 (operating) + HB1259 (capital) — both must be parsed to get the full
# biennial picture.
HISTORICAL_BIENNIAL_BILLS: dict[int, dict] = {
    2015: {
        "fy_covered": (2016, 2017),
        "bills": [
            {"number": "HB500", "act": "Act 119, SLH 2015", "scope": "combined"},
        ],
    },
    2017: {
        "fy_covered": (2018, 2019),
        "bills": [
            {"number": "HB100", "act": "Act 049, SLH 2017", "scope": "combined"},
        ],
    },
    2019: {
        "fy_covered": (2020, 2021),
        "bills": [
            {"number": "HB2",    "act": "Act 005, SLH 2019", "scope": "operating"},
            {"number": "HB1259", "act": "Act 042, SLH 2019", "scope": "capital"},
        ],
    },
    2021: {
        "fy_covered": (2022, 2023),
        "bills": [
            {"number": "HB200", "act": "Act 088, SLH 2021", "scope": "combined"},
        ],
    },
    2023: {
        "fy_covered": (2024, 2025),
        "bills": [
            {"number": "HB300", "act": "Act 164, SLH 2023", "scope": "combined"},
        ],
    },
    2025: {
        "fy_covered": (2026, 2027),
        "bills": [
            {"number": "HB300", "act": "Act 250, SLH 2025", "scope": "combined"},
        ],
    },
}


def iter_biennial_bills() -> Iterator[Tuple[int, dict]]:
    """Yield (session_year, session_info) pairs in chronological order.

    session_info is the full dict including "fy_covered" and "bills".
    """
    for session_year in sorted(HISTORICAL_BIENNIAL_BILLS):
        yield session_year, HISTORICAL_BIENNIAL_BILLS[session_year]


def iter_all_bills() -> Iterator[Tuple[int, dict]]:
    """Yield (session_year, bill_info) one row per bill.

    Unlike iter_biennial_bills, sessions with multiple bills (e.g. 2019)
    yield once per bill.  bill_info is the inner dict with "number", "act",
    and "scope".  The session_year is attached externally so callers can
    build year-scoped directories/paths.
    """
    for session_year in sorted(HISTORICAL_BIENNIAL_BILLS):
        session = HISTORICAL_BIENNIAL_BILLS[session_year]
        for bill in session["bills"]:
            yield session_year, bill


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


def primary_bill_label(session_year: int) -> str:
    """Return a human-readable bill label for display.

    Single-bill sessions: "HB300".
    Multi-bill sessions:  "HB2 + HB1259".
    """
    session = HISTORICAL_BIENNIAL_BILLS[session_year]
    return " + ".join(b["number"] for b in session["bills"])
