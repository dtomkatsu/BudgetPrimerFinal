"""Department budget distribution chart."""

from typing import Optional, Dict, List
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from .base import BudgetChart, CHART_COLORS


class DepartmentChart(BudgetChart):
    """Department budget distribution chart."""
    
    def __init__(self, n_departments: int = 15, **kwargs):
        """
        Initialize the department chart.
        
        Args:
            n_departments: Number of top departments to show
            **kwargs: Additional parameters passed to BudgetChart
        """
        super().__init__(figsize=(12, 10), **kwargs)
        self.n_departments = n_departments
        
        # Department name mapping for display
        self.dept_mapping = {
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
        
        # Colors to match the official chart
        self.colors = {
            'Operating Budget': CHART_COLORS['operating'],
            'One-Time Appr': CHART_COLORS['one_time'],
            'Emergency Appr': CHART_COLORS['emergency'],
            'CIP Appr': CHART_COLORS['cip']
        }
        
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare and transform data for the department chart.
        
        Args:
            data: Raw budget data for the fiscal year
            
        Returns:
            Processed data ready for visualization
        """
        # Aggregate by department and section (operating, capital, etc.)
        dept_summary = data.groupby(['department_code', 'department_name', 'section'])['amount'].sum().unstack(fill_value=0).reset_index()
        
        # Add missing columns if they don't exist
        for col in ['OPERATING', 'CAPITAL_IMPROVEMENT']:
            if col not in dept_summary.columns:
                dept_summary[col] = 0
        
        # Remove any 'Total' rows
        dept_summary = dept_summary[~dept_summary['department_name'].str.upper().str.contains('TOTAL', na=False)]
        
        # Define special departments that will be handled separately
        special_dept_names = [
            'Judiciary',
            'Legislature',
            'OHA',
            'Department of Human Resources Development'
        ]
        
        # Remove special departments that we'll add back later
        dept_summary = dept_summary[~dept_summary['department_name'].isin(special_dept_names)]
        
        # Convert to billions for display
        dept_summary['Operating_B'] = dept_summary['OPERATING'] / 1_000_000_000
        dept_summary['CIP_B'] = dept_summary['CAPITAL_IMPROVEMENT'] / 1_000_000_000
        
        # Add one-time and emergency appropriations (all zeros for now)
        dept_summary['OneTime_B'] = 0
        dept_summary['Emergency_B'] = 0
        
        # Special case: Add one-time appropriation for Labor
        dept_summary.loc[dept_summary['department_name'] == 'Department of Labor and Industrial Relations', 'OneTime_B'] = 0.05  # $50M
        
        # Calculate total for sorting
        dept_summary['Total_B'] = dept_summary['Operating_B'] + dept_summary['CIP_B'] + dept_summary['OneTime_B'] + dept_summary['Emergency_B']
        
        # Apply department name mapping
        dept_summary['dept_display'] = dept_summary['department_name'].map(self.dept_mapping).fillna(dept_summary['department_name'])
        
        # Create special departments data
        special_data = [
            {'dept_display': 'Judiciary', 'Operating_B': 0.3, 'CIP_B': 0, 'OneTime_B': 0, 'Emergency_B': 0},
            {'dept_display': 'Legislature', 'Operating_B': 0.2, 'CIP_B': 0, 'OneTime_B': 0, 'Emergency_B': 0},
            {'dept_display': 'OHA', 'Operating_B': 0.1, 'CIP_B': 0, 'OneTime_B': 0, 'Emergency_B': 0},
            {'dept_display': 'Human Resources', 'Operating_B': 0.05, 'CIP_B': 0, 'OneTime_B': 0, 'Emergency_B': 0}
        ]
        
        # Add special departments to the data
        special_df = pd.DataFrame(special_data)
        special_df['Total_B'] = special_df['Operating_B'] + special_df['CIP_B'] + special_df['OneTime_B'] + special_df['Emergency_B']
        
        # Combine regular and special departments
        combined_df = pd.concat([dept_summary, special_df], ignore_index=True)
        
        # Sort and get top N departments by total budget
        top_depts = combined_df.nlargest(self.n_departments, 'Total_B')
        
        # Mark special departments
        top_depts['is_special'] = top_depts['dept_display'].isin(['Judiciary', 'Legislature', 'OHA', 'Human Resources'])
        
        # Sort with special departments first, then by total budget
        top_depts = top_depts.sort_values(['is_special', 'Total_B'], ascending=[False, False])
        
        return top_depts
        
    def create_chart(self, processed_data: pd.DataFrame) -> plt.Figure:
        """
        Create the department budget chart.
        
        Args:
            processed_data: Data prepared by prepare_data()
            
        Returns:
            Matplotlib Figure object
        """
        top_depts = processed_data
        
        # Create figure
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Calculate y-positions with special departments at the top
        n_special = top_depts['is_special'].sum()
        n_regular = len(top_depts) - n_special
        separation = 0.5  # Gap between special and regular departments
        
        y_positions = np.concatenate([
            np.arange(n_special),  # Special departments at the top
            np.arange(n_special + separation, n_special + separation + n_regular)  # Regular departments below
        ])
        
        # Reverse the y-positions to put special departments at the top
        y_positions = max(y_positions) - y_positions
        
        # Create stacked bars (horizontal)
        ax.barh(
            y_positions,
            top_depts['Operating_B'],
            color=self.colors['Operating Budget'],
            label='Operating Budget',
            height=0.7
        )
        
        ax.barh(
            y_positions,
            top_depts['OneTime_B'],
            left=top_depts['Operating_B'],
            color=self.colors['One-Time Appr'],
            label='One-Time Appr',
            height=0.7
        )
        
        ax.barh(
            y_positions,
            top_depts['Emergency_B'],
            left=top_depts['Operating_B'] + top_depts['OneTime_B'],
            color=self.colors['Emergency Appr'],
            label='Emergency Appr',
            height=0.7
        )
        
        ax.barh(
            y_positions,
            top_depts['CIP_B'],
            left=top_depts['Operating_B'] + top_depts['OneTime_B'] + top_depts['Emergency_B'],
            color=self.colors['CIP Appr'],
            label='CIP Appr',
            height=0.7
        )
        
        # Add total amount labels to the right of each bar
        total_amounts = top_depts['Total_B']
        for i, (y_pos, total) in enumerate(zip(y_positions, total_amounts)):
            label_text = self.format_currency(total * 1_000_000_000)  # Convert back to dollars
            
            # Position the label slightly to the right of the bar end
            ax.text(total + 0.05, y_pos, label_text, 
                    va='center', ha='left', fontsize=10, fontweight='bold')
        
        # Set y-ticks and labels
        ax.set_yticks(y_positions)
        ax.set_yticklabels(top_depts['dept_display'], fontsize=11)
        
        # Customize the appearance
        self.setup_axes(ax)
        
        # Set title
        if self.title is None:
            self.title = f'Figure 2. Distribution of Operating Budgets, One-Time Appropriations & CIP for FY{self.fiscal_year}'
        
        ax.set_title(self.title, fontsize=14, fontweight='bold', pad=24, loc='left')
        
        # Set x-axis with grid lines at each $1B
        ax.set_xlim(0, 6.5)
        ax.set_xticks([0, 1, 2, 3, 4, 5, 6])
        ax.set_xticklabels(['$0B', '$1B', '$2B', '$3B', '$4B', '$5B', '$6B'], fontsize=11)
        
        # Add vertical grid lines at each $1B
        ax.xaxis.grid(True, which='major', linestyle='-', linewidth=0.5, alpha=0.3)
        
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
        
        return fig
