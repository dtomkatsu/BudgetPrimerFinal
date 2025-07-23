"""
Budget data visualization functions.

This module contains functions for creating various visualizations
of budget data using matplotlib and seaborn.
"""
from typing import List, Dict, Any, Optional, Tuple, Union
import logging
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

from ..models import BudgetAllocation, BudgetSection, FundType

# Set up logging
logger = logging.getLogger(__name__)

# Color palettes
FUND_TYPE_COLORS = {
    'A': '#1f77b4',  # General Fund
    'B': '#ff7f0e',  # Special Fund
    'F': '#2ca02c',  # Federal Funds
    'D': '#d62728',  # Bond Funds
    'T': '#9467bd',  # Trust Funds
    'S': '#8c564b',  # Special Management Area Funds
    'W': '#e377c2',  # Special Outlay Funds
    'R': '#7f7f7f',  # Revenue Bond Funds
    'X': '#bcbd22',  # Other Funds
    'U': '#17becf'   # Unknown/Unspecified
}

# Styling
# Try seaborn-v0_8 style if available, otherwise use default
plt.style.use('seaborn-v0_8' if 'seaborn-v0_8' in plt.style.available else 'default')
sns.set_theme(style="whitegrid")

# Chart defaults
DEFAULT_FIGSIZE = (12, 8)
DEFAULT_FONTSIZE = 12
DEFAULT_TITLE_FONTSIZE = 14
DEFAULT_LABEL_FONTSIZE = 10
DEFAULT_LEGEND_FONTSIZE = 10
DEFAULT_DPI = 300


def create_pie_chart(
    data: pd.DataFrame,
    values: str,
    names: str,
    title: str = '',
    colors: Optional[Dict[str, str]] = None,
    figsize: Tuple[int, int] = DEFAULT_FIGSIZE,
    fontsize: int = DEFAULT_FONTSIZE,
    autopct: str = '%1.1f%%',
    startangle: float = 90,
    explode: Optional[List[float]] = None,
    shadow: bool = True,
    **kwargs
) -> plt.Figure:
    """
    Create a pie chart from the given data.
    
    Args:
        data: DataFrame containing the data
        values: Column name for the values
        names: Column name for the labels
        title: Chart title
        colors: Optional color mapping for categories
        figsize: Figure size (width, height)
        fontsize: Base font size
        autopct: Format string for percentage labels
        startangle: Starting angle for the pie chart
        explode: List of values to explode slices
        **kwargs: Additional keyword arguments for plt.pie()
        
    Returns:
        Matplotlib Figure object
    """
    if data.empty:
        raise ValueError("Cannot create pie chart with empty data")
    
    # Prepare data
    values_data = data[values]
    labels = data[names]
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=figsize)
    
    # Create pie chart
    wedges, texts, autotexts = ax.pie(
        values_data,
        labels=labels,
        autopct=autopct,
        startangle=startangle,
        explode=explode,
        shadow=shadow,
        colors=[colors.get(str(x), '#999999') for x in labels] if colors else None,
        **kwargs
    )
    
    # Style the chart
    ax.set_title(title, fontsize=fontsize + 2, pad=20)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    
    # Style text elements
    for text in texts + autotexts:
        text.set_fontsize(fontsize)
    
    # Add legend
    ax.legend(
        wedges,
        [f"{l}: ${v:,.0f}M ({(v/values_data.sum()*100):.1f}%)" 
         for l, v in zip(labels, values_data)],
        title=names.title(),
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=fontsize - 2
    )
    
    plt.tight_layout()
    return fig


def create_bar_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    hue: Optional[str] = None,
    title: str = '',
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    figsize: Tuple[int, int] = DEFAULT_FIGSIZE,
    fontsize: int = DEFAULT_FONTSIZE,
    rotation: int = 45,
    horizontal: bool = False,
    **kwargs
) -> plt.Figure:
    """
    Create a bar chart from the given data.
    
    Args:
        data: DataFrame containing the data
        x: Column name for the x-axis
        y: Column name for the y-axis
        hue: Optional column name for grouping
        title: Chart title
        xlabel: X-axis label
        ylabel: Y-axis label
        figsize: Figure size (width, height)
        fontsize: Base font size
        rotation: Rotation angle for x-axis labels
        horizontal: Whether to create a horizontal bar chart
        **kwargs: Additional keyword arguments for sns.barplot()
        
    Returns:
        Matplotlib Figure object
    """
    if data.empty:
        raise ValueError("Cannot create bar chart with empty data")
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=figsize)
    
    # Create bar chart
    if horizontal:
        sns.barplot(data=data, y=x, x=y, hue=hue, ax=ax, **kwargs)
    else:
        sns.barplot(data=data, x=x, y=y, hue=hue, ax=ax, **kwargs)
    
    # Style the chart
    ax.set_title(title, fontsize=fontsize + 2, pad=20)
    
    # Set axis labels
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=fontsize)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=fontsize)
    
    # Rotate x-axis labels
    if not horizontal:
        plt.xticks(rotation=rotation, ha='right')
    
    # Adjust layout
    plt.tight_layout()
    
    return fig


def create_time_series_plot(
    data: pd.DataFrame,
    x: str,
    y: str,
    hue: Optional[str] = None,
    title: str = '',
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    figsize: Tuple[int, int] = DEFAULT_FIGSIZE,
    fontsize: int = DEFAULT_FONTSIZE,
    rotation: int = 45,
    **kwargs
) -> plt.Figure:
    """
    Create a time series plot from the given data.
    
    Args:
        data: DataFrame containing the data
        x: Column name for the x-axis (time)
        y: Column name for the y-axis
        hue: Optional column name for grouping
        title: Chart title
        xlabel: X-axis label
        ylabel: Y-axis label
        figsize: Figure size (width, height)
        fontsize: Base font size
        rotation: Rotation angle for x-axis labels
        **kwargs: Additional keyword arguments for sns.lineplot()
        
    Returns:
        Matplotlib Figure object
    """
    if data.empty:
        raise ValueError("Cannot create time series plot with empty data")
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=figsize)
    
    # Create line plot
    sns.lineplot(data=data, x=x, y=y, hue=hue, ax=ax, **kwargs)
    
    # Style the chart
    ax.set_title(title, fontsize=fontsize + 2, pad=20)
    
    # Set axis labels
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=fontsize)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=fontsize)
    
    # Rotate x-axis labels
    plt.xticks(rotation=rotation, ha='right')
    
    # Adjust layout
    plt.tight_layout()
    
    return fig


def create_means_of_finance_chart(
    data: pd.DataFrame,
    fiscal_year: int,
    title: Optional[str] = None,
    output_file: Optional[Union[str, Path]] = None,
    **kwargs
) -> plt.Figure:
    """
    Create a pie chart showing the means of finance for a given fiscal year.
    
    Args:
        data: DataFrame containing budget data
        fiscal_year: Fiscal year to visualize
        title: Chart title (default: auto-generated)
        output_file: Optional path to save the chart
        **kwargs: Additional keyword arguments for create_pie_chart()
        
    Returns:
        Matplotlib Figure object
    """
    if data.empty:
        raise ValueError("Cannot create chart with empty data")
    
    # Filter data for the specified fiscal year
    df_year = data[data['fiscal_year'] == fiscal_year].copy()
    
    if df_year.empty:
        raise ValueError(f"No data found for fiscal year {fiscal_year}")
    
    # Aggregate by fund type
    fund_summary = df_year.groupby('fund_type')['amount'].sum().reset_index()
    
    # Add fund category and sort
    fund_summary['category'] = fund_summary['fund_type'].apply(
        lambda x: FundType(x).category if pd.notna(x) else 'Unknown'
    )
    
    # Convert to millions for display
    fund_summary['amount_millions'] = fund_summary['amount'] / 1_000_000
    
    # Sort by amount (descending)
    fund_summary = fund_summary.sort_values('amount', ascending=False)
    
    # Create chart title if not provided
    if title is None:
        title = f"Means of Finance - FY{fiscal_year}\n" \
                f"Total: ${fund_summary['amount_millions'].sum():,.0f}M"
    
    # Create the pie chart
    fig = create_pie_chart(
        data=fund_summary,
        values='amount_millions',
        names='category',
        title=title,
        colors=FUND_TYPE_COLORS,
        autopct='%1.1f%%',
        startangle=140,
        wedgeprops={'edgecolor': 'white', 'linewidth': 0.5},
        **kwargs
    )
    
    # Save the chart if output file is provided
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=DEFAULT_DPI, bbox_inches='tight')
        logger.info(f"Saved means of finance chart to {output_path}")
    
    return fig


def create_department_budget_chart(
    data: pd.DataFrame,
    fiscal_year: int,
    n_departments: int = 15,
    title: Optional[str] = None,
    output_file: Optional[Union[str, Path]] = None,
    **kwargs
) -> plt.Figure:
    """
    Create a horizontal bar chart showing the largest department budgets.
    
    Args:
        data: DataFrame containing budget data
        fiscal_year: Fiscal year to visualize
        n_departments: Number of top departments to show
        title: Chart title (default: auto-generated)
        output_file: Optional path to save the chart
        **kwargs: Additional keyword arguments for create_bar_chart()
        
    Returns:
        Matplotlib Figure object
    """
    if data.empty:
        raise ValueError("Cannot create chart with empty data")
    
    # Filter data for the specified fiscal year
    df_year = data[data['fiscal_year'] == fiscal_year].copy()
    
    if df_year.empty:
        raise ValueError(f"No data found for fiscal year {fiscal_year}")
    
    # Aggregate by department
    dept_summary = df_year.groupby(['department_code', 'department_name'])['amount'].sum().reset_index()
    
    # Sort and get top N departments
    dept_summary = dept_summary.sort_values('amount', ascending=False).head(n_departments)
    
    # Convert to millions for display
    dept_summary['amount_millions'] = dept_summary['amount'] / 1_000_000
    
    # Create a combined label with code and name
    dept_summary['label'] = dept_summary.apply(
        lambda x: f"{x['department_code']} - {x['department_name']}", axis=1
    )
    
    # Create chart title if not provided
    if title is None:
        title = f"Top {n_departments} Department Budgets - FY{fiscal_year}\n" \
                f"Total Shown: ${dept_summary['amount_millions'].sum():,.0f}M"
    
    # Create the bar chart
    fig = create_bar_chart(
        data=dept_summary,
        x='amount_millions',
        y='label',
        title=title,
        xlabel='Budget (Millions $)',
        ylabel='Department',
        horizontal=True,
        palette='viridis',
        **kwargs
    )
    
    # Add value labels
    ax = fig.axes[0]
    for i, v in enumerate(dept_summary['amount_millions']):
        ax.text(v + (dept_summary['amount_millions'].max() * 0.01),
                i, f"${v:,.0f}M",
                va='center',
                fontsize=DEFAULT_LABEL_FONTSIZE)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the chart if output file is provided
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=DEFAULT_DPI, bbox_inches='tight')
        logger.info(f"Saved department budget chart to {output_path}")
    
    return fig


def create_cip_funding_chart(
    data: pd.DataFrame,
    fiscal_year: int,
    n_projects: int = 15,
    title: Optional[str] = None,
    output_file: Optional[Union[str, Path]] = None,
    **kwargs
) -> plt.Figure:
    """
    Create a horizontal bar chart showing the largest CIP projects.
    
    Args:
        data: DataFrame containing budget data
        fiscal_year: Fiscal year to visualize
        n_projects: Number of top projects to show
        title: Chart title (default: auto-generated)
        output_file: Optional path to save the chart
        **kwargs: Additional keyword arguments for create_bar_chart()
        
    Returns:
        Matplotlib Figure object
    """
    if data.empty:
        raise ValueError("Cannot create chart with empty data")
    
    # Filter data for the specified fiscal year and CIP projects
    df_cip = data[
        (data['fiscal_year'] == fiscal_year) &
        (data['section'] == BudgetSection.CAPITAL_IMPROVEMENT.value)
    ].copy()
    
    if df_cip.empty:
        raise ValueError(f"No CIP data found for fiscal year {fiscal_year}")
    
    # Sort and get top N projects
    top_projects = df_cip.nlargest(n_projects, 'amount')
    
    # Convert to millions for display
    top_projects['amount_millions'] = top_projects['amount'] / 1_000_000
    
    # Create a truncated program name for display
    max_name_length = 50
    top_projects['short_name'] = top_projects['program_name'].apply(
        lambda x: (x[:max_name_length] + '...') if len(x) > max_name_length else x
    )
    
    # Create chart title if not provided
    if title is None:
        title = f"Top {n_projects} Capital Improvement Projects - FY{fiscal_year}\n" \
                f"Total Shown: ${top_projects['amount_millions'].sum():,.0f}M"
    
    # Create the bar chart
    fig = create_bar_chart(
        data=top_projects,
        x='amount_millions',
        y='short_name',
        title=title,
        xlabel='Funding (Millions $)',
        ylabel='Project',
        horizontal=True,
        palette='rocket',
        **kwargs
    )
    
    # Add value labels
    ax = fig.axes[0]
    for i, v in enumerate(top_projects['amount_millions']):
        ax.text(v + (top_projects['amount_millions'].max() * 0.01),
                i, f"${v:,.1f}M",
                va='center',
                fontsize=DEFAULT_LABEL_FONTSIZE)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the chart if output file is provided
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=DEFAULT_DPI, bbox_inches='tight')
        logger.info(f"Saved CIP funding chart to {output_path}")
    
    return fig


def save_figure(
    fig: plt.Figure,
    output_file: Union[str, Path],
    dpi: int = DEFAULT_DPI,
    **kwargs
) -> None:
    """
    Save a matplotlib figure to a file.
    
    Args:
        fig: Matplotlib Figure object to save
        output_file: Path to save the figure to
        dpi: Resolution in dots per inch
        **kwargs: Additional keyword arguments for fig.savefig()
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Default savefig options
    save_kwargs = {
        'dpi': dpi,
        'bbox_inches': 'tight',
        'facecolor': 'white',
        **kwargs
    }
    
    # Save the figure
    fig.savefig(output_path, **save_kwargs)
    logger.info(f"Saved figure to {output_path}")
