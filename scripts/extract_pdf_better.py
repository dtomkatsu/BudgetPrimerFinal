#!/usr/bin/env python3
"""
Extract text from PDF budget document using pdfplumber for better formatting.
"""
import sys
from pathlib import Path
import pdfplumber

def extract_pdf_text_better(pdf_path, output_path):
    """Extract text from PDF using pdfplumber for better layout preservation."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Processing PDF with {len(pdf.pages)} pages...")
            
            all_text = []
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"Extracting page {page_num}...")
                
                # Extract text with layout preservation
                text = page.extract_text(layout=True, x_tolerance=3, y_tolerance=3)
                
                if text and text.strip():
                    all_text.append(text)
            
            # Join all pages with page breaks
            full_text = '\n\n'.join(all_text)
            
            # Save to output file
            with open(output_path, 'w', encoding='utf-8') as output_file:
                output_file.write(full_text)
            
            print(f"Successfully extracted text to {output_path}")
            print(f"Total characters: {len(full_text)}")
            
            # Show a preview
            lines = full_text.split('\n')[:15]
            print("\nFirst 15 lines preview:")
            for i, line in enumerate(lines, 1):
                print(f"{i:2d}: {line}")
                
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_pdf> <output_txt>")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    
    if not pdf_path.exists():
        print(f"Error: PDF file '{pdf_path}' not found")
        sys.exit(1)
    
    extract_pdf_text_better(pdf_path, output_path)

if __name__ == "__main__":
    main()
