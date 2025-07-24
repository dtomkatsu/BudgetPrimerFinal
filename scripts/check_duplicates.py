#!/usr/bin/env python3
"""
Check for duplicate entries in the budget_parsed.csv file.
"""
import pandas as pd
import argparse
from pathlib import Path

def check_duplicates(csv_path):
    """Check for and display duplicate entries in the budget CSV."""
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Get total number of rows
    total_rows = len(df)
    print(f"Total rows in CSV: {total_rows:,}")
    
    # Check for exact duplicates across all columns
    duplicates = df[df.duplicated(keep=False)]
    exact_duplicates = len(duplicates)
    
    if exact_duplicates > 0:
        print(f"\nFound {exact_duplicates} exact duplicate rows (all columns match):")
        print(duplicates.sort_values(by=df.columns.tolist()).to_string())
    else:
        print("\nNo exact duplicate rows found (all columns match).")
    
    # Check for potential duplicates based on key fields
    key_columns = ['program_id', 'department_code', 'section', 'fund_type', 'fiscal_year']
    potential_dupes = df[df.duplicated(subset=key_columns, keep=False)]
    
    if not potential_dupes.empty:
        print(f"\nFound {len(potential_dupes)} rows that might be potential duplicates "
              f"(based on program_id, department_code, section, fund_type, fiscal_year):")
        
        # Group by the key columns to show duplicates together
        grouped = potential_dupes.groupby(key_columns)
        for (key), group in grouped:
            if len(group) > 1:  # Only show groups with more than one entry
                print("\nPotential duplicates:")
                print(group.to_string())
    else:
        print("\nNo potential duplicates found based on key fields.")
    
    return duplicates, potential_dupes

def main():
    parser = argparse.ArgumentParser(description='Check for duplicate entries in the budget CSV')
    parser.add_argument('input_file', help='Path to the parsed budget CSV file',
                      default='data/processed/budget_parsed.csv', nargs='?')
    args = parser.parse_args()
    
    csv_path = Path(args.input_file)
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        return 1
    
    check_duplicates(csv_path)
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
