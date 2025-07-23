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
- **Fast, modular parsing** of budget documents
- **Comprehensive data models** for budget allocations
- **Robust fund type extraction** with proper validation
- **Precise transformation pipeline** from pre-veto to post-veto data
- **High-quality visualizations** matching official styles

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

The pipeline includes tools to process gubernatorial vetoes:

1. **Input Files**:
   - `data/raw/vetoes/governor_vetoes_fy2026_actual.csv` - Veto details
   - `data/raw/HB 300 CD 1.txt` - Original budget bill

2. **Processing Steps**:
   - Parse original budget allocations
   - Apply veto adjustments
   - Reconcile fund types
   - Generate post-veto dataset

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
