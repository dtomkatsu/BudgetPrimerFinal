# Windsurf AI Rules for BudgetPrimerFinal

Authoritative guidelines for AI-assisted changes to this repository. Follow these rules to maintain consistency, correctness, and project conventions.

## 1) Project Objective
- Generate clear, consistent departmental budget reports (HTML + charts).
- Ensure budget numbers are consistently formatted and readable across:
  - Department charts
  - Department report HTML (summary cards + tables)
  - Index page department cards and summary tiles

## 2) Number Formatting Rules (Authoritative)
- All numeric inputs to formatters are in millions (M) unless explicitly noted.
- Display amounts based on threshold:
  - If amount ≥ 1000 (million) → show in billions with one decimal place and suffix `B`: e.g., `$1.2B`.
  - If amount < 1000 → show in millions with no decimals and suffix `M`: e.g., `$850M`.
- Always include a dollar sign `$` and thousands separators.
- Apply these rules consistently in ALL places (charts, summary cards, tables, index page).

### Implementation Requirements
- Prefer centralized helpers over inline formatting:
  - `format_amount(amount_millions)` and/or `format_budget(amount_millions)` should return the fully formatted string including `$` and the unit (`M` or `B`).
  - Do NOT inline format in HTML f-strings (avoid `.../1_000_000 ... 'M'`). Always call the helper.
- Keep helper logic in one place; update all call sites to use it.

## 3) Charts and Visuals
- Chart labels must follow the same formatting rules above (B for ≥ 1000M, M otherwise).
- Labels placement:
  - Place labels inside large segments; for small segments use outside labels with leader lines.
  - Use overlap-avoidance strategy already implemented; do not regress this.
- Improve readability: sufficient figure size, font sizes, and clear legend. Maintain centered stacked bar appearance.

## 4) HTML/CSS and Templates
- When embedding CSS inside Python f-strings, ESCAPE curly braces by doubling them: `{{` and `}}`.
  - This prevents f-string parsing errors (e.g., `display: flex;`).
- Avoid double dollar signs in templates:
  - If helper returns a value with `$`, do NOT prepend `$` again in HTML.
- Keep the index page default sort to operating budget (descending) on page load.

## 5) Files and Key Locations
- Main generation script: `scripts/generate_departmental_reports.py`
  - Methods of interest:
    - `create_department_chart`
    - `generate_html_report`
    - `create_index_page`
    - `format_amount` / `format_budget` (helpers)
- Parsing utilities (contextual): `scripts/parse_budget.py`
- PDF extraction (contextual): `scripts/extract_pdf_better.py`
- Output directory: `data/output/departmental_reports`

## 6) Commands and Workflows
- Regenerate reports after any change to generation logic:
  ```bash
  python scripts/generate_departmental_reports.py data/processed/budget_allocations_fy2026_post_veto.csv
  ```
- Open `data/output/departmental_reports/index.html` to validate visuals.

## 7) Validation Checklist (Run after changes)
- Number formatting:
  - Department report summary cards show `$x.xB` when ≥ 1000M; `$xxxM` otherwise.
  - Table rows for fund types follow the same rule.
  - Charts display labels with the same units and style.
  - Index page department cards and summary tiles use the same formatting; no duplicated `$`.
- UI/UX:
  - Legend visible and not clipped.
  - Labels not overlapping; leader lines appear for small segments.
  - Index default sort is operating budget descending.
- HTML/CSS:
  - All CSS blocks in f-strings use `{{ ... }}`.
  - No console or Python errors during generation.

## 8) Coding Standards
- Python 3, use built-in logging for status and errors.
- Prefer small, targeted diffs; do not reflow entire files.
- Add imports if needed; keep dependencies minimal (pandas, matplotlib, numpy, base64, logging, pathlib, argparse).
- Handle None/NaN gracefully in formatting and chart logic.
- Keep functions pure where practical; centralize formatting logic.

## 9) Safety and Tooling Rules (for AI)
- Do not run destructive shell commands automatically.
- When running commands, set the working directory via tool `cwd` rather than using `cd`.
- Only open browser preview after starting a web server (not required here unless one is introduced).
- Use write/edit tools conservatively; include minimal contextual patches.

## 10) Do-Not List
- Do NOT inline number formatting in multiple places—always use the helper.
- Do NOT forget to escape CSS braces in f-strings.
- Do NOT add or remove dollar signs inconsistently; avoid double `$`.
- Do NOT change data semantics or units without explicit instruction.
- Do NOT introduce UI regressions to label placement or legend.

## 11) Glossary
- "amount" refers to millions (M) unless stated otherwise.
- `M` = Millions; `B` = Billions (1000M).
- "Index page" = the landing page listing all departments with summary cards and sort controls.

## 12) When In Doubt
- Centralize logic, remove duplication, and run the Validation Checklist.
- If a place shows incorrect units, refactor it to use the shared formatter.

## 13) Documentation Updates
- Update `README.md` after every substantial change, including any of the following:
  - Creation of a new file
  - Significant refactor
  - Alteration of approximately 25% or more of an existing file
- The README update should briefly describe:
  - What changed and why
  - Any new commands or options
  - Any new files or directories and their purposes
  - Any impacts on usage, outputs, or workflows

## 14) Loop Handling in Cascade
- If the assistant detects it is stuck in a loop (repeating the same or substantially similar outputs/actions), it must:
  1. Stop the loop immediately.
  2. State explicitly that a loop was detected and halted.
  3. Summarize the last successful state and what it was trying to achieve.
  4. Propose a different, concrete next step (e.g., gather logs, inspect another file, add guards, ask a clarifying question).
  5. If applicable, add a minimal guard in code or logic to prevent the loop condition from recurring.
