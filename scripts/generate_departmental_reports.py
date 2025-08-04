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
import json  # For embedding chart data as JSON
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
        
        # Department code to full name mapping
        self.department_names = {
            'AGR': 'AGRICULTURE',
            'AGS': 'ACCOUNTING AND GENERAL SERVICES',
            'ATG': 'ATTORNEY GENERAL',
            'BED': 'BUSINESS, ECONOMIC DEVELOPMENT & TOURISM',
            'BUF': 'BUDGET AND FINANCE',
            'CCA': 'COMMERCE AND CONSUMER AFFAIRS',
            'CCH': 'CITY AND COUNTY OF HONOLULU',
            'COH': 'COUNTY OF HAWAII',
            'COK': 'COUNTY OF KAUAI',
            'DEF': 'DEFENSE',
            'EDN': 'EDUCATION',
            'GOV': 'GOVERNOR',
            'HHL': 'HAWAIIAN HOME LANDS',
            'HMS': 'HUMAN SERVICES',
            'HRD': 'HUMAN RESOURCES DEVELOPMENT',
            'HTH': 'HEALTH',
            'LAW': 'LAW ENFORCEMENT',
            'LBR': 'LABOR AND INDUSTRIAL RELATIONS',
            'LNR': 'LAND AND NATURAL RESOURCES',
            'LTG': 'LIEUTENANT GOVERNOR',
            'P': 'LEGISLATURE',
            'PSD': 'PUBLIC SAFETY',
            'TAX': 'TAXATION',
            'TRN': 'TRANSPORTATION',
            'UOH': 'UNIVERSITY OF HAWAII'
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
        
        # Use full department name from mapping
        dept_name = self.department_names.get(dept_code, dept_code)
        
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
        # Get department names and budget breakdown
        dept_info = []
        for code in dept_codes:
            dept_data = self.df[self.df['department_code'] == code]
            if not dept_data.empty:
                # Use full department name from mapping
                name = self.department_names.get(code, code)
                total = dept_data['amount'].sum() / 1_000_000
                
                # Calculate operating vs capital breakdown
                operating = dept_data[dept_data['section'] == 'Operating']['amount'].sum() / 1_000_000
                capital = dept_data[dept_data['section'] == 'Capital Improvement']['amount'].sum() / 1_000_000
                
                dept_info.append((code, name, total, operating, capital))
        
        # Sort by total budget (descending)
        dept_info.sort(key=lambda x: x[2], reverse=True)
        
        # Calculate totals for summary cards
        total_budget = sum(info[2] for info in dept_info)
        total_departments = len(dept_info)
        largest_dept = dept_info[0] if dept_info else ('', '', 0)
        
        # Calculate operating vs capital budget totals
        operating_total = self.df[self.df['section'] == 'Operating']['amount'].sum() / 1_000_000
        capital_total = self.df[self.df['section'] == 'Capital Improvement']['amount'].sum() / 1_000_000
        
        # Helper function to format budget amounts
        def format_budget(amount_millions):
            if amount_millions >= 1000:
                return f"${amount_millions/1000:,.1f}B"
            else:
                return f"${amount_millions:,.0f}M"
        
        # Prepare chart data JSON for embedding in the JavaScript code
        chart_data = [
            {
                "code": code,
                "name": name,
                "operating": operating,
                "capital": capital
            } for code, name, total, operating, capital in dept_info
        ]
        chart_data_json = json.dumps(chart_data)
        print(f"DEBUG: chart_data_json = {chart_data_json}")
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hawaii State Budget FY 2026 - Departmental Reports</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #1a202c;
            background: linear-gradient(135deg, #007fb2 0%, #005a7d 100%);
            min-height: 100vh;
            font-size: 16px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 40px;
            background-color: #fff;
            border-radius: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            color: #1a202c;
            margin: 0 0 12px 0;
            font-size: 3rem;
            font-weight: 700;
            letter-spacing: -0.025em;
        }}
        
        .header p {{
            color: #4a5568;
            font-size: 1.25rem;
            font-weight: 400;
            margin: 0;
        }}
        
        .summary-section {{
            margin-bottom: 40px;
        }}
        
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
        }}
        
        .summary-card {{
            background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%);
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 4px 20px rgba(0,127,178,0.1);
            border: 1px solid rgba(0,127,178,0.1);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .summary-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        }}
        
        .summary-card h3 {{
            font-size: 0.875rem;
            font-weight: 600;
            color: #4a5568;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }}
        
        .summary-card .value {{
            font-size: 2.5rem;
            font-weight: 700;
            color: #1a202c;
            line-height: 1;
            margin-bottom: 4px;
        }}
        
        .summary-card .label {{
            font-size: 1rem;
            color: #718096;
            font-weight: 500;
        }}
        
        .search-section {{
            background-color: #fff;
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 32px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}
        
        .search-container {{
            position: relative;
            max-width: 500px;
            margin: 0 auto;
        }}
        
        .search-input {{
            width: 100%;
            padding: 16px 24px 16px 48px;
            font-size: 1.125rem;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            background-color: #f8fafc;
            transition: all 0.2s ease;
            font-family: inherit;
        }}
        
        .search-input:focus {{
            outline: none;
            border-color: #007fb2;
            background-color: #fff;
            box-shadow: 0 0 0 3px rgba(0, 127, 178, 0.1);
        }}
        
        .search-icon {{
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            color: #a0aec0;
            font-size: 1.25rem;
        }}
        
        .departments-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 24px;
            margin: 32px 0;
        }}
        
        .dept-card {{
            background: linear-gradient(135deg, #f8fcff 0%, #eef7ff 100%);
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 4px 20px rgba(0,127,178,0.08);
            transition: all 0.3s ease;
            text-decoration: none;
            color: inherit;
            border: 1px solid rgba(0,127,178,0.15);
            position: relative;
            overflow: hidden;
        }}
        
        .dept-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #007fb2 0%, #005a7d 100%);
        }}
        
        .dept-card:hover {{
            transform: translateY(-8px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
            text-decoration: none;
            color: inherit;
        }}
        
        .dept-name {{
            font-size: 1.375rem;
            font-weight: 600;
            color: #1a202c;
            margin-bottom: 12px;
            line-height: 1.3;
            letter-spacing: -0.025em;
        }}
        
        .dept-code {{
            font-size: 0.75rem;
            font-weight: 600;
            color: #007fb2;
            background: linear-gradient(135deg, #e6f3ff 0%, #d9ecff 100%);
            padding: 6px 12px;
            border-radius: 8px;
            display: inline-block;
            margin-bottom: 16px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .dept-budget {{
            color: #38a169;
            font-weight: 700;
            font-size: 1.5rem;
            letter-spacing: -0.025em;
            margin-bottom: 16px;
        }}
        
        .dept-breakdown {{
            display: flex;
            gap: 16px;
            margin-top: 8px;
        }}
        
        .breakdown-item {{
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            flex: 1;
        }}
        
        .breakdown-label {{
            font-size: 0.75rem;
            font-weight: 500;
            color: #718096;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }}
        
        .breakdown-value {{
            font-size: 1rem;
            font-weight: 600;
            color: #2d3748;
        }}
        
        .chart-section {{
            margin-bottom: 40px;
        }}
        
        .chart-container {{
            background-color: #fff;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 4px 20px rgba(0,127,178,0.08);
            border: 1px solid rgba(0,127,178,0.1);
        }}
        
        .chart-title {{
            font-size: 1.75rem;
            font-weight: 600;
            color: #1a202c;
            margin-bottom: 32px;
            text-align: center;
        }}
        
        .chart-wrapper {{
            display: flex;
            flex-direction: column;
            gap: 16px;
            max-height: 600px;
            overflow-y: auto;
        }}
        
        .dept-chart-row {{
            display: flex;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        .dept-chart-row:last-child {{
            border-bottom: none;
        }}
        
        .dept-label {{
            width: 200px;
            font-size: 0.875rem;
            font-weight: 600;
            color: #007fb2;
            text-decoration: none;
            flex-shrink: 0;
            cursor: pointer;
            transition: color 0.2s ease;
        }}
        
        .dept-label:hover {{
            color: #005a7d;
            text-decoration: underline;
        }}
        
        .chart-bars {{
            display: flex;
            flex: 1;
            gap: 8px;
            align-items: center;
            margin-left: 16px;
        }}
        
        .bar-group {{
            display: flex;
            flex-direction: column;
            gap: 4px;
            flex: 1;
        }}
        
        .bar-container {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .bar-label {{
            font-size: 0.75rem;
            font-weight: 500;
            color: #4a5568;
            width: 60px;
            text-align: right;
        }}
        
        .bar {{
            height: 20px;
            border-radius: 4px;
            position: relative;
            min-width: 2px;
            transition: all 0.3s ease;
        }}
        
        .bar-operating {{
            background: linear-gradient(90deg, #007fb2 0%, #0099d4 100%);
        }}
        
        .bar-capital {{
            background: linear-gradient(90deg, #38a169 0%, #48bb78 100%);
        }}
        
        .bar-value {{
            position: absolute;
            right: 8px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 0.75rem;
            font-weight: 600;
            color: white;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
        }}
        
        .chart-legend {{
            display: flex;
            justify-content: center;
            gap: 24px;
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid #e2e8f0;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
        }}
        
        .legend-operating {{
            background: linear-gradient(90deg, #007fb2 0%, #0099d4 100%);
        }}
        
        .legend-capital {{
            background: linear-gradient(90deg, #38a169 0%, #48bb78 100%);
        }}
        
        .legend-text {{
            font-size: 0.875rem;
            font-weight: 500;
            color: #4a5568;
        }}
        
        .footer {{
            margin-top: 60px;
            padding: 32px;
            background-color: #fff;
            border-radius: 16px;
            text-align: center;
            color: #4a5568;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}
        
        .footer p {{
            font-size: 0.875rem;
            font-weight: 500;
        }}
        
        .hidden {{
            display: none !important;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 2.25rem;
            }}
            
            .summary-cards {{
                grid-template-columns: 1fr;
            }}
            
            .departments-grid {{
                grid-template-columns: 1fr;
            }}
            
            .dept-card {{
                padding: 24px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Hawaii State Budget FY 2026</h1>
        <p>Departmental Budget Reports (Post-Veto)</p>
    </div>
    
    <div class="summary-section">
        <div class="summary-cards">
            <div class="summary-card">
                <h3>Total Budget</h3>
                <div class="value">{format_budget(total_budget)}</div>
                <div class="label">All Departments</div>
            </div>
            <div class="summary-card">
                <h3>Departments</h3>
                <div class="value">{total_departments}</div>
                <div class="label">State Agencies</div>
            </div>
            <div class="summary-card">
                <h3>Largest Department</h3>
                <div class="value">{format_budget(largest_dept[2])}</div>
                <div class="label">{largest_dept[1]}</div>
            </div>
        </div>
        
        <div class="summary-cards">
            <div class="summary-card">
                <h3>Operating Budget</h3>
                <div class="value">{format_budget(operating_total)}</div>
                <div class="label">All Departments Combined</div>
            </div>
            <div class="summary-card">
                <h3>Capital Budget</h3>
                <div class="value">{format_budget(capital_total)}</div>
                <div class="label">Capital Improvement Projects</div>
            </div>
        </div>
    </div>
    
    <div class="chart-section">
        <div class="chart-container">
            <h2 class="chart-title">Operating vs Capital Budget by Department</h2>
            <div class="chart-wrapper" id="budgetChart">
                <!-- Chart will be generated here -->
            </div>
        </div>
    </div>
    
    <div class="search-section">
        <div class="search-container">
            <span class="search-icon">🔍</span>
            <input type="text" id="searchInput" class="search-input" placeholder="Search departments by name or code...">
        </div>
    </div>
    
    <div class="departments-grid" id="departmentsGrid">
"""
        
        for code, name, total, operating, capital in dept_info:
            # Format the budget amounts
            def format_amount(amount):
                if amount >= 1000:
                    return f"{amount/1000:.1f}B"
                else:
                    return f"{amount:.0f}M"
            
            total_display = format_amount(total)
            operating_display = format_amount(operating)
            capital_display = format_amount(capital)
            
            html += f"""
        <a href="{code.lower()}_budget_report.html" class="dept-card">
            <div class="dept-name">{name}</div>
            <div class="dept-code">{code}</div>
            <div class="dept-budget">${total_display} Total Budget</div>
            <div class="dept-breakdown">
                <div class="breakdown-item">
                    <span class="breakdown-label">Operating:</span>
                    <span class="breakdown-value">${operating_display}</span>
                </div>
                <div class="breakdown-item">
                    <span class="breakdown-label">Capital:</span>
                    <span class="breakdown-value">${capital_display}</span>
                </div>
            </div>
        </a>
"""
        
        html += """
    </div>
    
    <div class="footer">
        <p>Generated from Hawaii State Budget FY 2026 Post-Veto Data</p>
        <p>Data source: HB300 CD1 - State of Hawaii Operating and Capital Budget</p>
    </div>
    
    <script>
        // Search functionality
        const searchInput = document.getElementById('searchInput');
        const departmentsGrid = document.getElementById('departmentsGrid');
        const deptCards = departmentsGrid.querySelectorAll('.dept-card');
        
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            
            deptCards.forEach(card => {
                const deptName = card.querySelector('.dept-name').textContent.toLowerCase();
                const deptCode = card.querySelector('.dept-code').textContent.toLowerCase();
                
                if (deptName.includes(searchTerm) || deptCode.includes(searchTerm) || searchTerm === '') {
                    card.classList.remove('hidden');
                } else {
                    card.classList.add('hidden');
                }
            });
            
            // Show/hide "no results" message
            const visibleCards = departmentsGrid.querySelectorAll('.dept-card:not(.hidden)');
            let noResultsMsg = document.getElementById('noResultsMsg');
            
            if (visibleCards.length === 0 && searchTerm !== '') {
                if (!noResultsMsg) {
                    noResultsMsg = document.createElement('div');
                    noResultsMsg.id = 'noResultsMsg';
                    noResultsMsg.style.cssText = `
                        text-align: center;
                        padding: 60px 20px;
                        color: #4a5568;
                        font-size: 1.125rem;
                        background-color: #fff;
                        border-radius: 16px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                        margin: 20px 0;
                    `;
                    noResultsMsg.innerHTML = `
                        <div style="font-size: 3rem; margin-bottom: 16px;">🔍</div>
                        <div style="font-weight: 600; margin-bottom: 8px;">No departments found</div>
                        <div>Try searching with different keywords</div>
                    `;
                    departmentsGrid.appendChild(noResultsMsg);
                }
            } else if (noResultsMsg) {
                noResultsMsg.remove();
            }
        });
        
        // Add smooth scrolling for better UX
        searchInput.addEventListener('focus', function() {
            this.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
        
        // Add keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                searchInput.focus();
            }
            if (e.key === 'Escape' && document.activeElement === searchInput) {
                searchInput.blur();
                searchInput.value = '';
                searchInput.dispatchEvent(new Event('input'));
            }
        });
        
        // Generate budget chart
        function generateBudgetChart() {
            const chartContainer = document.getElementById('budgetChart');
            const departments = {chart_data_json};
            
            // Find the maximum value for scaling
            const maxValue = Math.max(...departments.map(d => Math.max(d.operating, d.capital)));
            
            let chartHTML = '';
            
            departments.forEach(dept => {
                const operatingWidth = (dept.operating / maxValue) * 100;
                const capitalWidth = (dept.capital / maxValue) * 100;
                
                // Format amounts for display
                function formatAmount(amount) {
                    if (amount >= 1000) {
                        return (amount / 1000).toFixed(1) + 'B';
                    } else if (amount >= 1) {
                        return amount.toFixed(0) + 'M';
                    } else {
                        return amount.toFixed(1) + 'M';
                    }
                }
                
                chartHTML += `
                    <div class="dept-chart-row">
                        <a href="${{dept.code.toLowerCase()}}_budget_report.html" class="dept-label">
                            ${{dept.name}}
                        </a>
                        <div class="chart-bars">
                            <div class="bar-group">
                                <div class="bar-container">
                                    <div class="bar-label">Operating</div>
                                    <div class="bar bar-operating" style="width: ${{operatingWidth}}%">
                                        <span class="bar-value">${{formatAmount(dept.operating)}}</span>
                                    </div>
                                </div>
                                <div class="bar-container">
                                    <div class="bar-label">Capital</div>
                                    <div class="bar bar-capital" style="width: ${{capitalWidth}}%">
                                        <span class="bar-value">${{formatAmount(dept.capital)}}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            chartHTML += `
                <div class="chart-legend">
                    <div class="legend-item">
                        <div class="legend-color legend-operating"></div>
                        <span class="legend-text">Operating Budget</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color legend-capital"></div>
                        <span class="legend-text">Capital Budget</span>
                    </div>
                </div>
            `;
            
            chartContainer.innerHTML = chartHTML;
        }
        
        // Generate chart on page load
        generateBudgetChart();
    </script>
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
