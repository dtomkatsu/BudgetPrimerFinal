#!/usr/bin/env python3
"""
Budget Parser Script

This script parses a budget file and saves the results to separate CSV files for FY 2026 and FY 2027.
"""
import argparse
import logging
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from budgetprimer.parsers import parse_budget_file
from budgetprimer.models import BudgetSection

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all messages
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Enable debug logging for our parser
logging.getLogger('budgetprimer.parsers').setLevel(logging.DEBUG)

def save_budget_data(df: 'pd.DataFrame', output_dir: Path, fiscal_year: int, section: str = 'all') -> None:
    """Save budget data for a specific fiscal year and section."""
    # Filter by fiscal year
    df_year = df[df['fiscal_year'] == fiscal_year].copy()
    
    # Filter by section if specified
    if section != 'all':
        section_map = {
            'operating': BudgetSection.OPERATING.value,
            'capital': BudgetSection.CAPITAL_IMPROVEMENT.value
        }
        df_year = df_year[df_year['section'] == section_map[section]]
    
    # Skip if no data for this year
    if df_year.empty:
        logger.warning(f"No data found for FY {fiscal_year} (section: {section})")
        return
    
    # Sort by line number to maintain original document order
    sort_column = 'line_number' if 'line_number' in df_year.columns else 'program_id'
    df_year = df_year.sort_values(sort_column)
    
    # Determine output filename
    section_suffix = f"_{section}" if section != 'all' else ''
    output_path = output_dir / f"budget_parsed_fy{fiscal_year}{section_suffix}.csv"
    
    # Save to CSV
    df_year.to_csv(output_path, index=False)
    logger.info(f"Saved {len(df_year)} allocations to {output_path}")

def main():
    """Main function to parse and save budget data for both fiscal years."""
    parser = argparse.ArgumentParser(description='Parse a budget file and save results to CSV')
    parser.add_argument('input_file', help='Path to the budget file to parse')
    parser.add_argument('--output-dir', '-o', default='data/processed',
                      help='Output directory for CSV files (default: data/processed)')
    parser.add_argument('--fiscal-year', type=int, choices=[2026, 2027, 0], default=0,
                      help='Specific fiscal year to process (2026, 2027), or 0 for both (default: 0)')
    parser.add_argument('--section', choices=['operating', 'capital', 'all'], default='all',
                      help='Budget section to include (default: all)')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Parse the budget file
        logger.info(f"Parsing budget file: {args.input_file}")
        allocations = parse_budget_file(args.input_file)
        
        if not allocations:
            logger.error("No budget allocations found in the input file")
            return 1
        
        logger.info(f"Successfully parsed {len(allocations)} budget allocations")
        
        # Convert to list of dicts and create DataFrame
        import pandas as pd
        df = pd.DataFrame([alloc.to_dict() for alloc in allocations])
        
        # Determine which years to process
        fiscal_years = [2026, 2027] if args.fiscal_year == 0 else [args.fiscal_year]
        
        # Save data for each fiscal year
        for year in fiscal_years:
            save_budget_data(df, output_dir, year, args.section)
        
        # For backward compatibility, also save the default file for FY 2026
        if 2026 in fiscal_years and args.section == 'all':
            default_output = output_dir / "budget_parsed.csv"
            df_2026 = df[df['fiscal_year'] == 2026].copy()
            if 'line_number' in df_2026.columns:
                df_2026 = df_2026.sort_values('line_number')
            else:
                df_2026 = df_2026.sort_values('program_id')
            df_2026.to_csv(default_output, index=False)
            logger.info(f"Saved default output to {default_output}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error processing budget data: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
