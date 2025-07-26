# BudgetPrimer Scripts

This directory contains utility scripts for working with the BudgetPrimer package.

## Available Scripts

### `process_budget.py`

Process and visualize Hawaii State Budget data with optional veto application.

**Usage:**
```bash
python scripts/process_budget.py <input_file> [options]
```

**Arguments:**
- `input_file`: Path to the budget file to process (PDF or text)

**Options:**
- `--output-dir`: Output directory for results (default: 'output')
- `--fiscal-year`: Fiscal year to analyze (default: 2026)
- `--top-n`: Number of top items to show in charts (default: 15)
- `--veto-mode`: How to handle vetoes: 'none', 'apply', or 'both' (default: 'none')
- `--veto-file`: Path to veto definitions CSV (default: 'data/raw/vetoes/governor_vetoes_fy2026_actual.csv')
- `--section`: Filter by section: 'operating', 'capital', or 'all' (default: 'all')

**Examples:**
```bash
# Process with vetoes applied
python scripts/process_budget.py data/raw/HB300_CD1.txt --veto-mode apply

# Generate comparison visualizations (pre- and post-veto)
python scripts/process_budget.py data/raw/HB300_CD1.txt --veto-mode both --top-n 20

# Process with custom veto file
python scripts/process_budget.py data/raw/HB300_CD1.txt --veto-mode apply --veto-file path/to/custom_vetoes.csv
```

### `analyze_budget_totals.py`

Generate detailed budget analysis reports with comprehensive breakdowns.

**Usage:**
```bash
python scripts/analyze_budget_totals.py <input_csv> [--output <output_file>]
```

**Arguments:**
- `input_csv`: Path to the parsed budget CSV file

**Options:**
- `--output`: Save analysis to Excel file (optional)

**Analysis Includes:**
- Budget totals by section and fiscal year
- Funding breakdown by category (General Fund, Special Funds, etc.)
- Detailed section-by-section analysis
- Top programs by budget amount
- Duplicate entry detection and reporting

**Examples:**
```bash
# Basic analysis with console output
python scripts/analyze_budget_totals.py data/processed/budget_parsed_fy2026.csv

# Save analysis to Excel
python scripts/analyze_budget_totals.py data/processed/budget_parsed_fy2026.csv --output analysis_results.xlsx
```

### `extract_pdf_better.py`

Extract text from PDF budget documents with improved formatting.

**Usage:**
```bash
python scripts/extract_pdf_better.py <input_pdf> <output_txt>
```

**Example:**
```bash
python scripts/extract_pdf_better.py "data/raw/HB300 CD1.pdf" "data/raw/HB300_CD1_better.txt"
```

## Creating New Scripts

When creating new scripts, follow these guidelines:

1. Add a shebang line at the top: `#!/usr/bin/env python3`
2. Include a docstring describing the script's purpose
3. Use the `argparse` module for command-line arguments
4. Add proper logging for debugging and progress tracking
5. Include error handling with informative messages
6. Add type hints for better code clarity

## Best Practices

- Keep scripts focused on a single task
- Use relative imports within the package
- Document any external dependencies
- Follow PEP 8 style guidelines
- Include example usage in the script's docstring
