#!/usr/bin/env python3
"""
Parse department descriptions from text file and generate a JSON file.
"""

import json
import re
from pathlib import Path

def parse_descriptions(text_file: str) -> dict:
    """
    Parse department descriptions from text file.
    
    Args:
        text_file: Path to the text file containing department descriptions
        
    Returns:
        Dictionary mapping department codes to their descriptions
    """
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match department headers and their descriptions
    # Looks for "The Department of... (CODE)" followed by the description
    pattern = r"The Department of ([^(]+)\(([A-Z]+)\)\s*(.*?)(?=\n\s*The Department of |\Z)"
    
    # Find all matches
    matches = re.findall(pattern, content, re.DOTALL)
    
    # Create dictionary with department codes as keys
    descriptions = {}
    for dept_name, code, desc in matches:
        # Clean up the description text
        desc = desc.strip()
        desc = re.sub(r'\s+', ' ', desc)  # Replace multiple whitespace with single space
        descriptions[code.strip()] = {
            'name': f"The Department of {dept_name.strip()}",
            'description': desc
        }
    
    # Add any missing departments that might be in the data but not in the descriptions
    additional_departments = {
        'CCH': {
            'name': 'City and County of Honolulu',
            'description': 'The City and County of Honolulu is the local government entity for the island of Oʻahu.'
        },
        'COH': {
            'name': 'County of Hawaiʻi',
            'description': 'The County of Hawaiʻi is the local government entity for the island of Hawaiʻi.'
        },
        'COK': {
            'name': 'County of Kauaʻi',
            'description': 'The County of Kauaʻi is the local government entity for the island of Kauaʻi.'
        },
        'P': {
            'name': 'Legislature',
            'description': 'The Hawaiʻi State Legislature is the state legislature of the U.S. state of Hawaiʻi.'
        },
        'LAW': {
            'name': 'Department of Law Enforcement',
            'description': 'The Department of Law Enforcement consolidates criminal law enforcement and investigation functions.'
        },
        'PSD': {
            'name': 'Department of Corrections and Rehabilitation',
            'description': 'The Department of Corrections and Rehabilitation oversees Hawaiʻi\'s state correctional facilities and related programs.'
        }
    }
    
    # Add any additional departments that aren't already in the descriptions
    for code, dept_info in additional_departments.items():
        if code not in descriptions:
            descriptions[code] = dept_info
    
    return descriptions

def save_descriptions(descriptions: dict, output_file: str):
    """
    Save department descriptions to a JSON file.
    
    Args:
        descriptions: Dictionary of department descriptions
        output_file: Path to the output JSON file
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save descriptions to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(descriptions, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(descriptions)} department descriptions to {output_file}")

if __name__ == "__main__":
    # Paths
    input_file = "data/raw/Department Descriptions.txt"
    output_file = "data/processed/department_descriptions.json"
    
    # Parse and save descriptions
    descriptions = parse_descriptions(input_file)
    save_descriptions(descriptions, output_file)
    
    # Print summary
    print(f"Processed {len(descriptions)} department descriptions.")
    print("Sample department:")
    sample_code = next(iter(descriptions))
    print(f"{sample_code}: {descriptions[sample_code]['name']}")
    print(f"{descriptions[sample_code]['description'][:100]}...")
