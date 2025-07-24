#!/usr/bin/env python3
"""
Extract text from PDF budget document.
Creates a clean text file that preserves the original formatting.
"""
import sys
from pathlib import Path
import PyPDF2

def extract_pdf_text(pdf_path, output_path):
    """Extract text from PDF and save to text file."""
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            print(f"Processing PDF with {len(pdf_reader.pages)} pages...")
            
            all_text = []
            for page_num, page in enumerate(pdf_reader.pages, 1):
                print(f"Extracting page {page_num}...")
                text = page.extract_text()
                if text.strip():
                    all_text.append(text)
            
            # Join all pages with page breaks
            full_text = '\n\n'.join(all_text)
            
            # Save to output file
            with open(output_path, 'w', encoding='utf-8') as output_file:
                output_file.write(full_text)
            
            print(f"Successfully extracted text to {output_path}")
            print(f"Total characters: {len(full_text)}")
            
            # Show a preview
            lines = full_text.split('\n')[:10]
            print("\nFirst 10 lines preview:")
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
    
    extract_pdf_text(pdf_path, output_path)

if __name__ == "__main__":
    main()
