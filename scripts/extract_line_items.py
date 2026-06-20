#!/usr/bin/env python3
"""
Extract worksheet line item appropriations from HB1800 CD1 and HB300 CD1.

These are the specific purpose-restricted allocations and supplemental grants
that live *within* programs but aren't captured in the program-level totals:

  - HB1800 CD1 §13.1 — Supplemental grants (112 nonprofits via LBR903, $20M)
  - HB1800 CD1 §11.x — Purpose restrictions on specific programs (earmarks)
  - HB300 CD1  §13   — Enacted supplemental grants (multi-dept, $10M)
  - HB300 CD1  §4-§12 — Enacted purpose restrictions / earmarks

Output: docs/js/line_items.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
HB1800_CD1 = REPO / "data" / "raw" / "drafts" / "HB1800_CD1.txt"
HB300_CD1  = REPO / "data" / "raw" / "HB 300 CD 1.txt"
OUT_PATH   = REPO / "docs" / "js" / "line_items.json"

# ── helpers ─────────────────────────────────────────────────────────────────

def normalize(s: str) -> str:
    """Replace non-breaking spaces and collapse whitespace."""
    return re.sub(r'[\s\xa0]+', ' ', s).strip()


def title_case(s: str) -> str:
    """Readable title case for all-caps names."""
    minor = {"a","an","and","as","at","but","by","for","if","in","nor","of",
              "on","or","so","the","to","up","yet","hrs","inc","llc","ltd"}
    words = s.lower().split()
    result = []
    for i, w in enumerate(words):
        if i == 0 or w not in minor:
            result.append(w.capitalize())
        else:
            result.append(w)
    return " ".join(result)


def parse_dollar(s: str) -> float:
    return float(re.sub(r'[,$]', '', s.strip()))


# ── HB1800 §13.1 supplemental grants ────────────────────────────────────────
#
# Format (after text normalization):
#   "N. $AMOUNT      RECIPIENT NAME\n\nADD FUNDS ... FOR RECIPIENT, FOR COSTS
#    RELATED TO PURPOSE FOR OFFICE OF COMMUNITY SERVICES (LBR903) ..."

def extract_hb1800_grants(raw: str) -> list[dict]:
    """HB1800 CD1 §13.1 — all 112 supplemental grants via LBR903."""
    text = normalize(raw)

    start = text.find("SECTION 13.1 SUPPLEMENTAL APPROPRIATIONS")
    if start < 0:
        print("WARNING: §13.1 not found in HB1800_CD1", file=sys.stderr)
        return []
    end = text.find("SECTION 7.", start)
    if end < 0:
        end = len(text)
    block = text[start:end]

    # Match numbered entries:  "N. $AMOUNT   NAME"
    header_re = re.compile(r'(\d+)\.\s+\$?([\d,]+\.?\d*)\s+(.+?)(?=\s+\d+\.\s+\$|\Z)',
                           re.DOTALL)
    grants: list[dict] = []

    for m in header_re.finditer(block):
        seq = int(m.group(1))
        amount = parse_dollar(m.group(2))
        rest = m.group(3)

        # First line(s) before "ADD FUNDS" = recipient name
        add_pos = rest.upper().find("ADD FUNDS")
        if add_pos < 0:
            name_raw = rest.split('\n')[0].strip()
            purpose_raw = ""
        else:
            name_raw = rest[:add_pos].split('\n')[0].strip()
            add_text = rest[add_pos:]
            # "FOR COSTS RELATED TO X FOR OFFICE OF COMMUNITY SERVICES"
            costs_m = re.search(
                r'FOR COSTS RELATED TO (.+?)'
                r'(?:\s*FOR\s+(?:OFFICE OF COMMUNITY SERVICES|[A-Z &\-]+)\s*\([A-Z]{3}\d+\))',
                add_text, re.IGNORECASE | re.DOTALL
            )
            purpose_raw = normalize(costs_m.group(1)).rstrip(";., ") if costs_m else ""

        # Extract program id from "(PROGID)" pattern
        prog_id_m = re.search(r'\(([A-Z]{3}\d{3,4})\)', rest)
        prog_id = prog_id_m.group(1) if prog_id_m else "LBR903"

        grants.append({
            "seq": seq,
            "recipient": title_case(name_raw.strip('."')),
            "amount": amount,
            "purpose": title_case(purpose_raw) if purpose_raw else "",
            "program_id": prog_id,
            "program_name": "Office of Community Services",
            "dept_code": "LBR",
            "type": "grant",
            "bill": "HB1800",
            "source": "HB1800 CD1 §13.1",
        })

    return grants


# ── HB1800 §11.x purpose restrictions ───────────────────────────────────────
#
# Format (after normalization):
#   "SECTION 11.X Provided that [out of / of] the [TYPE] fund appropriation
#    for PROGRAM_NAME (PROG_ID), the sum of $AMOUNT ... for fiscal year YYYY
#    shall be PURPOSE."

def extract_hb1800_restrictions(raw: str) -> list[dict]:
    """HB1800 CD1 §11.x — purpose restrictions (earmarks) within programs."""
    text = normalize(raw)

    start = text.find("SECTION 5.")
    if start < 0:
        print("WARNING: §11 restrictions not found in HB1800_CD1", file=sys.stderr)
        return []
    end = text.find("SECTION 6.", start)
    if end < 0:
        end = len(text)
    block = text[start:end]

    # Each section is delimited by "SECTION 11.N"
    sec_re = re.compile(
        r'"SECTION\s+(1[12]\.\d+)[.\s]+Provided that (?:out of |of )?the (\S+) (?:fund )?appropriation for\s+'
        r'([^(]+?)\s*\(([A-Z]{3}\d{3,4})\)',
        re.IGNORECASE
    )

    # Collect all section match positions so we can bound each section's text
    all_matches = list(sec_re.finditer(block))

    restrictions: list[dict] = []
    for idx, m in enumerate(all_matches):
        sec_num = m.group(1)
        fund_type = m.group(2).lower()
        prog_name = normalize(m.group(3))
        prog_id = m.group(4)

        # Bound "after" to just this section (stop at the next section header)
        after_start = m.end()
        after_end = all_matches[idx + 1].start() if idx + 1 < len(all_matches) else len(block)
        after = block[after_start:after_end]

        # Find amounts and fiscal years — biennium range "YYYY-YYYY" or single "YYYY"
        amt_re = re.findall(
            r'\$\s*([\d,]+(?:\.\d+)?) or so much thereof[^f]*for fiscal year (\d{4}(?:-\d{4})?)',
            after, re.IGNORECASE
        )

        # Purpose: "shall be [PURPOSE]"
        shall_m = re.search(r'shall be\s+(.+?)(?:;|\.")', after[:600], re.DOTALL | re.IGNORECASE)
        purpose = title_case(normalize(shall_m.group(1)).rstrip(';"')) if shall_m else ""

        # Emit one entry per (fiscal_year, amount) pair
        seen_fy: set[str] = set()
        for amt_s, fy_s in amt_re:
            if fy_s in seen_fy:
                continue
            seen_fy.add(fy_s)
            restrictions.append({
                "section": sec_num,
                "program_id": prog_id,
                "program_name": title_case(prog_name),
                "dept_code": prog_id[:3],
                "fund_type": fund_type,
                "amount": parse_dollar(amt_s),
                "fiscal_year": fy_s,
                "purpose": purpose,
                "type": "restriction",
                "bill": "HB1800",
                "source": f"HB1800 CD1 §{sec_num}",
            })

        if not amt_re:
            # Section without a dollar amount (rare) — skip
            pass

    return restrictions


# ── HB300 §13 enacted grants ─────────────────────────────────────────────────
#
# Same numbered-entry format as HB1800 §13.1 but:
# - Multiple expending agencies (not just LBR903)
# - Contains non-breaking spaces (\xa0) in the raw file

def extract_hb300_grants(raw: str) -> list[dict]:
    """HB300 CD1 §13 — enacted supplemental grants ($10M)."""
    text = normalize(raw)

    start = text.find("SECTION 13. APPROPRIATIONS")
    if start < 0:
        start = text.find("SECTION 13. APPROPRIATIONS")
    # Also try without period variant
    if start < 0:
        idx = text.find("SECTION 13.")
        if idx >= 0 and "APPROPRIATIONS" in text[idx:idx+60].upper():
            start = idx
    if start < 0:
        print("WARNING: §13 not found in HB300_CD1", file=sys.stderr)
        return []
    end = text.find("SECTION 14.", start)
    if end < 0:
        end = len(text)
    block = text[start:end]

    header_re = re.compile(
        r'(\d+)\.\s+\$\s*([\d,]+\.?\d*)\s+(.+?)(?=\s*\d+\.\s+\$|\Z)',
        re.DOTALL
    )
    grants: list[dict] = []

    for m in header_re.finditer(block):
        seq = int(m.group(1))
        amount = parse_dollar(m.group(2))
        rest = m.group(3)

        add_pos = rest.upper().find("ADD FUNDS")
        if add_pos < 0:
            name_raw = rest.split('\n')[0].strip()
            purpose_raw = ""
        else:
            name_raw = rest[:add_pos].split('\n')[0].strip()
            add_text = rest[add_pos:]
            costs_m = re.search(
                r'FOR COSTS RELATED TO (.+?)'
                r'(?:\s*FOR\s+[A-Z][A-Z &\-\']+\s*\([A-Z]{3}\d+\))',
                add_text, re.IGNORECASE | re.DOTALL
            )
            purpose_raw = normalize(costs_m.group(1)).rstrip(";., ") if costs_m else ""

        # Program id and name — extract the text immediately preceding (PROG_ID)
        prog_id_m = re.search(r'\(([A-Z]{3}\d{3,4})\)', rest)
        prog_id = prog_id_m.group(1) if prog_id_m else ""

        prog_name = ""
        if prog_id_m:
            # The program name is the last "FOR X (PROG)" match before the PROG_ID paren
            before_paren = rest[:prog_id_m.start()]
            # Walk backwards from the paren to find the last "FOR " before the name
            for_m = list(re.finditer(r'\bFOR\b\s+', before_paren, re.IGNORECASE))
            if for_m:
                last_for = for_m[-1]
                name_candidate = before_paren[last_for.end():].strip()
                prog_name = title_case(normalize(name_candidate))

        grants.append({
            "seq": seq,
            "recipient": title_case(name_raw.strip('."')),
            "amount": amount,
            "purpose": title_case(purpose_raw) if purpose_raw else "",
            "program_id": prog_id,
            "program_name": prog_name,
            "dept_code": prog_id[:3] if prog_id else "",
            "type": "grant",
            "bill": "HB300",
            "source": "HB300 CD1 §13",
        })

    return grants


# ── HB300 §4-§12 enacted purpose restrictions ────────────────────────────────

def extract_hb300_restrictions(raw: str) -> list[dict]:
    """HB300 CD1 §4-§12 — enacted purpose restrictions / earmarks."""
    text = normalize(raw)

    start = text.find("SECTION 4. Provided")
    if start < 0:
        start = text.find("SECTION 4.")
    if start < 0:
        return []
    end = text.find("SECTION 13.", start)
    if end < 0:
        end = len(text)
    block = text[start:end]

    sec_re = re.compile(
        r'SECTION\s+(\d+)\.\s+Provided that (?:out of |of )?the (\S+) (?:fund )?appropriation[s]? for\s+'
        r'([^(]+?)\s*\(([A-Z]{3}[\d\-]{3,10})\)',
        re.IGNORECASE
    )

    all_matches_hb300 = list(sec_re.finditer(block))

    restrictions: list[dict] = []
    for idx, m in enumerate(all_matches_hb300):
        sec_num = m.group(1)
        fund_type = m.group(2).lower()
        prog_name = normalize(m.group(3))
        prog_id = m.group(4).replace("-", "")[:6]  # clean up e.g. "BUF721-BUF728"

        after_start = m.end()
        after_end = all_matches_hb300[idx + 1].start() if idx + 1 < len(all_matches_hb300) else len(block)
        after = block[after_start:after_end]

        amt_re = re.findall(
            r'\$\s*([\d,]+(?:\.\d+)?) or so much thereof[^f]*for fiscal year (\d{4}(?:-\d{4})?)',
            after, re.IGNORECASE
        )
        shall_m = re.search(r'shall be\s+(.+?)(?:;|\.)', after[:500], re.DOTALL | re.IGNORECASE)
        purpose = title_case(normalize(shall_m.group(1)).rstrip(';"')) if shall_m else ""

        seen_fy: set[str] = set()
        for amt_s, fy_s in amt_re:
            if fy_s in seen_fy:
                continue
            seen_fy.add(fy_s)
            restrictions.append({
                "section": sec_num,
                "program_id": prog_id,
                "program_name": title_case(prog_name),
                "dept_code": prog_id[:3],
                "fund_type": fund_type,
                "amount": parse_dollar(amt_s),
                "fiscal_year": fy_s,
                "purpose": purpose,
                "type": "restriction",
                "bill": "HB300",
                "source": f"HB300 CD1 §{sec_num}",
            })

    return restrictions


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    hb1800_text = HB1800_CD1.read_text(encoding="utf-8", errors="replace")
    hb300_text  = HB300_CD1.read_text(encoding="utf-8", errors="replace")

    print("Extracting HB1800 §13.1 supplemental grants …")
    hb1800_grants = extract_hb1800_grants(hb1800_text)
    print(f"  → {len(hb1800_grants)} grants, "
          f"${sum(g['amount'] for g in hb1800_grants):,.0f} total")

    print("Extracting HB1800 §11.x purpose restrictions …")
    hb1800_restrictions = extract_hb1800_restrictions(hb1800_text)
    print(f"  → {len(hb1800_restrictions)} restrictions")
    for r in hb1800_restrictions:
        print(f"     §{r['section']} {r['program_id']} FY{r['fiscal_year']} "
              f"${r['amount']:,.0f}  {r['purpose'][:60]}")

    print("Extracting HB300 §13 enacted grants …")
    hb300_grants = extract_hb300_grants(hb300_text)
    print(f"  → {len(hb300_grants)} grants, "
          f"${sum(g['amount'] for g in hb300_grants):,.0f} total")

    print("Extracting HB300 §4-§12 enacted purpose restrictions …")
    hb300_restrictions = extract_hb300_restrictions(hb300_text)
    print(f"  → {len(hb300_restrictions)} restrictions")

    out = {
        "metadata": {
            "description": (
                "Worksheet line item appropriations — grants and purpose "
                "restrictions within programs"
            ),
            "sources": [
                "HB1800 CD1 (2026 Supplemental Appropriations Act), "
                "§13.1 grants and §11.x restrictions",
                "HB300 CD1 (2025 Biennial Appropriations Act), "
                "§13 grants and §4–§12 restrictions",
            ],
        },
        "hb1800_grants": hb1800_grants,
        "hb1800_restrictions": hb1800_restrictions,
        "hb300_grants": hb300_grants,
        "hb300_restrictions": hb300_restrictions,
    }

    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    total_items = (len(hb1800_grants) + len(hb1800_restrictions)
                   + len(hb300_grants) + len(hb300_restrictions))
    print(f"\nWrote {OUT_PATH}  ({total_items} total line items)")


if __name__ == "__main__":
    main()
