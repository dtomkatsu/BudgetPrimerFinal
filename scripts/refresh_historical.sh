#!/usr/bin/env bash
# Refresh the historical-budgets data feed end-to-end.
#
# Pipeline:
#   1. Download CD1 HTM for each biennial budget bill (skips if present)
#   2. Parse each year into one combined CSV
#   3. Fetch latest Honolulu CPI-U from BLS
#   4. Generate the SPA's historical_trends.json
#
# Cadence:
#   - Bill data only changes when a new biennial act is signed (every 2 years).
#     Pass --force to re-pull bills if a fix to the parser warrants reparsing
#     from scratch.
#   - CPI updates monthly. Re-running this script monthly keeps deflators
#     current and is cheap (one BLS request).
#
# Usage:
#   scripts/refresh_historical.sh
#   scripts/refresh_historical.sh --force      # re-download all bills
set -euo pipefail

cd "$(dirname "$0")/.."

DOWNLOAD_FLAGS=""
if [[ "${1:-}" == "--force" ]]; then
    DOWNLOAD_FLAGS="--force"
fi

echo "==> Step 1/4: download historical bills"
python3 scripts/download_historical_bills.py $DOWNLOAD_FLAGS

echo
echo "==> Step 2/4: parse all biennial bills"
python3 scripts/parse_historical_budgets.py

echo
echo "==> Step 3/4: fetch Honolulu CPI-U"
python3 scripts/fetch_cpi.py

echo
echo "==> Step 4/4: regenerate docs/js/historical_trends.json"
python3 scripts/generate_historical_spa_report.py

echo
echo "Done. Reload the dashboard at #/history to see the refreshed data."
