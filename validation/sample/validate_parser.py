#!/usr/bin/env python3
"""
Validate the budget parser by testing it against the sample budget and comparing results.
This script:
1. Parses the sample budget text file
2. Compares parsed totals against expected totals
3. Reports any discrepancies
4. Provides detailed breakdown by fund type and section
"""

import sys
import json
from pathlib import Path
import pandas as pd

# Add the parent directory to the path to import the parser
sys.path.append(str(Path(__file__).parent.parent))

try:
    # Add the project root to the path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from budgetprimer.parsers import parse_budget_file
except ImportError as e:
    print(f"Error importing parser: {e}")
    print("Make sure budgetprimer.parsers module exists")
    sys.exit(1)

def load_expected_totals(expected_file: str) -> dict:
    """Load expected totals from JSON file."""
    try:
        with open(expected_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading expected totals: {e}")
        return {}

def parse_sample_budget(text_file: str) -> pd.DataFrame:
    """Parse the sample budget text file."""
    try:
        allocations = parse_budget_file(text_file)
        
        if not allocations:
            print("Warning: No allocations parsed from sample budget")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame([alloc.to_dict() for alloc in allocations])
        print(f"Parsed {len(df)} budget allocations from sample budget")
        return df
        
    except Exception as e:
        print(f"Error parsing sample budget: {e}")
        return pd.DataFrame()

def calculate_parsed_totals(df: pd.DataFrame) -> dict:
    """Calculate totals from parsed data."""
    if df.empty:
        return {'operating': {}, 'capital': {}, 'totals': {'operating': 0, 'capital': 0, 'grand': 0}}
    
    # Filter to FY2026 only (sample budget has both 2026 and 2027)
    df_2026 = df[df['fiscal_year'] == 2026]
    if df_2026.empty:
        print("Warning: No FY2026 data found in parsed results")
        return {'operating': {}, 'capital': {}, 'totals': {'operating': 0, 'capital': 0, 'grand': 0}}
    
    # Group by section and fund type
    operating_df = df_2026[df_2026['section'] == 'Operating']
    capital_df = df_2026[df_2026['section'] == 'Capital Improvement']
    
    parsed = {
        'operating': {},
        'capital': {},
        'totals': {}
    }
    
    # Calculate operating totals by fund type
    if not operating_df.empty:
        operating_by_fund = operating_df.groupby('fund_type')['amount'].sum()
        parsed['operating'] = operating_by_fund.to_dict()
    
    # Calculate capital totals by fund type  
    if not capital_df.empty:
        capital_by_fund = capital_df.groupby('fund_type')['amount'].sum()
        parsed['capital'] = capital_by_fund.to_dict()
    
    # Calculate section totals
    parsed['totals']['operating'] = operating_df['amount'].sum() if not operating_df.empty else 0
    parsed['totals']['capital'] = capital_df['amount'].sum() if not capital_df.empty else 0
    parsed['totals']['grand'] = parsed['totals']['operating'] + parsed['totals']['capital']
    
    return parsed

def compare_totals(expected: dict, parsed: dict) -> dict:
    """Compare expected vs parsed totals and return comparison results."""
    results = {
        'operating': {},
        'capital': {},
        'totals': {},
        'summary': {'passed': 0, 'failed': 0, 'total': 0}
    }
    
    # Compare operating funds
    all_operating_funds = set(expected.get('operating', {}).keys()) | set(parsed.get('operating', {}).keys())
    for fund in all_operating_funds:
        exp_val = expected.get('operating', {}).get(fund, 0)
        parsed_val = parsed.get('operating', {}).get(fund, 0)
        diff = parsed_val - exp_val
        passed = diff == 0
        
        results['operating'][fund] = {
            'expected': exp_val,
            'parsed': parsed_val,
            'difference': diff,
            'passed': passed
        }
        
        results['summary']['total'] += 1
        if passed:
            results['summary']['passed'] += 1
        else:
            results['summary']['failed'] += 1
    
    # Compare capital funds
    all_capital_funds = set(expected.get('capital', {}).keys()) | set(parsed.get('capital', {}).keys())
    for fund in all_capital_funds:
        exp_val = expected.get('capital', {}).get(fund, 0)
        parsed_val = parsed.get('capital', {}).get(fund, 0)
        diff = parsed_val - exp_val
        passed = diff == 0
        
        results['capital'][fund] = {
            'expected': exp_val,
            'parsed': parsed_val,
            'difference': diff,
            'passed': passed
        }
        
        results['summary']['total'] += 1
        if passed:
            results['summary']['passed'] += 1
        else:
            results['summary']['failed'] += 1
    
    # Compare totals
    for total_type in ['operating', 'capital', 'grand']:
        exp_val = expected.get('totals', {}).get(total_type, 0)
        parsed_val = parsed.get('totals', {}).get(total_type, 0)
        diff = parsed_val - exp_val
        passed = diff == 0
        
        results['totals'][total_type] = {
            'expected': exp_val,
            'parsed': parsed_val,
            'difference': diff,
            'passed': passed
        }
        
        results['summary']['total'] += 1
        if passed:
            results['summary']['passed'] += 1
        else:
            results['summary']['failed'] += 1
    
    return results

def print_results(results: dict):
    """Print comparison results in a readable format."""
    print("\n" + "="*60)
    print("PARSER VALIDATION RESULTS")
    print("="*60)
    
    # Summary
    summary = results['summary']
    print(f"\nSUMMARY:")
    print(f"  Total checks: {summary['total']}")
    print(f"  Passed: {summary['passed']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Success rate: {(summary['passed']/summary['total']*100):.1f}%" if summary['total'] > 0 else "N/A")
    
    # Operating funds
    print(f"\nOPERATING FUNDS:")
    print(f"{'Fund':<6} {'Expected':<15} {'Parsed':<15} {'Difference':<15} {'Status':<8}")
    print("-" * 65)
    for fund, data in results['operating'].items():
        status = "PASS" if data['passed'] else "FAIL"
        print(f"{fund:<6} ${data['expected']:<14,} ${data['parsed']:<14,} ${data['difference']:<14,} {status:<8}")
    
    # Capital funds
    if results['capital']:
        print(f"\nCAPITAL FUNDS:")
        print(f"{'Fund':<6} {'Expected':<15} {'Parsed':<15} {'Difference':<15} {'Status':<8}")
        print("-" * 65)
        for fund, data in results['capital'].items():
            status = "PASS" if data['passed'] else "FAIL"
            print(f"{fund:<6} ${data['expected']:<14,} ${data['parsed']:<14,} ${data['difference']:<14,} {status:<8}")
    
    # Totals
    print(f"\nTOTALS:")
    print(f"{'Type':<12} {'Expected':<15} {'Parsed':<15} {'Difference':<15} {'Status':<8}")
    print("-" * 70)
    for total_type, data in results['totals'].items():
        status = "PASS" if data['passed'] else "FAIL"
        print(f"{total_type.title():<12} ${data['expected']:<14,} ${data['parsed']:<14,} ${data['difference']:<14,} {status:<8}")
    
    print("\n" + "="*60)

def main():
    """Main validation function."""
    sample_dir = Path(__file__).parent
    
    # Check required files
    text_file = sample_dir / "sample_budget.txt"
    expected_file = sample_dir / "expected_totals.json"
    
    if not text_file.exists():
        print(f"Error: Sample budget text file not found: {text_file}")
        print("Run extract_sample_text.py first to create the text file.")
        return 1
    
    if not expected_file.exists():
        print(f"Error: Expected totals file not found: {expected_file}")
        print("Run generate_sample_budget.py first to create expected totals.")
        return 1
    
    # Load expected totals
    expected = load_expected_totals(str(expected_file))
    if not expected:
        print("Error: Could not load expected totals")
        return 1
    
    # Parse sample budget
    print("Parsing sample budget...")
    df = parse_sample_budget(str(text_file))
    if df.empty:
        print("Error: No data parsed from sample budget")
        return 1
    
    # Calculate parsed totals
    parsed = calculate_parsed_totals(df)
    
    # Compare results
    results = compare_totals(expected, parsed)
    
    # Print results
    print_results(results)
    
    # Save detailed results (convert numpy types to native Python types for JSON serialization)
    results_file = sample_dir / "validation_results.json"
    
    def convert_for_json(obj):
        """Convert numpy types and other non-serializable types for JSON."""
        if hasattr(obj, 'item'):  # numpy scalar
            return obj.item()
        elif isinstance(obj, dict):
            return {k: convert_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_for_json(v) for v in obj]
        else:
            return obj
    
    json_results = convert_for_json(results)
    with open(results_file, 'w') as f:
        json.dump(json_results, f, indent=2)
    print(f"\nDetailed results saved to: {results_file}")
    
    # Return exit code based on success
    return 0 if results['summary']['failed'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
