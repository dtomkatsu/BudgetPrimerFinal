#!/usr/bin/env python3
import sys
import re
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Read the file and simulate the parser logic
with open('data/raw/HB300_CD1_better.txt', 'r') as f:
    content = f.read()

# Normalize line endings and replace non-breaking spaces
content = content.replace('\r\n', '\n').replace('\r', '\n')
content = content.replace('\u00A0', ' ')  # Replace non-breaking spaces

lines = content.split('\n')
current_program = None
current_program_name = None

# Compile regex patterns
program_pattern = re.compile(r'^\d+\.\s+([A-Z]+\d+)\s*-\s*(.+)$')

for i, line in enumerate(lines):
    original_line = line
    line = line.strip()
    
    if not line:
        continue
    
    # Check for program header
    program_match = program_pattern.match(line)
    if program_match:
        program_id = program_match.group(1).strip()
        program_name = program_match.group(2).strip()
        current_program = program_id
        current_program_name = program_name
        
        if program_id == 'TRN595':
            print(f"Line {i+1}: Found TRN595 program: '{program_name}'")
            print(f"  Current program set to: {current_program}")
        continue
    
    # Check for OPERATING line
    if 'OPERATING' in original_line and '20,000,000A' in original_line:
        print(f"\nLine {i+1}: Found 20,000,000A OPERATING line")
        print(f"  Current program: {current_program}")
        print(f"  Line content: {repr(original_line)}")
        
        # Test the pattern
        pdf_pattern = r'^\s*OPERATING\s+([A-Z]+)\s+([\d,]+)([A-Z])\s+([A-Z])\s*$'
        match = re.search(pdf_pattern, original_line)
        if match:
            print(f"  Pattern matched! Groups: {match.groups()}")
        else:
            print(f"  Pattern did not match")
        break
