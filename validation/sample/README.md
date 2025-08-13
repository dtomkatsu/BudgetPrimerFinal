# Budget Parser Validation

This directory contains a complete validation system for testing the budget parser against a controlled sample budget.

## Files

- **`generate_sample_budget.py`** - Creates a 3-page sample budget PDF matching the real Hawaii budget format
- **`extract_sample_text.py`** - Extracts text from the sample PDF using pdfplumber (same method as real budget)
- **`validate_parser.py`** - Parses the sample budget and compares results against expected totals
- **`run_validation.py`** - Runs the complete validation workflow

## Generated Files

- **`sample_budget.pdf`** - The generated sample budget PDF (3 pages max)
- **`sample_budget.txt`** - Text extracted from the PDF
- **`expected_totals.json`** - Expected totals by fund type and section
- **`validation_results.json`** - Detailed comparison results

## Usage

### Quick Start
```bash
# Run complete validation workflow
python sample/run_validation.py
```

### Step by Step
```bash
# 1. Generate sample budget PDF
python sample/generate_sample_budget.py

# 2. Extract text from PDF
python sample/extract_sample_text.py

# 3. Validate parser
python sample/validate_parser.py
```

## Sample Budget Contents

The sample budget includes:
- **5 departments**: AGR, BED, LBR, TRN, HMS
- **Operating budget**: $3.8B across multiple fund types
- **Capital budget**: $1.4B in bond funds
- **Fund types**: A (General), B (Special), N (Federal), P (Other Federal), T (Trust), W (Revolving), C (Bonds)
- **Known totals** for validation

## Validation Checks

The validation compares:
- Operating budget totals by fund type (A, B, N, P, T, W)
- Capital budget totals by fund type (C)
- Section totals (Operating vs Capital)
- Grand total

## Requirements

```bash
pip install reportlab pdfplumber pandas
```

## Expected Results

If the parser is working correctly, all validation checks should pass with zero differences between expected and parsed totals.
