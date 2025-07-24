#!/usr/bin/env python3
"""
Analyze budget totals by section (Operating vs Capital) from the parsed budget CSV.
"""
import pandas as pd
import argparse
from pathlib import Path

def analyze_budget_totals(csv_path):
    """Analyze and print budget totals by section."""
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Convert amount to numeric in case it's not already
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    
    # Group by section and sum the amounts
    section_totals = df.groupby('section')['amount'].sum()
    
    # Get total budget
    total_budget = df['amount'].sum()
    
    # Print results
    print("\n=== Budget Totals by Section ===")
    print(section_totals.to_string())
    print("\n=== Percentage of Total Budget ===")
    print((section_totals / total_budget * 100).round(2).astype(str) + "%")
    print(f"\nTotal Budget: ${total_budget:,.2f}")
    
    return section_totals

def main():
    parser = argparse.ArgumentParser(description='Analyze budget totals by section (Operating vs Capital)')
    parser.add_argument('input_file', help='Path to the parsed budget CSV file',
                       default='data/processed/budget_parsed.csv', nargs='?')
    args = parser.parse_args()
    
    csv_path = Path(args.input_file)
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        return 1
    
    analyze_budget_totals(csv_path)
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
