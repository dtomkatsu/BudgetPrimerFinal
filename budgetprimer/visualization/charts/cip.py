"""Capital Improvement Program (CIP) funding chart."""

from typing import Optional, Dict
import pandas as pd
import matplotlib.pyplot as plt
from .base import BudgetChart, CHART_COLORS, DEFAULT_TITLE_FONTSIZE, DEFAULT_LABEL_FONTSIZE


class CIPChart(BudgetChart):
    """Capital Improvement Program funding pie chart by category."""
    
    def __init__(self, **kwargs):
        """
        Initialize the CIP chart.
        
        Args:
            **kwargs: Additional parameters passed to BudgetChart
        """
        super().__init__(figsize=(10, 8), **kwargs)
        
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare and transform data for the CIP chart.
        
        Args:
            data: Raw budget data for the fiscal year
            
        Returns:
            Processed data ready for visualization
        """
        # Filter for CIP data only
        cip_data = data[data['section'] == 'Capital Improvement'].copy()
        
        if cip_data.empty:
            raise ValueError(f"No CIP data found for fiscal year {self.fiscal_year}")
        
        # Clean up category names
        cip_data['category'] = cip_data['category'].fillna('Uncategorized')
        cip_data['category'] = cip_data['category'].str.strip()
        
        # Group categories as per reference: Transportation, Formal Education, Economic Development, Health, and All Others
        main_categories = ['Transportation', 'Education', 'Economic Development', 'Health']
        
        # Create consolidated category totals
        consolidated_totals = {}
        for category in main_categories:
            if category == 'Education':
                # Map 'Education' to 'Formal Education' for display
                consolidated_totals['Formal Education'] = cip_data[cip_data['category'] == category]['amount'].sum()
            else:
                consolidated_totals[category] = cip_data[cip_data['category'] == category]['amount'].sum()
        
        # Sum all other categories into 'All Others'
        other_categories = cip_data[~cip_data['category'].isin(main_categories)]['amount'].sum()
        consolidated_totals['All Others'] = other_categories
        
        # Convert to pandas Series and sort by value (descending)
        category_totals = pd.Series(consolidated_totals).sort_values(ascending=False)
        
        # Remove categories with zero funding
        category_totals = category_totals[category_totals > 0]
        
        return pd.DataFrame({
            'category': category_totals.index,
            'amount': category_totals.values,
            'amount_millions': category_totals.values / 1e6
        })
        
    def create_chart(self, processed_data: pd.DataFrame) -> plt.Figure:
        """
        Create the CIP funding pie chart.
        
        Args:
            processed_data: Data prepared by prepare_data()
            
        Returns:
            Matplotlib Figure object
        """
        # Create figure
        fig, ax = plt.subplots(figsize=self.figsize)
        
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
            processed_data['amount'],
            labels=None,  # No labels on slices, we'll use legend
            colors=colors[:len(processed_data)],
            autopct=make_autopct(processed_data['amount']),
            startangle=90,
            textprops={'fontsize': 14, 'fontweight': 'bold', 'color': 'white'}
        )
        
        # Customize the value text on pie slices
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(14)
            autotext.set_fontweight('bold')
        
        # Create legend with category names only (matching reference style)
        legend_labels = list(processed_data['category'])
        ax.legend(
            wedges, 
            legend_labels, 
            title="",
            loc="center left", 
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=12, 
            title_fontsize=12
        )
        
        # Calculate total for title
        total_cip = processed_data['amount'].sum()
        
        # Set title matching the reference format
        if self.title is None:
            self.title = f'Figure 4. Distribution of Capital Improvement Project Funding, FY{self.fiscal_year[-2:]} ($ Millions)'
        
        ax.set_title(
            self.title, 
            fontsize=14, 
            fontweight='bold', 
            pad=20
        )
        
        # Ensure the pie chart is circular
        ax.axis('equal')
        
        # Adjust layout
        plt.tight_layout()
        
        return fig
