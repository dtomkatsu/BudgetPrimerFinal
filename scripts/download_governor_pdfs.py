"""Download Governor's Supplemental Budget FY2027 PDFs from budget.hawaii.gov.

One-shot script. Downloads 22 department PDFs (09 AGS through 30 UH).
"""
import urllib.request
import pathlib
import sys

PDFS = [
    ("09_AGS", "Accounting and General Services", "https://budget.hawaii.gov/wp-content/uploads/2025/12/09.-Department-of-Accounting-and-General-Services-FY-27-SUPP.xApH_-1.pdf"),
    ("10_AGR", "Agriculture", "https://budget.hawaii.gov/wp-content/uploads/2025/12/10.-Department-of-Agriculture-FY-27-SUPP.pdf"),
    ("11_ATG", "Attorney General", "https://budget.hawaii.gov/wp-content/uploads/2025/12/11.-Department-of-Attorney-General-FY-27-SUPP.xApH_.pdf"),
    ("12_BUF", "Budget and Finance", "https://budget.hawaii.gov/wp-content/uploads/2025/12/12.-Department-of-Budget-and-Finance-FY-27-SUPP.xApH_.pdf"),
    ("13_BED", "Business, Economic Development and Tourism", "https://budget.hawaii.gov/wp-content/uploads/2025/12/13.-Department-of-Business-Economic-Development-and-Tourism-FY-27-SUPP.xApH_.v1.pdf"),
    ("14_CCA", "Commerce and Consumer Affairs", "https://budget.hawaii.gov/wp-content/uploads/2025/12/14.-Department-of-Commerce-and-Consumer-Affairs-FY-27-SUPP.xApH_-1.pdf"),
    ("15_CCR", "Corrections and Rehabilitation", "https://budget.hawaii.gov/wp-content/uploads/2025/12/15.-Department-of-Corrections-and-Rehabilitation-FY-27-SUPP.xApH_-1.pdf"),
    ("16_DEF", "Defense", "https://budget.hawaii.gov/wp-content/uploads/2025/12/16.-Department-of-Defense-FY-27-SUPP.xApH_.pdf"),
    ("17_EDN", "Education", "https://budget.hawaii.gov/wp-content/uploads/2025/12/17.-Department-of-Education-FY-27-SUPP.xApH_-1.pdf"),
    ("18_GOV", "Governor", "https://budget.hawaii.gov/wp-content/uploads/2025/12/18.-Office-of-the-Governor-FY-27-SUPP.xApH_-1.pdf"),
    ("19_HHL", "Hawaiian Home Lands", "https://budget.hawaii.gov/wp-content/uploads/2025/12/19.-Department-of-Hawaiian-Home-Lands-FY-27-SUPP.xApH_.pdf"),
    ("20_HTH", "Health", "https://budget.hawaii.gov/wp-content/uploads/2025/12/20.-Department-of-Health-FY-27-SUPP.xApH_-2.pdf"),
    ("21_HRD", "Human Resources Development", "https://budget.hawaii.gov/wp-content/uploads/2025/12/21.-Department-of-Human-Resources-Development-FY-27-SUPP.xApH_-1.pdf"),
    ("22_HMS", "Human Services", "https://budget.hawaii.gov/wp-content/uploads/2025/12/22.-Department-of-Human-Services-FY-27-SUPP.xApH_.pdf"),
    ("23_LBR", "Labor and Industrial Relations", "https://budget.hawaii.gov/wp-content/uploads/2025/12/23.-Department-of-Labor-and-Industrial-Relations-FY-27-SUPP.xApH_.pdf"),
    ("24_LNR", "Land and Natural Resources", "https://budget.hawaii.gov/wp-content/uploads/2025/12/24.-Department-of-Land-and-Natural-Resources-FY-27-SUPP.xApH_.pdf"),
    ("25_LAW", "Law Enforcement", "https://budget.hawaii.gov/wp-content/uploads/2025/12/25.-Department-of-Law-Enforcement-FY-27-SUPP.xApH_.pdf"),
    ("26_LTG", "Lieutenant Governor", "https://budget.hawaii.gov/wp-content/uploads/2025/12/26.-Office-of-the-Lieutenant-Governor-FY-27-SUPP.xApH_-1.pdf"),
    ("27_SUB", "Subsidies", "https://budget.hawaii.gov/wp-content/uploads/2025/12/27.-Subsidies-FY-27-SUPP.xApH_.pdf"),
    ("28_TAX", "Taxation", "https://budget.hawaii.gov/wp-content/uploads/2025/12/28.-Department-of-Taxation-FY-27-SUPP.xApH_-1.pdf"),
    ("29_TRN", "Transportation", "https://budget.hawaii.gov/wp-content/uploads/2025/12/29.-Department-of-Transportation-FY-27-SUPP.xApH_.pdf"),
    ("30_UOH", "University of Hawaii", "https://budget.hawaii.gov/wp-content/uploads/2025/12/30.-University-of-Hawaii-FY-27-SUPP.xApH_.pdf"),
]

def main():
    out_dir = pathlib.Path(__file__).parent.parent / "data" / "raw" / "governor_supplemental_fy27"
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
