"""Department budget distribution chart."""

from typing import Optional, Dict, List
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from .base import BudgetChart, CHART_COLORS


class DepartmentChart(BudgetChart):
    """Department budget distribution chart."""
    
    def __init__(self, **kwargs):
        """
        Initialize the department chart.
        
        Args:
            **kwargs: Additional parameters passed to BudgetChart
        """
        super().__init__(figsize=(12, 10), **kwargs)
        
        # First map department codes to full names - include ALL codes from data
        self.code_to_name = {
            'AGR': 'Department of Agriculture',
            'AGS': 'Department of Accounting and General Services',
            'ATG': 'Department of the Attorney General',
            'BED': 'Department of Business, Economic Development and Tourism',
            'BUF': 'Department of Budget and Finance',
            'CCA': 'Department of Commerce and Consumer Affairs',
            'CCH': 'City and County of Honolulu',
            'COH': 'County of Hawaii',
            'COK': 'County of Kauai',
            'DEF': 'Department of Defense',
            'EDN': 'Department of Education',
            'GOV': 'Office of the Governor',
            'HHL': 'Department of Hawaiian Home Lands',
            'HMS': 'Department of Human Services',
            'HRD': 'Department of Human Resources Development',
            'HTH': 'Department of Health',
            'LAW': 'Department of Law Enforcement',
            'LBR': 'Department of Labor and Industrial Relations',
            'LNR': 'Department of Land and Natural Resources',
            'LTG': 'Office of the Lieutenant Governor',
            'P': 'General Administration',
            'PSD': 'Department of Corrections and Rehabilitation',
            'TAX': 'Department of Taxation',
            'TRN': 'Department of Transportation',
            'UOH': 'University of Hawaii'
        }
        
        # Then map full names to display names - include all departments
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
            'Department of Human Resources Development': 'Human Resources',
            'City and County of Honolulu': 'Honolulu County',
            'County of Hawaii': 'Hawaii County',
            'County of Kauai': 'Kauai County',
            'Office of the Governor': 'Governor',
            'Office of the Lieutenant Governor': 'Lieutenant Governor',
            'General Administration': 'General Admin'
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
        dept_summary = data.groupby(['department_code', 'section'])['amount'].sum().unstack(fill_value=0).reset_index()
        
        # Add missing columns if they don't exist
        for col in ['Operating', 'Capital Improvement']:
            if col not in dept_summary.columns:
                dept_summary[col] = 0
        
        # Map department codes to full names
        dept_summary['department_name'] = dept_summary['department_code'].map(self.code_to_name)
        
        # Remove departments that don't have a mapping (likely special cases)
        dept_summary = dept_summary.dropna(subset=['department_name'])
        
        # Define special departments that will be handled separately
        special_dept_names = [
            'Judiciary',
            'Legislature', 
            'OHA',
            'Department of Human Resources Development'  # We'll handle HR specially
        ]
        
        # Remove only TOTAL rows and Subaccounts - keep all real departments including counties and governor offices
        dept_summary = dept_summary[~dept_summary['department_name'].str.upper().str.contains('TOTAL', na=False)]
        dept_summary = dept_summary[~dept_summary['department_name'].str.contains('Subaccount', case=False, na=False)]
        # Note: We now keep counties and governor offices to show ALL departments
        # Only remove the special departments that will be added back manually
        dept_summary = dept_summary[~dept_summary['department_name'].isin(special_dept_names)]
        
        # Reset index after filtering
        dept_summary = dept_summary.reset_index(drop=True)
        
        # Convert amounts from dollars to billions for display
        dept_summary['Operating_B'] = dept_summary['Operating'] / 1e9
        dept_summary['CIP_B'] = dept_summary['Capital Improvement'] / 1e9
        
        # Add one-time appropriation for Department of Labor and Industrial Relations
        dept_summary.loc[dept_summary['department_name'] == 'Department of Labor and Industrial Relations', 'OneTime_B'] = 0.05  # $50M
        dept_summary['OneTime_B'] = dept_summary.get('OneTime_B', 0).fillna(0)
        
        # Add emergency appropriations (all zeros for now)
        dept_summary['Emergency_B'] = 0
        
        # Calculate total for sorting
        dept_summary['Total_B'] = dept_summary['Operating_B'] + dept_summary['CIP_B'] + dept_summary['OneTime_B'] + dept_summary['Emergency_B']
        
        # Map department names for display
        dept_summary['dept_display'] = dept_summary['department_name'].map(self.dept_mapping).fillna(dept_summary['department_name'])
        
        # Add special departments with fixed amounts (in billions)
        special_depts = [
            {'dept_display': 'OHA', 'Operating_B': 0.0046, 'OneTime_B': 0, 'Emergency_B': 0, 'CIP_B': 0, 'Total_B': 0.0046, 'is_special': True},
            {'dept_display': 'Legislature', 'Operating_B': 0.044, 'OneTime_B': 0, 'Emergency_B': 0, 'CIP_B': 0, 'Total_B': 0.044, 'is_special': True},
            {'dept_display': 'Judiciary', 'Operating_B': 0.2017, 'OneTime_B': 0, 'Emergency_B': 0, 'CIP_B': 0, 'Total_B': 0.2017, 'is_special': True}
        ]
        
        # Mark regular departments
        dept_summary['is_special'] = False
        
        # Sort regular departments by total amount (ascending - smallest at top)
        dept_summary = dept_summary.sort_values('Total_B', ascending=True)
        
        # Combine special and regular departments (special at bottom like reference)
        special_df = pd.DataFrame(special_depts)
        all_depts = pd.concat([dept_summary, special_df], ignore_index=True)
        
        return all_depts
        
    def create_chart(self, processed_data: pd.DataFrame) -> plt.Figure:
        """
        Create the department budget chart.
        
        Args:
            processed_data: Data prepared by prepare_data()
            
        Returns:
            Matplotlib Figure object
        """
        all_depts = processed_data
        
        # Create figure
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Keep the order from prepare_data (ascending - smallest at top, largest at bottom)
        # Calculate y-positions
        y_positions = np.arange(len(all_depts))
        
        # Create stacked bars (horizontal)
        ax.barh(
            y_positions,
            all_depts['Operating_B'],
            color=self.colors['Operating Budget'],
            label='Operating Budget',
            height=0.7
        )
        
        ax.barh(
            y_positions,
            all_depts['OneTime_B'],
            left=all_depts['Operating_B'],
            color=self.colors['One-Time Appr'],
            label='One-Time Appr',
            height=0.7
        )
        
        ax.barh(
            y_positions,
            all_depts['Emergency_B'],
            left=all_depts['Operating_B'] + all_depts['OneTime_B'],
            color=self.colors['Emergency Appr'],
            label='Emergency Appr',
            height=0.7
        )
        
        ax.barh(
            y_positions,
            all_depts['CIP_B'],
            left=all_depts['Operating_B'] + all_depts['OneTime_B'] + all_depts['Emergency_B'],
            color=self.colors['CIP Appr'],
            label='CIP Appr',
            height=0.7
        )
        
        # Set y-ticks and labels to show department display names
        ax.set_yticks(y_positions)
        ax.set_yticklabels(all_depts['dept_display'].values, fontsize=9)
        
        # Add total amount labels to the right of each bar
        total_amounts = all_depts['Total_B']
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
        
        # Set y-ticks and labels
        ax.set_yticks(y_positions)
        ax.set_yticklabels(all_depts['dept_display'], fontsize=11)
        
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
