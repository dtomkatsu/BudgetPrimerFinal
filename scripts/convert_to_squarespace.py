#!/usr/bin/env python3
"""
Convert HTML departmental reports to Squarespace-compatible format.

This script takes the existing HTML reports and converts them to code blocks
that can be embedded in Squarespace pages.
"""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
import argparse

def extract_content_from_html(html_content):
    """Extract the main content from HTML, removing base64 images and restructuring for Squarespace."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract key information
    title = soup.find('title').text if soup.find('title') else "Budget Report"
    
    # Extract department name from header
    header_h1 = soup.find('h1')
    header_h2 = soup.find('h2')
    
    dept_name = header_h2.text if header_h2 else "Department"
    budget_title = header_h1.text if header_h1 else "Budget Report"
    
    # Extract description
    dept_desc = soup.find('div', class_='dept-description')
    description = ""
    if dept_desc:
        desc_p = dept_desc.find('p')
        if desc_p:
            description = desc_p.text
    
    # Extract budget cards data
    budget_cards = soup.find_all('div', class_='budget-card')
    cards_data = []
    for card in budget_cards:
        amount_elem = card.find('div', class_='budget-amount')
        label_elem = card.find('div', class_='budget-label')
        if amount_elem and label_elem:
            cards_data.append({
                'amount': amount_elem.text,
                'label': label_elem.text
            })
    
    # Extract table data
    table = soup.find('table', class_='budget-table')
    table_rows = []
    if table:
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    is_total = 'total-row' in row.get('class', [])
                    table_rows.append({
                        'label': cells[0].text.strip(),
                        'amount': cells[1].text.strip(),
                        'is_total': is_total
                    })
    
    return {
        'title': title,
        'dept_name': dept_name,
        'budget_title': budget_title,
        'description': description,
        'cards_data': cards_data,
        'table_rows': table_rows
    }

def generate_squarespace_html(data, dept_code):
    """Generate Squarespace-compatible HTML code block."""
    
    template = f"""<!-- Squarespace Code Block Version - {data['dept_name']} Budget Report -->
<div class="budget-report-container">
    <style>
        .budget-report-container {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        
        .budget-report-container .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }}
        
        .budget-report-container .header h1 {{
            color: #2c3e50;
            margin: 0;
            font-size: 2.2em;
        }}
        
        .budget-report-container .header h2 {{
            color: #7f8c8d;
            margin: 10px 0 0 0;
            font-weight: normal;
        }}
        
        .budget-report-container .budget-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .budget-report-container .budget-table th {{
            background-color: #3498db;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: bold;
        }}
        
        .budget-report-container .budget-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ecf0f1;
        }}
        
        .budget-report-container .budget-table tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        .budget-report-container .budget-table tr:hover {{
            background-color: #e8f4fd;
        }}
        
        .budget-report-container .amount {{
            text-align: right;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .budget-report-container .total-row {{
            background-color: #3498db !important;
            color: white;
            font-weight: bold;
        }}
        
        .budget-report-container .total-row td {{
            border-bottom: none;
        }}
        
        .budget-report-container .summary-stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin: 30px 0;
            flex-wrap: wrap;
        }}
        
        .budget-report-container .budget-card {{
            background-color: #fff;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            text-align: center;
            flex: 0 1 300px;
            transition: transform 0.2s, box-shadow 0.2s;
            min-width: 200px;
        }}
        
        .budget-report-container .budget-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }}
        
        .budget-report-container .budget-amount {{
            font-size: 2.2em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 8px;
        }}
        
        .budget-report-container .budget-label {{
            color: #7f8c8d;
            font-size: 1.1em;
            font-weight: 500;
        }}
        
        .budget-report-container .dept-description {{
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 20px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }}
        
        .budget-report-container .dept-description h3 {{
            color: #2c3e50;
            margin-top: 0;
            margin-bottom: 10px;
            font-size: 1.4em;
        }}
        
        .budget-report-container .dept-description p {{
            margin: 0;
            line-height: 1.6;
            color: #4a5568;
        }}
        
        .budget-report-container .note-section {{
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }}
        
        @media (max-width: 768px) {{
            .budget-report-container .summary-stats {{
                flex-direction: column;
                align-items: center;
            }}
            
            .budget-report-container .budget-card {{
                width: 100%;
                max-width: 300px;
            }}
        }}
    </style>
    
    <div class="header">
        <h1>{data['budget_title']}</h1>
        <h2>{data['dept_name']}</h2>
    </div>"""

    if data['description']:
        template += f"""
    
    <div class="dept-description">
        <h3>About {data['dept_name']}</h3>
        <p>{data['description']}</p>
    </div>"""

    if data['cards_data']:
        template += """
    
    <div class="summary-stats">"""
        for card in data['cards_data']:
            template += f"""
        <div class="budget-card">
            <div class="budget-amount">{card['amount']}</div>
            <div class="budget-label">{card['label']}</div>
        </div>"""
        template += """
    </div>"""

    if data['table_rows']:
        # Find the main budget header
        main_header = None
        for row in data['table_rows']:
            if 'FY26' in row['label'] and 'Budget' in row['label']:
                main_header = row
                break
        
        if main_header:
            template += f"""
    
    <table class="budget-table">
        <thead>
            <tr>
                <th>{main_header['label']}</th>
                <th class="amount">{main_header['amount']}</th>
            </tr>
        </thead>
        <tbody>"""
            
            # Add non-total rows
            for row in data['table_rows']:
                if row != main_header and not row['is_total']:
                    template += f"""
            <tr>
                <td>{row['label']}</td>
                <td class="amount">{row['amount']}</td>
            </tr>"""
            
            template += """
        </tbody>
    </table>"""

    template += """
    
    <div class="note-section">
        <p><strong>Note:</strong> Charts and detailed visualizations are available in the full PDF report.</p>
        <p style="font-size: 0.9em; color: #7f8c8d;">Generated from Hawaii State Budget FY 2026 Post-Veto Data</p>
    </div>
</div>"""

    return template

def convert_html_file(input_file, output_dir):
    """Convert a single HTML file to Squarespace format."""
    with open(input_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Extract department code from filename
    filename = Path(input_file).stem
    dept_code = filename.split('_')[0].upper()
    
    # Extract content
    data = extract_content_from_html(html_content)
    
    # Generate Squarespace HTML
    squarespace_html = generate_squarespace_html(data, dept_code)
    
    # Write output file
    output_file = Path(output_dir) / f"{dept_code.lower()}_squarespace.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(squarespace_html)
    
    return output_file

def create_navigation_index(output_dir, converted_files):
    """Create a navigation index for all departments."""
    
    # Department name mapping
    dept_names = {
        'AGR': 'Department of Agriculture',
        'AGS': 'Department of Accounting and General Services',
        'ATG': 'Department of the Attorney General',
        'BED': 'Department of Business, Economic Development and Tourism',
        'BUF': 'Department of Budget and Finance',
        'CCA': 'Department of Commerce and Consumer Affairs',
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
        'LBR': 'Department of Labor and Industrial Relations',
        'LNR': 'Department of Land and Natural Resources',
        'LTG': 'Office of the Lieutenant Governor',
        'P': 'General Administration',
        'PSD': 'Department of Corrections and Rehabilitation',
        'TAX': 'Department of Taxation',
        'TRN': 'Department of Transportation',
        'UOH': 'University of Hawaii'
    }
    
    index_html = """<!-- Squarespace Navigation Index for Budget Reports -->
<div class="budget-index-container">
    <style>
        .budget-index-container {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }
        
        .budget-index-container .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: linear-gradient(135deg, #3498db, #2c3e50);
            color: white;
            border-radius: 12px;
        }
        
        .budget-index-container .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        
        .budget-index-container .header p {
            margin: 10px 0 0 0;
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .budget-index-container .dept-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .budget-index-container .dept-card {
            background: white;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            padding: 20px;
            transition: all 0.3s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .budget-index-container .dept-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border-color: #3498db;
        }
        
        .budget-index-container .dept-code {
            font-size: 1.2em;
            font-weight: bold;
            color: #3498db;
            margin-bottom: 8px;
        }
        
        .budget-index-container .dept-name {
            color: #2c3e50;
            font-size: 1em;
            line-height: 1.4;
        }
        
        .budget-index-container .instructions {
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 20px;
            margin: 30px 0;
            border-radius: 0 8px 8px 0;
        }
        
        .budget-index-container .instructions h3 {
            color: #2c3e50;
            margin-top: 0;
        }
    </style>
    
    <div class="header">
        <h1>Hawaii State Budget FY 2026</h1>
        <p>Departmental Budget Reports - Post-Veto</p>
    </div>
    
    <div class="instructions">
        <h3>How to Use These Reports</h3>
        <p>Each department has its own detailed budget report. Click on any department below to view its budget breakdown, including operating expenses, capital improvements, and special appropriations.</p>
    </div>
    
    <div class="dept-grid">"""
    
    # Sort departments by code
    sorted_files = sorted(converted_files, key=lambda x: Path(x).stem.split('_')[0])
    
    for file_path in sorted_files:
        dept_code = Path(file_path).stem.split('_')[0].upper()
        dept_name = dept_names.get(dept_code, f"Department {dept_code}")
        
        index_html += f"""
        <div class="dept-card">
            <div class="dept-code">{dept_code}</div>
            <div class="dept-name">{dept_name}</div>
        </div>"""
    
    index_html += """
    </div>
    
    <div style="text-align: center; margin-top: 40px; padding: 20px; background-color: #f8f9fa; border-radius: 8px;">
        <p style="color: #7f8c8d; margin: 0;">Generated from Hawaii State Budget FY 2026 Post-Veto Data</p>
        <p style="color: #7f8c8d; margin: 5px 0 0 0; font-size: 0.9em;">Data source: HB300 CD1 - State of Hawaii Operating and Capital Budget</p>
    </div>
</div>"""
    
    # Write index file
    index_file = Path(output_dir) / "index_squarespace.html"
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    return index_file

def main():
    parser = argparse.ArgumentParser(description='Convert HTML budget reports to Squarespace format')
    parser.add_argument('input_dir', help='Directory containing HTML reports')
    parser.add_argument('--output-dir', default='squarespace_conversion', help='Output directory')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Find all HTML files
    html_files = list(input_dir.glob('*_budget_report.html'))
    
    if not html_files:
        print(f"No HTML budget report files found in {input_dir}")
        return
    
    print(f"Found {len(html_files)} HTML files to convert")
    
    converted_files = []
    
    # Convert each file
    for html_file in html_files:
        try:
            output_file = convert_html_file(html_file, output_dir)
            converted_files.append(output_file)
            print(f"Converted: {html_file.name} -> {output_file.name}")
        except Exception as e:
            print(f"Error converting {html_file.name}: {e}")
    
    # Create navigation index
    if converted_files:
        index_file = create_navigation_index(output_dir, converted_files)
        print(f"Created navigation index: {index_file.name}")
    
    print(f"\nConversion complete! {len(converted_files)} files converted.")
    print(f"Output directory: {output_dir}")
    print("\nNext steps for Squarespace:")
    print("1. Create a new page for each department")
    print("2. Add a Code Block to each page")
    print("3. Copy and paste the HTML content from each converted file")
    print("4. Use the index file content for your main navigation page")

if __name__ == "__main__":
    main()
