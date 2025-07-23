#!/usr/bin/env python3
import re

# Test the indented amount pattern
pattern = re.compile(
    r'^([A-Z]{3})[\s\u00A0]+([\d,]+)([A-Z]?)(?:[\s\u00A0]+([\d,]+)([A-Z]?))?[\s\u00A0]*$',
    re.IGNORECASE
)

# Read the problematic line from the file
with open('data/raw/HB 300 CD 1.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 403 (0-indexed would be 402)
test_line = lines[402]
print(f"Original line: {repr(test_line)}")
print(f"Stripped line: {repr(test_line.strip())}")

# Test the pattern
match = pattern.match(test_line.strip())
if match:
    print("Pattern matched!")
    print(f"Groups: {match.groups()}")
else:
    print("Pattern did not match")
    
# Also test with a simpler pattern
simple_pattern = re.compile(r'^[\s\u00A0]+([A-Z]+)[\s\u00A0]+([0-9,]+)([A-Z]?).*$', re.IGNORECASE)
simple_match = simple_pattern.match(test_line.strip())
if simple_match:
    print("Simple pattern matched!")
    print(f"Simple groups: {simple_match.groups()}")
else:
    print("Simple pattern did not match")
