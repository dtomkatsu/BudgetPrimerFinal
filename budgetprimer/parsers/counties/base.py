"""
Base class for county budget parsers.

Each county publishes its budget in a different format (Socrata open data,
ordinance PDFs, program budget books), so each gets its own parser. Parsers
consume committed raw files from data/raw/counties/<county>/ — downloading is
handled separately by scripts/fetch_county_budgets.py so parsing is
reproducible offline, mirroring the HB300 text-file convention.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from budgetprimer.models.county_allocation import CountyAllocation


class BaseCountyParser(ABC):
    """Parse one county's raw budget files into CountyAllocation rows."""

    #: slug key: 'honolulu' | 'maui' | 'hawaii' | 'kauai'
    county: str = ''
    #: human-readable source citation shown in the web app footer
    source_label: str = ''
    source_url: str = ''
    #: caveat about what the parsed data does/doesn't cover, shown in the UI
    coverage_note: str = ''

    @abstractmethod
    def parse(self, raw_dir: Path, fiscal_year: int) -> List[CountyAllocation]:
        """Parse raw files for the given fiscal year.

        Args:
            raw_dir: data/raw/counties/<county>/
            fiscal_year: e.g. 2026 (= FY July 2025 – June 2026)

        Returns:
            List of CountyAllocation rows (empty if raw files are missing).
        """
        raise NotImplementedError
