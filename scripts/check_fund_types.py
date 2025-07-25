#!/usr/bin/env python3
"""
Script to analyze fund type distribution in the parsed budget data.
"""
import pandas as pd
from pathlib import Path

def analyze_fund_types(csv_path):
    """Analyze fund type distribution in the parsed budget data."""
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Count total entries
    total_entries = len(df)
    
    # Count entries with missing fund_type
    missing_fund_type = df['fund_type'].isna().sum()
    
    # Count entries with empty fund_type (if stored as empty string)
    empty_fund_type = (df['fund_type'] == '').sum()
    
    # Get fund type distribution
    fund_type_dist = df['fund_type'].value_counts(dropna=False).to_dict()
    
    # Calculate percentages
    pct_missing = (missing_fund_type / total_entries) * 100
    pct_empty = (empty_fund_type / total_entries) * 100
    
    # Print results
    print(f"Total entries: {total_entries:,}")
    print(f"Entries with missing fund_type (None/NaN): {missing_fund_type:,} ({pct_missing:.2f}%)")
    print(f"Entries with empty fund_type (''): {empty_fund_type:,} ({pct_empty:.2f}%)")
    print("\nFund Type Distribution:")
    for fund_type, count in sorted(fund_type_dist.items()):
        pct = (count / total_entries) * 100
        print(f"  {str(fund_type):<5}: {count:>8,} entries ({pct:.2f}%)")
    
    # Return the results as a dictionary
    return {
        'total_entries': total_entries,
        'missing_fund_type': missing_fund_type,
        'empty_fund_type': empty_fund_type,
        'fund_type_distribution': fund_type_dist
    }

if __name__ == "__main__":
    # Path to the parsed budget CSV
    csv_path = Path("data/processed/budget_parsed_fy2026.csv")
    
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        print("Please run the parser first to generate the CSV file.")
    else:
        analyze_fund_types(csv_path)
