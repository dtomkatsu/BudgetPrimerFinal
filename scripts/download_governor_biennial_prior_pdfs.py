"""Download Governor's Executive Biennium Budget FY2023-25 department PDFs
from budget.hawaii.gov — used as a fallback source for program-purpose
tooltips when the FY25-27 biennial PDF has a stripped/missing narrative
page for a given program.

Why we need two biennial vintages
---------------------------------
The FY25-27 biennial LNR PDF has 14 narrative pages whose text layer was
entirely stripped (only section headers A/B/C/D remain, no body).  The
FY23-25 LNR PDF has the same narrative structure WITH the body text
intact.  Similarly, HTH520 is missing its section-A narrative page in the
FY25-27 biennial but present in FY23-25.  The prior biennium's objectives
describe the same program purpose and are a clean fallback.

Coverage discovered from FY23-25 when FY25-27 fails:
  HTH520, LNR101, LNR102, LNR111, LNR802, LNR907, LNR908  (7 programs)

Programs still missing after FY23-25 fallback (created/renamed after 2022):
  AGS820  (Hawaii Broadband & Digital Equity Office — post-2022)
  LAW822  (State Fire Marshal — transferred into DLE after 2022)
  LNR909  (Mauna Kea Stewardship — est. Act 255, SLH 2022)
  UOH120  (UH Manoa CTAHR reorg — post-2022)
  SUB201/401/501 (subsidies — no standard narrative in biennial PDFs)

The downloader includes every FY23-25 department PDF for completeness and
future-proofing, but only AGS/HTH/LAW/LNR/UOH are currently relevant.
Naming matches the FY25-27 convention (NN_DEPT.pdf) so the extractor's
department-code derivation works unchanged.

Note: FY23-25 used "Public Safety" (25_PSD) rather than the post-split
"Corrections and Rehabilitation" (15_CCR) + "Law Enforcement" (25_LAW)
that FY25-27 uses.  We save it as 25_PSD to reflect the source rather
than force a shape it didn't have at the time.
"""
import urllib.request
import pathlib
import sys

PDFS = [
    ("09_AGS", "Accounting and General Services",        "https://budget.hawaii.gov/wp-content/uploads/2022/12/08.-Department-of-Accounting-and-General-Services-FB23-25-PFP.Lk0_.pdf"),
    ("10_AGR", "Agriculture",                            "https://budget.hawaii.gov/wp-content/uploads/2022/12/09.-Department-of-Agriculture-FB23-25-PFP.Lk0_.pdf"),
    ("11_ATG", "Attorney General",                       "https://budget.hawaii.gov/wp-content/uploads/2022/12/10.-Department-of-the-Attorney-General-FB23-25-PFP.Lk0_.pdf"),
    ("12_BUF", "Budget and Finance",                     "https://budget.hawaii.gov/wp-content/uploads/2022/12/11.-Department-of-Budget-and-Finance-FB23-25-PFP.Lk0_.pdf"),
    ("13_BED", "Business, Economic Development & Tourism","https://budget.hawaii.gov/wp-content/uploads/2022/12/12.-Department-of-Business-Economic-Development-and-Tourism-FB23-25-PFP.Lk0_.pdf"),
    ("14_CCA", "Commerce and Consumer Affairs",          "https://budget.hawaii.gov/wp-content/uploads/2022/12/13.-Department-of-Commerce-and-Consumer-Affairs-FB23-25-PFP.Lk0_.pdf"),
    ("16_DEF", "Defense",                                "https://budget.hawaii.gov/wp-content/uploads/2021/03/14.-Department-of-Defense-FB23-25-PFP.Lk2_.pdf"),
    ("17_EDN", "Education",                              "https://budget.hawaii.gov/wp-content/uploads/2021/03/15.-Department-of-Education-FB23-25-PFP.Lk1_.pdf"),
    ("18_GOV", "Office of the Governor",                 "https://budget.hawaii.gov/wp-content/uploads/2021/03/16.-Office-of-the-Governor-FB23-25.Lk1_.pdf"),
    ("19_HHL", "Hawaiian Home Lands",                    "https://budget.hawaii.gov/wp-content/uploads/2022/12/17.-Department-of-Hawaiian-Home-Lands-FB23-25-PFP.Lk0_.pdf"),
    ("20_HTH", "Health",                                 "https://budget.hawaii.gov/wp-content/uploads/2021/03/18.-Department-of-Health-FB23-25-PFP.Lk2_.pdf"),
    ("21_HRD", "Human Resources Development",            "https://budget.hawaii.gov/wp-content/uploads/2022/12/19.-Department-of-Human-Resources-Development-FB23-25-PFP.Lk0_.pdf"),
    ("22_HMS", "Human Services",                         "https://budget.hawaii.gov/wp-content/uploads/2022/12/20.-Department-of-Human-Services-FB23-25-PFP.Lk0_.pdf"),
    ("23_LBR", "Labor and Industrial Relations",         "https://budget.hawaii.gov/wp-content/uploads/2022/12/21.-Department-of-Labor-and-Industrial-Relations-FB23-25-PFP.Lk0_.pdf"),
    ("24_LNR", "Land and Natural Resources",             "https://budget.hawaii.gov/wp-content/uploads/2022/12/22.-Department-of-Land-and-Natural-Resources-FB23-25-PFP.Lk0_.pdf"),
    ("25_LAW", "Law Enforcement (split from PSD in 2022)","https://budget.hawaii.gov/wp-content/uploads/2022/12/23.-Department-of-Law-Enforcement-FB23-25-PFP.Lk0_.pdf"),
    ("25_PSD", "Public Safety / Corrections (pre-split)", "https://budget.hawaii.gov/wp-content/uploads/2022/12/25.-Department-of-Public-Safety-Corrections-and-Rehabilitation-FB23-25-PFP.Lk0_.pdf"),
    ("26_LTG", "Lieutenant Governor",                    "https://budget.hawaii.gov/wp-content/uploads/2022/12/24.-Office-of-the-Lieutenant-Governor-FB23-25-PFP.Lk0_.pdf"),
    ("28_TAX", "Taxation",                               "https://budget.hawaii.gov/wp-content/uploads/2022/12/26.-Department-of-Taxation-FB23-25-PFP.Lk0_.pdf"),
    ("29_TRN", "Transportation",                         "https://budget.hawaii.gov/wp-content/uploads/2022/12/27.-Department-of-Transportation-FB23-25-PFP.Lk0_.pdf"),
    ("30_UOH", "University of Hawaii",                   "https://budget.hawaii.gov/wp-content/uploads/2021/03/28.-University-of-Hawaii-FB23-25-PFP.Lk1_.pdf"),
]

def main():
    out_dir = pathlib.Path(__file__).parent.parent / "data" / "raw" / "governor_biennial_fy23-25"
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, label, url in PDFS:
        out_path = out_dir / f"{name}.pdf"
        if out_path.exists() and out_path.stat().st_size > 10_000:
            print(f"SKIP  {name} ({label}) — exists ({out_path.stat().st_size:,} bytes)")
            continue
        print(f"FETCH {name} ({label})...", end=" ", flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            out_path.write_bytes(data)
            print(f"{len(data):,} bytes")
        except Exception as e:
            print(f"FAILED: {e}")
            # Don't abort — the prior biennium is a fallback, not required.
            continue

    print(f"\nDone. Attempted {len(PDFS)} PDFs in {out_dir}")

if __name__ == "__main__":
    main()
