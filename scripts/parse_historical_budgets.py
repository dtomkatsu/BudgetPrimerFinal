#!/usr/bin/env python3
"""Parse all historical biennial budget bills into one combined CSV.

Iterates the year→bill table, runs FastBudgetParser on each year's CD1 text
file (downloaded by scripts/download_historical_bills.py), tags every
allocation with session_year/bill_number/act_number, and concatenates
everything into data/processed/historical_allocations.csv.

Per-year totals are logged so format regressions are easy to spot.

Usage:
    python scripts/parse_historical_budgets.py
    python scripts/parse_historical_budgets.py --year 2023
    python scripts/parse_historical_budgets.py --output custom.csv
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

from budgetprimer.parsers import FastBudgetParser  # noqa: E402
from budgetprimer.historical import (  # noqa: E402
    HISTORICAL_BIENNIAL_BILLS,
    iter_biennial_bills,
)

HISTORICAL_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "historical"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "historical_allocations.csv"

# Quiet the very chatty parser logs unless --verbose is set
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("parse_historical_budgets")
logger.setLevel(logging.INFO)


def parse_one_year(session_year: int, info: dict) -> pd.DataFrame:
    """Parse a single year's CD1 bill, returning a DataFrame of allocations
    tagged with session_year/bill_number/act_number.
    """
    bill = info["bill"]
    expected_fys = info["fy_covered"]
    txt_path = HISTORICAL_RAW_DIR / str(session_year) / f"{bill}_CD1_.txt"

    if not txt_path.exists():
        raise FileNotFoundError(
            f"Missing parsed text for session {session_year}: {txt_path}\n"
            f"Run scripts/download_historical_bills.py first."
        )

    logger.info(
        f"[{session_year}] parsing {bill} CD1  ({txt_path.stat().st_size:,} bytes)"
    )
    # The parser's column 1 → fy1, column 2 → fy2.  Pass the actual fiscal
    # years for this bill so allocations are tagged correctly across history
    # (the default FY1=2026/FY2=2027 only fits the 2025 session).
    fy1, fy2 = expected_fys
    parser = FastBudgetParser(fy1=fy1, fy2=fy2)
    allocations = parser.parse(str(txt_path))
    if not allocations:
        logger.warning(f"[{session_year}] parser returned 0 allocations")
        return pd.DataFrame()

    df = pd.DataFrame([a.to_dict() for a in allocations])
    df["session_year"] = session_year
    df["bill_number"] = bill
    df["act_number"] = info["act"]

    # Sanity-check: parsed FYs should match expected_fys
    parsed_fys = sorted(int(y) for y in df["fiscal_year"].unique() if y)
    expected_set = set(expected_fys)
    parsed_set = set(parsed_fys)
    if parsed_set != expected_set:
        logger.warning(
            f"[{session_year}] FY mismatch: expected {sorted(expected_set)}, "
            f"parsed {sorted(parsed_set)}"
        )

    # Per-year summary
    n = len(df)
    by_fy = df.groupby("fiscal_year")["amount"].sum()
    by_section = df.groupby(["fiscal_year", "section"])["amount"].sum()
    logger.info(f"[{session_year}] {n:,} allocations")
    for fy in sorted(by_fy.index):
        total = by_fy[fy] / 1e9
        logger.info(f"  FY{int(fy)} total = ${total:,.2f}B")
        for sec in ("Operating", "Capital Improvement"):
            try:
                amt = by_section.loc[(fy, sec)] / 1e9
                logger.info(f"    {sec:<22s} ${amt:,.2f}B")
            except KeyError:
                pass

    return df


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Parse historical biennial budget bills into one CSV."
    )
    ap.add_argument(
        "--year",
        type=int,
        action="append",
        help="Restrict to one or more session years (repeatable). "
        "Default: all years in the historical table.",
    )
    ap.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)})",
    )
    ap.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show parser DEBUG output (very chatty).",
    )
    args = ap.parse_args()

    if args.verbose:
        logging.getLogger("budgetprimer").setLevel(logging.DEBUG)

    if args.year:
        years = sorted(set(args.year))
        unknown = [y for y in years if y not in HISTORICAL_BIENNIAL_BILLS]
        if unknown:
            print(f"ERROR: unknown session year(s) {unknown}")
            return 1
        targets = [(y, HISTORICAL_BIENNIAL_BILLS[y]) for y in years]
    else:
        targets = list(iter_biennial_bills())

    frames: list[pd.DataFrame] = []
    for session_year, info in targets:
        try:
            df = parse_one_year(session_year, info)
        except Exception as e:
            logger.error(f"[{session_year}] FAILED: {e}", exc_info=True)
            continue
        if not df.empty:
            frames.append(df)

    if not frames:
        logger.error("No allocations parsed across any year.")
        return 1

    combined = pd.concat(frames, ignore_index=True)

    # Stable ordering for downstream diffability
    sort_cols = [c for c in ("session_year", "fiscal_year", "department_code",
                             "program_id", "section", "fund_type")
                 if c in combined.columns]
    combined = combined.sort_values(sort_cols).reset_index(drop=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(args.output, index=False)
    logger.info(
        f"Wrote {len(combined):,} rows × {len(combined.columns)} cols → "
        f"{args.output.relative_to(PROJECT_ROOT)}"
    )

    # Compact per-year summary at the end
    print()
    print(f"{'Session':<8} {'Bill':<8} {'Rows':>8}  Per-FY Totals (B$)")
    print("-" * 78)
    for sy in sorted(combined["session_year"].unique()):
        sub = combined[combined["session_year"] == sy]
        bill = sub["bill_number"].iloc[0]
        per_fy = sub.groupby("fiscal_year")["amount"].sum() / 1e9
        fy_str = "  ".join(f"FY{int(fy)}=${v:,.2f}B" for fy, v in per_fy.items())
        print(f"{sy:<8} {bill:<8} {len(sub):>8,}  {fy_str}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
