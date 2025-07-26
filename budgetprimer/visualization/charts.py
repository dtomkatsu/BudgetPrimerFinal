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
# Updated to match the reference chart styles
FUND_TYPE_COLORS = {
    'A': '#1f4e79',  # Dark blue - General Fund
    'B': '#2d8659',  # Green - Special Funds
    'C': '#8c510a',  # Brown - General Obligation Bond Fund
    'D': '#d8b365',  # Tan - GO Bond Fund with Debt Service from Special Funds
    'E': '#5ab4ac',  # Teal - Revenue Bond Funds
    'F': '#d53e4f',  # Red - Federal Funds (F)
    'N': '#d53e4f',  # Red - Federal Funds (N) - Same as F
    'P': '#d53e4f',  # Red - Federal Funds (P) - Same as F
    'T': '#c51b7d',  # Magenta - Trust Funds
    'W': '#e377c2',  # Pink - Special Outlay Funds
    'R': '#7f7f7f',  # Gray - Revenue Bond Funds
    'X': '#bcbd22',  # Olive - Other Funds
    'U': '#17becf'   # Cyan - Unknown/Unspecified
}

# Chart element colors
CHART_COLORS = {
    'operating': '#1f4e79',      # Dark blue
    'onetime': '#2d8659',        # Green
    'emergency': '#2c2c2c',      # Black/dark gray
    'cip': '#5fb3d4'            # Light blue/teal
}

# Styling
plt.style.use('seaborn-v0_8' if 'seaborn-v0_8' in plt.style.available else 'default')
sns.set_theme(style="whitegrid", font_scale=1.1)

# Chart defaults
DEFAULT_FIGSIZE = (14, 10)
DEFAULT_FONTSIZE = 12
DEFAULT_TITLE_FONTSIZE = 16
DEFAULT_LABEL_FONTSIZE = 11
DEFAULT_LEGEND_FONTSIZE = 11
DEFAULT_DPI = 300

# Set default font family
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']
plt.rcParams['axes.titlesize'] = DEFAULT_TITLE_FONTSIZE
plt.rcParams['axes.labelsize'] = DEFAULT_LABEL_FONTSIZE
plt.rcParams['xtick.labelsize'] = DEFAULT_LABEL_FONTSIZE - 1
plt.rcParams['ytick.labelsize'] = DEFAULT_LABEL_FONTSIZE - 1
plt.rcParams['legend.fontsize'] = DEFAULT_LEGEND_FONTSIZE
plt.rcParams['figure.titlesize'] = DEFAULT_TITLE_FONTSIZE + 2

# Custom styles
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#e0e0e0'
plt.rcParams['grid.alpha'] = 0.7


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
    fund_df = data[data['fiscal_year'] == fiscal_year].copy()
    
    if fund_df.empty:
        raise ValueError(f"No data found for fiscal year {fiscal_year}")
    
    # Create simplified fund categories for MOF chart
    def categorize_fund_type(fund_type):
        if fund_type == 'A':
            return 'General Funds'
        elif fund_type == 'B':
            return 'Special Funds'
        elif fund_type in ['N', 'P', 'F']:
            return 'Federal Funds'
        else:
            return 'Other Funds'
    
    fund_df['mof_category'] = fund_df['fund_type'].apply(categorize_fund_type)
    
    # Group by MOF category and sum amounts
    fund_summary = fund_df.groupby('mof_category', observed=True).agg({
        'amount': 'sum'
    }).reset_index()
    
    # Rename columns for consistency with existing code
    fund_summary = fund_summary.rename(columns={'mof_category': 'category'})
    
    # Convert to billions for display
    fund_summary['amount_billions'] = fund_summary['amount'] / 1_000_000_000
    
    # Sort by amount in descending order
    fund_summary = fund_summary.sort_values('amount', ascending=False)
    
    # Create chart title if not provided
    if title is None:
        total = fund_summary['amount'].sum() / 1_000_000_000  # Convert to billions
        title = f"Figure 1. Means of Finance for FY{fiscal_year}\nTotal: ${total:,.1f}B"
    
    # Define colors for MOF categories
    mof_colors = {
        'General Funds': '#1f4e79',   # Dark blue
        'Special Funds': '#2d8659',   # Green
        'Federal Funds': '#d53e4f',   # Red
        'Other Funds': '#bcbd22'      # Olive
    }
    
    # Filter out invalid kwargs for pie chart
    valid_pie_kwargs = {k: v for k, v in kwargs.items() 
                       if k in ['figsize', 'fontsize', 'autopct', 'startangle', 'explode', 'shadow', 'ax']}
    
    # Create the pie chart
    fig = create_pie_chart(
        data=fund_summary,
        values='amount',
        names='category',
        title=title,
        colors=mof_colors,  # Pass the dictionary directly
        **valid_pie_kwargs
    )
    
    # The create_pie_chart function handles all the styling and layout
    
    # Adjust layout to prevent legend cutoff
    plt.tight_layout(rect=[0, 0, 0.8, 1])
    
    # Save the chart if output file is provided
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as PNG
        fig.savefig(
            output_path, 
            dpi=DEFAULT_DPI, 
            bbox_inches='tight',
            facecolor='white',
            edgecolor='none',
            transparent=False
        )
        logger.info(f"Saved chart to {output_path}")
        
        # Also save as PDF for high quality
        pdf_path = output_path.with_suffix('.pdf')
        fig.savefig(
            pdf_path,
            bbox_inches='tight',
            facecolor='white',
            edgecolor='none',
            transparent=False
        )
        logger.info(f"Saved PDF version to {pdf_path}")
    
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
        **kwargs: Additional keyword arguments for styling
        
    Returns:
        Matplotlib Figure object
    """
    if data.empty:
        raise ValueError("Cannot create chart with empty data")
    
    # Filter data for the specified fiscal year
    df_year = data[data['fiscal_year'] == fiscal_year].copy()
    
    if df_year.empty:
        raise ValueError(f"No data found for fiscal year {fiscal_year}")
    
    # Aggregate by department and section (operating, capital, etc.)
    dept_summary = df_year.groupby(['department_code', 'department_name', 'section'])['amount'].sum().unstack(fill_value=0).reset_index()
    
    # Add missing columns if they don't exist
    for col in ['OPERATING', 'CAPITAL_IMPROVEMENT']:
        if col not in dept_summary.columns:
            dept_summary[col] = 0
    
    # Calculate total budget for each department
    dept_summary['total'] = dept_summary[['OPERATING', 'CAPITAL_IMPROVEMENT']].sum(axis=1)
    
    # Sort and get top N departments
    top_depts = dept_summary.nlargest(n_departments, 'total')
    
    # Convert to billions for display
    top_depts['total_billions'] = top_depts['total'] / 1_000_000_000
    top_depts['operating_billions'] = top_depts['OPERATING'] / 1_000_000_000
    top_depts['capital_billions'] = top_depts['CAPITAL_IMPROVEMENT'] / 1_000_000_000
    
    # Sort by total in descending order
    top_depts = top_depts.sort_values('total', ascending=True)  # Reversed for horizontal bar
    
    # Create chart title if not provided
    if title is None:
        total = top_depts['total'].sum() / 1_000_000_000  # Convert to billions
        title = f"Figure 2. Department Budgets for FY{fiscal_year}\nTotal: ${total:,.1f}B"
    
    # Create figure with larger size
    fig, ax = plt.subplots(figsize=kwargs.pop('figsize', (14, 10)))
    
    # Define colors for stacked bars
    colors = [CHART_COLORS['operating'], CHART_COLORS['cip']]
    
    # Create stacked horizontal bars
    bars1 = ax.barh(
        range(len(top_depts)),
        top_depts['operating_billions'],
        color=colors[0],
        label='Operating Budget',
        height=0.7
    )
    
    bars2 = ax.barh(
        range(len(top_depts)),
        top_depts['capital_billions'],
        left=top_depts['operating_billions'],
        color=colors[1],
        label='Capital Budget',
        height=0.7
    )
    
    # Add department labels on the left
    y_labels = [f"{row['department_code']} - {row['department_name']}" for _, row in top_depts.iterrows()]
    ax.set_yticks(range(len(top_depts)))
    ax.set_yticklabels(y_labels, fontsize=DEFAULT_LABEL_FONTSIZE)
    
    # Add value labels on the right of each bar
    for i, (operating, capital) in enumerate(zip(top_depts['operating_billions'], 
                                               top_depts['capital_billions'])):
        total = operating + capital
        # Format the label based on the value size
        if total >= 1.0:
            label = f'${total:,.1f}B'
        else:
            # Show in millions if less than $1B
            label = f'${total*1000:,.0f}M'
            
        ax.text(total + 0.05, i, label, 
               va='center', ha='left', 
               fontsize=DEFAULT_LABEL_FONTSIZE,
               fontweight='bold')
    
    # Set x-axis label
    ax.set_xlabel('Budget (Billions $)', fontsize=DEFAULT_LABEL_FONTSIZE + 1)
    
    # Add grid lines
    ax.xaxis.grid(True, linestyle='--', alpha=0.7, color='#dddddd')
    ax.set_axisbelow(True)
    
    # Remove spines
    for spine in ['top', 'right', 'left']:
        ax.spines[spine].set_visible(False)
    
    # Add title
    ax.set_title(title, fontsize=DEFAULT_TITLE_FONTSIZE + 2, pad=20, loc='left')
    
    # Add legend at the bottom
    ax.legend(
        loc='upper center',
        bbox_to_anchor=(0.5, -0.1),
        ncol=2,
        frameon=False,
        fontsize=DEFAULT_LEGEND_FONTSIZE
    )
    
    # Adjust layout to make room for legend
    plt.tight_layout(rect=[0, 0.05, 1, 1])
    
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
        **kwargs: Additional keyword arguments for styling
        
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
    top_projects = df_cip.nlargest(n_projects, 'amount').copy()
    
    # Convert to millions for display
    top_projects['amount_millions'] = top_projects['amount'] / 1_000_000
    
    # Create a truncated program name for display
    max_name_length = 60
    top_projects['short_name'] = top_projects['program_name'].apply(
        lambda x: (x[:max_name_length] + '...') if len(x) > max_name_length else x
    )
    
    # Add department code to the label if available
    if 'department_code' in top_projects.columns:
        top_projects['label'] = top_projects.apply(
            lambda x: f"{x['department_code']} - {x['short_name']}", 
            axis=1
        )
    else:
        top_projects['label'] = top_projects['short_name']
    
    # Sort by amount (ascending for horizontal bar)
    top_projects = top_projects.sort_values('amount', ascending=True)
    
    # Create chart title if not provided
    if title is None:
        total = top_projects['amount_millions'].sum()
        title = f"Figure 3. Top {n_projects} Capital Improvement Projects - FY{fiscal_year}\n" \
                f"Total Shown: ${total:,.0f}M"
    
    # Create figure with larger size
    fig, ax = plt.subplots(figsize=kwargs.pop('figsize', (14, 10)))
    
    # Create horizontal bars
    bars = ax.barh(
        range(len(top_projects)),
        top_projects['amount_millions'],
        color=CHART_COLORS['cip'],
        height=0.7
    )
    
    # Add project labels on the left
    ax.set_yticks(range(len(top_projects)))
    ax.set_yticklabels(top_projects['label'], fontsize=DEFAULT_LABEL_FONTSIZE)
    
    # Add value labels on the right of each bar
    for i, amount in enumerate(top_projects['amount_millions']):
        # Format the label based on the value size
        if amount >= 100:
            label = f'${amount:,.0f}M'
        elif amount >= 10:
            label = f'${amount:,.1f}M'
        else:
            label = f'${amount:,.2f}M'
            
        ax.text(amount + (top_projects['amount_millions'].max() * 0.01), 
                i, label, 
                va='center', ha='left',
                fontsize=DEFAULT_LABEL_FONTSIZE,
                fontweight='bold')
    
    # Set x-axis label
    ax.set_xlabel('Funding (Millions $)', fontsize=DEFAULT_LABEL_FONTSIZE + 1)
    
    # Add grid lines
    ax.xaxis.grid(True, linestyle='--', alpha=0.7, color='#dddddd')
    ax.set_axisbelow(True)
    
    # Remove spines
    for spine in ['top', 'right', 'left']:
        ax.spines[spine].set_visible(False)
    
    # Add title
    ax.set_title(title, fontsize=DEFAULT_TITLE_FONTSIZE + 2, pad=20, loc='left')
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0, 1, 1])
    
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
