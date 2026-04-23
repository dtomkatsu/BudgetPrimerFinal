#!/usr/bin/env python3
"""Download historical Hawaii biennial budget bills (CD1) from data.capitol.hawaii.gov.

Iterates the year→bill table in budgetprimer.historical.year_bill_table and
fetches each biennium's Conference Draft 1 (the version transmitted to the
Governor) as HTM, converts to plain text using the same htm_to_text helper
the existing download_bill.py uses, and writes both the raw HTM and the
converted .txt under data/raw/historical/{session_year}/.

Usage:
    python scripts/download_historical_bills.py            # all years, skip existing
    python scripts/download_historical_bills.py --year 2023
    python scripts/download_historical_bills.py --force    # re-download everything
    python scripts/download_historical_bills.py --list     # show what's downloaded

The Capitol's data subdomain does not publish RTF for these bills (verified
2026-04 against all six years), so HTM is the only programmatic option.
PDF could be a fallback but the existing parser pipeline assumes HTM-derived
text, so we stick with HTM here.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Allow `from scripts.download_bill import ...` and `from budgetprimer...`
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Reuse the proven HTM→text converter from the existing single-bill downloader
from scripts.download_bill import htm_to_text  # noqa: E402
from budgetprimer.historical import (  # noqa: E402
    HISTORICAL_BIENNIAL_BILLS,
    iter_biennial_bills,
)

HISTORICAL_DIR = PROJECT_ROOT / "data" / "raw" / "historical"
METADATA_FILE = HISTORICAL_DIR / "metadata.json"
USER_AGENT = "BudgetPrimer-Historical/1.0 (research; contact via github)"

# Be a polite citizen of the Capitol's data subdomain.
INTER_REQUEST_SLEEP_SEC = 1.0


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------

def build_cd1_url(session_year: int, bill: str) -> str:
    """Build the CD1 HTM URL for a session/bill on data.capitol.hawaii.gov."""
    return (
        f"https://data.capitol.hawaii.gov/sessions/session{session_year}"
        f"/bills/{bill.upper()}_CD1_.HTM"
    )


# ---------------------------------------------------------------------------
# Download + convert
# ---------------------------------------------------------------------------

def _fetch(url: str) -> bytes:
    """Fetch a URL, returning the raw bytes.  Raises HTTPError on non-200."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=60) as resp:
        return resp.read()


def download_year(session_year: int, bill: str, *, force: bool = False) -> dict:
    """Download a single year's CD1 bill text.

    Writes:
      data/raw/historical/{session_year}/{bill}_CD1_.HTM   (raw)
      data/raw/historical/{session_year}/{bill}_CD1_.txt   (cleaned)

    Returns a metadata dict with download stats (or skip status).
    """
    year_dir = HISTORICAL_DIR / str(session_year)
    year_dir.mkdir(parents=True, exist_ok=True)

    htm_path = year_dir / f"{bill.upper()}_CD1_.HTM"
    txt_path = year_dir / f"{bill.upper()}_CD1_.txt"
    url = build_cd1_url(session_year, bill)

    if not force and htm_path.exists() and txt_path.exists():
        print(f"  [{session_year}] {bill} CD1: already present, skipping")
        return {
            "session_year": session_year,
            "bill": bill,
            "url": url,
            "htm_path": str(htm_path.relative_to(PROJECT_ROOT)),
            "txt_path": str(txt_path.relative_to(PROJECT_ROOT)),
            "status": "skipped",
        }

    print(f"  [{session_year}] GET {url}")
    try:
        raw = _fetch(url)
    except HTTPError as e:
        print(f"    HTTP {e.code}: {e.reason}")
        return {
            "session_year": session_year,
            "bill": bill,
            "url": url,
            "status": f"http_error_{e.code}",
        }
    except URLError as e:
        print(f"    Connection error: {e.reason}")
        return {
            "session_year": session_year,
            "bill": bill,
            "url": url,
            "status": f"url_error",
            "error": str(e.reason),
        }

    # Capitol HTM declares windows-1252; fall back to utf-8 with replacement
    try:
        html = raw.decode("windows-1252")
    except UnicodeDecodeError:
        html = raw.decode("utf-8", errors="replace")

    # Save raw HTM (preserves the source for later debugging)
    htm_path.write_bytes(raw)

    # Convert and save cleaned plain text
    text = htm_to_text(html)
    txt_path.write_text(text, encoding="utf-8")

    line_count = text.count("\n")
    print(
        f"    saved HTM={len(raw):,}B  TXT={len(text):,}B "
        f"({line_count:,} lines) → {txt_path.relative_to(PROJECT_ROOT)}"
    )

    return {
        "session_year": session_year,
        "bill": bill,
        "url": url,
        "htm_path": str(htm_path.relative_to(PROJECT_ROOT)),
        "txt_path": str(txt_path.relative_to(PROJECT_ROOT)),
        "htm_bytes": len(raw),
        "txt_bytes": len(text),
        "txt_lines": line_count,
        "downloaded_at": datetime.now().isoformat(timespec="seconds"),
        "status": "ok",
    }


# ---------------------------------------------------------------------------
# Metadata persistence
# ---------------------------------------------------------------------------

def _write_metadata(results: list[dict]) -> None:
    """Update data/raw/historical/metadata.json with the latest results.

    Preserves existing entries for years not touched in this run.
    """
    HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)
    existing = {}
    if METADATA_FILE.exists():
        try:
            existing = json.loads(METADATA_FILE.read_text())
        except json.JSONDecodeError:
            existing = {}

    existing.setdefault("downloads", {})
    for r in results:
        if r.get("status") == "ok":
            key = str(r["session_year"])
            existing["downloads"][key] = r

    existing["last_run"] = datetime.now().isoformat(timespec="seconds")
    METADATA_FILE.write_text(json.dumps(existing, indent=2) + "\n")


def list_downloaded() -> None:
    """Print a summary of what's currently on disk."""
    if not HISTORICAL_DIR.exists():
        print("No historical downloads yet.")
        return
    print(f"{'Year':<6} {'Bill':<8} {'Act':<25} HTM      TXT      Status")
    print("-" * 78)
    for session_year, info in iter_biennial_bills():
        bill = info["bill"]
        act = info["act"]
        htm = HISTORICAL_DIR / str(session_year) / f"{bill}_CD1_.HTM"
        txt = HISTORICAL_DIR / str(session_year) / f"{bill}_CD1_.txt"
        htm_status = f"{htm.stat().st_size:,}B" if htm.exists() else "—"
        txt_status = f"{txt.stat().st_size:,}B" if txt.exists() else "—"
        present = "✓" if (htm.exists() and txt.exists()) else "—"
        print(
            f"{session_year:<6} {bill:<8} {act:<25} {htm_status:<8} {txt_status:<8} {present}"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Download historical Hawaii biennial budget bills (CD1)."
    )
    ap.add_argument(
        "--year",
        type=int,
        action="append",
        help="Restrict to one or more session years (repeatable). "
        "Default: all years in the historical table.",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if files already exist locally.",
    )
    ap.add_argument(
        "--list",
        action="store_true",
        help="List download status of all known biennial bills and exit.",
    )
    args = ap.parse_args()

    if args.list:
        list_downloaded()
        return 0

    if args.year:
        years = sorted(set(args.year))
        unknown = [y for y in years if y not in HISTORICAL_BIENNIAL_BILLS]
        if unknown:
            print(
                f"ERROR: unknown session year(s) {unknown}. "
                f"Known years: {sorted(HISTORICAL_BIENNIAL_BILLS)}"
            )
            return 1
        targets = [(y, HISTORICAL_BIENNIAL_BILLS[y]) for y in years]
    else:
        targets = list(iter_biennial_bills())

    print(
        f"Downloading {len(targets)} biennial budget bill(s) from "
        f"data.capitol.hawaii.gov (force={args.force})..."
    )
    results: list[dict] = []
    n_ok = n_skipped = n_failed = 0
    for i, (session_year, info) in enumerate(targets):
        if i > 0:
            time.sleep(INTER_REQUEST_SLEEP_SEC)
        r = download_year(session_year, info["bill"], force=args.force)
        results.append(r)
        status = r.get("status", "?")
        if status == "ok":
            n_ok += 1
        elif status == "skipped":
            n_skipped += 1
        else:
            n_failed += 1

    _write_metadata(results)

    print()
    print(f"Done. {n_ok} downloaded, {n_skipped} skipped, {n_failed} failed.")
    return 0 if n_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
