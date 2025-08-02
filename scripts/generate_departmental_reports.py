#!/usr/bin/env python3
"""
Generate departmental budget reports with HTML tables and charts for Squarespace.
Creates individual department reports similar to the AGR example provided.
"""

import pandas as pd
# Disable pandas' IPython display integration
pd.set_option('display.notebook_repr_html', False)
pd.set_option('display.max_columns', None)

import matplotlib
# Set the backend to 'Agg' to prevent display issues
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path
import base64
from io import BytesIO
import argparse
import logging
import traceback
import sys

# Ensure matplotlib doesn't try to use display
os.environ['MPLBACKEND'] = 'Agg'
plt.ioff()  # Turn off interactive mode

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DepartmentalBudgetAnalyzer:
    """Generate departmental budget reports with HTML tables and charts."""
    
    def __init__(self, data_file: str, output_dir: str = "data/output/departmental_reports"):
        """
        Initialize the analyzer.
        
        Args:
            data_file: Path to the budget allocations CSV file
            output_dir: Directory to save HTML reports
        """
        self.data_file = data_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load data
        self.df = pd.read_csv(data_file)
        logger.info(f"Loaded {len(self.df)} budget allocations")
        
        # Fund type mappings to match the reference
        self.fund_mappings = {
            'A': 'General Funds',
            'B': 'Special Funds', 
            'N': 'Federal Funds',
            'P': 'Federal Funds',  # Other Federal Funds -> Federal Funds
            'W': 'Other Funds',    # Revolving Funds -> Other Funds
            'T': 'Other Funds',    # Trust Funds -> Other Funds
            'U': 'Other Funds',    # Interdepartmental Transfers -> Other Funds
            'R': 'Other Funds',    # Reimbursements -> Other Funds
            'S': 'Other Funds'     # Other Special Funds -> Other Funds
        }
        
        # Colors for charts (matching official style)
        self.colors = {
            'General Funds': '#1f77b4',      # Blue
            'Special Funds': '#2ca02c',      # Green  
            'Federal Funds': '#2c3e50',      # Dark blue/gray
            'Other Funds': '#17a2b8'         # Cyan
        }
    
    def get_department_summary(self, dept_code: str) -> dict:
        """
        Get comprehensive budget summary for a department.
        
        Args:
            dept_code: Department code (e.g., 'AGR')
            
        Returns:
            Dictionary with department budget breakdown
        """
        dept_data = self.df[self.df['department_code'] == dept_code].copy()
        
        if dept_data.empty:
            logger.warning(f"No data found for department {dept_code}")
            return None
        
        dept_name = dept_data['department_name'].iloc[0]
        
        # Map fund types
        dept_data['fund_category_mapped'] = dept_data['fund_type'].map(self.fund_mappings)
        
        # Calculate operating budget by fund type
        operating_data = dept_data[dept_data['section'] == 'Operating']
        operating_by_fund = operating_data.groupby('fund_category_mapped')['amount'].sum()
        
        # Calculate CIP projects (Capital Improvement section)
        cip_data = dept_data[dept_data['section'] == 'Capital Improvement']
        cip_total = cip_data['amount'].sum()
        
        # Calculate other appropriations (non-operating, non-CIP)
        other_data = dept_data[(dept_data['section'] != 'Operating') & (dept_data['section'] != 'Capital Improvement')]
        other_total = other_data['amount'].sum()
        
        # Total operating budget
        total_operating = operating_by_fund.sum()
        
        # Overall total
        total_budget = total_operating + other_total
        
        summary = {
            'department_code': dept_code,
            'department_name': dept_name,
            'total_budget': total_budget,
            'operating_budget': {
                'General Funds': operating_by_fund.get('General Funds', 0),
                'Special Funds': operating_by_fund.get('Special Funds', 0),
                'Federal Funds': operating_by_fund.get('Federal Funds', 0),
                'Other Funds': operating_by_fund.get('Other Funds', 0),
                'total': total_operating
            },
            'other_appropriations': other_total,
            'cip_projects': cip_total,
            'raw_data': dept_data
        }
        
        return summary
    
    def create_department_chart(self, summary: dict) -> str:
        """
        Create a horizontal stacked bar chart for department budget.
        
        Args:
            summary: Department summary dictionary
            
        Returns:
            Base64 encoded image string
        """
        try:
            # Create figure with explicit backend
            plt.switch_backend('Agg')
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Prepare data for stacked bar chart
            fund_types = ['General Funds', 'Special Funds', 'Federal Funds', 'Other Funds']
            amounts = [summary['operating_budget'][ft] / 1_000_000 for ft in fund_types]  # Convert to millions
            colors = [self.colors[ft] for ft in fund_types]
            
            # Check if we have any data to plot
            total_amount = sum(amounts)
            if total_amount == 0:
                # Create a simple placeholder chart
                ax.text(0.5, 0.5, 'No Operating Budget Data', 
                       ha='center', va='center', transform=ax.transAxes, fontsize=14)
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
            else:
                # Create horizontal stacked bar
                left = 0
                bars = []
                for i, (amount, color, label) in enumerate(zip(amounts, colors, fund_types)):
                    if amount > 0:  # Only show non-zero amounts
                        bar = ax.barh(0, amount, left=left, color=color, label=label, height=0.6)
                        bars.append(bar)
                        left += amount
                
                # Formatting
                ax.set_xlim(0, max(total_amount * 1.1, 1))  # Ensure minimum xlim
                ax.set_ylim(-0.5, 0.5)
                ax.set_xlabel('Amount (Millions of Dollars)', fontsize=12)
                
                # Add legend only if we have bars
                if bars:
                    ax.legend(loc='upper right', bbox_to_anchor=(1, 1))
                
                # Add value labels on bars
                left = 0
                for amount, label in zip(amounts, fund_types):
                    if amount > 0:
                        ax.text(left + amount/2, 0, f'${amount:.1f}M', 
                               ha='center', va='center', fontweight='bold', color='white')
                        left += amount
            
            ax.set_title(f'{summary["department_code"]} Operating Budget', fontsize=14, fontweight='bold')
            
            # Remove y-axis
            ax.set_yticks([])
            ax.spines['left'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['top'].set_visible(False)
            
            plt.tight_layout()
            
            # Convert to base64 string
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)  # Explicitly close the figure
            plt.clf()  # Clear the current figure
            
            return image_base64
            
        except Exception as e:
            logger.error(f"Error creating chart for {summary['department_code']}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Return a simple placeholder image as base64
            try:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.text(0.5, 0.5, f'Chart Error\n{summary["department_code"]}', 
                       ha='center', va='center', transform=ax.transAxes, fontsize=14)
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.set_xticks([])
                ax.set_yticks([])
                
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
                buffer.seek(0)
                image_base64 = base64.b64encode(buffer.getvalue()).decode()
                plt.close(fig)
                plt.clf()
                
                return image_base64
            except:
                # If even the error chart fails, return empty string
                return ""
    
    def generate_html_report(self, summary: dict) -> str:
        """
        Generate HTML report for a department.
        
        Args:
            summary: Department summary dictionary
            
        Returns:
            HTML string
        """
        chart_base64 = self.create_department_chart(summary)
        
        # Convert amounts to millions for display
        op_budget = summary['operating_budget']
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{summary['department_code']} FY26 Budget Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }}
        
        .header h1 {{
            color: #2c3e50;
            margin: 0;
            font-size: 2.2em;
        }}
        
        .header h2 {{
            color: #7f8c8d;
            margin: 10px 0 0 0;
            font-weight: normal;
        }}
        
        .budget-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .budget-table th {{
            background-color: #3498db;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: bold;
        }}
        
        .budget-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ecf0f1;
        }}
        
        .budget-table tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        .budget-table tr:hover {{
            background-color: #e8f4fd;
        }}
        
        .amount {{
            text-align: right;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .total-row {{
            background-color: #3498db !important;
            color: white;
            font-weight: bold;
        }}
        
        .total-row td {{
            border-bottom: none;
        }}
        
        .chart-container {{
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }}
        
        .chart-container h3 {{
            color: #2c3e50;
            margin-bottom: 20px;
        }}
        
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .summary-stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin: 30px 0;
        }}
        
        .budget-card {{
            background-color: #fff;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            text-align: center;
            flex: 0 1 300px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .budget-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }}
        
        .budget-amount {{
            font-size: 2.2em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 8px;
        }}
        
        .budget-label {{
            color: #7f8c8d;
            font-size: 1.1em;
            font-weight: 500;
        }}
        
        .footer {{
            margin-top: 40px;
            padding: 20px;
            background-color: #ecf0f1;
            border-radius: 8px;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{summary['department_code']} FY26 Operating Budget</h1>
        <h2>{summary['department_name']}</h2>
    </div>
    
    <div class="summary-stats">
        <div class="budget-card">
            <div class="budget-amount">${summary['operating_budget']['total'] / 1_000_000:,.1f}M</div>
            <div class="budget-label">Total Operating</div>
        </div>
        <div class="budget-card">
            <div class="budget-amount">${summary['cip_projects'] / 1_000_000:,.1f}M</div>
            <div class="budget-label">Capital Improvement Projects</div>
        </div>
    </div>
    
    <table class="budget-table">
        <thead>
            <tr>
                <th>{summary['department_code']} FY26 Operating Budget:</th>
                <th class="amount">${summary['operating_budget']['total'] / 1_000_000:.1f} Million</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>General Funds:</td>
                <td class="amount">${op_budget['General Funds'] / 1_000_000:.1f} Million</td>
            </tr>
            <tr>
                <td>Special Funds:</td>
                <td class="amount">${op_budget['Special Funds'] / 1_000_000:.1f} Million</td>
            </tr>
            <tr>
                <td>Federal Funds:</td>
                <td class="amount">${op_budget['Federal Funds'] / 1_000_000:.1f} Million</td>
            </tr>
            <tr>
                <td>Other Funds:</td>
                <td class="amount">${op_budget['Other Funds'] / 1_000_000:.1f} Million</td>
            </tr>

            <tr class="total-row">
                <td>FY26 Capital Improvement Projects:</td>
                <td class="amount">${summary['cip_projects'] / 1_000_000:.1f} Million</td>
            </tr>
        </tbody>
    </table>
    
    <div class="chart-container">
        <h3>Figure 15. {summary['department_code']} Operating Budget</h3>
        <img src="data:image/png;base64,{chart_base64}" alt="{summary['department_code']} Budget Chart">
    </div>
    
    <div class="footer">
        <p>Generated from Hawaii State Budget FY 2026 Post-Veto Data</p>
        <p>Data source: HB300 CD1 - State of Hawaii Operating and Capital Budget</p>
    </div>
</body>
</html>
"""
        return html
    
    def generate_all_reports(self):
        """Generate HTML reports for all departments."""
        # Get all unique department codes
        dept_codes = sorted(self.df['department_code'].unique())
        
        logger.info(f"Generating reports for {len(dept_codes)} departments")
        
        # Create index page
        index_html = self.create_index_page(dept_codes)
        index_path = self.output_dir / "index.html"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_html)
        logger.info(f"Created index page: {index_path}")
        
        # Generate individual department reports
        for dept_code in dept_codes:
            try:
                logger.info(f"Processing department: {dept_code}")
                summary = self.get_department_summary(dept_code)
                if summary:
                    logger.info(f"Got summary for {dept_code}, generating HTML report...")
                    html_report = self.generate_html_report(summary)
                    
                    # Save to file
                    filename = f"{dept_code.lower()}_budget_report.html"
                    filepath = self.output_dir / filename
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html_report)
                    
                    logger.info(f"Successfully generated report for {dept_code}: {filepath}")
                else:
                    logger.warning(f"Skipped {dept_code} - no data available")
                    
            except Exception as e:
                logger.error(f"Error generating report for {dept_code}: {e}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                # Continue with next department instead of stopping
    
    def create_index_page(self, dept_codes: list) -> str:
        """Create an index page linking to all department reports."""
        # Get department names
        dept_info = []
        for code in dept_codes:
            dept_data = self.df[self.df['department_code'] == code]
            if not dept_data.empty:
                name = dept_data['department_name'].iloc[0]
                total = dept_data['amount'].sum() / 1_000_000
                dept_info.append((code, name, total))
        
        # Sort by total budget (descending)
        dept_info.sort(key=lambda x: x[2], reverse=True)
        
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hawaii State Budget FY 2026 - Departmental Reports</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background-color: #fff;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            color: #2c3e50;
            margin: 0;
            font-size: 2.5em;
        }}
        
        .header p {{
            color: #7f8c8d;
            font-size: 1.1em;
            margin: 15px 0 0 0;
        }}
        
        .departments-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        
        .dept-card {{
            background-color: #fff;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
            text-decoration: none;
            color: inherit;
        }}
        
        .dept-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
            text-decoration: none;
            color: inherit;
        }}
        
        .dept-name {{
            font-size: 1.4em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 8px;
            line-height: 1.3;
        }}
        
        .dept-code {{
            font-size: 0.9em;
            font-weight: 600;
            color: #3498db;
            background-color: #ecf0f1;
            padding: 4px 8px;
            border-radius: 4px;
            display: inline-block;
            margin-bottom: 12px;
        }}
        
        .dept-budget {{
            color: #27ae60;
            font-weight: bold;
            font-size: 1.2em;
        }}
        
        .footer {{
            margin-top: 50px;
            padding: 25px;
            background-color: #fff;
            border-radius: 12px;
            text-align: center;
            color: #7f8c8d;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Hawaii State Budget FY 2026</h1>
        <p>Departmental Budget Reports (Post-Veto)</p>
    </div>
    
    <div class="departments-grid">
"""
        
        for code, name, total in dept_info:
            html += f"""
        <a href="{code.lower()}_budget_report.html" class="dept-card">
            <div class="dept-name">{name}</div>
            <div class="dept-code">{code}</div>
            <div class="dept-budget">${total:.1f}M Total Budget</div>
        </a>
"""
        
        html += """
    </div>
    
    <div class="footer">
        <p>Generated from Hawaii State Budget FY 2026 Post-Veto Data</p>
        <p>Data source: HB300 CD1 - State of Hawaii Operating and Capital Budget</p>
    </div>
</body>
</html>
"""
        return html


def main():
    """Main function to run the departmental budget analyzer."""
    parser = argparse.ArgumentParser(description='Generate departmental budget reports')
    parser.add_argument('data_file', help='Path to budget allocations CSV file')
    parser.add_argument('--output-dir', '-o', 
                       default='data/output/departmental_reports',
                       help='Output directory for HTML reports')
    
    args = parser.parse_args()
    
    # Create analyzer and generate reports
    analyzer = DepartmentalBudgetAnalyzer(args.data_file, args.output_dir)
    analyzer.generate_all_reports()
    
    logger.info(f"All reports generated successfully in {args.output_dir}")
    logger.info("Open index.html to view all department reports")


if __name__ == "__main__":
    main()
