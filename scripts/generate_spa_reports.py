#!/usr/bin/env python3
"""
Generate SPA (Single Page Application) structure for GitHub Pages deployment.
Creates the complete SPA with real departmental data, proper routing, and embedded content.
"""

import pandas as pd
import json
import os
import sys
from pathlib import Path
import argparse
import logging
from datetime import datetime

# Default department description to use when none is found
DEFAULT_DEPT_DESCRIPTION = "No description available for this department."

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SPAGenerator:
    """Generate SPA structure for GitHub Pages deployment."""
    
    def __init__(self, data_file: str, output_dir: str = "gh-pages/docs", 
                 descriptions_file: str = "data/processed/department_descriptions.json"):
        """
        Initialize the SPA generator.
        
        Args:
            data_file: Path to the budget allocations CSV file
            output_dir: Directory to save SPA files
            descriptions_file: Path to the JSON file containing department descriptions
        """
        self.data_file = data_file
        self.output_dir = Path(output_dir)
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "css").mkdir(exist_ok=True)
        (self.output_dir / "js").mkdir(exist_ok=True)
        (self.output_dir / "pages").mkdir(exist_ok=True)
        
        # Load data
        self.df = pd.read_csv(data_file)
        
        # Load department descriptions
        self.descriptions = self._load_descriptions(descriptions_file)
        
        # Department code to full name mapping
        self.dept_names = {
            'AGR': 'Department of Agriculture',
            'ATG': 'Department of the Attorney General',
            'BED': 'Department of Business, Economic Development and Tourism',
            'BUF': 'Department of Budget and Finance',
            'CCA': 'Department of Commerce and Consumer Affairs',
            'DEF': 'Department of Defense',
            'EDN': 'Department of Education',
            'GOV': 'Office of the Governor',
            'HHL': 'Department of Hawaiian Home Lands',
            'HRD': 'Department of Human Resources Development',
            'HTH': 'Department of Health',
            'LBR': 'Department of Labor and Industrial Relations',
            'LNR': 'Department of Land and Natural Resources',
            'LTG': 'Office of the Lieutenant Governor',
            'P': 'Legislature',
            'PSD': 'Department of Public Safety',
            'TAX': 'Department of Taxation',
            'TRN': 'Department of Transportation',
            'UOH': 'University of Hawaii'
        }
        
        # Department code to display name mapping (for the descriptions)
        self.display_names = {
            'AGR': 'Department of Agriculture',
            'AGS': 'Department of Accounting & General Services',
            'ATG': 'Department of the Attorney General',
            'BED': 'Department of Business, Economic Development & Tourism',
            'BUF': 'Department of Budget & Finance',
            'CCA': 'Department of Commerce & Consumer Affairs',
            'CCH': 'City and County of Honolulu',
            'COH': 'County of Hawaii',
            'COK': 'County of Kauai',
            'DEF': 'Department of Defense',
            'EDN': 'Department of Education',
            'GOV': 'Office of the Governor',
            'HHL': 'Department of Hawaiian Home Lands',
            'HMS': 'Department of Human Services',
            'HRD': 'Department of Human Resources Development',
            'HTH': 'Department of Health',
            'LAW': 'Department of Law Enforcement',
            'LBR': 'Department of Labor & Industrial Relations',
            'LNR': 'Department of Land & Natural Resources',
            'LTG': 'Office of the Lieutenant Governor',
            'P': 'State Legislature',
            'PSD': 'Department of Corrections and Rehabilitation',
            'TAX': 'Department of Taxation',
            'TRN': 'Department of Transportation',
            'UOH': 'University of Hawaii System'
        }
    
    def _load_descriptions(self, descriptions_file: str) -> dict:
        """
        Load department descriptions from a JSON file.
        
        Args:
            descriptions_file: Path to the JSON file containing department descriptions
            
        Returns:
            Dictionary mapping department codes to their descriptions
        """
        try:
            with open(descriptions_file, 'r', encoding='utf-8') as f:
                descriptions = json.load(f)
            logger.info(f"Loaded descriptions for {len(descriptions)} departments")
            return descriptions
        except FileNotFoundError:
            logger.warning(f"Department descriptions file not found: {descriptions_file}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing department descriptions: {e}")
            return {}
    
    def get_department_description(self, dept_code: str) -> str:
        """
        Get the description for a department.
        
        Args:
            dept_code: Department code (e.g., 'AGR')
            
        Returns:
            Department description as a string
        """
        # Get the display name for the department
        display_name = self.display_names.get(dept_code, dept_code)
        
        # Try to get the description for the department
        dept_info = self.descriptions.get(dept_code, {})
        
        # If we have a description, use it
        if 'description' in dept_info:
            return dept_info['description']
            
        # Otherwise, use the display name with a default message
        return f"{display_name} is a department of the State of Hawaii. {DEFAULT_DEPT_DESCRIPTION}"
    
    def _format_currency(self, amount):
        """Format currency amounts with appropriate precision."""
        if amount >= 1_000_000_000:
            return f"${amount / 1_000_000_000:.1f}B"
        elif amount >= 10_000_000:
            return f"${amount / 1_000_000:.0f}M"
        elif amount >= 1_000_000:
            return f"${amount / 1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount / 1_000:.0f}K"
        else:
            return f"${amount:.0f}"
    
    def get_department_summary(self, dept_code):
        """Get budget summary for a department."""
        dept_data = self.df[self.df['department_code'] == dept_code]
        
        if dept_data.empty:
            return None
        
        # Calculate operating budget
        operating_data = dept_data[dept_data['section'] == 'Operating']
        total_operating = operating_data['amount'].sum()
        
        # Calculate one-time appropriations
        onetime_data = dept_data[dept_data['section'] == 'One-Time']
        total_onetime = onetime_data['amount'].sum()
        
        # Calculate capital budget
        capital_data = dept_data[dept_data['section'] == 'Capital Improvement']
        total_capital = capital_data['amount'].sum()
        
        return {
            'department_code': dept_code,
            'department_name': self.dept_names.get(dept_code, f"Department of {dept_code}"),
            'operating_budget': total_operating,
            'one_time_appropriations': total_onetime,
            'capital_budget': total_capital,
            'total_budget': total_operating + total_onetime + total_capital
        }
    
    def generate_departments_json(self):
        """Generate departments.json with all department data."""
        departments = []
        
        # Get unique departments
        dept_codes = sorted(self.df['department_code'].unique())
        
        for dept_code in dept_codes:
            summary = self.get_department_summary(dept_code)
            if summary and summary['total_budget'] > 0:
                departments.append({
                    "id": dept_code.lower(),
                    "name": summary['department_name'],
                    "budget": self._format_currency(summary['total_budget']),
                    "operating_budget": summary['operating_budget'],
                    "capital_budget": summary['capital_budget'],
                    "one_time_appropriations": summary['one_time_appropriations'],
                    "path": f"/pages/{dept_code.lower()}.html"
                })
        
        # Sort by name
        departments.sort(key=lambda x: x['name'])
        
        # Save to file
        with open(self.output_dir / "js" / "departments.json", 'w') as f:
            json.dump(departments, f, indent=2)
        
        logger.info(f"Generated departments.json with {len(departments)} departments")
        return departments
    
    def _get_css_styles(self) -> str:
        """Return the CSS styles for the department pages."""
        return """
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
                background-color: #fff;
            }
            
            .header {
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 15px;
                border-bottom: 2px solid #e9ecef;
            }
            
            .header h1 {
                color: #2c3e50;
                margin-bottom: 5px;
                font-size: 2.2em;
            }
            
            .header h2 {
                color: #6c757d;
                margin-top: 0;
                font-size: 1.5em;
                font-weight: normal;
            }
            
            .dept-description {
                background-color: #f8f9fa;
                border-left: 4px solid #3498db;
                padding: 20px;
                margin-bottom: 30px;
                border-radius: 0 8px 8px 0;
            }
            
            .dept-description h3 {
                color: #2c3e50;
                margin-top: 0;
                margin-bottom: 10px;
                font-size: 1.4em;
            }
            
            .dept-description p {
                margin: 0;
                line-height: 1.6;
                color: #4a5568;
            }
            
            .summary-stats {
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .budget-card {
                flex: 1;
                min-width: 200px;
                background: #fff;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                padding: 20px;
                text-align: center;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            
            .budget-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            }
            
            .budget-amount {
                font-size: 1.8em;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 5px;
            }
            
            .budget-label {
                color: #6c757d;
                font-size: 0.9em;
            }
            
            .budget-table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 0.9em;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                overflow: hidden;
            }
            
            .budget-table thead tr {
                background-color: #2c3e50;
                color: #ffffff;
                text-align: left;
            }
            
            .budget-table th,
            .budget-table td {
                padding: 12px 15px;
            }
            
            .budget-table tbody tr {
                border-bottom: 1px solid #dddddd;
            }
            
            .budget-table tbody tr:nth-of-type(even) {
                background-color: #f8f9fa;
            }
            
            .budget-table tbody tr:last-of-type {
                border-bottom: 2px solid #2c3e50;
            }
            
            .budget-table tbody tr:hover {
                background-color: #f1f3f5;
            }
            
            .amount {
                text-align: right;
                font-family: 'Courier New', monospace;
                font-weight: bold;
            }
            
            .total-row {
                font-weight: bold;
                background-color: #e9ecef !important;
            }
        </style>
        """
    
    def generate_department_page(self, dept_code, summary):
        """Generate individual department page content."""
        # Get department description
        dept_description = self.get_department_description(dept_code)
        
        # Generate summary cards
        cards_html = f"""
            <div class="budget-card">
                <div class="budget-amount">{self._format_currency(summary['operating_budget'])}</div>
                <div class="budget-label">Operating Budget</div>
            </div>
        """
        
        if summary['one_time_appropriations'] > 0:
            cards_html += f"""
            <div class="budget-card">
                <div class="budget-amount">{self._format_currency(summary['one_time_appropriations'])}</div>
                <div class="budget-label">One-Time Appropriations</div>
            </div>
            """
        
        if summary['capital_budget'] > 0:
            cards_html += f"""
            <div class="budget-card">
                <div class="budget-amount">{self._format_currency(summary['capital_budget'])}</div>
                <div class="budget-label">Capital Improvement Projects</div>
            </div>
            """
        
        # Get CSS styles
        css_styles = self._get_css_styles()
        
        # Format the currency values
        operating_budget = self._format_currency(summary['operating_budget'])
        one_time = self._format_currency(summary['one_time_appropriations'])
        capital = self._format_currency(summary['capital_budget'])
        total = self._format_currency(summary['total_budget'])
        
        # Generate the complete page HTML
        page_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{summary['department_name']} - FY26 Budget</title>
            {css_styles}
        </head>
        <body>
            <div class="header">
                <h1>{dept_code} FY26 Budget</h1>
                <h2>{summary['department_name']}</h2>
            </div>
            
            <div class="dept-description">
                <h3>About {summary['department_name']}</h3>
                <p>{dept_description}</p>
            </div>
            
            <div class="summary-stats">
                {cards_html}
            </div>
            
            <table class="budget-table">
                <thead>
                    <tr>
                        <th>Budget Category</th>
                        <th class="amount">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Operating Budget</td>
                        <td class="amount">{operating_budget}</td>
                    </tr>"""
        
        if summary['one_time_appropriations'] > 0:
            page_html += f"""
                    <tr>
                        <td>One-Time Appropriations</td>
                        <td class="amount">{one_time}</td>
                    </tr>"""
        
        if summary['capital_budget'] > 0:
            page_html += f"""
                    <tr class="total-row">
                        <td>Capital Improvement Projects</td>
                        <td class="amount">{capital}</td>
                    </tr>
                    <tr class="total-row">
                        <td>Total Budget</td>
                        <td class="amount">{total}</td>
                    </tr>"""
        
        page_html += """
                </tbody>
            </table>
        </body>
        </html>
        """
        
        return page_html
        
        return page_html
    
    def generate_all_pages(self):
        """Generate all department pages."""
        # Generate departments.json
        departments = self.generate_departments_json()
        
        # Generate individual department pages
        dept_codes = sorted(self.df['department_code'].unique())
        
        for dept_code in dept_codes:
            summary = self.get_department_summary(dept_code)
            if summary and summary['total_budget'] > 0:
                page_content = self.generate_department_page(dept_code, summary)
                
                # Save to file
                page_file = self.output_dir / "pages" / f"{dept_code.lower()}.html"
                with open(page_file, 'w') as f:
                    f.write(page_content)
                
                logger.info(f"Generated page for {dept_code}")
        
        logger.info(f"Generated {len(dept_codes)} department pages")
        return departments

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description='Generate SPA reports for GitHub Pages')
    parser.add_argument('data_file', help='Path to the budget allocations CSV file')
    parser.add_argument('--output-dir', default='gh-pages/docs', help='Output directory for SPA files')
    parser.add_argument('--descriptions', default='data/processed/department_descriptions.json', 
                       help='Path to department descriptions JSON file')
    
    args = parser.parse_args()
    
    try:
        # Generate SPA
        generator = SPAGenerator(
            data_file=args.data_file,
            output_dir=args.output_dir,
            descriptions_file=args.descriptions
        )
        generator.generate_all_pages()
        generator.generate_departments_json()
        
        logger.info(f"SPA generated successfully in {args.output_dir}")
    except Exception as e:
        logger.error(f"Error generating SPA: {str(e)}")
        sys.exit(1)
    logger.info("2. git add .")
    logger.info("3. git commit -m 'Update SPA with generated content'")
    logger.info("4. git push")
