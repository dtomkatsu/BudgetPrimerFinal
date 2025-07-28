#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import sys
import logging

# Add the project root to the path to allow absolute imports
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import utility functions
from budgetprimer.utils.special_departments import add_special_departments

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_department_budget_chart(csv_file_path, output_path=None):
    """
    Create a horizontal bar chart showing department budget distribution.
    
    Args:
        csv_file_path (str): Path to the budget summary CSV file
        output_path (str): Path to save the chart (optional)
    """
    # Read the data
    df = pd.read_csv(csv_file_path)
    
    # Debug: Print the raw data for Human Resources
    hr_raw = df[df['dept_name'] == 'Department of Human Resources Development']
    if not hr_raw.empty:
        logger.info("\n=== RAW HUMAN RESOURCES BUDGET ===")
        logger.info(f"Operating: ${hr_raw['OPERATING'].values[0]:.2f}")
        logger.info(f"CIP: ${hr_raw['CAPITAL IMPROVEMENT'].values[0]:.2f}")
    
    # Define special departments that will be handled separately
    special_dept_names = [
        'Judiciary',
        'Legislature',
        'OHA',
        'Department of Human Resources Development'  # We'll handle HR specially
    ]
    
    # Remove any row where dept_name is 'TOTAL' or contains 'County of' or 'Subaccount'
    # Also remove special departments that we'll add back later
    # Also remove Governor and Lieutenant Governor offices since they'll be combined
    df = df[~df['dept_name'].str.upper().str.contains('TOTAL', na=False)]
    df = df[~df['dept_name'].str.contains('County of', case=False, na=False)]
    df = df[~df['dept_name'].str.contains('Subaccount', case=False, na=False)]
    df = df[~df['dept_name'].isin(special_dept_names)]  # Remove special departments
    df = df[~df['dept_name'].str.contains('Office of the Governor', case=False, na=False)]
    df = df[~df['dept_name'].str.contains('Office of the Lieutenant Governor', case=False, na=False)]
    
    # Reset index after filtering
    df = df.reset_index(drop=True)
    
    # Debug: Print the filtered data for Human Resources
    hr_filtered = df[df['dept_name'] == 'Department of Human Resources Development']
    if not hr_filtered.empty:
        logger.info("\n=== FILTERED HUMAN RESOURCES BUDGET ===")
        logger.info(f"Operating: ${hr_filtered['OPERATING'].values[0]:.2f}")
        logger.info(f"CIP: ${hr_filtered['CAPITAL IMPROVEMENT'].values[0]:.2f}")
    
    # Convert amounts from dollars to billions for display
    df['Operating_B'] = df['OPERATING'] / 1e9
    df['CIP_B'] = df['CAPITAL IMPROVEMENT'] / 1e9
    
    # Add one-time appropriation for Department of Labor and Industrial Relations
    df.loc[df['dept_name'] == 'Department of Labor and Industrial Relations', 'OneTime_B'] = 0.05  # $50M
    df['OneTime_B'] = df.get('OneTime_B', 0).fillna(0)
    
    # Add emergency appropriations (all zeros for now)
    df['Emergency_B'] = 0
    
    # Calculate total for sorting
    df['Total_B'] = df['Operating_B'] + df['CIP_B'] + df['OneTime_B'] + df['Emergency_B']
    
    # Create department name mapping for display
    dept_mapping = {
        'Department of Human Services': 'Human Services',
        'Department of Budget and Finance': 'Budget & Finance',
        'Department of Education': 'Education',
        'Department of Transportation': 'Transportation',
        'Department of Health': 'Health',
        'University of Hawaii': 'UH System',
        'Department of Business, Economic Development and Tourism': 'Bus, Econ Dev, Tour',
        'Department of Labor and Industrial Relations': 'Labor',
        'Department of Corrections and Rehabilitation': 'Corrections',
        'Department of Land and Natural Resources': 'Land & Natural Res',
        'Department of Accounting and General Services': 'Accounting & Gen Ser',
        'Department of Defense': 'Defense',
        'Department of Hawaiian Home Lands': 'Hawaiian Home Lands',
        'Department of the Attorney General': 'Attorney General',
        'Department of Commerce and Consumer Affairs': 'Commerce',
        'Department of Law Enforcement': 'Law Enforcement',
        'Department of Agriculture': 'Agriculture',
        'Department of Taxation': 'Taxation',
        'Department of Human Resources Development': 'Human Resources'
    }
    
    # Debug: Check the Human Resources row before mapping
    hr_raw = df[df['dept_name'] == 'Department of Human Resources Development']
    if not hr_raw.empty:
        logger.info("\n=== RAW HUMAN RESOURCES BUDGET ===")
        logger.info(f"Operating: ${hr_raw['OPERATING'].values[0] / 1e9:.3f}B")
        logger.info(f"CIP: ${hr_raw['CAPITAL IMPROVEMENT'].values[0] / 1e9:.3f}B")
    
    # Apply department name mapping first
    df['dept_display'] = df['dept_name'].map(dept_mapping).fillna(df['dept_name'])
    
    # Add special departments using the utility function
    special_df = add_special_departments(pd.DataFrame())
    df = pd.concat([df, special_df], ignore_index=True)
    
    # Remove any 'Total' row
    df = df[df['dept_name'] != 'Total']
    
    # Mark special departments
    special_depts = ['Judiciary', 'Legislature', 'OHA']
    df['is_special'] = df['dept_name'].isin(special_depts)
    
    # Sort with special departments first, then by total budget
    df = df.sort_values(['is_special', 'Total_B'], ascending=[False, False])
    
    # Debug: Check Human Resources department
    hr_row = df[df['dept_display'] == 'Human Resources']
    if not hr_row.empty:
        logger.info("\n=== HUMAN RESOURCES BUDGET ===")
        logger.info(f"Operating: ${hr_row['Operating_B'].values[0]:.3f}B")
        logger.info(f"One-Time: ${hr_row['OneTime_B'].values[0]:.3f}B")
        logger.info(f"CIP: ${hr_row['CIP_B'].values[0]:.3f}B")
        logger.info(f"Emergency: ${hr_row['Emergency_B'].values[0]:.3f}B")
        logger.info(f"Total: ${hr_row['Total_B'].values[0]:.3f}B")
    
    # Reset index for proper y-positions
    df = df.reset_index(drop=True)
    
    # Extract data for plotting
    departments = df['dept_display'].tolist()
    operating_budget = df['Operating_B'].values
    one_time_appr = df['OneTime_B'].values
    emergency_appr = df['Emergency_B'].values
    cip_appr = df['CIP_B'].values
    
    # Create figure and axis with appropriate size
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Define colors to match the official chart
    colors = {
        'Operating Budget': '#1f4e79',  # Dark blue
        'One-Time Appr': '#2d8659',     # Green  
        'Emergency Appr': '#2c2c2c',    # Black/dark gray
        'CIP Appr': '#5fb3d4'           # Light blue/teal
    }
    
    # Create the stacked horizontal bar chart with separation
    n_special = df['is_special'].sum()
    n_regular = len(df) - n_special
    
    # Add extra space after special departments
    separation = 0.5  # Gap between special and regular departments
    
    # Calculate y-positions with special departments at the top
    y_positions = np.concatenate([
        np.arange(n_special),  # Special departments at the top
        np.arange(n_special + separation, n_special + separation + n_regular)  # Regular departments below
    ])
    
    # Reverse the y-positions to put special departments at the top
    y_positions = max(y_positions) - y_positions
    
    # Create stacked bars (horizontal)
    ax.barh(y_positions, operating_budget, 
            color=colors['Operating Budget'], 
            label='Operating Budget',
            height=0.7)
    
    ax.barh(y_positions, one_time_appr, 
            left=operating_budget, 
            color=colors['One-Time Appr'], 
            label='One-Time Appr',
            height=0.7)
    
    ax.barh(y_positions, emergency_appr, 
            left=operating_budget + one_time_appr, 
            color=colors['Emergency Appr'], 
            label='Emergency Appr',
            height=0.7)
    
    ax.barh(y_positions, cip_appr, 
            left=operating_budget + one_time_appr + emergency_appr, 
            color=colors['CIP Appr'], 
            label='CIP Appr',
            height=0.7)
    
    # Add total amount labels to the right of each bar
    total_amounts = operating_budget + one_time_appr + emergency_appr + cip_appr
    for i, (y_pos, total) in enumerate(zip(y_positions, total_amounts)):
        # Format the total amount - show billions for >=1B, millions for <1B
        if total >= 1.0:
            label_text = f'${total:.1f}B'
        else:
            # Convert to millions and show with M suffix
            millions = total * 1000
            if millions >= 100:
                label_text = f'${millions:.0f}M'
            elif millions >= 10:
                label_text = f'${millions:.1f}M'
            else:
                label_text = f'${millions:.2f}M'
        
        # Position the label slightly to the right of the bar end
        ax.text(total + 0.05, y_pos, label_text, 
                va='center', ha='left', fontsize=10, fontweight='bold')
    
    # Customize the appearance
    ax.set_yticks(y_positions)
    ax.set_yticklabels(departments, fontsize=11)
    
    # Remove spines for cleaner look
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # Set title and labels
    ax.set_title(
        'Figure 2. Distribution of Operating Budgets, One-Time Appropriations & CIP for FY26',
        fontsize=14, 
        fontweight='bold', 
        pad=24,
        loc='left'
    )
    
    # Set x-axis with grid lines at each $1B (extended to accommodate labels)
    ax.set_xlim(0, 6.5)
    ax.set_xticks([0, 1, 2, 3, 4, 5, 6])
    ax.set_xticklabels(['$0B', '$1B', '$2B', '$3B', '$4B', '$5B', '$6B'], fontsize=11)
    
    # Add vertical grid lines at each $1B
    ax.xaxis.grid(True, which='major', linestyle='-', linewidth=0.5, alpha=0.3)
    
    ax.set_axisbelow(True)  # Ensure grid is behind bars
    
    # Add legend in a single row below the chart
    ax.legend(
        loc='upper center',
        bbox_to_anchor=(0.5, -0.1),  # Position below the chart
        ncol=4,  # Number of columns in the legend
        frameon=False,
        fontsize=11,
        borderaxespad=0.5
    )
    
    # Adjust the bottom margin to make room for the legend
    plt.subplots_adjust(bottom=0.15)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the chart
    if output_path is None:
        output_path = Path('output/charts/department_budget_distribution_v2.png')
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    logger.info(f"Chart saved to: {output_path}")
    
    # Also save as PDF for high quality
    pdf_path = output_path.with_suffix('.pdf')
    plt.savefig(pdf_path, bbox_inches='tight', facecolor='white', edgecolor='none')
    logger.info(f"PDF version saved to: {pdf_path}")
    
    # Show the plot
    plt.show()
    
    return output_path

def main():
    """Main function to run the chart creation script."""
    
    # Default path to post-veto FY26 summary
    default_csv_path = "data/post_veto/post_veto_fy26_summary.csv"
    
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = default_csv_path
    
    if not Path(csv_path).exists():
        logger.error(f"CSV file not found: {csv_path}")
        logger.info(f"Please ensure the file exists or provide a valid path.")
        logger.info(f"Usage: python {sys.argv[0]} [path_to_csv_file]")
        sys.exit(1)
    
    try:
        output_path = create_department_budget_chart(csv_path)
        logger.info("Chart creation completed successfully!")
        
    except Exception as e:
        logger.error(f"Error creating chart: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
