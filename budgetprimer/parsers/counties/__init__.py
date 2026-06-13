"""
County budget parsers — one per county, registered in COUNTY_PARSERS.

Counties without a parser yet (Maui, Hawaiʻi, Kauaʻi — PDF ordinance sources)
appear in the web app as "coming soon"; adding a parser here and rerunning
scripts/process_county_budgets.py is all that's needed to light them up.
"""
from .base import BaseCountyParser
from .honolulu import HonoluluParser
from .kauai import KauaiParser
from .maui import MauiParser

COUNTY_PARSERS = {
    'honolulu': HonoluluParser,
    'kauai': KauaiParser,         # operating worksheet + CIP from budget ordinances
    'maui': MauiParser,           # FY2026 Mayor's Proposed program budget book (op + CIP)
    # 'hawaii': HawaiiParser,     # blocked — records.hawaiicounty.gov SSL cert failure
}

__all__ = ['BaseCountyParser', 'HonoluluParser', 'KauaiParser', 'MauiParser', 'COUNTY_PARSERS']
