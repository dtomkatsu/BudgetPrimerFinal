#!/usr/bin/env python3
"""
Analyze Operating Budget Discrepancy - Version 2

Identifies specific line items that differ between manual CSV and parser output.
This version focuses on program codes and MOE codes for better matching.
"""

import pandas as pd
import numpy as np

def load_manual_data(csv_path):
    """Load and process manual CSV data with program and MOE codes."""
    df = pd.read_csv(csv_path)
    
    # Clean and process the data
    manual_data = []
    for _, row in df.iterrows():
        if pd.notna(row.get('Operating')) or pd.notna(row.get('Capital')):
            program = str(row.get('Program', 'UNKNOWN')).strip()
            moe = str(row.get('MOE', '')).strip()
            operating = float(str(row.get('Operating', '0')).replace(',', '')) if pd.notna(row.get('Operating')) else 0
            capital = float(str(row.get('Capital', '0')).replace(',', '')) if pd.notna(row.get('Capital')) else 0
            
            # Extract program code if available (e.g., "TRN102 - Description" -> "TRN102")
            program_code = program.split(' - ')[0] if ' - ' in program else program
            
            manual_data.append({
                'program_code': program_code,
                'program_name': program,
                'moe': moe,
                'operating': operating,
                'capital': capital,
                'total': operating + capital,
                'source': 'manual'
            })
    
    return pd.DataFrame(manual_data)

def load_parser_data(csv_path, department_code):
    """Load and process parser output data."""
    df = pd.read_csv(csv_path)
    
    # Filter for the specified department
    filtered = df[df['department_code'] == department_code].copy()
    
    # Process the data
    parser_data = []
    for _, row in filtered.iterrows():
        program_code = row.get('program_id', 'UNKNOWN')
        program_name = row.get('program_name', 'UNKNOWN')
        section = row.get('section', '')
        fund_type = str(row.get('fund_type', '')).strip()
        amount = float(row.get('amount', 0))
        
        # Map fund_type to MOE code (first character)
        moe = fund_type[0] if fund_type and len(fund_type) > 0 else ''
        
        # Categorize as operating or capital
        is_operating = section == 'Operating'
        is_capital = section == 'Capital Improvement'
        
        parser_data.append({
            'program_code': program_code,
            'program_name': program_name,
            'moe': moe,
            'operating': amount if is_operating else 0,
            'capital': amount if is_capital else 0,
            'total': amount,
            'source': 'parser',
            'section': section,
            'fund_type': fund_type
        })
    
    return pd.DataFrame(parser_data)

def find_discrepancies(manual_df, parser_df):
    """Find discrepancies between manual and parser data."""
    # Create a composite key for comparison (program_code + moe)
    manual_df['key'] = manual_df['program_code'] + '|' + manual_df['moe']
    parser_df['key'] = parser_df['program_code'] + '|' + parser_df['moe']
    
    # Calculate totals for comparison
    manual_total = manual_df['operating'].sum()
    parser_operating_total = parser_df[parser_df['section'] == 'Operating']['total'].sum()
    
    print(f"Manual Operating Total: ${manual_total:,.2f}")
    print(f"Parser Operating Total: ${parser_operating_total:,.2f}")
    print(f"Discrepancy: ${parser_operating_total - manual_total:,.2f}")
    
    # Find unique keys in each dataset
    manual_keys = set(manual_df['key'])
    parser_keys = set(parser_df['key'])
    
    # Find matching and non-matching keys
    common_keys = manual_keys.intersection(parser_keys)
    manual_only = manual_keys - parser_keys
    parser_only = parser_keys - manual_keys
    
    # Analyze differences
    if manual_only:
        print("\nItems in manual but not in parser:")
        for key in sorted(manual_only):
            program, moe = key.split('|')
            item = manual_df[manual_df['key'] == key].iloc[0]
            print(f"- {program} | MOE: {moe} | Operating: ${item['operating']:,.2f}")
    
    if parser_only:
        print("\nItems in parser but not in manual:")
        for key in sorted(parser_only):
            program, moe = key.split('|')
            items = parser_df[parser_df['key'] == key]
            for _, item in items.iterrows():
                print(f"- {program} | MOE: {moe} | {item['section']}: ${item['total']:,.2f} | {item.get('fund_type', '')}")
    
    # Compare common items
    if common_keys:
        print("\nMatching items with amount differences:")
        for key in sorted(common_keys):
            manual_amt = manual_df[manual_df['key'] == key]['operating'].sum()
            parser_amt = parser_df[(parser_df['key'] == key) & (parser_df['section'] == 'Operating')]['total'].sum()
            
            if not np.isclose(manual_amt, parser_amt, rtol=1e-5):
                program, moe = key.split('|')
                print(f"- {program} | MOE: {moe}")
                print(f"  Manual: ${manual_amt:,.2f}")
                print(f"  Parser: ${parser_amt:,.2f}")
                print(f"  Diff:   ${parser_amt - manual_amt:,.2f}")

def main():
    import sys
    
    if len(sys.argv) != 4:
        print("Usage: python analyze_operating_discrepancy_v2.py [manual_csv] [parser_csv] [dept_code]")
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
