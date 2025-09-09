"""
Budget data visualization functions.

This module contains functions for creating various visualizations
"""

from pathlib import Path
from typing import Optional, Union, Dict, Any
import logging
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Import new modular chart classes
from .charts import DepartmentChart, MeansOfFinanceChart, CIPChart
from .charts.base import (
    CHART_COLORS, 
    DEFAULT_TITLE_FONTSIZE, 
    DEFAULT_LABEL_FONTSIZE, 
    DEFAULT_LEGEND_FONTSIZE, 
    DEFAULT_DPI
)

# Set up logging
logger = logging.getLogger(__name__)

# Legacy color schemes for backward compatibility
FUND_TYPE_COLORS = {
    'A': '#4472C4',  # General Fund - Blue
    'B': '#70AD47',  # Special Fund - Green  
    'N': '#000022',  # Federal Fund - Very dark blue (almost black)
    'R': '#FFC000',  # Revolving Fund - Orange/yellow
    'T': '#C5504B',  # Trust Fund - Red
    'W': '#9966CC',  # Bond Fund - Purple
    'Other': '#7F7F7F'  # Other - Gray
}

# Fund type labels for legend
FUND_TYPE_LABELS = {
    'A': 'General Funds',
    'B': 'Special Funds', 
    'N': 'Federal Funds',
    'R': 'Revolving Funds',
    'T': 'Trust Funds',
    'W': 'Bond Funds',
    'Other': 'Other Funds'
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
    
    # Filter data for the specified fiscal year and only include Operating budget
    fund_df = data[
        (data['fiscal_year'] == fiscal_year) & 
        (data['section'] == 'Operating')
    ].copy()
    
    if fund_df.empty:
        raise ValueError(f"No operating budget data found for fiscal year {fiscal_year}")
    
    # Create simplified fund categories for MOF chart to match reference
    def categorize_fund_type(fund_type):
        if fund_type == 'A':
            return 'General Funds'
        elif fund_type == 'B':
            return 'Special Funds'
        elif fund_type in ['N', 'P', 'F']:
            return 'Federal Funds'
        else:
            return 'All Others'
    
    fund_df['mof_category'] = fund_df['fund_type'].apply(categorize_fund_type)
    
    # Group by MOF category and sum amounts
    fund_summary = fund_df.groupby('mof_category', observed=True).agg({
        'amount': 'sum'
    }).reset_index()
    
    # Convert to billions for display
    fund_summary['amount_billions'] = fund_summary['amount'] / 1_000_000_000
    
    # Sort by amount in descending order to match reference layout
    fund_summary = fund_summary.sort_values('amount', ascending=False)
    
    # Create chart title if not provided
    if title is None:
        title = f"Figure 10. Means of Finance for Operations and Other Appropriations ($ Billions)"
    
    # Define colors to match the reference chart exactly
    mof_colors = {
        'General Funds': '#1f77b4',    # Blue (matplotlib default blue)
        'Special Funds': '#2ca02c',    # Green (matplotlib default green) 
        'Federal Funds': '#000022',    # Extremely dark blue (almost black)
        'All Others': '#17becf'        # Light blue/teal
    }
    
    # Create figure with specific size to match reference
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create pie chart with custom formatting
    colors = [mof_colors.get(cat, '#999999') for cat in fund_summary['mof_category']]
    
    # Custom autopct function to show dollar amounts in billions
    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = pct * total / 100.0
            return f'${val/1_000_000_000:.1f}'
        return my_autopct
    
    wedges, texts, autotexts = ax.pie(
        fund_summary['amount'],
        labels=None,  # We'll use a legend instead
        autopct=make_autopct(fund_summary['amount']),
        colors=colors,
        startangle=90,
        textprops={'fontsize': 16, 'fontweight': 'bold', 'color': 'white'}
    )
    
    # Create legend on the right side
    ax.legend(
        wedges, 
        fund_summary['mof_category'],
        title="",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=14
    )
    
    # Set title
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    # Ensure the pie chart is circular
    ax.axis('equal')
    
    # Adjust layout to accommodate legend
    plt.tight_layout()
    plt.subplots_adjust(left=0.1, right=0.75)
    
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
    
    # Remove any 'Total' rows
    dept_summary = dept_summary[~dept_summary['department_name'].str.upper().str.contains('TOTAL', na=False)]
    
    # Define special departments that will be handled separately
    special_dept_names = [
        'Judiciary',
        'Legislature',
        'OHA'
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
    
    # Apply department name mapping
    dept_summary['dept_display'] = dept_summary['department_name'].map(dept_mapping).fillna(dept_summary['department_name'])
    
    # Create special departments data
    special_data = [
        {'dept_display': 'Judiciary', 'Operating_B': 0.21457, 'CIP_B': 0.0129, 'OneTime_B': 0, 'Emergency_B': 0},
        {'dept_display': 'Legislature', 'Operating_B': 0.05163, 'CIP_B': 0, 'OneTime_B': 0, 'Emergency_B': 0},
        {'dept_display': 'OHA', 'Operating_B': 0.006, 'CIP_B': 0, 'OneTime_B': 0, 'Emergency_B': 0}
    ]
    
    # Add special departments to the data
    special_df = pd.DataFrame(special_data)
    special_df['Total_B'] = special_df['Operating_B'] + special_df['CIP_B'] + special_df['OneTime_B'] + special_df['Emergency_B']
    
    # Combine regular and special departments
    combined_df = pd.concat([dept_summary, special_df], ignore_index=True)
    
    # Sort and get top N departments by total budget
    top_depts = combined_df.nlargest(n_departments, 'Total_B')
    
    # Mark special departments
    top_depts['is_special'] = top_depts['dept_display'].isin(['Judiciary', 'Legislature', 'OHA', 'Human Resources'])
    
    # Sort with special departments first, then by total budget
    top_depts = top_depts.sort_values(['is_special', 'Total_B'], ascending=[False, False])
    
    # Create figure with larger size
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Define colors to match the official chart
    colors = {
        'Operating Budget': '#1f4e79',  # Dark blue
        'One-Time Appr': '#2d8659',     # Green  
        'Emergency Appr': '#2c2c2c',    # Black/dark gray
        'CIP Appr': '#5fb3d4'           # Light blue/teal
    }
    
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
        color=colors['Operating Budget'],
        label='Operating Budget',
        height=0.7
    )
    
    ax.barh(
        y_positions,
        top_depts['OneTime_B'],
        left=top_depts['Operating_B'],
        color=colors['One-Time Appr'],
        label='One-Time Appr',
        height=0.7
    )
    
    ax.barh(
        y_positions,
        top_depts['Emergency_B'],
        left=top_depts['Operating_B'] + top_depts['OneTime_B'],
        color=colors['Emergency Appr'],
        label='Emergency Appr',
        height=0.7
    )
    
    ax.barh(
        y_positions,
        top_depts['CIP_B'],
        left=top_depts['Operating_B'] + top_depts['OneTime_B'] + top_depts['Emergency_B'],
        color=colors['CIP Appr'],
        label='CIP Appr',
        height=0.7
    )
    
    # Add total amount labels to the right of each bar
    total_amounts = top_depts['Total_B']
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
    ax.set_yticklabels(top_depts['dept_display'], fontsize=11)
    
    # Customize the appearance
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # Set title
    if title is None:
        title = f'Figure 2. Distribution of Operating Budgets, One-Time Appropriations & CIP for FY{fiscal_year}'
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=24, loc='left')
    
    # Set x-axis with grid lines at each $1B
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
    
    # Save the chart if output file is provided
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as PNG
        fig.savefig(output_path, dpi=DEFAULT_DPI, bbox_inches='tight', facecolor='white', edgecolor='none')
        logger.info(f"Saved department budget chart to {output_path}")
        
        # Also save as PDF for high quality
        pdf_path = output_path.with_suffix('.pdf')
        fig.savefig(pdf_path, bbox_inches='tight', facecolor='white', edgecolor='none')
        logger.info(f"PDF version saved to: {pdf_path}")
    
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


# =============================================================================
# BACKWARD COMPATIBILITY WRAPPERS
# =============================================================================
# These functions maintain compatibility with existing code while using the
# new modular chart classes internally.

def create_department_budget_chart_new(
    data: pd.DataFrame,
    fiscal_year: int,
    n_departments: int = 15,
    title: Optional[str] = None,
    output_file: Optional[Union[str, Path]] = None,
    **kwargs
) -> plt.Figure:
    """
    Create a department budget chart using the new modular system.
    
    This is a wrapper around the new DepartmentChart class that maintains
    backward compatibility with the existing function signature.
    
    Args:
        data: DataFrame containing budget data
        fiscal_year: Fiscal year to visualize
        n_departments: Number of top departments to show
        title: Chart title (default: auto-generated)
        output_file: Optional path to save the chart
        **kwargs: Additional keyword arguments
        
    Returns:
        Matplotlib Figure object
    """
    chart = DepartmentChart(
        fiscal_year=fiscal_year,
        n_departments=n_departments,
        title=title,
        **kwargs
    )
    return chart.create(data, output_file)


def create_means_of_finance_chart_new(
    data: pd.DataFrame,
    fiscal_year: int,
    title: Optional[str] = None,
    output_file: Optional[Union[str, Path]] = None,
    **kwargs
) -> plt.Figure:
    """
    Create a means of finance chart using the new modular system.
    
    This is a wrapper around the new MeansOfFinanceChart class that maintains
    backward compatibility with the existing function signature.
    
    Args:
        data: DataFrame containing budget data
        fiscal_year: Fiscal year to visualize
        title: Chart title (default: auto-generated)
        output_file: Optional path to save the chart
        **kwargs: Additional keyword arguments
        
    Returns:
        Matplotlib Figure object
    """
    chart = MeansOfFinanceChart(
        fiscal_year=fiscal_year,
        title=title,
        **kwargs
    )
    return chart.create(data, output_file)


def create_cip_funding_chart_new(
    data: pd.DataFrame,
    fiscal_year: int,
    n_departments: int = 10,
    title: Optional[str] = None,
    output_file: Optional[Union[str, Path]] = None,
    **kwargs
) -> plt.Figure:
    """
    Create a CIP funding chart using the new modular system.
    
    This is a wrapper around the new CIPChart class that maintains
    backward compatibility with the existing function signature.
    
    Args:
        data: DataFrame containing budget data
        fiscal_year: Fiscal year to visualize
        n_departments: Number of top departments to show
        title: Chart title (default: auto-generated)
        output_file: Optional path to save the chart
        **kwargs: Additional keyword arguments
        
    Returns:
        Matplotlib Figure object
    """
    chart = CIPChart(
        fiscal_year=fiscal_year,
        n_departments=n_departments,
        title=title,
        **kwargs
    )
    return chart.create(data, output_file)
