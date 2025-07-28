"""Base chart class and common utilities for budget visualization."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union, Dict, Any
import logging
import pandas as pd
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# Chart styling constants
DEFAULT_TITLE_FONTSIZE = 16
DEFAULT_LABEL_FONTSIZE = 12
DEFAULT_LEGEND_FONTSIZE = 11
DEFAULT_DPI = 300

# Color schemes
CHART_COLORS = {
    'operating': '#1f4e79',      # Dark blue
    'cip': '#5fb3d4',            # Light blue/teal
    'one_time': '#2d8659',       # Green
    'emergency': '#2c2c2c',      # Black/dark gray
    'federal': '#000022',        # Very dark blue (almost black)
    'general': '#4472C4',        # Blue
    'special': '#70AD47',        # Green
    'revolving': '#FFC000',      # Orange/yellow
    'trust': '#C5504B',          # Red
    'bond': '#9966CC',           # Purple
    'other': '#7F7F7F'           # Gray
}

class BudgetChart(ABC):
    """Base class for budget charts."""
    
    def __init__(
        self,
        fiscal_year: int,
        title: Optional[str] = None,
        figsize: tuple = (12, 8),
        **kwargs
    ):
        """
        Initialize the chart.
        
        Args:
            fiscal_year: Fiscal year for the chart
            title: Chart title (if None, will be auto-generated)
            figsize: Figure size as (width, height)
            **kwargs: Additional chart-specific parameters
        """
        self.fiscal_year = fiscal_year
        self.title = title
        self.figsize = figsize
        self.kwargs = kwargs
        
    @abstractmethod
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare and transform data for the chart.
        
        Args:
            data: Raw budget data
            
        Returns:
            Processed data ready for visualization
        """
        pass
        
    @abstractmethod
    def create_chart(self, processed_data: pd.DataFrame) -> plt.Figure:
        """
        Create the matplotlib figure and axes.
        
        Args:
            processed_data: Data prepared by prepare_data()
            
        Returns:
            Matplotlib Figure object
        """
        pass
        
    def create(self, data: pd.DataFrame, output_file: Optional[Union[str, Path]] = None) -> plt.Figure:
        """
        Main method to create the chart.
        
        Args:
            data: Raw budget data
            output_file: Optional path to save the chart
            
        Returns:
            Matplotlib Figure object
        """
        if data.empty:
            raise ValueError("Cannot create chart with empty data")
            
        # Filter data for the specified fiscal year
        df_year = data[data['fiscal_year'] == self.fiscal_year].copy()
        
        if df_year.empty:
            raise ValueError(f"No data found for fiscal year {self.fiscal_year}")
            
        # Prepare data
        processed_data = self.prepare_data(df_year)
        
        # Create chart
        fig = self.create_chart(processed_data)
        
        # Save if output file is provided
        if output_file:
            self.save_chart(fig, output_file)
            
        return fig
        
    def save_chart(self, fig: plt.Figure, output_file: Union[str, Path]) -> None:
        """
        Save the chart to file.
        
        Args:
            fig: Matplotlib Figure object
            output_file: Path to save the chart
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as PNG
        fig.savefig(
            output_path,
            dpi=DEFAULT_DPI,
            bbox_inches='tight',
            facecolor='white',
            edgecolor='none'
        )
        logger.info(f"Saved chart to {output_path}")
        
        # Also save as PDF for high quality
        pdf_path = output_path.with_suffix('.pdf')
        fig.savefig(
            pdf_path,
            bbox_inches='tight',
            facecolor='white',
            edgecolor='none'
        )
        logger.info(f"PDF version saved to: {pdf_path}")
        
    def format_currency(self, amount: float, use_billions: bool = True) -> str:
        """
        Format currency amounts for display.
        
        Args:
            amount: Amount in dollars
            use_billions: If True, format in billions; otherwise millions
            
        Returns:
            Formatted currency string
        """
        if use_billions:
            billions = amount / 1_000_000_000
            if billions >= 1.0:
                return f'${billions:.1f}B'
            else:
                millions = billions * 1000
                if millions >= 100:
                    return f'${millions:.0f}M'
                elif millions >= 10:
                    return f'${millions:.1f}M'
                else:
                    return f'${millions:.2f}M'
        else:
            millions = amount / 1_000_000
            return f'${millions:.1f}M'
            
    def setup_axes(self, ax: plt.Axes, remove_spines: bool = True) -> None:
        """
        Common axes setup for charts.
        
        Args:
            ax: Matplotlib Axes object
            remove_spines: Whether to remove chart spines
        """
        if remove_spines:
            for spine in ax.spines.values():
                spine.set_visible(False)
                
        ax.set_axisbelow(True)  # Ensure grid is behind bars
