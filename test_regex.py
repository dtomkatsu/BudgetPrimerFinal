#!/usr/bin/env python3
import re

# Test the regex pattern with the actual line
line = '               OPERATING                  TRN     20,000,000A        A              \n'
print(f"Testing line: {repr(line)}")

# Test different patterns
patterns = [
    r'^\s*OPERATING\s+([A-Z]+)\s+([\d,]+)([A-Z])\s+([A-Z])\s*$',
    r'OPERATING\s+([A-Z]+)\s+([\d,]+)([A-Z])\s+([A-Z])\s*',
    r'\s*OPERATING\s+([A-Z]+)\s+([\d,]+)([A-Z])\s+([A-Z])\s*',
    r'OPERATING.*?([A-Z]+)\s+([\d,]+)([A-Z])\s+([A-Z])',
]

for i, pattern in enumerate(patterns, 1):
    print(f"\nPattern {i}: {pattern}")
    match = re.search(pattern, line)
    if match:
        print(f"  MATCH! Groups: {match.groups()}")
    else:
        print(f"  No match")

# Test with stripped line
stripped_line = line.strip()
print(f"\nTesting stripped line: {repr(stripped_line)}")
for i, pattern in enumerate(patterns, 1):
    print(f"\nPattern {i}: {pattern}")
    match = re.search(pattern, stripped_line)
    if match:
        print(f"  MATCH! Groups: {match.groups()}")
    else:
        print(f"  No match")
