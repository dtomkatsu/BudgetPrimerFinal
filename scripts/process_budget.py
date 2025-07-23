#!/usr/bin/env python3
"""
Budget Data Processing Script

This script demonstrates how to use the BudgetPrimerFinal package to process
and visualize Hawaii State Budget data.
"""
import argparse
import logging
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd

from budgetprimer import (
    parse_budget_file,
    process_budget_data,
    transform_to_post_veto
)
from budgetprimer.visualization import (
    create_means_of_finance_chart,
    create_department_budget_chart,
    create_cip_funding_chart
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('budget_processing.log')
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Main function to process and visualize budget data."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process Hawaii State Budget data')
    parser.add_argument('input_file', help='Path to the budget file to process')
    parser.add_argument('--output-dir', default='output', help='Output directory for results')
    parser.add_argument('--fiscal-year', type=int, default=2026, help='Fiscal year to analyze')
    parser.add_argument('--top-n', type=int, default=15, help='Number of top items to show in charts')
    args = parser.parse_args()
    
    # Create output directories
    output_dir = Path('data/output')
    processed_dir = Path('data/processed')
    charts_dir = output_dir / 'charts'
    
    # Create necessary directories
    for d in [output_dir, charts_dir, processed_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    try:
        # Step 1: Parse the budget file
        logger.info(f"Parsing budget file: {args.input_file}")
        allocations = parse_budget_file(args.input_file)
        
        if not allocations:
            logger.error("No budget allocations found in the input file")
            return 1
        
        logger.info(f"Successfully parsed {len(allocations)} budget allocations")
        
        # Step 2: Process the budget data
        logger.info("Processing budget data...")
        df = process_budget_data(allocations, fiscal_year=args.fiscal_year)
        
        # Save processed data to processed directory
        output_csv = processed_dir / 'budget_allocations.csv'
        df.to_csv(output_csv, index=False)
        logger.info(f"Saved processed data to {output_csv}")
        
        # Also save a copy to output directory for backward compatibility
        output_csv_compat = output_dir / 'processed_budget.csv'
        df.to_csv(output_csv_compat, index=False)
        
        # Step 3: Create visualizations
        logger.info("Creating visualizations...")
        
        # 3.1 Means of Finance pie chart
        moa_chart = create_means_of_finance_chart(
            data=df,
            fiscal_year=args.fiscal_year,
            title=f"Hawaii State Budget - Means of Finance (FY{args.fiscal_year})",
            figsize=(14, 10)
        )
        moa_output = charts_dir / f'means_of_finance_fy{args.fiscal_year}.png'
        moa_chart.savefig(moa_output, dpi=300, bbox_inches='tight')
        logger.info(f"Saved Means of Finance chart to {moa_output}")
        
        # 3.2 Department budget chart
        dept_chart = create_department_budget_chart(
            data=df,
            fiscal_year=args.fiscal_year,
            n_departments=args.top_n,
            title=f"Top {args.top_n} Department Budgets (FY{args.fiscal_year})",
            figsize=(14, 10)
        )
        dept_output = charts_dir / f'top_departments_fy{args.fiscal_year}.png'
        dept_chart.savefig(dept_output, dpi=300, bbox_inches='tight')
        logger.info(f"Saved Department Budget chart to {dept_output}")
        
        # 3.3 CIP funding chart (if there are capital projects)
        if 'CAPITAL_IMPROVEMENT' in df['section'].unique():
            cip_chart = create_cip_funding_chart(
                data=df,
                fiscal_year=args.fiscal_year,
                n_projects=args.top_n,
                title=f"Top {args.top_n} Capital Improvement Projects (FY{args.fiscal_year})",
                figsize=(14, 10)
            )
            cip_output = charts_dir / f'top_cip_projects_fy{args.fiscal_year}.png'
            cip_chart.savefig(cip_output, dpi=300, bbox_inches='tight')
            logger.info(f"Saved CIP Funding chart to {cip_output}")
        
        logger.info("Processing completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Error processing budget data: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
