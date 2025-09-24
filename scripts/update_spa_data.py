#!/usr/bin/env python3
"""
Update SPA with real departmental data from existing HTML reports.
"""
import os
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

def extract_department_data():
    """Extract department data from existing HTML reports."""
    reports_dir = Path("data/output/departmental_reports")
    departments = []
    
    # Department code to full name mapping
    dept_names = {
        'AGR': 'Department of Agriculture',
        'AGS': 'Department of the Attorney General',
        'ATG': 'Department of the Attorney General',
        'BED': 'Department of Business, Economic Development and Tourism',
        'BUF': 'Department of Budget and Finance',
        'CCA': 'Department of Commerce and Consumer Affairs',
        'CCH': 'Department of Community and Cultural Affairs',
        'COH': 'County of Hawaii',
        'COK': 'County of Kauai',
        'DEF': 'Department of Defense',
        'EDN': 'Department of Education',
        'GOV': 'Office of the Governor',
        'HHL': 'Department of Hawaiian Home Lands',
        'HMS': 'Hawaii Medical Service Association',
        'HRD': 'Department of Human Resources Development',
        'HTH': 'Department of Health',
        'LAW': 'Department of Law Enforcement',
        'LBR': 'Department of Labor and Industrial Relations',
        'LNR': 'Department of Land and Natural Resources',
        'LTG': 'Office of the Lieutenant Governor',
        'P': 'Legislature',
        'PSD': 'Department of Public Safety',
        'TAX': 'Department of Taxation',
        'TRN': 'Department of Transportation',
        'UOH': 'University of Hawaii'
    }
    
    # Process each HTML file (exclude budget_report suffix)
    for html_file in reports_dir.glob("*.html"):
        if html_file.name == "index.html":
            continue
            
        # Extract department code (remove _budget_report suffix if present)
        dept_code = html_file.stem.upper()
        if dept_code.endswith('_BUDGET_REPORT'):
            dept_code = dept_code.replace('_BUDGET_REPORT', '')
        
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            # Extract department name from the HTML
            dept_name = dept_names.get(dept_code, f"Department of {dept_code}")
            
            # Extract total budget from budget cards
            total_budget = "$0"
            budget_cards = soup.find_all('div', class_='budget-card')
            
            # Look for Operating Budget first
            for card in budget_cards:
                label_elem = card.find('div', class_='budget-label')
                if label_elem and 'Operating Budget' in label_elem.get_text():
                    amount_elem = card.find('div', class_='budget-amount')
                    if amount_elem:
                        total_budget = amount_elem.get_text().strip()
                        break
            
            # If no operating budget found, try to get from table header
            if total_budget == "$0":
                table_headers = soup.find_all('th', class_='amount')
                for header in table_headers:
                    text = header.get_text().strip()
                    if '$' in text:
                        total_budget = text
                        break
            
            departments.append({
                "id": dept_code.lower(),
                "name": dept_name,
                "budget": total_budget,
                "path": f"/pages/{dept_code.lower()}.html"
            })
            
        except Exception as e:
            print(f"Error processing {html_file}: {e}")
            continue
    
    # Sort departments by name
    departments.sort(key=lambda x: x['name'])
    
    return departments

def update_spa_files():
    """Update SPA files with real data and styling."""
    
    # Extract department data
    departments = extract_department_data()
    
    # Update departments.json
    gh_pages_dir = Path("gh-pages/docs")
    departments_json_path = gh_pages_dir / "js" / "departments.json"
    
    with open(departments_json_path, 'w', encoding='utf-8') as f:
        json.dump(departments, f, indent=2)
    
    print(f"✅ Updated departments.json with {len(departments)} departments")
    
    # Copy CSS from existing reports
    reports_dir = Path("data/output/departmental_reports")
    sample_html = reports_dir / "EDN.html"
    
    if sample_html.exists():
        with open(sample_html, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        
        # Extract CSS styles
        style_tags = soup.find_all('style')
        extracted_css = ""
        
        for style in style_tags:
            extracted_css += style.get_text() + "\n\n"
        
        # Update SPA CSS with departmental report styles
        spa_css_path = gh_pages_dir / "css" / "styles.css"
        
        # Read existing SPA CSS
        with open(spa_css_path, 'r', encoding='utf-8') as f:
            spa_css = f.read()
        
        # Append departmental report CSS
        updated_css = spa_css + "\n\n/* Departmental Report Styles */\n" + extracted_css
        
        with open(spa_css_path, 'w', encoding='utf-8') as f:
            f.write(updated_css)
        
        print("✅ Updated SPA CSS with departmental report styles")
    
    # Update individual department pages with actual content
    for dept in departments:
        dept_code = dept['id'].upper()
        # Try both naming patterns
        source_html = reports_dir / f"{dept_code}_budget_report.html"
        if not source_html.exists():
            source_html = reports_dir / f"{dept_code}.html"
        target_html = gh_pages_dir / "pages" / f"{dept['id']}.html"
        
        if source_html.exists():
            with open(source_html, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            # Extract the main content (everything inside body, excluding navigation)
            body = soup.find('body')
            if body:
                # Remove any existing navigation elements
                for nav in body.find_all(['nav', 'header']):
                    nav.decompose()
                
                # Create SPA-compatible page
                spa_content = f"""<!-- Department: {dept['name']} -->
<div class="department-content">
{body.decode_contents()}
</div>
"""
                
                with open(target_html, 'w', encoding='utf-8') as f:
                    f.write(spa_content)
        
        print(f"✅ Updated {dept['id']}.html")

if __name__ == "__main__":
    print("Updating SPA with real departmental data...")
    update_spa_files()
    print("\n🎉 SPA update complete!")
    print("Next steps:")
    print("1. cd gh-pages")
    print("2. git add .")
    print("3. git commit -m 'Update SPA with real departmental data'")
    print("4. git push")
