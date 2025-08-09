#!/usr/bin/env python3
"""
Generate a sample budget PDF with the same format as the real Hawaii budget.
This creates a controlled test case for validating the budget parser.

The sample budget includes:
- Multiple departments (AGR, BED, LBR, TRN, HMS)
- Both Operating and Capital Improvement sections
- Various fund types (A, B, N, P, T, W, C)
- Position ceilings and multi-line entries
- Known totals for validation
"""

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import os
from pathlib import Path

def create_sample_budget_pdf(output_path: str):
    """Create a sample budget PDF matching the real format."""
    
    # Create the PDF document
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
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
    story.append(Paragraph("HOUSE OF REPRESENTATIVES", title_style))
    story.append(Paragraph("H.B. NO. 300", title_style))
    story.append(Paragraph("SAMPLE BUDGET FOR PARSER VALIDATION", title_style))
    story.append(Spacer(1, 0.5*inch))
    
    # Fund definitions
    story.append(Paragraph("FUND TYPE DEFINITIONS:", header_style))
    fund_defs = [
        "A  general funds",
        "B  special funds", 
        "C  general obligation bond fund",
        "N  federal funds",
        "P  other federal funds",
        "T  trust funds",
        "W  revolving funds"
    ]
    for fund_def in fund_defs:
        story.append(Paragraph(fund_def, normal_style))
    
    story.append(PageBreak())
    
    # Sample budget entries
    story.append(Paragraph("PART II. PROGRAM APPROPRIATIONS", header_style))
    story.append(Spacer(1, 0.2*inch))
    
    # A. AGRICULTURE
    story.append(Paragraph("A. AGRICULTURE", header_style))
    
    budget_lines = [
        "1.   AGR100 - AGRICULTURAL LOAN DIVISION",
        "                                                  5.00*          5.00*",
        "OPERATING                         AGR        1,500,000A     1,500,000A",
        "                                  AGR          250,000B       250,000B",
        "",
        "2.   AGR150 - PLANT AND ANIMAL HEALTH",
        "                                                 12.00*         12.00*",
        "                                                  2.00#          2.00#", 
        "OPERATING                         AGR        2,800,000A     2,800,000A",
        "                                  AGR          450,000N       450,000N",
        "INVESTMENT CAPITAL                AGR        5,000,000C     3,000,000C",
        "",
        "B. BUSINESS AND ECONOMIC DEVELOPMENT",
        "",
        "3.   BED100 - STRATEGIC MARKETING",
        "                                                 10.00*         10.00*",
        "OPERATING                         BED        3,200,000A     3,200,000A",
        "                                  BED        1,800,000W     1,800,000W",
        "",
        "4.   BED120 - ENERGY OFFICE",
        "                                                  8.00*          8.00*",
        "OPERATING                         BED        2,100,000A     2,100,000A",
        "                                  BED          750,000T       750,000T",
        "INVESTMENT CAPITAL                BED       15,000,000C    10,000,000C",
        "",
        "C. LABOR AND INDUSTRIAL RELATIONS",
        "",
        "5.   LBR111 - WORKFORCE DEVELOPMENT", 
        "                                                 15.00*         15.00*",
        "OPERATING                         LBR        4,500,000A     4,500,000A",
        "                                  LBR        2,200,000N     2,200,000N",
        "",
        "6.   LBR171 - UNEMPLOYMENT INSURANCE",
        "                                                 25.00*         25.00*",
        "OPERATING                         LBR        1,800,000A     1,800,000A",
        "                                  LBR       12,000,000T    12,000,000T",
        ""
    ]
    
    for line in budget_lines:
        story.append(Paragraph(line, normal_style))
    
    story.append(PageBreak())
    
    # Page 3 - Transportation and Human Services
    story.append(Paragraph("D. TRANSPORTATION", header_style))
    
    transport_lines = [
        "7.   TRN595 - HIGHWAYS ADMINISTRATION",
        "OPERATING                         TRN       20,000,000A    20,000,000A",
        "                                  TRN      229,186,637B   207,904,208B",
        "INVESTMENT CAPITAL                TRN      500,000,000C   400,000,000C",
        "",
        "8.   TRN195 - AIRPORTS ADMINISTRATION",
        "                                                 50.00*         50.00*",
        "OPERATING                         TRN       75,000,000B    75,000,000B",
        "INVESTMENT CAPITAL                TRN      200,000,000C   150,000,000C",
        "",
        "E. HUMAN SERVICES",
        "",
        "9.   HMS401 - HEALTH CARE PAYMENTS",
        "OPERATING                         HMS    1,031,467,000A 1,031,467,000A",
        "                                  HMS    2,291,497,000A 2,291,497,000A",
        "",
        "10.  HMS230 - BENEFIT, EMPLOYMENT AND SUPPORT SERVICES",
        "                                                 80.00*         80.00*",
        "OPERATING                         HMS       45,000,000A    45,000,000A",
        "                                  HMS       25,000,000N    25,000,000N",
        "INVESTMENT CAPITAL                HMS       10,000,000C     8,000,000C",
        "",
        "SUMMARY TOTALS:",
        "Operating Budget Total: $3,798,050,637",
        "Capital Budget Total: $1,386,000,000",
        "Grand Total: $5,184,050,637"
    ]
    
    for line in transport_lines:
        story.append(Paragraph(line, normal_style))
    
    # Build the PDF
    doc.build(story)
    print(f"Sample budget PDF created: {output_path}")

def create_expected_totals():
    """Create expected totals for validation."""
    expected = {
        'operating': {
            'A': 20000000 + 1500000 + 2800000 + 3200000 + 2100000 + 4500000 + 1800000 + 1031467000 + 2291497000 + 45000000,  # General funds
            'B': 250000 + 229186637 + 75000000,  # Special funds  
            'N': 450000 + 2200000 + 25000000,  # Federal funds
            'T': 750000 + 12000000,  # Trust funds
            'W': 1800000,  # Revolving funds
            'P': 0  # Other federal funds
        },
        'capital': {
            'C': 5000000 + 15000000 + 500000000 + 200000000 + 10000000  # Bond funds
        }
    }
    
    # Calculate totals
    operating_total = sum(expected['operating'].values())
    capital_total = sum(expected['capital'].values())
    grand_total = operating_total + capital_total
    
    expected['totals'] = {
        'operating': operating_total,
        'capital': capital_total, 
        'grand': grand_total
    }
    
    return expected

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
