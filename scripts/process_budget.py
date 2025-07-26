#!/usr/bin/env python3
"""
Budget Data Processing Script

This script processes and visualizes Hawaii State Budget data with optional
veto processing. It can show the original budget, the budget with vetoes applied,
or a comparison of both.
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import matplotlib.pyplot as plt

from budgetprimer import (
    parse_budget_file,
    process_budget_data,
    process_budget_with_vetoes,
    load_veto_changes,
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


def create_comparison_chart(
    pre_veto_df: pd.DataFrame,
    post_veto_df: pd.DataFrame,
    fiscal_year: int,
    chart_type: str,
    title_suffix: str = "",
    **kwargs
) -> Optional[plt.Figure]:
    """Create a comparison chart showing pre and post-veto data."""
    try:
        if chart_type == 'means_of_finance':
            # Create side-by-side pie charts
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
            
            # Pre-veto chart
            create_means_of_finance_chart(
                data=pre_veto_df,
                fiscal_year=fiscal_year,
                title=f"Pre-Veto: {title_suffix}",
                ax=ax1,
                **kwargs
            )
            
            # Post-veto chart
            create_means_of_finance_chart(
                data=post_veto_df,
                fiscal_year=fiscal_year,
                title=f"Post-Veto: {title_suffix}",
                ax=ax2,
                **kwargs
            )
            
            plt.tight_layout()
            return fig
            
        elif chart_type == 'department_budget':
            # Create side-by-side bar charts
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 12))
            
            create_department_budget_chart(
                data=pre_veto_df,
                fiscal_year=fiscal_year,
                title=f"Pre-Veto: {title_suffix}",
                ax=ax1,
                **kwargs
            )
            
            create_department_budget_chart(
                data=post_veto_df,
                fiscal_year=fiscal_year,
                title=f"Post-Veto: {title_suffix}",
                ax=ax2,
                **kwargs
            )
            
            plt.tight_layout()
            return fig
            
    except Exception as e:
        logger.error(f"Error creating comparison chart: {str(e)}", exc_info=True)
        return None

def main():
    """Main function to process and visualize budget data with optional veto processing."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process Hawaii State Budget data with optional veto processing')
    parser.add_argument('input_file', help='Path to the budget file to process')
    parser.add_argument('--output-dir', default='data/output', help='Output directory for results')
    parser.add_argument('--fiscal-year', type=int, default=2026, help='Fiscal year to analyze')
    parser.add_argument('--top-n', type=int, default=15, help='Number of top items to show in charts')
    parser.add_argument('--veto-mode', choices=['none', 'apply', 'both'], default='none',
                      help="How to handle vetoes: 'none' (default), 'apply' (show post-veto only), 'both' (compare pre/post)")
    parser.add_argument('--veto-file', default='data/raw/vetoes/governor_vetoes_fy2026_actual.csv',
                      help='Path to the veto CSV file (default: data/raw/vetoes/governor_vetoes_fy2026_actual.csv)')
    args = parser.parse_args()
    
    # Create output directories
    output_dir = Path(args.output_dir)
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
        
        # Step 2: Process the budget data with optional veto handling
        logger.info("Processing budget data...")
        
        # Process with veto mode handling
        result = process_budget_with_vetoes(
            allocations=allocations,
            veto_mode=args.veto_mode,
            veto_file=Path(args.veto_file) if args.veto_file else None,
            fiscal_year=args.fiscal_year
        )
        
        # Get the appropriate DataFrame based on veto mode
        if args.veto_mode == 'apply':
            df = result['post_veto_df']
            logger.info("Showing post-veto budget data")
        else:
            df = result['pre_veto_df']
            if args.veto_mode == 'both':
                logger.info("Showing pre-veto budget data (use --veto-mode=apply for post-veto)")
        
        # Save processed data to CSV
        output_csv = processed_dir / f'budget_allocations_fy{args.fiscal_year}.csv'
        df.to_csv(output_csv, index=False)
        logger.info(f"Saved processed data to {output_csv}")
        
        # Save a copy with veto status in filename
        if args.veto_mode == 'apply':
            output_csv_veto = processed_dir / f'budget_allocations_fy{args.fiscal_year}_post_veto.csv'
            df.to_csv(output_csv_veto, index=False)
            logger.info(f"Saved post-veto data to {output_csv_veto}")
        
        # Step 3: Create visualizations
        logger.info("Creating visualizations...")
        
        # Common chart arguments
        chart_kwargs = {
            'fiscal_year': args.fiscal_year,
            'n_departments': args.top_n,
            'n_projects': args.top_n,
            'figsize': (14, 10)
        }
        
        if args.veto_mode == 'both':
            # Create comparison visualizations
            logger.info("Creating comparison visualizations (pre-veto vs post-veto)")
            
            # 3.1 Means of Finance comparison
            moa_chart = create_comparison_chart(
                pre_veto_df=result['pre_veto_df'],
                post_veto_df=result['post_veto_df'],
                fiscal_year=args.fiscal_year,
                chart_type='means_of_finance',
                title_suffix=f"Means of Finance (FY{args.fiscal_year})",
                **chart_kwargs
            )
            if moa_chart:
                moa_output = charts_dir / f'means_of_finance_fy{args.fiscal_year}_comparison.png'
                moa_chart.savefig(moa_output, dpi=300, bbox_inches='tight')
                logger.info(f"Saved Means of Finance comparison to {moa_output}")
            
            # 3.2 Department budget comparison
            dept_chart = create_comparison_chart(
                pre_veto_df=result['pre_veto_df'],
                post_veto_df=result['post_veto_df'],
                fiscal_year=args.fiscal_year,
                chart_type='department_budget',
                title_suffix=f"Top {args.top_n} Department Budgets (FY{args.fiscal_year})",
                **chart_kwargs
            )
            if dept_chart:
                dept_output = charts_dir / f'top_departments_fy{args.fiscal_year}_comparison.png'
                dept_chart.savefig(dept_output, dpi=300, bbox_inches='tight')
                logger.info(f"Saved Department Budget comparison to {dept_output}")
            
        else:
            # Create standard visualizations (single view)
            veto_suffix = "_post_veto" if args.veto_mode == 'apply' else ""
            
            # 3.1 Means of Finance pie chart
            moa_chart = create_means_of_finance_chart(
                data=df,
                title=f"Hawaii State Budget - Means of Finance (FY{args.fiscal_year}{' - Post-Veto' if args.veto_mode == 'apply' else ''})",
                **chart_kwargs
            )
            moa_output = charts_dir / f'means_of_finance_fy{args.fiscal_year}{veto_suffix}.png'
            moa_chart.savefig(moa_output, dpi=300, bbox_inches='tight')
            logger.info(f"Saved Means of Finance chart to {moa_output}")
            
            # 3.2 Department budget chart
            dept_chart = create_department_budget_chart(
                data=df,
                title=f"Top {args.top_n} Department Budgets (FY{args.fiscal_year}{' - Post-Veto' if args.veto_mode == 'apply' else ''})",
                **chart_kwargs
            )
            dept_output = charts_dir / f'top_departments_fy{args.fiscal_year}{veto_suffix}.png'
            dept_chart.savefig(dept_output, dpi=300, bbox_inches='tight')
            logger.info(f"Saved Department Budget chart to {dept_output}")
            
            # 3.3 CIP funding chart (if there are capital projects)
            if 'Capital Improvement' in df['section'].unique():
                cip_chart = create_cip_funding_chart(
                    data=df,
                    title=f"Top {args.top_n} Capital Improvement Projects (FY{args.fiscal_year}{' - Post-Veto' if args.veto_mode == 'apply' else ''})",
                    **chart_kwargs
                )
                cip_output = charts_dir / f'top_cip_projects_fy{args.fiscal_year}{veto_suffix}.png'
                cip_chart.savefig(cip_output, dpi=300, bbox_inches='tight')
                logger.info(f"Saved CIP Funding chart to {cip_output}")
        
        logger.info("Processing completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Error processing budget data: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
