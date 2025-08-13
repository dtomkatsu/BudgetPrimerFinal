#!/usr/bin/env python3
"""
Generate a sample budget PDF with the same format as the real Hawaii budget.
Easily customizable by editing the SAMPLE_DATA dictionary below.
"""

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from pathlib import Path
from typing import Dict, List, Any

# ====================================================
# CUSTOMIZE THIS SECTION TO EDIT THE BUDGET DATA
# ====================================================

# Main configuration - edit these values to customize the output
SAMPLE_DATA = {
    # Document title and header info
    "title": "HOUSE OF REPRESENTATIVES",
    "bill_number": "H.B. NO. 300",
    "subtitle": "SAMPLE BUDGET FOR PARSER VALIDATION",
    "fiscal_year": "FY2026",
    
    # Fund type definitions
    "fund_definitions": [
        "A  general funds",
        "B  special funds",
        "C  general obligation bond fund",
        "N  federal funds",
        "P  other federal funds",
        "T  trust funds",
        "W  revolving funds"
    ],
    
    # Department data
    "departments": [
        {
            "code": "AGR",
            "name": "AGRICULTURE",
            "programs": [
                {
                    "number": 1,
                    "code": "AGR100",
                    "name": "AGRICULTURAL LOAN DIVISION",
                    "positions": {"*": 5.0},  # Permanent positions
                    "allocations": [
                        {"section": "OPERATING", "fund_type": "A", "amount": 1_500_000},
                        {"section": "OPERATING", "fund_type": "B", "amount": 250_000}
                    ]
                },
                {
                    "number": 2,
                    "code": "AGR150",
                    "name": "PLANT AND ANIMAL HEALTH",
                    "positions": {"*": 12.0, "#": 2.0},  # Permanent and temporary positions
                    "allocations": [
                        {"section": "OPERATING", "fund_type": "A", "amount": 2_800_000},
                        {"section": "OPERATING", "fund_type": "N", "amount": 450_000},
                        {"section": "INVESTMENT CAPITAL", "fund_type": "C", "amount": 5_000_000}
                    ]
                }
            ]
        },
        {
            "code": "BED",
            "name": "BUSINESS AND ECONOMIC DEVELOPMENT",
            "programs": [
                {
                    "number": 3,
                    "code": "BED100",
                    "name": "STRATEGIC MARKETING",
                    "positions": {"*": 10.0},
                    "allocations": [
                        {"section": "OPERATING", "fund_type": "A", "amount": 3_200_000},
                        {"section": "OPERATING", "fund_type": "W", "amount": 1_800_000}
                    ]
                },
                {
                    "number": 4,
                    "code": "BED120",
                    "name": "ENERGY OFFICE",
                    "positions": {"*": 8.0},
                    "allocations": [
                        {"section": "OPERATING", "fund_type": "A", "amount": 2_100_000},
                        {"section": "OPERATING", "fund_type": "T", "amount": 750_000},
                        {"section": "INVESTMENT CAPITAL", "fund_type": "C", "amount": 15_000_000}
                    ]
                }
            ]
        },
        {
            "code": "LBR",
            "name": "LABOR AND INDUSTRIAL RELATIONS",
            "programs": [
                {
                    "number": 5,
                    "code": "LBR111",
                    "name": "WORKFORCE DEVELOPMENT",
                    "positions": {"*": 15.0},
                    "allocations": [
                        {"section": "OPERATING", "fund_type": "A", "amount": 4_500_000},
                        {"section": "OPERATING", "fund_type": "N", "amount": 2_200_000}
                    ]
                },
                {
                    "number": 6,
                    "code": "LBR171",
                    "name": "UNEMPLOYMENT INSURANCE",
                    "positions": {"*": 25.0},
                    "allocations": [
                        {"section": "OPERATING", "fund_type": "A", "amount": 1_800_000},
                        {"section": "OPERATING", "fund_type": "T", "amount": 12_000_000}
                    ]
                }
            ]
        },
        {
            "code": "TRN",
            "name": "TRANSPORTATION",
            "programs": [
                {
                    "number": 7,
                    "code": "TRN595",
                    "name": "HIGHWAYS ADMINISTRATION",
                    "positions": {},
                    "allocations": [
                        {"section": "OPERATING", "fund_type": "A", "amount": 20_000_000},
                        {"section": "OPERATING", "fund_type": "B", "amount": 229_186_637},
                        {"section": "INVESTMENT CAPITAL", "fund_type": "C", "amount": 500_000_000}
                    ]
                },
                {
                    "number": 8,
                    "code": "TRN195",
                    "name": "AIRPORTS ADMINISTRATION",
                    "positions": {"*": 50.0},
                    "allocations": [
                        {"section": "OPERATING", "fund_type": "B", "amount": 75_000_000},
                        {"section": "INVESTMENT CAPITAL", "fund_type": "C", "amount": 200_000_000}
                    ]
                }
            ]
        },
        {
            "code": "HMS",
            "name": "HUMAN SERVICES",
            "programs": [
                {
                    "number": 9,
                    "code": "HMS401",
                    "name": "HEALTH CARE PAYMENTS",
                    "positions": {},
                    "allocations": [
                        {"section": "OPERATING", "fund_type": "A", "amount": 1_031_467_000},
                        {"section": "OPERATING", "fund_type": "A", "amount": 2_291_497_000}
                    ]
                },
                {
                    "number": 10,
                    "code": "HMS230",
                    "name": "BENEFIT, EMPLOYMENT AND SUPPORT SERVICES",
                    "positions": {"*": 80.0},
                    "allocations": [
                        {"section": "OPERATING", "fund_type": "A", "amount": 45_000_000},
                        {"section": "OPERATING", "fund_type": "N", "amount": 25_000_000},
                        {"section": "INVESTMENT CAPITAL", "fund_type": "C", "amount": 10_000_000}
                    ]
                }
            ]
        }
    ]
}

# ====================================================
# END OF CUSTOMIZATION SECTION
# ====================================================

def format_currency(amount: int) -> str:
    """Format a number as currency with commas."""
    return f"{amount:,}"

def format_positions(positions: Dict[str, float]) -> List[str]:
    """Format position counts into lines."""
    if not positions:
        return []
    
    # Format each position type (e.g., 5.00*)
    position_lines = []
    for pos_type, count in positions.items():
        position_lines.append(f"{count:>54.2f}{pos_type}         {count:>6.2f}{pos_type}")
    
    return position_lines

def format_allocation(dept_code: str, alloc: Dict[str, Any]) -> str:
    """Format a single allocation line."""
    section = alloc["section"]
    fund_type = alloc["fund_type"]
    amount = format_currency(alloc["amount"])
    
    # For capital improvements, show reduced amount (80% of original)
    if section == "INVESTMENT CAPITAL":
        reduced_amount = int(alloc["amount"] * 0.8)
        reduced_str = format_currency(reduced_amount)
        return f"{section:25} {dept_code:10} {amount:>12}{fund_type}   {reduced_str:>12}{fund_type}"
    else:
        return f"{section:25} {dept_code:10} {amount:>12}{fund_type}     {amount:>12}{fund_type}"

def create_sample_budget_pdf(output_path: str, data: Dict[str, Any]):
    """Create a sample budget PDF with the given data."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6,
        alignment=TA_LEFT
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Courier',
        spaceAfter=3,
        alignment=TA_LEFT
    )
    
    # Build the document content
    story = []
    
    # Title page
    story.append(Paragraph(data["title"], title_style))
    story.append(Paragraph(data["bill_number"], title_style))
    story.append(Paragraph(data["subtitle"], title_style))
    story.append(Spacer(1, 0.5*inch))
    
    # Fund definitions
    story.append(Paragraph("FUND TYPE DEFINITIONS:", header_style))
    for fund_def in data["fund_definitions"]:
        story.append(Paragraph(fund_def, normal_style))
    
    story.append(PageBreak())
    
    # Program appropriations header
    story.append(Paragraph("PART II. PROGRAM APPROPRIATIONS", header_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Process each department
    for i, dept in enumerate(data["departments"]):
        # Department header (A., B., C., etc.)
        dept_letter = chr(65 + i)  # A, B, C, ...
        story.append(Paragraph(f"{dept_letter}. {dept['name']}", header_style))
        
        # Process each program in the department
        for program in dept["programs"]:
            # Program header
            program_header = f"{program['number']}.   {program['code']} - {program['name']}"
            story.append(Paragraph(program_header, normal_style))
            
            # Position counts
            for line in format_positions(program["positions"]):
                story.append(Paragraph(line, normal_style))
            
            # Allocations
            for alloc in program["allocations"]:
                story.append(Paragraph(format_allocation(dept['code'], alloc), normal_style))
            
            # Add spacing after each program
            story.append(Paragraph("", normal_style))
        
        # Add spacing between departments
        if i < len(data["departments"]) - 1:
            story.append(Paragraph("", normal_style))
    
    # Calculate and add summary totals
    story.append(Paragraph("SUMMARY TOTALS:", normal_style))
    
    # Calculate totals
    totals = calculate_expected_totals(data)
    
    # Format and add totals
    op_total = format_currency(totals['totals']['operating'])
    cap_total = format_currency(totals['totals']['capital'])
    grand_total = format_currency(totals['totals']['grand'])
    
    story.append(Paragraph(f"Operating Budget Total: ${op_total}", normal_style))
    story.append(Paragraph(f"Capital Budget Total: ${cap_total}", normal_style))
    story.append(Paragraph(f"Grand Total: ${grand_total}", normal_style))
    
    # Build the PDF
    doc.build(story)
    print(f"Sample budget PDF created: {output_path}")

def calculate_expected_totals(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate expected totals from the budget data."""
    expected = {
        'operating': {},
        'capital': {}
    }
    
    # Initialize all fund types to zero
    for fund_type in 'ABNPTW':
        expected['operating'][fund_type] = 0
    expected['capital']['C'] = 0
    
    # Calculate totals
    for dept in data["departments"]:
        for program in dept["programs"]:
            for alloc in program["allocations"]:
                section = 'capital' if 'CAPITAL' in alloc['section'] else 'operating'
                fund_type = alloc['fund_type']
                amount = alloc['amount']
                
                if fund_type not in expected[section]:
                    expected[section][fund_type] = 0
                expected[section][fund_type] += amount
    
    # Calculate section totals
    operating_total = sum(expected['operating'].values())
    capital_total = sum(expected['capital'].values())
    grand_total = operating_total + capital_total
    
    expected['totals'] = {
        'operating': operating_total,
        'capital': capital_total,
        'grand': grand_total
    }
    
    return expected

def main():
    """Main function to generate the sample budget."""
    output_path = Path(__file__).parent / "sample_budget.pdf"
    create_sample_budget_pdf(str(output_path), SAMPLE_DATA)
    
    # Save expected totals for validation
    totals = calculate_expected_totals(SAMPLE_DATA)
    import json
    with open(Path(__file__).parent / "expected_totals.json", 'w') as f:
        json.dump(totals, f, indent=2)
    
    print(f"Expected totals saved to: {Path(__file__).parent / 'expected_totals.json'}")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    # Create sample directory if it doesn't exist
    sample_dir = Path(__file__).parent
    sample_dir.mkdir(exist_ok=True)
    
    # Generate the sample budget PDF
    pdf_path = sample_dir / "sample_budget.pdf"
    create_sample_budget_pdf(str(pdf_path))
    
    # Save expected totals
    import json
    expected = create_expected_totals()
    with open(sample_dir / "expected_totals.json", 'w') as f:
        json.dump(expected, f, indent=2)
    
    print(f"Expected totals saved to: {sample_dir / 'expected_totals.json'}")
    print(f"Operating total: ${expected['totals']['operating']:,}")
    print(f"Capital total: ${expected['totals']['capital']:,}")
    print(f"Grand total: ${expected['totals']['grand']:,}")
