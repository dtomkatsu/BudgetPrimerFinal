"""
Budget data visualization module.

This module provides functions for creating various visualizations
of budget data, including pie charts, bar charts, and other plots.

The module now supports both the legacy chart functions and new modular chart classes.
"""

# Import new modular chart classes
from .charts import DepartmentChart, MeansOfFinanceChart, CIPChart

# Import legacy chart functions (avoiding circular imports)
try:
    from .charts import (
        create_pie_chart,
        create_bar_chart,
        create_time_series_plot,
        create_means_of_finance_chart,
        create_department_budget_chart,
        create_cip_funding_chart
    )
except ImportError:
    # If legacy functions aren't available, define placeholder warnings
    def _legacy_function_warning(func_name):
        def wrapper(*args, **kwargs):
            raise ImportError(f"Legacy function {func_name} is not available. Use the new modular chart classes instead.")
        return wrapper
    
    create_pie_chart = _legacy_function_warning('create_pie_chart')
    create_bar_chart = _legacy_function_warning('create_bar_chart')
    create_time_series_plot = _legacy_function_warning('create_time_series_plot')
    create_means_of_finance_chart = _legacy_function_warning('create_means_of_finance_chart')
    create_department_budget_chart = _legacy_function_warning('create_department_budget_chart')
    create_cip_funding_chart = _legacy_function_warning('create_cip_funding_chart')

__all__ = [
    # New modular chart classes
    'DepartmentChart',
    'MeansOfFinanceChart', 
    'CIPChart',
    # Legacy functions (for backward compatibility)
    'create_pie_chart',
    'create_bar_chart',
    'create_time_series_plot',
    'create_means_of_finance_chart',
    'create_department_budget_chart',
    'create_cip_funding_chart'
]
