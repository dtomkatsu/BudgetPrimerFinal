### Watch Mode (Auto Rebuild + Validate)
Regenerate reports and run validations automatically when key files change.

Requirements:
```bash
pip install watchdog
```

Run:
```bash
python scripts/watch_and_rebuild.py
```

This will:
- Rebuild reports via `scripts/generate_departmental_reports.py`
- Run validations via `scripts/validate_reports.py` (checks duplicate `$`, amount formatting, etc.)

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
- **High-quality visualizations** matching official styles with a modular, extensible chart system
- **Detailed Budget Analysis**: Comprehensive breakdowns by section, fund type, and program
- **Department Descriptions**: Informative descriptions for each department with automatic inclusion in reports

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

### Sample Testing Workflow

The project includes a sample testing system to validate the budget parser with controlled test cases. This is particularly useful for:

1. Verifying parser accuracy with known inputs/outputs
2. Testing edge cases in budget data
3. Ensuring consistent behavior across code changes

#### Running Sample Tests

1. Generate a sample budget PDF and expected totals:
   ```bash
   python sample/generate_sample_budget.py
   ```
   This creates:
   - `sample/sample_budget.pdf`: A sample budget document
   - `sample/expected_totals.json`: Expected totals by fund type and section

2. Run the validation script to test the parser:
   ```bash
   python sample/validate_parser.py
   ```
   This will:
   - Extract text from the sample PDF
   - Parse it using the main budget parser
   - Compare the results against expected totals
   - Report any discrepancies

#### Customizing Sample Data

To modify the sample budget data:
1. Edit the `SAMPLE_DATA` dictionary in `sample/generate_sample_budget.py`
2. The structure is organized by departments, programs, and allocations
3. Key fields to customize:
   - Department codes and names
   - Program numbers, codes, and names
   - Position counts (permanent `*` and temporary `#`)
   - Allocations with section, fund type, and amount

Example of adding a new program:
```python
{
    "number": 11,  # Next sequential number
    "code": "NEW101",
    "name": "NEW PROGRAM NAME",
    "positions": {"*": 5.0, "#": 2.0},  # 5 permanent, 2 temp positions
    "allocations": [
        {"section": "OPERATING", "fund_type": "A", "amount": 1_000_000},
        {"section": "INVESTMENT CAPITAL", "fund_type": "C", "amount": 5_000_000}
    ]
}
```

### Department Descriptions

The system includes a comprehensive database of department descriptions that are automatically included in generated reports. These descriptions provide context about each department's role and responsibilities.

#### Updating Descriptions

1. Edit the source file: `data/raw/Department Descriptions.txt`
2. Run the parser to update the JSON file:
   ```bash
   python scripts/parse_department_descriptions.py
   ```
3. The updated descriptions will be included in the next report generation

Descriptions are stored in JSON format in `data/processed/department_descriptions.json` with the following structure:

```json
{
  "AGR": {
    "name": "Department of Agriculture",
    "description": "Detailed description of the department's role and responsibilities..."
  },
  ...
}
```

### Data Processing

```python
from budgetprimer.parsers.budget_parser import parse_budget_file
from budgetprimer.pipeline import process_budget_data

# Parse a budget file
budget_data = parse_budget_file("data/raw/budget_document.txt")

# Process through the full pipeline
processed_data = process_budget_data(budget_data)
```

### Department Reports

The system generates detailed HTML reports for each department, including:

- Department name and code
- Informative description of the department's role
- Budget summary with operating and capital expenditures
- Visualizations of budget breakdown
- Detailed line-item budget data

To generate department reports:

```python
from budgetprimer.reports import generate_departmental_reports

# Generate all department reports
generate_departmental_reports(
    budget_data=processed_data,
    output_dir="output/reports/departments"
)

# Generate a report for a specific department
generate_departmental_reports(
    budget_data=processed_data,
    departments=["AGR", "EDN", "TRN"],
    output_dir="output/reports/selected_departments"
)
```

### Visualization

The BudgetPrimer provides a powerful, modular charting system for creating consistent, publication-quality visualizations of budget data. The system is built around a base `BudgetChart` class with specialized chart types for different budget views.

### Chart Types

1. **Department Budget Chart**
   - Horizontal bar chart showing operating vs. capital budgets by department
   - Special handling for key departments (Judiciary, Legislature, OHA)
   - Consistent color scheme and sorting

2. **Means of Finance Chart**
   - Pie chart showing budget breakdown by fund type (General, Special, Federal, etc.)
   - Custom color mapping for different fund types
   - Clear labeling and legend

3. **CIP Funding Chart**
   - Bar chart showing Capital Improvement Project funding by program
   - Filtering by fiscal year and program type
   - Consistent styling with other charts

### Using the Chart System

#### Basic Usage (Legacy Functions)

```python
from budgetprimer.visualization import (
    create_department_budget_chart,
    create_means_of_finance_chart,
    create_cip_funding_chart
)

# Create a department budget chart
dept_chart = create_department_budget_chart(
    data=budget_df,
    fiscal_year=2026,
    title="Top 15 Departments by Budget (FY2026)",
    output_file="output/charts/top_departments.png"
)

# Create a means of finance chart
mof_chart = create_means_of_finance_chart(
    data=budget_df,
    fiscal_year=2026,
    title="Means of Finance (FY2026)",
    output_file="output/charts/means_of_finance.png"
)
```

#### Advanced Usage (Modular System)

```python
from budgetprimer.visualization.charts import DepartmentChart, MeansOfFinanceChart, CIPChart

# Create a department chart with custom settings
dept_chart = DepartmentChart(
    data=budget_df,
    fiscal_year=2026,
    n_departments=10,  # Show top 10 departments
    figsize=(12, 8)
)
dept_chart.prepare_data()
fig = dept_chart.create_figure()
fig.savefig("output/charts/custom_dept_chart.png")

# Create a means of finance chart with custom colors
mof_chart = MeansOfFinanceChart(
    data=budget_df,
    fiscal_year=2026,
    title="Custom MOF Chart",
    colors={
        'A': '#1f77b4',  # Custom colors for fund types
        'B': '#ff7f0e',
        'C': '#2ca02c',
        'N': '#000000'   # Federal funds in black
    }
)
mof_chart.prepare_data()
fig = mof_chart.create_figure()
fig.savefig("output/charts/custom_mof_chart.png")
```

### Chart Customization

All charts support the following customization options:

- `figsize`: Figure dimensions as a tuple (width, height)
- `dpi`: Resolution in dots per inch
- `title`: Chart title
- `title_fontsize`: Font size for the title
- `label_fontsize`: Font size for axis labels
- `tick_fontsize`: Font size for tick labels
- `legend_fontsize`: Font size for legend text
- `colors`: Dictionary mapping fund types to colors

### Creating Custom Charts

To create a new chart type, extend the `BudgetChart` base class and implement the required methods:

```python
from budgetprimer.visualization.charts.base import BudgetChart

class MyCustomChart(BudgetChart):
    def prepare_data(self):
        """Prepare and process data for visualization."""
        # Data processing logic here
        pass
    
    def create_figure(self):
        """Create and return a matplotlib Figure object."""
        # Chart creation logic here
        pass
```

### Output Formats

Charts can be saved in multiple formats:

```python
# Save as PNG (default)
chart.save("output/charts/chart.png")

# Save as PDF (vector format)
chart.save("output/charts/chart.pdf")

# Save as SVG (scalable vector graphics)
chart.save("output/charts/chart.svg")
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
