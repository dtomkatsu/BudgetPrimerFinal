#!/usr/bin/env python3
"""
Download Hawaii legislative bill text from data.capitol.hawaii.gov.

Fetches HTM versions of bill drafts, converts to clean plain text suitable
for parsing by FastBudgetParser, and saves to data/raw/drafts/.

Usage:
    python scripts/download_bill.py HB1800                 # download Introduced
    python scripts/download_bill.py HB1800 --draft HD1     # download HD1
    python scripts/download_bill.py HB1800 --all           # download all known drafts
    python scripts/download_bill.py --list                 # show downloaded drafts
"""
import argparse
import json
import re
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).parent.parent
DRAFTS_DIR = PROJECT_ROOT / 'data' / 'raw' / 'drafts'
METADATA_FILE = DRAFTS_DIR / 'metadata.json'

KNOWN_DRAFTS = ['introduced', 'HD1', 'SD1', 'CD1']


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------

def build_url(bill: str, draft: str = '', session: int = 2026) -> str:
    """Build download URL for a bill draft on data.capitol.hawaii.gov."""
    bill = bill.upper()
    if draft.lower() == 'introduced' or draft == '':
        suffix = '_'
    else:
        suffix = f'_{draft.upper()}_'
    return f'https://data.capitol.hawaii.gov/sessions/session{session}/bills/{bill}{suffix}.HTM'


# ---------------------------------------------------------------------------
# HTM → plain text conversion
# ---------------------------------------------------------------------------

class _BillHTMLParser(HTMLParser):
    """Extract text from Word-exported HTM, preserving whitespace layout."""

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in ('style', 'script', 'head'):
            self.skip = True
        if t == 'br':
            self.parts.append('\n')
        if t in ('p', 'div'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ('style', 'script', 'head'):
            self.skip = False
        if t in ('p', 'div'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    def handle_entityref(self, name):
        if self.skip:
            return
        mapping = {'nbsp': ' ', 'amp': '&', 'lt': '<', 'gt': '>', 'quot': '"'}
        self.parts.append(mapping.get(name, ''))

    def handle_charref(self, name):
        if self.skip:
            return
        try:
            code = int(name, 16) if name.startswith('x') else int(name)
            self.parts.append(' ' if code == 160 else chr(code))
        except ValueError:
            pass


def htm_to_text(html: str) -> str:
    """Convert Word-exported HTM to clean plain text for the budget parser."""
    parser = _BillHTMLParser()
    parser.feed(html)
    text = ''.join(parser.parts)

    # Normalize whitespace characters
    text = text.replace('\xa0', ' ')
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Strip bracket markup used for FY2 column in some drafts: [ 3,893,040A]
    text = re.sub(r'\[([^\]]*)\]', r' \1', text)

    # Rejoin split program headers:
    #   "1.   BED100\n- STRATEGIC MARKETING AND SUPPORT"
    #   → "1.   BED100 - STRATEGIC MARKETING AND SUPPORT"
    text = re.sub(
        r'(\d+\.\s+[A-Z][A-Z0-9]+)\s*\n+\s*(-\s)',
        r'\1 \2',
        text,
    )

    # Rejoin split "INVESTMENT CAPITAL" headers that Word wraps onto two lines:
    #   "INVESTMENT\nCAPITAL  TRN  17,061,000E  26,760,000E"
    #   → "INVESTMENT CAPITAL  TRN  17,061,000E  26,760,000E"
    # The split prevents the investment_capital pattern from matching and causes
    # the amounts to be misclassified as Operating instead of Capital.
    text = re.sub(
        r'\bINVESTMENT\s*\n(\s*CAPITAL\b)',
        r'INVESTMENT CAPITAL',
        text,
    )

    # Collapse excessive blank lines (keep at most one)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove common page header lines
    text = re.sub(r'^.*H\.B\. NO\.\s+\d+.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^.*S\.B\. NO\.\s+\d+.*$', '', text, flags=re.MULTILINE)

    # Strip leading/trailing whitespace from the whole document
    text = text.strip() + '\n'

    return text


# ---------------------------------------------------------------------------
# Download logic
# ---------------------------------------------------------------------------

def download_draft(bill: str, draft: str, session: int = 2026) -> Path:
    """Download a bill draft and save as plain text.

    Returns the path to the saved file.
    Raises HTTPError on 404 (draft not yet available).
    """
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    url = build_url(bill, draft, session)
    label = draft if draft.lower() != 'introduced' and draft else 'introduced'
    out_name = f'{bill.upper()}_{label}.txt'
    out_path = DRAFTS_DIR / out_name

    print(f'Downloading {url} ...')
    req = Request(url, headers={'User-Agent': 'BudgetPrimer/1.0'})

    try:
        with urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except HTTPError as e:
        if e.code == 404:
            print(f'  → 404: Draft "{label}" not yet available for {bill}')
            raise
        raise

    # Decode — the HTM declares windows-1252
    try:
        html = raw.decode('windows-1252')
    except UnicodeDecodeError:
        html = raw.decode('utf-8', errors='replace')

    text = htm_to_text(html)
    out_path.write_text(text, encoding='utf-8')
    line_count = text.count('\n')
    print(f'  → Saved {out_path.name} ({line_count} lines, {len(text):,} bytes)')

    # Update metadata
    _update_metadata(bill, label, url, out_name, line_count, session)

    return out_path


def _update_metadata(bill: str, label: str, url: str, filename: str,
                     line_count: int, session: int):
    """Update the metadata.json tracking file."""
    meta = {}
    if METADATA_FILE.exists():
        meta = json.loads(METADATA_FILE.read_text())

    meta.setdefault('bill_number', bill.upper())
    meta.setdefault('session', session)
    meta.setdefault('drafts', {})

    meta['drafts'][label] = {
        'filename': filename,
        'source_url': url,
        'downloaded_at': datetime.now().isoformat(),
        'line_count': line_count,
    }

    METADATA_FILE.write_text(json.dumps(meta, indent=2) + '\n')


def list_drafts():
    """Print downloaded drafts from metadata."""
    if not METADATA_FILE.exists():
        print('No drafts downloaded yet.')
        return

    meta = json.loads(METADATA_FILE.read_text())
    bill = meta.get('bill_number', '?')
    session = meta.get('session', '?')
    drafts = meta.get('drafts', {})

    print(f'Bill: {bill}  Session: {session}')
    print(f'Downloaded drafts ({len(drafts)}):')
    for label, info in drafts.items():
        fname = info.get('filename', '?')
        dt = info.get('downloaded_at', '?')[:19]
        lines = info.get('line_count', '?')
        exists = '✓' if (DRAFTS_DIR / fname).exists() else '✗'
        print(f'  {exists} {label:12s}  {fname:30s}  {lines:>6} lines  ({dt})')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Download Hawaii bill text from data.capitol.hawaii.gov')
    parser.add_argument('bill', nargs='?', default=None,
                        help='Bill number (e.g., HB1800)')
    parser.add_argument('--draft', default='introduced',
                        help='Draft version: introduced, HD1, SD1, CD1')
    parser.add_argument('--all', action='store_true',
                        help='Download all known drafts')
    parser.add_argument('--session', type=int, default=2026,
                        help='Legislative session year')
    parser.add_argument('--list', action='store_true',
                        help='List downloaded drafts')
    args = parser.parse_args()

    if args.list:
        list_drafts()
        return 0

    if not args.bill:
        parser.error('Bill number required (e.g., HB1800)')

    if args.all:
        drafts_to_get = KNOWN_DRAFTS
    else:
        drafts_to_get = [args.draft]

    success = 0
    for draft in drafts_to_get:
        try:
            download_draft(args.bill, draft, args.session)
            success += 1
        except HTTPError:
            continue
        except Exception as e:
            print(f'  → Error downloading {draft}: {e}')

    print(f'\nDownloaded {success}/{len(drafts_to_get)} drafts.')
    return 0 if success > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
