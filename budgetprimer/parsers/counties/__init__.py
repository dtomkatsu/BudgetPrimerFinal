"""
County budget parsers — one per county, registered in COUNTY_PARSERS.

Counties without a parser yet (Maui, Hawaiʻi, Kauaʻi — PDF ordinance sources)
appear in the web app as "coming soon"; adding a parser here and rerunning
scripts/process_county_budgets.py is all that's needed to light them up.
"""
from .base import BaseCountyParser
from .honolulu import HonoluluParser

COUNTY_PARSERS = {
    'honolulu': HonoluluParser,
    # 'hawaii': HawaiiParser,   # Phase 2 — ordinance PDFs (Laserfiche)
    # 'kauai': KauaiParser,     # Phase 3 — ordinance PDFs
    # 'maui': MauiParser,       # Phase 4 — program budget book PDF
}

__all__ = ['BaseCountyParser', 'HonoluluParser', 'COUNTY_PARSERS']
