#!/usr/bin/env python3
"""
Download Hawaii legislative bill text from data.capitol.hawaii.gov.

Fetches HTM versions of bill drafts, converts to clean plain text suitable
for parsing by FastBudgetParser, and saves to data/raw/drafts/.

Also supports converting locally-saved RTF files (e.g. from the Legislature
website) which avoid the word-wrap line-splitting issues in the HTM export.

Usage:
    python scripts/download_bill.py HB1800                 # download Introduced
    python scripts/download_bill.py HB1800 --draft HD1     # download HD1
    python scripts/download_bill.py HB1800 --all           # download all known drafts
    python scripts/download_bill.py --list                 # show downloaded drafts
    python scripts/download_bill.py HB1800 --draft HD1 --from-rtf "HB 1800 HD1.rtf"
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

    # Rejoin "OPERATING DEPT\namount" / "DEPT\namount" split lines where Word
    # wrapped the dollar amounts onto the next line.
    #   "OPERATING  BED       \n3,802,604A    3,802,952A"
    #   → "OPERATING  BED  3,802,604A    3,802,952A"
    # Guard: only rejoin when the next line starts with a comma-formatted dollar
    # amount (e.g. "3,802,604A"), not prose like "1970S." or TMK numbers.
    text = re.sub(
        r'\b([A-Z]{2,4}) *\n(\s*\d+(?:,\d+)+[A-Z])',
        r'\1  \2',
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
# RTF → plain text conversion
# ---------------------------------------------------------------------------

def rtf_to_text(rtf: str) -> str:
    """Convert a macOS/Word RTF bill export to clean plain text.

    RTF files from the Legislature avoid the word-wrap line-splitting issues
    that appear in the Word-exported HTM.  Each budget allocation row is a
    single RTF paragraph (ending with \\ + newline), so OPERATING/DEPT/amounts
    are always on the same line without needing rejoin hacks.

    The RTF uses literal [ ] brackets around struck-through enacted values
    (same convention as the HTM bracket markup), so the same post-processing
    pipeline applies after stripping the RTF control words.
    """
    # ── 1. Remove header groups that contain no bill text ──────────────────
    for pat in (
        r'\{\\fonttbl[^}]*\}',
        r'\{\\colortbl[^}]*\}',
        r'\{\\\*\\expandedcolortbl[^}]*\}',
    ):
        rtf = re.sub(pat, '', rtf)

    # ── 2. Paragraph breaks: \ at end of content line → newline ───────────
    # In these RTF exports each visible document line ends with "\" then \n.
    rtf = re.sub(r'\\\n', '\n', rtf)

    # ── 3. Decode \'xx hex entity references ──────────────────────────────
    def _decode(m: re.Match) -> str:
        code = int(m.group(1), 16)
        if code == 0xa0:          return ' '   # non-breaking space
        if code in (0x96, 0x97): return '-'   # en / em dash
        if code in (0x91, 0x92): return "'"   # curly single quotes
        if code in (0x93, 0x94): return '"'   # curly double quotes
        return chr(code) if 0x20 <= code < 0x7f else ' '

    rtf = re.sub(r"\\'([0-9a-fA-F]{2})", _decode, rtf)

    # ── 4. Strip all RTF control words (\keyword or \keyword-N) ───────────
    rtf = re.sub(r'\\[a-zA-Z]+[-\d]*[ ]?', '', rtf)

    # Remove { } group delimiters (table headers, etc.)
    rtf = re.sub(r'[{}]', '', rtf)

    # ── 5. Shared post-processing (same as htm_to_text) ───────────────────
    text = rtf.replace('\r\n', '\n').replace('\r', '\n')

    # Strip bracket markup used for struck-through enacted column: [ 3,893,040A]
    text = re.sub(r'\[([^\]]*)\]', r' \1', text)

    # Rejoin split program headers: "1.   BED100\n- STRATEGIC MARKETING..."
    text = re.sub(
        r'(\d+\.\s+[A-Z][A-Z0-9]+)\s*\n+\s*(-\s)',
        r'\1 \2',
        text,
    )

    # Collapse excessive blank lines (keep at most one)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove page header lines
    text = re.sub(r'^.*H\.B\. NO\.\s+\d+.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^.*S\.B\. NO\.\s+\d+.*$', '', text, flags=re.MULTILINE)

    # Strip trailing closing-quote on last amount line of quoted sections
    # (same guard as htm_to_text: only strip when line starts with dept code)
    lines_out = []
    for raw_line in text.splitlines():
        if raw_line.endswith('"') and len(raw_line) >= 2 and raw_line[-2].isalpha():
            _candidate = raw_line[:-1]
            if re.match(r'^[A-Z]{2,4}\s', _candidate.strip(), re.IGNORECASE):
                raw_line = _candidate
        lines_out.append(raw_line)
    text = '\n'.join(lines_out)

    return text.strip() + '\n'


def convert_rtf(bill: str, draft: str, rtf_path: Path) -> Path:
    """Convert a locally-saved RTF file to plain text and save it.

    Returns the path to the saved .txt file.
    """
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    label = draft if draft.lower() != 'introduced' and draft else 'introduced'
    out_name = f'{bill.upper()}_{label}.txt'
    out_path = DRAFTS_DIR / out_name

    print(f'Converting RTF: {rtf_path} ...')
    raw = rtf_path.read_bytes()
    try:
        rtf = raw.decode('mac_roman')
    except UnicodeDecodeError:
        rtf = raw.decode('utf-8', errors='replace')

    text = rtf_to_text(rtf)
    out_path.write_text(text, encoding='utf-8')
    line_count = text.count('\n')
    print(f'  → Saved {out_path.name} ({line_count} lines, {len(text):,} bytes)')

    _update_metadata(bill, label, f'file://{rtf_path.resolve()}', out_name,
                     line_count, session=2026)
    return out_path


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
    parser.add_argument('--from-rtf', metavar='RTF_FILE',
                        help='Convert a locally-saved RTF file instead of '
                             'downloading (use with --draft to set the label)')
    args = parser.parse_args()

    if args.list:
        list_drafts()
        return 0

    if not args.bill:
        parser.error('Bill number required (e.g., HB1800)')

    # RTF conversion path
    if args.from_rtf:
        rtf_path = Path(args.from_rtf)
        if not rtf_path.exists():
            print(f'Error: RTF file not found: {rtf_path}')
            return 1
        convert_rtf(args.bill, args.draft, rtf_path)
        return 0

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
