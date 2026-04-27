"""Download Governor's Executive Biennium Budget FY2025-27 department PDFs
from budget.hawaii.gov.

One-shot script.  Downloads 21 department PDFs.  These are the full biennial
budget PDFs (submitted Dec 2024) — unlike the FY27 supplemental, they include
'A. Statement of Program Objectives' narrative pages for EVERY program, not
just those with requested changes.  Used as the primary source for program-
purpose tooltips in the SPA (see scripts/extract_governor_narratives.py).

Note: biennial numbering skips 'Subsidies' (27) which appears only in the
supplemental.  That's fine — SUB programs that need tooltips are covered by
the supplemental extraction.
"""
import urllib.request
import pathlib
import sys

PDFS = [
    ("09_AGS", "Accounting and General Services", "https://budget.hawaii.gov/wp-content/uploads/2024/12/08.-Department-of-Accounting-and-General-Services-FB25-27-PFP.7Lt-1.pdf"),
    ("10_AGR", "Agriculture",                     "https://budget.hawaii.gov/wp-content/uploads/2024/12/09.-Department-of-Agriculture-FB25-27-PFP.7Lt.pdf"),
    ("11_ATG", "Attorney General",                "https://budget.hawaii.gov/wp-content/uploads/2024/12/10.-Department-of-the-Attorney-General-FB25-27-PFP.7Lt.pdf"),
    ("12_BUF", "Budget and Finance",              "https://budget.hawaii.gov/wp-content/uploads/2024/12/11.-Department-of-Budget-and-Finance-FB25-27-PFP.7Lt.pdf"),
    ("13_BED", "Business, Economic Development and Tourism", "https://budget.hawaii.gov/wp-content/uploads/2024/12/12.-Department-of-Business-Economic-Development-and-Tourism-FB25-27-PFP.7LT.pdf"),
    ("14_CCA", "Commerce and Consumer Affairs",   "https://budget.hawaii.gov/wp-content/uploads/2024/12/13.-Department-of-Commerce-and-Consumer-Affairs-FB25-27-PFP.7Lt.pdf"),
    ("15_CCR", "Corrections and Rehabilitation",  "https://budget.hawaii.gov/wp-content/uploads/2024/12/14.-Department-of-Corrections-and-Rehabilitation-FB25-27-PFP.7Lt-1.pdf"),
    ("16_DEF", "Defense",                         "https://budget.hawaii.gov/wp-content/uploads/2024/12/15.-Department-of-Defense-FB25-27-PFP.7Lt.pdf"),
    ("17_EDN", "Education",                       "https://budget.hawaii.gov/wp-content/uploads/2024/12/16.-Department-of-Education-FB25-27-PFP.7Lt.pdf"),
    ("18_GOV", "Office of the Governor",          "https://budget.hawaii.gov/wp-content/uploads/2024/12/17.-Office-of-the-Governor-FB25-27-PFP.7Lt.pdf"),
    ("19_HHL", "Hawaiian Home Lands",             "https://budget.hawaii.gov/wp-content/uploads/2024/12/18.-Department-of-Hawaiian-Home-Lands-FB25-27-PFP.7Lt.pdf"),
    ("20_HTH", "Health",                          "https://budget.hawaii.gov/wp-content/uploads/2024/12/19.-Department-of-Health-FB25-27-PFP.7Lt.pdf"),
    ("21_HRD", "Human Resources Development",     "https://budget.hawaii.gov/wp-content/uploads/2024/12/20.-Department-of-Human-Resources-Development-FB25-27-PFP.7Lt.pdf"),
    ("22_HMS", "Human Services",                  "https://budget.hawaii.gov/wp-content/uploads/2024/12/21.-Department-of-Human-Services-FB25-27-PFP.7Lt.pdf"),
    ("23_LBR", "Labor and Industrial Relations",  "https://budget.hawaii.gov/wp-content/uploads/2024/12/22.-Department-of-Labor-and-Industrial-Relations-FB25-27-PFP.7Lt.pdf"),
    ("24_LNR", "Land and Natural Resources",      "https://budget.hawaii.gov/wp-content/uploads/2024/12/23.-Department-of-Land-and-Natural-Resources-FB25-27-PFP.7Lt.pdf"),
    ("25_LAW", "Law Enforcement",                 "https://budget.hawaii.gov/wp-content/uploads/2024/12/24.-Department-of-Law-Enforcement-FB25-27-PFP.7Lt.pdf"),
    ("26_LTG", "Lieutenant Governor",             "https://budget.hawaii.gov/wp-content/uploads/2024/12/25.-Office-of-the-Lieutenant-Governor-FB25-27-PFP.7Lt.pdf"),
    ("28_TAX", "Taxation",                        "https://budget.hawaii.gov/wp-content/uploads/2024/12/26.-Department-of-Taxation-FB25-27-PFP.7Lt.pdf"),
    ("29_TRN", "Transportation",                  "https://budget.hawaii.gov/wp-content/uploads/2024/12/27.-Department-of-Transportation-FB25-27-PFP.7Lt.pdf"),
    ("30_UOH", "University of Hawaii",            "https://budget.hawaii.gov/wp-content/uploads/2024/12/28.-University-of-Hawaii-FB25-27-PFP.7Lt.pdf"),
]

def main():
    out_dir = pathlib.Path(__file__).parent.parent / "data" / "raw" / "governor_biennial_fy25-27"
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, label, url in PDFS:
        out_path = out_dir / f"{name}.pdf"
        if out_path.exists() and out_path.stat().st_size > 10_000:
            print(f"SKIP  {name} ({label}) — exists ({out_path.stat().st_size:,} bytes)")
            continue
        print(f"FETCH {name} ({label})...", end=" ", flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            out_path.write_bytes(data)
            print(f"{len(data):,} bytes")
        except Exception as e:
            print(f"FAILED: {e}")
            sys.exit(1)

    print(f"\nDone. {len(PDFS)} PDFs in {out_dir}")

if __name__ == "__main__":
    main()
