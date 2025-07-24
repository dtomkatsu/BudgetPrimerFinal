#!/usr/bin/env python3
"""
Fix line breaks in Hawaii budget document.
Creates a new file with '_fixed' suffix, preserving the original.
"""
import re
import sys
from pathlib import Path

def is_continuation(prev_line, current_line):
    """Check if current line is a continuation of the previous line."""
    # If previous line ends with a word character and current line starts with one
    if not prev_line or not current_line:
        return False
    
    # Check for word continuation (like "ADMIN" -> "ISTRATION")
    if (re.search(r'[A-Za-z0-9]\s*$', prev_line) and 
        re.match(r'^\s*[A-Za-z0-9]', current_line)):
        return True
    
    # Check for number patterns that should be together
    if (re.search(r'\d+[,\d]*[A-Z]?\s*$', prev_line) and 
        re.match(r'^\s*\d+[,\d]*[A-Z]?\b', current_line)):
        return True
    
    return False

def fix_line_breaks(content):
    """Fix line breaks in the content."""
    lines = content.splitlines()
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        current_line = lines[i].strip()
        
        # Skip empty lines at the start
        if not current_line and not fixed_lines:
            i += 1
            continue
            
        # If this is the first line, just add it
        if not fixed_lines:
            fixed_lines.append(current_line)
            i += 1
            continue
            
        prev_line = fixed_lines[-1]
        
        # Check if this line should be joined with the previous one
        if is_continuation(prev_line, current_line):
            # Join with a space if the previous line doesn't end with a space
            separator = '' if prev_line.endswith(' ') else ' '
            fixed_lines[-1] = prev_line + separator + current_line.strip()
        else:
            # Keep as separate lines
            fixed_lines.append(current_line)
            
        i += 1
    
    return '\n'.join(fixed_lines)

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input_file>")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: File '{input_path}' not found")
        sys.exit(1)
    
    # Read the input file
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix line breaks
    fixed_content = fix_line_breaks(content)
    
    # Create output filename
    output_path = input_path.with_stem(f"{input_path.stem}_fixed")
    
    # Show preview
    print(f"Original first 5 lines:")
    print('\n'.join(content.splitlines()[:5]))
    print("\nFixed first 5 lines:")
    print('\n'.join(fixed_content.splitlines()[:5]))
    
    # Ask for confirmation
    response = input(f"\nCreate {output_path}? [y/N] ").strip().lower()
    if response == 'y':
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print(f"Created {output_path}")
    else:
        print("No changes made.")

if __name__ == "__main__":
    main()
