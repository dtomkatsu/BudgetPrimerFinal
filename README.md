# BudgetPrimerFinal

A streamlined, well-structured Python tool for processing, analyzing, and visualizing Hawaii State Budget data, with special support for HB 300 format and veto processing.

## Project Structure

```
BudgetPrimerFinal/
├── budgetprimer/           # Core Python package
│   ├── __init__.py
│   ├── parsers/           # Budget file parsers
│   ├── models/            # Data models and schemas
│   ├── utils/             # Utility functions
│   └── analysis/          # Analysis modules
├── data/                  # Data files
│   ├── raw/              # Raw input files
│   ├── processed/        # Processed/cleaned data
│   └── output/           # Generated output files
├── notebooks/            # Jupyter notebooks for analysis
├── scripts/              # Utility scripts
├── config/               # Configuration files
├── tests/                # Test suite
└── requirements.txt      # Project dependencies
```

## Features

- **HB 300 Format Support**: Specialized parser for Hawaii's HB 300 budget format
- **Veto Processing**: Tools to apply and analyze gubernatorial vetoes
- **Duplicate Handling**: Flags duplicate entries without automatic removal
- **Fast, modular parsing** of budget documents
- **Comprehensive data models** for budget allocations
- **Robust fund type extraction** with proper validation
- **Precise transformation pipeline** from pre-veto to post-veto data
- **High-quality visualizations** matching official styles
- **Detailed Budget Analysis**: Comprehensive breakdowns by section, fund type, and program

## Prerequisites

- Python 3.12.10

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/BudgetPrimerFinal.git
   cd BudgetPrimerFinal
   ```

2. Create and activate a virtual environment:
   ```bash
   # Create virtual environment with Python 3.12.10
   python3.12 -m venv venv
   
   # Activate the virtual environment
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   # venv\Scripts\activate
   ```

3. Upgrade pip and install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

## Usage

### Data Processing

```python
from budgetprimer.parsers.budget_parser import parse_budget_file
from budgetprimer.pipeline import process_budget_data

# Parse a budget file
budget_data = parse_budget_file("data/raw/budget_document.txt")

# Process through the full pipeline
processed_data = process_budget_data(budget_data)
```

### Visualization

```python
from budgetprimer.visualization import create_means_of_finance_chart

# Create a pie chart of funding sources
chart = create_means_of_finance_chart(processed_data)
chart.save("output/visualizations/means_of_finance.png")
```

## HB 300 Format

The parser is specifically designed to handle Hawaii's HB 300 budget format, which includes:

- Program codes and descriptions
- Department identifiers
- Appropriation amounts with embedded fund type codes (A-Z)
- Position ceilings and types
- Operating vs. Capital Improvement sections

### Fund Type Extraction

Fund types are extracted directly from the single letter (A-Z) suffix immediately following appropriation amounts:
- Example: `1,000A` → Fund type 'A' (General Funds)
- Example: `2,500,000B` → Fund type 'B' (Special Funds)
- If no fund type is found, 'U' (Unspecified) is used

## Veto Processing

The pipeline includes powerful tools to process and visualize the impact of gubernatorial vetoes on the budget.

### Veto Processing Pipeline

1. **Input Parsing**:
   - Reads veto changes from a CSV file with program IDs and new amounts
   - Handles different fiscal years (FY2026, FY2027) in the same file
   - Preserves fund type information (A=General, B=Special, etc.)

2. **Veto Application**:
   - Matches programs by ID and fiscal year
   - Updates budget amounts while preserving other allocation details
   - Handles missing or blank amounts (treated as no change)
   - Maintains data integrity by keeping all original entries

3. **Output Generation**:
   - Creates separate CSV files for pre-veto and post-veto data
   - Generates comparison visualizations
   - Preserves all data, with flags for duplicate entries

### Input Files

1. **Veto Definitions** (`data/raw/vetoes/governor_vetoes_fy2026_actual.csv`):
   - `Program`: The program ID (e.g., 'BED143')
   - `Type`: Type of budget item ('Operating' or 'Capital')
   - `FY 2026 Amount`: New total amount for FY 2026 (with fund type suffix, e.g., '1,000,000A')
   - `FY 2027 Amount`: New total amount for FY 2027 (with fund type suffix, e.g., '500,000B')

   **Note**: Blank amounts mean no change to that fiscal year's allocation.

2. **Budget Data**:
   - `data/raw/HB 300 CD 1.txt` - Original budget bill text file
   - `data/processed/budget_parsed_fy2026.csv` - Parsed budget data

- `data/raw/HB 300 CD 1.txt` - Original budget bill text file

### Command Line Usage

Process the budget with different veto modes:

```bash
# Process budget without applying vetoes (default)
python scripts/process_budget.py data/raw/HB_300_CD1.txt --fiscal-year 2026

# Process budget with vetoes applied
python scripts/process_budget.py data/raw/HB_300_CD1.txt --veto-mode apply

# Generate comparison visualizations (pre-veto vs post-veto)
python scripts/process_budget.py data/raw/HB_300_CD1.txt --veto-mode both

# Specify a custom veto file
python scripts/process_budget.py data/raw/HB_300_CD1.txt --veto-mode apply --veto-file path/to/custom_vetoes.csv

# Control the number of items shown in charts
python scripts/process_budget.py data/raw/HB_300_CD1.txt --top-n 20
```

### Processing Steps

1. **Parse Original Budget**: Extract structured data from the HB 300 text document
2. **Load Veto Changes**: Read veto adjustments from the CSV file
3. **Apply Vetoes**: Update budget allocations based on veto specifications
4. **Generate Outputs**:
   - Processed CSV files (pre-veto and/or post-veto)
   - Visualizations showing budget breakdowns
   - Comparison charts when using `--veto-mode both`

### Output Files

When processing with vetoes, the following files are generated:

```
data/processed/
  ├── budget_allocations_fy2026.csv          # Original budget data
  ├── budget_allocations_fy2026_post_veto.csv # Post-veto budget data
  └── ...

data/output/charts/
  ├── means_of_finance_fy2026.png            # Pre-veto means of finance
  ├── means_of_finance_fy2026_post_veto.png   # Post-veto means of finance
  ├── means_of_finance_fy2026_comparison.png  # Side-by-side comparison
  ├── top_departments_fy2026.png             # Pre-veto department budgets
  ├── top_departments_fy2026_post_veto.png    # Post-veto department budgets
  └── top_departments_fy2026_comparison.png   # Department budget comparison
```

### Integration with Analysis

The veto processing pipeline is fully integrated with the analysis tools:

```python
from budgetprimer import (
    parse_budget_file,
    load_veto_changes,
    process_budget_with_vetoes
)

# Parse the budget file
allocations = parse_budget_file("data/raw/HB_300_CD1.txt")

# Process with vetoes
result = process_budget_with_vetoes(
    allocations=allocations,
    veto_mode="both",  # 'none', 'apply', or 'both'
    veto_file="data/raw/vetoes/governor_vetoes_fy2026_actual.csv",
    fiscal_year=2026
)

# Access pre-veto and post-veto data
pre_veto_df = result['pre_veto_df']
post_veto_df = result['post_veto_df']
```

## Data Flow

1. **Input**: Raw HB 300 text document and veto CSV
2. **Parsing**: Extract structured data with proper fund types
3. **Veto Processing**: Apply veto adjustments
4. **Transformation**: Clean and normalize data
5. **Analysis**: Generate insights and metrics
6. **Visualization**: Create publication-quality charts
7. **Output**: Reports, visualizations, and data exports

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
