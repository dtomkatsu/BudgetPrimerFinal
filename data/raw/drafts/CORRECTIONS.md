# Draft text corrections

The bill draft texts in this directory are the **source-of-truth inputs** for the
draft-compare feature. Every `docs/js/draft_comparison_*.json` and
`docs/js/projects_*.json` artifact is regenerated from them via
`scripts/compare_drafts.py` and `scripts/compare_projects.py`.

Most drafts are produced mechanically by `scripts/download_bill.py` (HTM download
or RTF conversion). That conversion is lossy: it silently drops a few pieces of
markup the parser depends on — notably **Section 14 program headers** and
**struck-through** project/appropriation lines (strikethrough has no plain-text
representation). Where that loss corrupts the parsed output, the affected draft
carries **hand-applied corrections** recorded here.

## Why a guard exists

A draft with manual corrections is flagged `"protected": true` in
`metadata.json`. `scripts/download_bill.py` refuses to overwrite a protected
draft unless you pass `--force`. This prevents an innocent re-download/re-convert
from silently reintroducing the bugs the corrections fixed.

If you ever must regenerate a protected draft from source:

1. Run with `--force` (e.g. `python scripts/download_bill.py HB1800 --draft CD1 --from-rtf "HB 1800 CD1.rtf" --force`).
2. **Re-apply every correction listed below** to the freshly converted text.
3. Regenerate the JSON artifacts (`compare_drafts.py` + `compare_projects.py`).
4. Re-verify by re-parsing — the parser should emit no `Reconcile: ... excess`
   warnings for the corrected programs.

## HB1800_CD1.txt — corrections (commit 08c5f83)

Both fixes restore markup the RTF→text conversion dropped. Neither changes any
dollar total (Section 14 does not feed program/grand totals); both fix the
*attribution* of capital projects on the projects page.

1. **Restored missing program header — Daniel K. Inouye International Airport.**
   The conversion dropped the `TRN102 - DANIEL K. INOUYE INTERNATIONAL AIRPORT`
   header from the Section 14 CIP project list (it sits right after the
   `C.  TRANSPORTATION FACILITIES` category header). Without it, the first
   Transportation project inherited the previous program's context
   (`LBR903`, Office of Community Services), producing a phantom $430M FY27 swing
   (−$215M "removed" from TRN102, +$215M "added" to OCS). SD1 still has this
   header at the equivalent spot, confirming it was lost in conversion, not absent
   from the bill.

2. **Removed struck project — Stadium Improvements, Kauai.**
   CD1 struck this project's `$700,000` C-fund FY26 appropriation; Part II shows
   the corresponding cut (LNR101 FY26 C-fund `3,355,000 → 2,655,000`). The
   strikethrough was lost in conversion, so the project text survived and the
   project list overstated LNR101 by $700K with no Part II backing (the parser
   flagged this as a `Reconcile: $700,000 excess` for `LNR101 fund=C fy=2026`).
   Removed the item-11 block (`STADIUM IMPROVEMENTS, KAUAI`); the two
   distinct projects `HANAPEPE STADIUM IMPROVEMENTS, KAUAI` (item 19) and
   `VIDINHA STADIUM IMPROVEMENTS, KAUAI` (item 21) are unaffected. After the fix,
   Section 14 LNR101 C-fund reconciles exactly with Part II (CD1 $2,655,000 /
   HD1 $3,355,000), and the projects page correctly shows the stadium as
   *removed* in CD1.
