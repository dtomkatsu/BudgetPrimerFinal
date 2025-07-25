#!/usr/bin/env python3
"""
Analyze budget totals by section (Operating vs Capital) and fund types from the parsed budget CSV.
"""
import pandas as pd
import argparse
from pathlib import Path
from typing import Dict, Tuple

# Define fund type categories
FUND_CATEGORIES = {
    'General Fund': ['A'],
    'Special Fund': ['B'],
    'Federal Funds': ['F'],
    'Bond Funds': ['D'],
    'Trust Funds': ['T'],
    'SMA Funds': ['S'],
    'Special Outlay': ['W'],
    'Revenue Bonds': ['R'],
    'Other Funds': ['X', 'U']  # Includes 'Other' and 'Unknown'
}

def format_currency(amount: float) -> str:
    """Format currency values with appropriate units (B for billions, M for millions)."""
    if abs(amount) >= 1_000_000_000:
        return f"${amount/1_000_000_000:,.2f}B"
    elif abs(amount) >= 1_000_000:
        return f"${amount/1_000_000:,.1f}M"
    return f"${amount:,.0f}"

def clean_budget_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and preprocess the budget data."""
    # Clean program names by removing newlines and extra spaces
    if 'program_name' in df.columns:
        df['program_name'] = df['program_name'].astype(str).str.replace('\n', ' ').str.strip()
    
    # Clean section names
    if 'section' in df.columns:
        df['section'] = df['section'].astype(str).str.strip()
    
    # Clean fund_type
    if 'fund_type' in df.columns:
        df['fund_type'] = df['fund_type'].fillna('U').astype(str).str.strip()
    
    # Convert amount to numeric, coercing errors to NaN
    if 'amount' in df.columns:
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    
    return df

def analyze_budget_totals(csv_path: str) -> Dict[str, pd.DataFrame]:
    """
    Analyze and print budget totals by section and fund types.
    
    Args:
        csv_path: Path to the parsed budget CSV file
        
    Returns:
        Dictionary containing DataFrames with the analysis results
    """
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Clean the data
    df = clean_budget_data(df)
    
    # Ensure fiscal_year is treated as string for consistency
    if 'fiscal_year' in df.columns:
        df['fiscal_year'] = df['fiscal_year'].astype(str)
    else:
        # Try to extract fiscal year from filename if not in data
        import re
        year_match = re.search(r'(20\d{2})', str(csv_path))
        if year_match:
            df['fiscal_year'] = year_match.group(1)
        else:
            df['fiscal_year'] = '2026'  # Default to 2026 if not found
    
    # Check for and handle duplicate entries
    if df.duplicated().any():
        print(f"\nWarning: Found {df.duplicated().sum()} duplicate rows. Removing duplicates.")
        df = df.drop_duplicates()
    
    # Check for unusually large amounts
    if 'amount' in df.columns:
        large_entries = df[df['amount'] > 1_000_000_000]  # Entries over $1B
        if not large_entries.empty:
            print("\nWarning: Found entries with amounts over $1B:")
            print(large_entries[['program_id', 'program_name', 'section', 'amount']].to_string())
    
    # Filter out any remaining invalid amounts
    df = df[df['amount'] > 0].dropna(subset=['amount'])
    
    # Ensure we have the required columns
    required_columns = ['section', 'fund_type', 'amount']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in the data")
    
    # 1. Analysis by section and fiscal year
    section_year_totals = df.groupby(['section', 'fiscal_year'])['amount'].sum().unstack()
    
    # 2. Analysis by fund category and fiscal year
    # Map fund types to categories
    fund_mapping = {}
    for category, codes in FUND_CATEGORIES.items():
        for code in codes:
            fund_mapping[code] = category
    
    # Add fund category column
    df['fund_category'] = df['fund_type'].map(fund_mapping)
    
    # Group by fund category and fiscal year
    fund_year_totals = df.groupby(['fund_category', 'fiscal_year'])['amount'].sum().unstack()
    
    # 3. Detailed analysis by section and fund category for each fiscal year
    detailed_analysis = {}
    for year in ['2026', '2027']:
        if year in df['fiscal_year'].unique():
            year_df = df[df['fiscal_year'] == year]
            analysis = year_df.groupby(['section', 'fund_category'])['amount'].sum().unstack().fillna(0)
            detailed_analysis[year] = analysis
    
    # Print results
    print("\n=== Budget Totals by Section and Fiscal Year ===")
    print(section_year_totals.map(format_currency).to_string())
    
    print("\n=== Budget Totals by Fund Category and Fiscal Year ===")
    print(fund_year_totals.map(format_currency).to_string())
    
    # Print detailed breakdown for each fiscal year
    for year, analysis in detailed_analysis.items():
        print(f"\n=== FY{year} - Budget by Section and Fund Category ===")
        print(analysis.map(format_currency).to_string())
    
    # Calculate and print grand totals with more details
    print("\n=== Grand Totals ===")
    for year in sorted(df['fiscal_year'].unique()):
        year_df = df[df['fiscal_year'] == str(year)]
        year_total = year_df['amount'].sum()
        operating = year_df[year_df['section'].str.contains('operating', case=False)]['amount'].sum()
        capital = year_df[year_df['section'].str.contains('capital', case=False)]['amount'].sum()
        
        print(f"\nFY{year}:")
        print(f"  Total Budget: {format_currency(year_total)}")
        print(f"  Operating:    {format_currency(operating)} ({(operating/year_total*100):.1f}%)")
        print(f"  Capital:      {format_currency(capital)} ({(capital/year_total*100):.1f}%)")
        
        # Identify top 5 programs by budget
        if 'program_name' in year_df.columns and 'program_id' in year_df.columns:
            print("\n  Top 5 Programs by Budget:")
            top_programs = year_df.groupby(['program_id', 'program_name'])['amount'].sum().nlargest(5)
            for (prog_id, prog_name), amount in top_programs.items():
                print(f"  - {prog_id}: {format_currency(amount)} - {prog_name[:60]}" + ("..." if len(prog_name) > 60 else ""))
    
    return {
        'section_year': section_year_totals,
        'fund_year': fund_year_totals,
        'detailed_analysis': detailed_analysis
    }

def main():
    parser = argparse.ArgumentParser(
        description='Analyze budget totals by section (Operating vs Capital) and fund types',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        'input_file', 
        help='Path to the parsed budget CSV file',
        default='data/processed/budget_parsed.csv', 
        nargs='?'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file path for saving the analysis (CSV format)',
        default=None
    )
    args = parser.parse_args()
    
    csv_path = Path(args.input_file)
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        return 1
    
    try:
        results = analyze_budget_totals(csv_path)
        
        # Save to CSV if output path is provided
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save each analysis to separate sheets in Excel
            with pd.ExcelWriter(output_path) as writer:
                if 'section_year' in results:
                    results['section_year'].to_excel(writer, sheet_name='By Section & Year')
                if 'fund_year' in results:
                    results['fund_year'].to_excel(writer, sheet_name='By Fund & Year')
                if 'detailed_analysis' in results:
                    for year, df in results['detailed_analysis'].items():
                        df.to_excel(writer, sheet_name=f'FY{year} Details')
            
            print(f"\nAnalysis saved to: {output_path}")
            
    except Exception as e:
        print(f"Error analyzing budget data: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
