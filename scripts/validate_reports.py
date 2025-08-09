#!/usr/bin/env python3
"""
Lightweight validations for generated departmental reports.

Checks:
- No duplicate dollar signs ("$$") in any generated HTML.
- Index page department card amounts use $ + number + M/B (e.g., $850M, $1.2B).

Exit codes:
- 0 on success (all checks passed)
- 1 on any failure
"""
from __future__ import annotations
import sys
import re
from pathlib import Path

OUTPUT_DIR = Path("data/output/departmental_reports")

AMOUNT_PATTERN = re.compile(r"\$\s*[0-9][0-9,]*(?:\.[0-9])?[MB]\b")


def fail(msg: str) -> None:
    print(f"VALIDATION FAIL: {msg}")
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"VALIDATION WARN: {msg}")


def pass_msg(msg: str) -> None:
    print(f"VALIDATION PASS: {msg}")


def check_exists() -> None:
    if not OUTPUT_DIR.exists():
        fail(f"Output directory not found: {OUTPUT_DIR}")
    index_file = OUTPUT_DIR / "index.html"
    if not index_file.exists():
        fail("index.html not found in output directory")
    pass_msg("Output directory and index.html present")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        fail(f"Could not read {path}: {e}")
        return ""  # unreachable


def check_no_double_dollar() -> None:
    offenders = []
    for p in OUTPUT_DIR.glob("*.html"):
        content = read_text(p)
        if "$$" in content:
            offenders.append(p)
    if offenders:
        fail("Found duplicate dollar signs in: " + ", ".join(str(x.name) for x in offenders))
    pass_msg("No duplicate dollar signs detected")


def extract_values(pattern: re.Pattern[str], text: str) -> list[str]:
    return pattern.findall(text)


def check_index_amount_format() -> None:
    index_file = OUTPUT_DIR / "index.html"
    content = read_text(index_file)

    # Look for the department card budget and breakdown values
    budget_values = re.findall(r'class="dept-budget">([^<]+)</div>', content)
    breakdown_values = re.findall(r'class=\"breakdown-value\">([^<]+)</span>', content)

    # Combine and trim
    values = [v.strip() for v in (budget_values + breakdown_values)]

    if not values:
        warn("No department card values found to validate. Skipping amount pattern check.")
        return

    bad = [v for v in values if not AMOUNT_PATTERN.search(v)]
    if bad:
        samples = "; ".join(bad[:5])
        fail(f"Some department card amounts are not in $[num][M/B] format. Samples: {samples}")
    pass_msg("Index department card amounts use $...M / $...B format")


def main() -> None:
    check_exists()
    check_no_double_dollar()
    check_index_amount_format()
    print("All validations passed.")


if __name__ == "__main__":
    main()
