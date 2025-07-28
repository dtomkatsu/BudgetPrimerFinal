"""Means of Finance chart for budget visualization."""

from typing import Optional, Dict
import pandas as pd
import matplotlib.pyplot as plt
from .base import BudgetChart, CHART_COLORS


class MeansOfFinanceChart(BudgetChart):
    """Means of Finance (MOF) chart showing funding sources."""
    
    def __init__(self, **kwargs):
        """
        Initialize the MOF chart.
        
        Args:
            **kwargs: Additional parameters passed to BudgetChart
        """
        super().__init__(figsize=(10, 8), **kwargs)
        
        # Fund type color mapping
        self.fund_colors = {
            'A': CHART_COLORS['general'],     # General Fund - Blue
            'B': CHART_COLORS['special'],     # Special Fund - Green  
            'N': CHART_COLORS['federal'],     # Federal Fund - Very dark blue
            'R': CHART_COLORS['revolving'],   # Revolving Fund - Orange/yellow
            'T': CHART_COLORS['trust'],       # Trust Fund - Red
            'W': CHART_COLORS['bond'],        # Bond Fund - Purple
            'Other': CHART_COLORS['other']    # Other - Gray
        }
        
        # Fund type labels for legend
        self.fund_labels = {
            'A': 'General Funds',
            'B': 'Special Funds', 
            'N': 'Federal Funds',
            'R': 'Revolving Funds',
            'T': 'Trust Funds',
            'W': 'Bond Funds',
            'Other': 'Other Funds'
        }
        
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare and transform data for the MOF chart.
        
        Args:
            data: Raw budget data for the fiscal year
            
        Returns:
            Processed data ready for visualization
        """
        # Filter for operating budget only (exclude CIP)
        operating_data = data[data['section'] == 'OPERATING'].copy()
        
        if operating_data.empty:
            raise ValueError(f"No operating budget data found for fiscal year {self.fiscal_year}")
        
        # Group by fund type and sum amounts
        fund_summary = operating_data.groupby('fund_type')['amount'].sum().reset_index()
        
        # Map fund types to categories
        fund_summary['category'] = fund_summary['fund_type'].map(self.fund_labels)
        fund_summary['category'] = fund_summary['category'].fillna('Other Funds')
        
        # Group by category in case multiple fund types map to same category
        category_summary = fund_summary.groupby('category')['amount'].sum().reset_index()
        
        # Sort by amount (descending)
        category_summary = category_summary.sort_values('amount', ascending=False)
        
        # Convert to billions
        category_summary['amount_billions'] = category_summary['amount'] / 1_000_000_000
        
        # Add colors
        category_summary['color'] = category_summary['category'].map({
            label: color for fund_type, color in self.fund_colors.items() 
            for label in [self.fund_labels.get(fund_type, 'Other Funds')]
        })
        
        return category_summary
        
    def create_chart(self, processed_data: pd.DataFrame) -> plt.Figure:
        """
        Create the MOF chart.
        
        Args:
            processed_data: Data prepared by prepare_data()
            
        Returns:
            Matplotlib Figure object
        """
        fund_data = processed_data
        
        # Create figure
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            fund_data['amount_billions'],
            labels=fund_data['category'],
            colors=fund_data['color'],
            autopct=lambda pct: f'${pct * fund_data["amount_billions"].sum() / 100:.1f}B\n({pct:.1f}%)',
            startangle=90,
            textprops={'fontsize': 10}
        )
        
        # Enhance the percentage labels
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(9)
        
        # Set title
        if self.title is None:
            total_billions = fund_data['amount_billions'].sum()
            self.title = f'Hawaii State Budget - Means of Finance (FY{self.fiscal_year})\nOperating Budget Total: ${total_billions:.1f}B'
        
        ax.set_title(self.title, fontsize=14, fontweight='bold', pad=20)
        
        # Equal aspect ratio ensures that pie is drawn as a circle
        ax.axis('equal')
        
        # Add legend
        ax.legend(
            wedges,
            fund_data['category'],
            title="Fund Types",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=10
        )
        
        # Adjust layout to make room for legend
        plt.tight_layout()
        
        return fig
