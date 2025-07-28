#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import sys
import logging

# Add the project root to the path to allow absolute imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_cip_funding_pie_chart(csv_file_path, output_path=None):
    """
    Create a pie chart showing distribution of Capital Improvement Project funding
    by category using the category information from the parsed data.
    
    Args:
        csv_file_path (str): Path to the budget data CSV file
        output_path (str): Path to save the chart (optional)
    """
    # Read the data with proper encoding and handling
    logger.info(f"Loading data from {csv_file_path}")
    try:
        # First try with standard CSV reading
        df = pd.read_csv(csv_file_path, dtype={'fiscal_year': str, 'amount': float})
        
        # If we don't have proper categories, try with different encoding
        if 'category' not in df.columns or df['category'].isna().all():
            logger.warning("Category data not found, trying with different encoding...")
            df = pd.read_csv(csv_file_path, encoding='latin1', dtype={'fiscal_year': str, 'amount': float})
            
        # Filter for Capital Improvement section and FY2026 only
        cip_df = df[(df['section'] == 'Capital Improvement') & (df['fiscal_year'] == '2026')].copy()
        
        # Clean up category names
        cip_df['category'] = cip_df['category'].fillna('Uncategorized')
        cip_df['category'] = cip_df['category'].str.strip()
        
        # Debug: Print unique categories found
        logger.info("\nFound CIP Categories:" + "\n- " + "\n- ".join(sorted(cip_df['category'].unique())))
        
        # Show some sample entries for verification
        logger.info("\nSample CIP entries by category:")
        for category in sorted(cip_df['category'].unique()):
            sample_entries = cip_df[cip_df['category'] == category][['department_code', 'program', 'amount']].head(2)
            logger.info(f"\n{category}:")
            for _, row in sample_entries.iterrows():
                logger.info(f"  {row['department_code']}: {row['program']} - ${row['amount']:,.0f}")
        
    except Exception as e:
        logger.error(f"Error reading or processing CSV file: {e}")
        raise
    
    # Group categories as requested: Transportation, Formal Education, Economic Development, Health, and All Others
    main_categories = ['Transportation', 'Education', 'Economic Development', 'Health']
    
    # Create consolidated category totals
    consolidated_totals = {}
    for category in main_categories:
        if category == 'Education':
            # Map 'Education' to 'Formal Education' for display
            consolidated_totals['Formal Education'] = cip_df[cip_df['category'] == category]['amount'].sum()
        else:
            consolidated_totals[category] = cip_df[cip_df['category'] == category]['amount'].sum()
    
    # Sum all other categories into 'All Others'
    other_categories = cip_df[~cip_df['category'].isin(main_categories)]['amount'].sum()
    consolidated_totals['All Others'] = other_categories
    
    # Convert to pandas Series and sort by value (descending)
    category_totals = pd.Series(consolidated_totals).sort_values(ascending=False)
    
    # Calculate total and print summary
    total_cip = category_totals.sum()
    logger.info(f"\nTotal CIP Funding (FY2026): ${total_cip:,.2f}")
    logger.info("\nConsolidated Funding by Category:")
    for category, amount in category_totals.items():
        logger.info(f"{category}: ${amount:,.2f} ({(amount/total_cip)*100:.1f}%)")
    
    # Create the pie chart with styling to match the reference
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Define colors matching the reference chart (blues and teals)
    colors = ['#5DADE2', '#17A2B8', '#138D75', '#1B4F72', '#2C3E50']  # Light blue to dark blue/teal
    
    # Create a function to format the values on pie slices
    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct*total/100.0))
            return f'${val/1e6:.0f}'
        return my_autopct
    
    # Create the pie chart with values displayed on slices
    wedges, texts, autotexts = ax.pie(
        category_totals,
        labels=None,  # No labels on slices, we'll use legend
        colors=colors[:len(category_totals)],
        autopct=make_autopct(category_totals),
        startangle=90,
        textprops={'fontsize': 14, 'fontweight': 'bold', 'color': 'white'}
    )
    
    # Customize the value text on pie slices
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(14)
        autotext.set_fontweight('bold')
    
    # Create legend with category names only (matching reference style)
    legend_labels = list(category_totals.index)
    ax.legend(
        wedges, 
        legend_labels, 
        title="",
        loc="center left", 
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=12, 
        title_fontsize=12
    )
    
    # Set title matching the reference format
    ax.set_title(
        f'Figure 4. Distribution of Capital Improvement Project Funding, FY26 ($ Millions)\nTotal: ${total_cip/1e6:.0f}M', 
        fontsize=14, 
        fontweight='bold', 
        pad=20
    )
    
    # Ensure the pie chart is circular
    ax.axis('equal')
    
    # Set output path if not provided
    if output_path is None:
        output_dir = Path("output/charts")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / 'cip_funding_by_category.png'
    
    # Save the chart
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=300)
    logger.info(f"\nChart saved to: {output_path}")
    
    # Also save as PDF for better quality
    pdf_path = str(output_path).replace('.png', '.pdf')
    plt.savefig(pdf_path, bbox_inches='tight', dpi=300)
    logger.info(f"PDF version saved to: {pdf_path}")
    
    plt.close()
    
    return {
        'total_cip': total_cip,
        'category_totals': category_totals.to_dict(),
        'chart_path': str(output_path),
        'pdf_path': pdf_path
    }

def main():
    """Main function to run the chart creation script."""
    # Find the most recent parsed budget file
    processed_dir = Path("data/processed")
    budget_files = sorted(processed_dir.glob("HB 300 CD 1_allocations.csv_*.csv"), reverse=True)
    
    if not budget_files:
        logger.error("No parsed budget files found. Please run the parser first.")
        return
    
    # Use the most recent file
    latest_file = budget_files[0]
    logger.info(f"Using file: {latest_file}")
    
    try:
        # Create the chart and get results
        results = create_cip_funding_pie_chart(latest_file)
        logger.info("\nChart creation completed successfully!")
        logger.info(f"Total CIP Funding: ${results['total_cip']:,.2f}")
        
    except Exception as e:
        logger.error(f"Error creating chart: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
