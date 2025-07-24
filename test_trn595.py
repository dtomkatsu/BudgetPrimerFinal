#!/usr/bin/env python3
import re

# Read the file and find TRN595 context
with open('data/raw/HB300_CD1_better.txt', 'r') as f:
    lines = f.readlines()

# Find the TRN595 program line
for i, line in enumerate(lines):
    if 'TRN595' in line and 'HIGHWAYS ADMINISTRATION' in line:
        print(f"Found TRN595 at line {i+1}: {repr(line)}")
        
        # Check the next few lines for OPERATING
        for j in range(1, 10):
            if i+j < len(lines):
                next_line = lines[i+j]
                print(f"Line {i+j+1}: {repr(next_line)}")
                
                if 'OPERATING' in next_line:
                    print(f"  -> OPERATING line found!")
                    
                    # Test our regex pattern
                    pattern = r'^\s*OPERATING\s+([A-Z]+)\s+([\d,]+)([A-Z])\s+([A-Z])\s*$'
                    match = re.search(pattern, next_line)
                    if match:
                        print(f"  -> Pattern matched! Groups: {match.groups()}")
                    else:
                        print(f"  -> Pattern did not match")
                    break
        break
