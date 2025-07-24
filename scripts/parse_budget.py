#!/usr/bin/env python3
"""
Budget Parser Script

This script parses a budget file and saves the results to CSV without generating visualizations.
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

def main():
    """Main function to parse and save budget data."""
    parser = argparse.ArgumentParser(description='Parse a budget file and save results to CSV')
    parser.add_argument('input_file', help='Path to the budget file to parse')
    parser.add_argument('--output', '-o', default='data/processed/budget_parsed.csv',
                      help='Output CSV file path (default: data/processed/budget_parsed.csv)')
    parser.add_argument('--fiscal-year', type=int, default=2026,
                      help='Fiscal year to include in the output (default: 2026)')
    parser.add_argument('--section', choices=['operating', 'capital', 'all'], default='all',
                      help='Budget section to include (default: all)')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Parse the budget file
        logger.info(f"Parsing budget file: {args.input_file}")
        allocations = parse_budget_file(args.input_file)
        
        if not allocations:
            logger.error("No budget allocations found in the input file")
            return 1
        
        logger.info(f"Successfully parsed {len(allocations)} budget allocations")
        
        # Convert to list of dicts
        data = [alloc.to_dict() for alloc in allocations]
        
        # Create DataFrame
        import pandas as pd
        df = pd.DataFrame(data)
        
        # Filter by fiscal year
        if args.fiscal_year > 0:  # Only filter if a specific year is requested
            df = df[df['fiscal_year'] == args.fiscal_year]
        
        # Filter by section if specified
        if args.section != 'all':
            section_map = {
                'operating': BudgetSection.OPERATING.value,
                'capital': BudgetSection.CAPITAL_IMPROVEMENT.value
            }
            df = df[df['section'] == section_map[args.section]]
        
        # Sort by line number to maintain original document order
        if 'line_number' in df.columns:
            df = df.sort_values('line_number')
        else:
            # Fallback to sorting by program_id if line_number is not available
            df = df.sort_values('program_id')
        
        # Save to CSV
        df.to_csv(output_path, index=False)
        logger.info(f"Saved parsed data to {output_path}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error processing budget data: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
