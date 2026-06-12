#!/usr/bin/env python3
"""
Fetch raw county budget source files into data/raw/counties/<county>/.

This is the only network-touching piece of the county pipeline. Downloaded
files are committed to the repo (like data/raw/HB 300 CD 1.txt) so that
scripts/process_county_budgets.py runs reproducibly offline.

Usage:
    python scripts/fetch_county_budgets.py --county honolulu --fy 2026
    python scripts/fetch_county_budgets.py --county all --fy 2026 --force
"""
import argparse
import json
import logging
import sys
from pathlib import Path

import requests

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from budgetprimer.parsers.counties.honolulu import DATASET_IDS as HONOLULU_DATASETS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

USER_AGENT = 'BudgetPrimer/1.0 (Hawaii budget transparency project; github.com pages app)'

RAW_ROOT = project_root / 'data' / 'raw' / 'counties'

# PDF sources for the three counties without open data, plus Honolulu CIP.
# Verified live 2026-06-12. Parsed in later phases; fetched now so the raw
# documents are committed alongside the code that will consume them.
PDF_SOURCES = {
    'honolulu': {
        2026: [
            ('fy2026_cip_ord_25-39.pdf', 'https://hnldoc.ehawaii.gov/hnldoc/document-download?id=25417'),
        ],
    },
    'hawaii': {
        2026: [
            ('fy2026_operating_ord_25-45.pdf', 'https://records.hawaiicounty.gov/weblink/DocView.aspx?dbid=0&id=1108350'),
            ('fy2026_cip_ord_25-46.pdf', 'https://records.hawaiicounty.gov/weblink/DocView.aspx?dbid=0&id=1108352'),
        ],
    },
    'kauai': {
        2026: [
            ('fy2026_operating_b-2025-905.pdf', 'https://www.kauai.gov/files/assets/public/v/1/county-council/documents/budget/fy-2025-2026-operating-budget-full-text-final-ordinance-no-b-2025-905.pdf'),
            ('fy2026_cip_b-2025-906.pdf', 'https://www.kauai.gov/files/assets/public/v/1/county-council/documents/budget/fy-2025-2026-cip-budget-full-text-final-ordinance-no-b-2025-906.pdf'),
        ],
        2027: [
            ('fy2027_operating_b-2026-917.pdf', 'https://www.kauai.gov/files/assets/public/v/1/county-council/documents/budget/ordinance-no.-b-2026-917.pdf'),
            ('fy2027_cip_b-2026-918.pdf', 'https://www.kauai.gov/files/assets/public/v/1/county-council/documents/budget/ordinance-no.-b-2026-918.pdf'),
        ],
    },
    'maui': {
        2026: [
            ('fy2026_program_budget.pdf', 'https://www.mauicounty.gov/DocumentCenter/View/152301/000---FY-2026-Program-Budget-Combined'),
        ],
    },
}


def download(url: str, dest: Path, force: bool = False) -> bool:
    if dest.exists() and not force:
        logger.info(f"Exists, skipping: {dest.name} (use --force to refetch)")
        return True
    logger.info(f"Downloading {url} → {dest}")
    try:
        resp = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=120)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to download {url}: {e}")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    logger.info(f"Saved {dest.name} ({len(resp.content):,} bytes)")
    return True


def fetch_honolulu_operating(fy: int, force: bool) -> bool:
    """Honolulu operating budget via the Socrata SODA API."""
    dataset_id = HONOLULU_DATASETS.get(fy)
    if not dataset_id:
        logger.warning(f"No Honolulu dataset id known for FY{fy}")
        return False
    dest = RAW_ROOT / 'honolulu' / f'fy{fy}_operating_{dataset_id}.json'
    if dest.exists() and not force:
        logger.info(f"Exists, skipping: {dest.name} (use --force to refetch)")
        return True
    url = f'https://data.honolulu.gov/resource/{dataset_id}.json'
    logger.info(f"Fetching Socrata dataset {dataset_id} (FY{fy})")
    try:
        resp = requests.get(url, params={'$limit': 50000},
                            headers={'User-Agent': USER_AGENT}, timeout=120)
        resp.raise_for_status()
        records = resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return False
    if len(records) >= 50000:
        logger.warning("Hit $limit=50000 — dataset may be truncated, raise the limit")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, 'w') as f:
        json.dump(records, f)
    logger.info(f"Saved {dest.name} ({len(records):,} records)")
    return True


def fetch_county(county: str, fy: int, force: bool, pdfs: bool) -> bool:
    ok = True
    if county == 'honolulu':
        ok = fetch_honolulu_operating(fy, force) and ok
    if pdfs:
        for filename, url in PDF_SOURCES.get(county, {}).get(fy, []):
            ok = download(url, RAW_ROOT / county / filename, force) and ok
    return ok


def main():
    parser = argparse.ArgumentParser(description='Fetch county budget source files')
    parser.add_argument('--county', choices=['honolulu', 'maui', 'hawaii', 'kauai', 'all'],
                        default='all')
    parser.add_argument('--fy', type=int, default=2026, help='Fiscal year (e.g. 2026)')
    parser.add_argument('--force', action='store_true', help='Refetch even if files exist')
    parser.add_argument('--pdfs', action='store_true',
                        help='Also download ordinance/budget-book PDFs (large files)')
    args = parser.parse_args()

    counties = ['honolulu', 'maui', 'hawaii', 'kauai'] if args.county == 'all' else [args.county]
    ok = True
    for county in counties:
        ok = fetch_county(county, args.fy, args.force, args.pdfs) and ok
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
