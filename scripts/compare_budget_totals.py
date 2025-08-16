#!/usr/bin/env python3
"""
Budget Comparison Script

Compares manual CSV budget totals with parser post-veto totals for specified departments.
Easily configurable for different CSV files and columns.
"""

import pandas as pd
import argparse
import sys

def compare_budget_totals(manual_csv_path, parser_csv_path, department_code, 
                         manual_operating_col='Operating', manual_capital_col='Capital',
                         parser_dept_col='department_code', parser_section_col='section', 
                         parser_amount_col='amount'):
    """
    Compare budget totals between manual CSV and parser output.
    
    Args:
        manual_csv_path: Path to manual CSV file
        parser_csv_path: Path to parser output CSV file
        department_code: Department code to filter (e.g., 'TRN')
        manual_operating_col: Column name for operating budget in manual CSV
        manual_capital_col: Column name for capital budget in manual CSV
        parser_dept_col: Column name for department code in parser CSV
        parser_section_col: Column name for section in parser CSV
        parser_amount_col: Column name for amount in parser CSV
    """
    
    print(f"Comparing budget totals for department: {department_code}")
    print("=" * 60)
    
    try:
        # Load manual CSV
        manual_df = pd.read_csv(manual_csv_path)
        print(f"Loaded manual CSV: {manual_csv_path}")
        
        # Load parser CSV
        parser_df = pd.read_csv(parser_csv_path)
        print(f"Loaded parser CSV: {parser_csv_path}")
        
        # Calculate manual operating total
        manual_operating = 0
        if manual_operating_col in manual_df.columns:
            for _, row in manual_df.iterrows():
                if pd.notna(row[manual_operating_col]):
                    manual_operating += float(str(row[manual_operating_col]).replace(',', ''))
        
        # Calculate manual capital total
        manual_capital = 0
        if manual_capital_col in manual_df.columns:
            for _, row in manual_df.iterrows():
                if pd.notna(row[manual_capital_col]):
                    manual_capital += float(str(row[manual_capital_col]).replace(',', ''))
        
        # Calculate parser operating total
        parser_operating = parser_df[
            (parser_df[parser_dept_col] == department_code) & 
            (parser_df[parser_section_col] == 'Operating')
        ][parser_amount_col].sum()
        
        # Calculate parser capital total
        parser_capital = parser_df[
            (parser_df[parser_dept_col] == department_code) & 
            (parser_df[parser_section_col] == 'Capital Improvement')
        ][parser_amount_col].sum()
        
        # Display results
        print("\nOPERATING BUDGET COMPARISON:")
        print(f"Manual CSV Operating Total:     ${manual_operating:,.0f}")
        print(f"Parser Post-Veto Operating:     ${parser_operating:,.0f}")
        print(f"Operating Discrepancy:          ${parser_operating - manual_operating:,.0f}")
        
        print("\nCAPITAL BUDGET COMPARISON:")
        print(f"Manual CSV Capital Total:       ${manual_capital:,.0f}")
        print(f"Parser Post-Veto Capital:       ${parser_capital:,.0f}")
        print(f"Capital Discrepancy:            ${parser_capital - manual_capital:,.0f}")
        
        print("\nTOTAL BUDGET COMPARISON:")
        manual_total = manual_operating + manual_capital
        parser_total = parser_operating + parser_capital
        print(f"Manual CSV Total:               ${manual_total:,.0f}")
        print(f"Parser Post-Veto Total:         ${parser_total:,.0f}")
        print(f"Total Discrepancy:              ${parser_total - manual_total:,.0f}")
        
        # Return results for programmatic use
        return {
            'manual_operating': manual_operating,
            'manual_capital': manual_capital,
            'parser_operating': parser_operating,
            'parser_capital': parser_capital,
            'operating_discrepancy': parser_operating - manual_operating,
            'capital_discrepancy': parser_capital - manual_capital,
            'total_discrepancy': parser_total - manual_total
        }
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Compare manual CSV budget totals with parser output')
    parser.add_argument('manual_csv', help='Path to manual CSV file')
    parser.add_argument('parser_csv', help='Path to parser output CSV file')
    parser.add_argument('department', help='Department code (e.g., TRN)')
    parser.add_argument('--manual-operating-col', default='Operating', 
                       help='Column name for operating budget in manual CSV')
    parser.add_argument('--manual-capital-col', default='Capital',
                       help='Column name for capital budget in manual CSV')
    parser.add_argument('--parser-dept-col', default='department_code',
                       help='Column name for department code in parser CSV')
    parser.add_argument('--parser-section-col', default='section',
                       help='Column name for section in parser CSV')
    parser.add_argument('--parser-amount-col', default='amount',
                       help='Column name for amount in parser CSV')
    
    args = parser.parse_args()
    
    compare_budget_totals(
        args.manual_csv,
        args.parser_csv,
        args.department,
        args.manual_operating_col,
        args.manual_capital_col,
        args.parser_dept_col,
        args.parser_section_col,
        args.parser_amount_col
    )

if __name__ == '__main__':
    main()
