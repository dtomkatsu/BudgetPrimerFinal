#!/usr/bin/env python3
"""
Analyze Operating Budget Discrepancy

Identifies specific line items that differ between manual CSV and parser output.
"""

import pandas as pd
import numpy as np

def load_manual_data(csv_path):
    """Load and process manual CSV data."""
    df = pd.read_csv(csv_path)
    
    # Clean and process the data
    manual_data = []
    for _, row in df.iterrows():
        if pd.notna(row.get('Operating')):
            amount = float(str(row['Operating']).replace(',', ''))
            moe = row.get('MOE', '')
            program = row.get('Program', 'UNKNOWN')
            manual_data.append({
                'program': program,
                'amount': amount,
                'moe': moe,
                'source': 'manual'
            })
    
    return pd.DataFrame(manual_data)

def load_parser_data(csv_path, department_code):
    """Load and process parser output data."""
    df = pd.read_csv(csv_path)
    
    # Filter for the specified department and operating budget
    filtered = df[
        (df['department_code'] == department_code) & 
        (df['section'] == 'Operating')
    ].copy()
    
    # Group by program and fund type to match manual CSV structure
    parser_data = []
    for (program_id, program_name, fund_type), group in filtered.groupby(['program_id', 'program_name', 'fund_type']):
        parser_data.append({
            'program': f"{program_id} - {program_name}",
            'amount': group['amount'].sum(),
            'moe': fund_type[0] if isinstance(fund_type, str) and len(fund_type) > 0 else '',
            'source': 'parser'
        })
    
    return pd.DataFrame(parser_data)

def find_discrepancies(manual_df, parser_df):
    """Find discrepancies between manual and parser data."""
    # Create a composite key for comparison
    manual_df['key'] = manual_df['program'] + '|' + manual_df['moe'].astype(str)
    parser_df['key'] = parser_df['program'] + '|' + parser_df['moe'].astype(str)
    
    # Find unique keys in each dataset
    manual_keys = set(manual_df['key'])
    parser_keys = set(parser_df['key'])
    
    # Find matching and non-matching keys
    common_keys = manual_keys.intersection(parser_keys)
    manual_only = manual_keys - parser_keys
    parser_only = parser_keys - manual_keys
    
    # Calculate totals for comparison
    manual_total = manual_df[manual_df['key'].isin(manual_keys)]['amount'].sum()
    parser_total = parser_df[parser_df['key'].isin(parser_keys)]['amount'].sum()
    
    print(f"Manual Total: ${manual_total:,.2f}")
    print(f"Parser Total: ${parser_total:,.2f}")
    print(f"Discrepancy: ${parser_total - manual_total:,.2f}")
    
    # Analyze differences
    if manual_only:
        print("\nItems in manual but not in parser:")
        for key in sorted(manual_only):
            amount = manual_df[manual_df['key'] == key]['amount'].values[0]
            print(f"- {key}: ${amount:,.2f}")
    
    if parser_only:
        print("\nItems in parser but not in manual:")
        for key in sorted(parser_only):
            amount = parser_df[parser_df['key'] == key]['amount'].values[0]
            print(f"- {key}: ${amount:,.2f}")
    
    # Compare common items
    if common_keys:
        print("\nMatching items with amount differences:")
        for key in sorted(common_keys):
            manual_amt = manual_df[manual_df['key'] == key]['amount'].values[0]
            parser_amt = parser_df[parser_df['key'] == key]['amount'].values[0]
            if not np.isclose(manual_amt, parser_amt, rtol=1e-5):
                print(f"- {key}")
                print(f"  Manual: ${manual_amt:,.2f}")
                print(f"  Parser: ${parser_amt:,.2f}")
                print(f"  Diff:   ${parser_amt - manual_amt:,.2f}")

def main():
    import sys
    
    if len(sys.argv) != 4:
        print("Usage: python analyze_operating_discrepancy.py [manual_csv] [parser_csv] [dept_code]")
        sys.exit(1)
    
    manual_csv = sys.argv[1]
    parser_csv = sys.argv[2]
    dept_code = sys.argv[3]
    
    print(f"Analyzing operating budget discrepancy for {dept_code}...")
    print("=" * 60)
    
    # Load data
    print("Loading manual data...")
    manual_df = load_manual_data(manual_csv)
    
    print("Loading parser data...")
    parser_df = load_parser_data(parser_csv, dept_code)
    
    # Find discrepancies
    print("\nAnalyzing discrepancies...")
    find_discrepancies(manual_df, parser_df)

if __name__ == "__main__":
    main()
