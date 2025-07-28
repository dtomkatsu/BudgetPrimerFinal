"""Capital Improvement Program (CIP) funding chart."""

from typing import Optional, Dict
import pandas as pd
import matplotlib.pyplot as plt
from .base import BudgetChart, CHART_COLORS, DEFAULT_TITLE_FONTSIZE, DEFAULT_LABEL_FONTSIZE


class CIPChart(BudgetChart):
    """Capital Improvement Program funding chart."""
    
    def __init__(self, n_departments: int = 10, **kwargs):
        """
        Initialize the CIP chart.
        
        Args:
            n_departments: Number of top departments to show
            **kwargs: Additional parameters passed to BudgetChart
        """
        super().__init__(figsize=(12, 8), **kwargs)
        self.n_departments = n_departments
        
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare and transform data for the CIP chart.
        
        Args:
            data: Raw budget data for the fiscal year
            
        Returns:
            Processed data ready for visualization
        """
        # Filter for CIP data only
        cip_data = data[data['section'] == 'CAPITAL_IMPROVEMENT'].copy()
        
        if cip_data.empty:
            raise ValueError(f"No CIP data found for fiscal year {self.fiscal_year}")
        
        # Group by department and sum amounts
        dept_summary = cip_data.groupby(['department_code', 'department_name'])['amount'].sum().reset_index()
        
        # Sort by amount and get top N departments
        top_depts = dept_summary.nlargest(self.n_departments, 'amount')
        
        # Convert to millions for display
        top_depts['amount_millions'] = top_depts['amount'] / 1_000_000
        
        # Sort by amount in descending order for chart display
        top_depts = top_depts.sort_values('amount', ascending=True)  # Reversed for horizontal bar
        
        return top_depts
        
    def create_chart(self, processed_data: pd.DataFrame) -> plt.Figure:
        """
        Create the CIP funding chart.
        
        Args:
            processed_data: Data prepared by prepare_data()
            
        Returns:
            Matplotlib Figure object
        """
        top_depts = processed_data
        
        # Create figure
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Create horizontal bar chart
        bars = ax.barh(
            range(len(top_depts)),
            top_depts['amount_millions'],
            color=CHART_COLORS['cip'],
            height=0.7
        )
        
        # Add department labels on the left
        y_labels = [f"{row['department_code']} - {row['department_name']}" 
                   for _, row in top_depts.iterrows()]
        ax.set_yticks(range(len(top_depts)))
        ax.set_yticklabels(y_labels, fontsize=DEFAULT_LABEL_FONTSIZE)
        
        # Add value labels on the right of each bar
        for i, amount in enumerate(top_depts['amount_millions']):
            label = self.format_currency(amount * 1_000_000, use_billions=False)
            ax.text(amount + max(top_depts['amount_millions']) * 0.01, i, label,
                   va='center', ha='left', 
                   fontsize=DEFAULT_LABEL_FONTSIZE,
                   fontweight='bold')
        
        # Set x-axis label
        ax.set_xlabel('CIP Funding (Millions $)', fontsize=DEFAULT_LABEL_FONTSIZE + 1)
        
        # Add grid lines
        ax.xaxis.grid(True, linestyle='--', alpha=0.7, color='#dddddd')
        
        # Customize appearance
        self.setup_axes(ax, remove_spines=True)
        
        # Set title
        if self.title is None:
            total_millions = top_depts['amount_millions'].sum()
            self.title = f"Figure 3. Top {self.n_departments} Departments - CIP Funding for FY{self.fiscal_year}\nTotal: ${total_millions:,.0f}M"
        
        ax.set_title(self.title, fontsize=DEFAULT_TITLE_FONTSIZE + 2, pad=20, loc='left')
        
        # Adjust layout
        plt.tight_layout(rect=[0, 0, 1, 1])
        
        return fig
