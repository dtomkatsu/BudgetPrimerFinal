# Budget Primer FY2026–27 — Rebuild Pipeline

**Goal:** Recreate the Budget Primer (FY2025–26 edition, InDesign) as a single-source
pipeline that emits (a) an interactive Squarespace code-injection bundle and (b) a
print-faithful PDF styled identically to the original.

## Architecture

```
report2027/
  sources/            original primer PDF + B&F revenue plans PDF (downloaded)
  tools/build_data.py extraction + merge → data/report_data.json  [WORKING]
  manual/research.json  hand-verified facts from bill research (Jud/Leg/OHA acts,
                        one-time + emergency approps)             [PENDING agents]
  data/report_data.json single source of truth for every number   [after research]
  web/                one HTML doc, two render modes:
                        - screen: Chart.js interactive (repo already self-hosts it)
                        - print:  @page 8.5×11 CSS, deterministic SVG charts
  dist/
    primer-embed.html   self-contained Squarespace injection bundle
    Budget-Primer-FY2026-27.pdf  via headless Chrome --print-to-pdf
```

One HTML source renders both outputs; `@media print` swaps interactive canvases for
pre-rendered SVG so the PDF is deterministic and matches the original layout.

## Page-by-page mapping (original → FY27 edition)

| Pg | Content | FY27 data source |
|----|---------|------------------|
| 1  | Cover | static (year text changes) |
| 2  | TOC/about | static |
| 3  | Budget Basics branch cards | static |
| 4  | Fig 1 budget lifecycle donut | static |
| 5  | Table 1 branch × category | Exec: Act 175 FY27 (repo). Jud/Leg/OHA + one-time/emergency: research.json |
| 6  | Fig 2 dept stacked bars | departments_act175_fy2027.json + research one-time/emergency segments |
| 7  | Obligated-costs callout; Fig 3 CIP pie | CIP functional `category` from budget_allocations_fy2027_post_veto.csv |
| 8  | Photo + one-time/emergency cards | research.json |
| 9  | Fig 4 means-of-finance pie | operating fund_category rollup (Other Federal → Other, per FY26 repro) |
| 10 | Fig 5 tax revenue pie + tax cards | revenue_plans_fb2527.pdf p.2, FY2027 column [EXTRACTED, validated against FY26 published figures] |
| 11 | Fig 6 ITEP quintiles + tax-credit box | unchanged (ITEP 2024; check for newer DOTAX credit report) |
| 12 | Endnotes | regenerated with 2026-session citations |

## Validation approach

`build_data.py --validate` reproduces the *published* FY25–26 numbers from Act 250
FY2026 repo data. Result: tax figures, CIP total, Transportation, Special Funds match
exactly. Known deltas (published PDF vs current repo parser):

- Operating: published $19.88B vs repo $19.941B (repo parser has been fixed since
  publication; repo is authoritative going forward)
- Fig 3 categories: published used the act's functional categories (CATEGORY_MAP in
  fast_parser.py), not dept codes — switch extractor to the post_veto CSV `category` col
- Fig 4: published maps "Other Federal Funds" into Other, not Federal

## OPEN QUESTIONS (Devin)

1. **Which total view?** post-veto CSVs (site's historical pane, FY27 total $22.09B)
   vs summary_stats_act175_fy2027 ($24.85B — includes revenue-bond CIP etc.). Table 1
   should probably mirror whatever the FY26 edition's basis was (act-level gross).
2. **Fonts.** Original = InDesign: Encorpada Classic (cover), Glober Black (headers),
   Source Sans Pro (body), Brandon Grotesque (logo). None installed locally; site uses
   Poppins/Manrope. Options: (a) Adobe Fonts web-project embed code from the org CC
   account → pixel-exact; (b) free stand-ins (Abril Fatface / Archivo Black / Source
   Sans 3). Build supports both via one @font-face block.
3. **Newer COR forecast?** The linked revenue PDF is the Sept 2024 COR meeting (same
   source as FY26 edition, endnote 16). A March 2026 COR forecast likely exists; the
   FY26 edition used the older one deliberately (means-of-finance consistency). Keep?

## Status log

- 2026-07-09: PDFs downloaded; fonts identified; revenue table extracted & validated;
  build_data.py drafted + FY26 validation run; two research agents dispatched
  (Jud/Leg/OHA 2026 acts; FY27 one-time & emergency approps).

## Status log (cont.)

- 2026-07-09 pm: research complete (see manual/research.json — Jud/Leg/OHA + one-time/
  emergency, all FY27). Validation 13/13 within tolerance (2 accepted parser-vintage
  deltas). Full pipeline built and running: build_data.py → render_report.py →
  web/index.html (12 pages, inline SVG charts, tooltip JS) → make pdf (headless
  Chrome, 12pp letter) + make embed (dist/primer-embed.html). Palette sampled from
  original (#6b9080 family); photos extracted from original PDF into web/assets/.
  Fonts: free stand-ins active (Abril Fatface/Archivo Black/Source Sans 3); swap via
  the three CSS font variables when the Adobe kit is available.
  Editorial defaults taken (flag for Devin review): Table 1 one-time = featured acts
  only (FY26 convention); Act 32 $55M shown in OHA column, not Executive; Legislature
  = published-style $51.9M; Fig 2 one-time/emergency segments mapped by dept per
  research.json featured items.
