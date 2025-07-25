#!/usr/bin/env python3
"""
Diagnose potential issues in the capital improvement budget for FY 2026.
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Configuration
CSV_PATH = 'data/processed/budget_parsed_fy2026.csv'
OUTPUT_DIR = 'analysis'

# Ensure output directory exists
Path(OUTPUT_DIR).mkdir(exist_ok=True)

def load_data():
    """Load and preprocess the budget data."""
    print(f"Loading data from {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)
    
    # Ensure amount is numeric
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    
    # Filter for capital improvements only
    capital = df[df['section'] == 'Capital Improvement'].copy()
    
    return df, capital

def check_duplicate_allocations(df):
    """Check for duplicate allocations that might be causing double-counting."""
    print("\nChecking for potential duplicate allocations...")
    
    # Group by key fields that should be unique
    duplicates = df[df.duplicated(
        ['program_id', 'fiscal_year', 'amount', 'fund_type'], 
        keep=False
    )].sort_values(['program_id', 'amount'])
    
    if not duplicates.empty:
        print(f"Found {len(duplicates)} potential duplicate allocations:")
        print(duplicates[['program_id', 'program_name', 'amount', 'fund_type']].to_string())
        
        # Save to CSV for review
        dup_file = Path(OUTPUT_DIR) / 'potential_duplicates.csv'
        duplicates.to_csv(dup_file, index=False)
        print(f"Saved potential duplicates to {dup_file}")
    else:
        print("No duplicate allocations found.")

def check_large_allocations(df, threshold=100_000_000):
    """Check for unusually large allocations that might be errors."""
    print(f"\nChecking for large allocations (over ${threshold/1e6:,.0f}M)...")
    
    large = df[df['amount'] > threshold].sort_values('amount', ascending=False)
    
    if not large.empty:
        print(f"Found {len(large)} large allocations:")
        print(large[['program_id', 'program_name', 'amount', 'fund_type']].to_string())
        
        # Save to CSV for review
        large_file = Path(OUTPUT_DIR) / 'large_allocations.csv'
        large.to_csv(large_file, index=False)
        print(f"Saved large allocations to {large_file}")
    else:
        print(f"No allocations over ${threshold/1e6:,.0f}M found.")

def check_fund_type_distribution(df):
    """Analyze distribution of fund types in capital budget."""
    print("\nAnalyzing fund type distribution...")
    
    fund_summary = df.groupby('fund_type').agg(
        count=('amount', 'count'),
        total_amount=('amount', 'sum'),
        avg_amount=('amount', 'mean')
    ).sort_values('total_amount', ascending=False)
    
    print("\nFund Type Summary:")
    print(fund_summary.to_string())
    
    # Save to CSV
    fund_file = Path(OUTPUT_DIR) / 'fund_type_analysis.csv'
    fund_summary.to_csv(fund_file)
    print(f"Saved fund type analysis to {fund_file}")

def check_department_totals(df):
    """Analyze capital budget by department."""
    print("\nAnalyzing capital budget by department...")
    
    dept_summary = df.groupby(['department_code', 'department_name']).agg(
        program_count=('program_id', 'nunique'),
        allocation_count=('amount', 'count'),
        total_amount=('amount', 'sum'),
    ).sort_values('total_amount', ascending=False)
    
    print("\nDepartment Summary (Top 10 by Total Amount):")
    print(dept_summary.head(10).to_string())
    
    # Save to CSV
    dept_file = Path(OUTPUT_DIR) / 'department_analysis.csv'
    dept_summary.to_csv(dept_file)
    print(f"Saved department analysis to {dept_file}")

def main():
    # Load the data
    df, capital_df = load_data()
    
    print(f"Total capital improvement allocations: {len(capital_df):,}")
    print(f"Total capital budget: ${capital_df['amount'].sum()/1e9:,.2f}B")
    
    # Run diagnostics
    check_duplicate_allocations(capital_df)
    check_large_allocations(capital_df)
    check_fund_type_distribution(capital_df)
    check_department_totals(capital_df)
    
    print("\nAnalysis complete. Check the 'analysis' directory for detailed reports.")

if __name__ == "__main__":
    main()
