#!/usr/bin/env python3
"""
Generate SPA (Single Page Application) structure for GitHub Pages deployment.
Creates the complete SPA with real departmental data, proper routing, and embedded content.
"""

import pandas as pd
import json
import os
from pathlib import Path
import argparse
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SPAGenerator:
    """Generate SPA structure for GitHub Pages deployment."""
    
    def __init__(self, data_file: str, output_dir: str = "gh-pages/docs"):
        """Initialize the SPA generator."""
        self.data_file = data_file
        self.output_dir = Path(output_dir)
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "css").mkdir(exist_ok=True)
        (self.output_dir / "js").mkdir(exist_ok=True)
        (self.output_dir / "pages").mkdir(exist_ok=True)
        
        # Load data
        self.df = pd.read_csv(data_file)
        
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
        capital_data = dept_data[dept_data['section'] == 'Capital']
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
                    "path": f"/pages/{dept_code.lower()}.html"
                })
        
        # Sort by name
        departments.sort(key=lambda x: x['name'])
        
        # Save to file
        with open(self.output_dir / "js" / "departments.json", 'w') as f:
            json.dump(departments, f, indent=2)
        
        logger.info(f"Generated departments.json with {len(departments)} departments")
        return departments
    
    def generate_department_page(self, dept_code, summary):
        """Generate individual department page content."""
        
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
        
        # Generate the complete page HTML
        page_html = f"""
        <div class="header">
            <h1>{dept_code} FY26 Budget</h1>
            <h2>{summary['department_name']}</h2>
        </div>
        
        <div class="summary-stats">
            {cards_html}
        </div>
        
        <table class="budget-table">
            <thead>
                <tr>
                    <th>{dept_code} FY26 Budget:</th>
                    <th class="amount">{self._format_currency(summary['total_budget'])}</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Operating Budget</td>
                    <td class="amount">{self._format_currency(summary['operating_budget'])}</td>
                </tr>"""
        
        if summary['one_time_appropriations'] > 0:
            page_html += f"""
                <tr>
                    <td>One-Time Appropriations</td>
                    <td class="amount">{self._format_currency(summary['one_time_appropriations'])}</td>
                </tr>"""
        
        if summary['capital_budget'] > 0:
            page_html += f"""
                <tr>
                    <td>Capital Improvement Projects</td>
                    <td class="amount">{self._format_currency(summary['capital_budget'])}</td>
                </tr>"""
        
        page_html += """
            </tbody>
        </table>
        """
        
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
    parser = argparse.ArgumentParser(description='Generate SPA reports for GitHub Pages')
    parser.add_argument('data_file', help='Path to the budget allocations CSV file')
    parser.add_argument('--output-dir', default='gh-pages/docs', help='Output directory for SPA files')
    
    args = parser.parse_args()
    
    generator = SPAGenerator(args.data_file, args.output_dir)
    logger.info("SPA Generator initialized successfully!")
    
    # Generate all pages
    departments = generator.generate_all_pages()
    
    logger.info(f"✅ SPA generation complete!")
    logger.info(f"Generated {len(departments)} departments")
    logger.info(f"Files saved to: {args.output_dir}")
    logger.info("Next steps:")
    logger.info("1. cd gh-pages")
    logger.info("2. git add .")
    logger.info("3. git commit -m 'Update SPA with generated content'")
    logger.info("4. git push")
