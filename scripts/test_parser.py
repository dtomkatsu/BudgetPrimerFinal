#!/usr/bin/env python3
"""
Test script to count allocations extracted by the FastBudgetParser.
"""
import sys
import logging
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from budgetprimer.parsers import FastBudgetParser

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # Path to the HB 300 file
    hb300_path = project_root / 'data' / 'raw' / 'HB 300 CD 1.txt'
    
    if not hb300_path.exists():
        print(f"Error: File not found: {hb300_path}")
        return 1
    
    print(f"Parsing {hb300_path}...")
    
    # Create the parser
    parser = FastBudgetParser()
    
    try:
        # Parse the file
        allocations = parser.parse(str(hb300_path))
        
        # Print summary
        print(f"\nParsing Complete!")
        print(f"Total allocations extracted: {len(allocations):,}")
        
        # Count by section
        sections = {}
        for alloc in allocations:
            sections[alloc.section] = sections.get(alloc.section, 0) + 1
        
        print("\nAllocations by section:")
        for section, count in sections.items():
            print(f"- {section.value}: {count:,}")
        
        # Count by fund type
        fund_types = {}
        for alloc in allocations:
            fund_types[alloc.fund_type] = fund_types.get(alloc.fund_type, 0) + 1
        
        print("\nAllocations by fund type:")
        for fund_type, count in sorted(fund_types.items(), key=lambda x: x[1], reverse=True):
            print(f"- {fund_type}: {count:,}")
        
        return 0
        
    except Exception as e:
        print(f"Error parsing file: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
