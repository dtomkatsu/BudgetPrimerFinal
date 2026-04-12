"""FY1 vs FY2 comparison bar chart."""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from .base import BudgetChart, CHART_COLORS, DEFAULT_DPI


class FYComparisonChart(BudgetChart):
    """Side-by-side bar chart comparing two fiscal years by department."""

    def __init__(self, fy1: int = 2026, fy2: int = 2027, **kwargs):
        super().__init__(fiscal_year=fy1, figsize=(14, 10), **kwargs)
        self.fy1 = fy1
        self.fy2 = fy2

    def create(self, data, output_file=None):
        """Override create() to skip the FY filter — we need both FYs."""
        if data.empty:
            raise ValueError("Cannot create chart with empty data")
        processed_data = self.prepare_data(data)
        fig = self.create_chart(processed_data)
        if output_file:
            self.save_chart(fig, output_file)
        return fig

    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Aggregate by department for both fiscal years."""
        dept_fy = data.groupby(['department_code', 'department_name', 'fiscal_year'])['amount'].sum().reset_index()
        pivot = dept_fy.pivot_table(index=['department_code', 'department_name'],
                                     columns='fiscal_year', values='amount', fill_value=0).reset_index()
        pivot.columns.name = None
        if self.fy1 not in pivot.columns:
            pivot[self.fy1] = 0
        if self.fy2 not in pivot.columns:
            pivot[self.fy2] = 0
        pivot['delta'] = pivot[self.fy2] - pivot[self.fy1]
        pivot['pct_change'] = (pivot['delta'] / pivot[self.fy1].replace(0, np.nan) * 100).round(1)
        pivot = pivot.sort_values(self.fy1, ascending=True)
        return pivot

    def create_chart(self, processed_data: pd.DataFrame) -> plt.Figure:
        fig, ax = plt.subplots(figsize=self.figsize)
        y = np.arange(len(processed_data))
        bar_h = 0.35

        fy1_b = processed_data[self.fy1] / 1e9
        fy2_b = processed_data[self.fy2] / 1e9

        ax.barh(y - bar_h / 2, fy1_b, bar_h, label=f'FY{self.fy1}', color='#4472C4')
        ax.barh(y + bar_h / 2, fy2_b, bar_h, label=f'FY{self.fy2}', color='#ED7D31')

        ax.set_yticks(y)
        ax.set_yticklabels(processed_data['department_name'], fontsize=8)
        ax.set_xlabel('Budget ($ Billions)')
        ax.set_title(self.title or f'Department Budgets: FY{self.fy1} vs FY{self.fy2}',
                      fontsize=14, fontweight='bold')
        ax.legend(loc='lower right')
        self.setup_axes(ax)
        ax.xaxis.grid(True, alpha=0.3)
        plt.tight_layout()
        return fig


class FundTypeStackedChart(BudgetChart):
    """Stacked horizontal bar chart showing fund-type composition per department."""

    FUND_COLORS = {
        'A': '#4472C4',
        'B': '#70AD47',
        'N': '#264478',
        'C': '#9966CC',
        'E': '#FFC000',
        'T': '#C5504B',
        'W': '#E97132',
    }

    def __init__(self, **kwargs):
        super().__init__(figsize=(14, 10), **kwargs)

    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        fy_data = data[data['fiscal_year'] == self.fiscal_year].copy()
        pivot = fy_data.pivot_table(index='department_name', columns='fund_type',
                                     values='amount', aggfunc='sum', fill_value=0)
        pivot['total'] = pivot.sum(axis=1)
        pivot = pivot.sort_values('total', ascending=True)
        return pivot

    def create_chart(self, processed_data: pd.DataFrame) -> plt.Figure:
        fig, ax = plt.subplots(figsize=self.figsize)
        fund_cols = [c for c in processed_data.columns if c != 'total']
        # Sort fund types by total descending so legend reads biggest first
        fund_order = processed_data[fund_cols].sum().sort_values(ascending=False).index.tolist()

        from budgetprimer.models import FundType  # absolute import to avoid path issues
        left = np.zeros(len(processed_data))
        for ft in fund_order:
            vals = processed_data[ft].values / 1e9
            label = FundType.from_string(ft).category if len(ft) == 1 else ft
            color = self.FUND_COLORS.get(ft, '#7F7F7F')
            ax.barh(range(len(processed_data)), vals, left=left, label=label,
                    color=color, height=0.7)
            left += vals

        ax.set_yticks(range(len(processed_data)))
        ax.set_yticklabels(processed_data.index, fontsize=8)
        ax.set_xlabel('Budget ($ Billions)')
        ax.set_title(self.title or f'Fund-Type Composition by Department (FY{self.fiscal_year})',
                      fontsize=14, fontweight='bold')
        ax.legend(loc='lower right', fontsize=8, ncol=2)
        self.setup_axes(ax)
        ax.xaxis.grid(True, alpha=0.3)
        plt.tight_layout()
        return fig
