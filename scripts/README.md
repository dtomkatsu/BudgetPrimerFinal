# BudgetPrimer Scripts

This directory contains utility scripts for working with the BudgetPrimer package.

## Available Scripts

### `process_budget.py`

Process and visualize Hawaii State Budget data.

**Usage:**
```bash
python scripts/process_budget.py <input_file> [options]
```

**Arguments:**
- `input_file`: Path to the budget file to process

**Options:**
- `--output-dir`: Output directory for results (default: 'output')
- `--fiscal-year`: Fiscal year to analyze (default: 2026)
- `--top-n`: Number of top items to show in charts (default: 15)

**Example:**
```bash
# Process the budget file and generate visualizations
python scripts/process_budget.py data/raw/budget_fy2026.txt --output-dir results --fiscal-year 2026 --top-n 20
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
