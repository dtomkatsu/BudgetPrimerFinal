#!/usr/bin/env python3
"""
Generate summary statistics from the post-veto budget data for the web application.
This script processes the CSV data and creates a JSON file with total budget figures.
"""

import pandas as pd
import json
import os
from pathlib import Path

def generate_summary_stats():
    """Generate summary statistics from post-veto budget data."""
    
    # File paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    csv_file = project_root / "data" / "processed" / "budget_allocations_fy2026_post_veto.csv"
    output_file = project_root / "docs" / "js" / "summary_stats.json"
    
    print(f"Reading data from: {csv_file}")
    
    # Read the CSV data
    try:
        df = pd.read_csv(csv_file)
        print(f"Loaded {len(df)} rows of budget data")
    except FileNotFoundError:
        print(f"Error: Could not find {csv_file}")
        return False
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return False
    
    # Calculate totals by section
    totals = {
        'operating_budget': 0,
        'capital_budget': 0,
        'one_time_appropriations': 0,
        'total_budget': 0
    }
    
    # Group by section and sum amounts
    section_totals = df.groupby('section')['amount'].sum()
    
    # Map sections to our categories
    for section, amount in section_totals.items():
        if section == 'Operating':
            totals['operating_budget'] = float(amount)
        elif section == 'Capital Improvement':
            totals['capital_budget'] = float(amount)
        elif section == 'One-Time':
            totals['one_time_appropriations'] = float(amount)
    
    # Calculate total budget
    totals['total_budget'] = (
        totals['operating_budget'] + 
        totals['capital_budget'] + 
        totals['one_time_appropriations']
    )
    
    # Add breakdown by fund type for additional context
    fund_breakdown = df.groupby('fund_category')['amount'].sum().to_dict()
    totals['fund_breakdown'] = {k: float(v) for k, v in fund_breakdown.items()}
    
    # Add metadata
    totals['metadata'] = {
        'generated_at': pd.Timestamp.now().isoformat(),
        'source_file': str(csv_file.name),
        'total_records': len(df),
        'fiscal_year': 2026
    }
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to JSON file
    try:
        with open(output_file, 'w') as f:
            json.dump(totals, f, indent=2)
        print(f"Summary statistics written to: {output_file}")
        
        # Print summary for verification
        print("\nSummary Statistics:")
        print(f"Operating Budget: ${totals['operating_budget']:,.0f}")
        print(f"Capital Budget: ${totals['capital_budget']:,.0f}")
        print(f"One-Time Appropriations: ${totals['one_time_appropriations']:,.0f}")
        print(f"Total Budget: ${totals['total_budget']:,.0f}")
        
        return True
        
    except Exception as e:
        print(f"Error writing JSON file: {e}")
        return False

if __name__ == "__main__":
    success = generate_summary_stats()
    if success:
        print("\n✅ Summary statistics generated successfully!")
    else:
        print("\n❌ Failed to generate summary statistics")
        exit(1)
