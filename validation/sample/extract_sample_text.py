#!/usr/bin/env python3
"""
Extract text from the sample budget PDF to create a text file for parser testing.
Uses pdfplumber to maintain the same extraction method as the real budget.
"""

import pdfplumber
from pathlib import Path
import sys

def extract_pdf_text(pdf_path: str, output_path: str):
    """Extract text from PDF using pdfplumber."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text_content = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"Processing page {page_num}...")
                
                # Extract text from the page
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
                    text_content.append("\n" + "="*50 + f" PAGE {page_num} END " + "="*50 + "\n")
            
            # Write to output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(text_content))
            
            print(f"Text extracted successfully to: {output_path}")
            return True
            
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return False

if __name__ == "__main__":
    sample_dir = Path(__file__).parent
    pdf_path = sample_dir / "sample_budget.pdf"
    txt_path = sample_dir / "sample_budget.txt"
    
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        print("Run generate_sample_budget.py first to create the PDF.")
        sys.exit(1)
    
    success = extract_pdf_text(str(pdf_path), str(txt_path))
    if success:
        print(f"Sample budget text file created: {txt_path}")
    else:
        sys.exit(1)
