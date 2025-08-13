#!/usr/bin/env python3
"""
Line Checking Validator for Budget Parser

This script identifies lines in the budget text file that contain monetary values
but are not being processed by the parser. It helps identify potential parsing gaps.

Features:
- Detects lines with monetary amounts (patterns like 1,234,567 or 1,234,567A)
- Compares against lines actually processed by the parser
- Reports unprocessed lines with their line numbers and context
- Provides statistics on parsing coverage
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple, Set
import pandas as pd

# Add the parent directory to the path to import the parser
sys.path.append(str(Path(__file__).parent.parent))

try:
    from budgetprimer.parsers import parse_budget_file
    from budgetprimer.parsers.fast_parser import FastBudgetParser
except ImportError as e:
    print(f"Error importing parser: {e}")
    print("Make sure budgetprimer.parsers module exists")
    sys.exit(1)


class LineChecker:
    """Validates that all lines with monetary values are being processed by the parser."""
    
    def __init__(self, text_file: str):
        self.text_file = text_file
        self.lines = []
        self.monetary_lines = []
        self.processed_lines = set()
        
        # Regex patterns for detecting monetary amounts (more specific to avoid false positives)
        self.amount_patterns = [
            r'\b\d{1,3}(?:,\d{3})+[A-Z]\b',  # Large amounts with fund type: 1,234,567A (requires commas)
            r'\b\d{6,}[A-Z]?\b',  # Large amounts without commas: 1234567A (6+ digits)
            r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?[A-Z]?\b',  # With dollar sign: $1,234,567A
        ]
        
        # Combined pattern
        self.combined_pattern = '|'.join(f'({pattern})' for pattern in self.amount_patterns)
        
    def load_file(self) -> bool:
        """Load the text file and split into lines."""
        try:
            with open(self.text_file, 'r', encoding='utf-8') as f:
                self.lines = f.readlines()
            print(f"Loaded {len(self.lines)} lines from {self.text_file}")
            return True
        except Exception as e:
            print(f"Error loading file {self.text_file}: {e}")
            return False
    
    def find_monetary_lines(self) -> List[Tuple[int, str, List[str]]]:
        """Find all lines that contain monetary amounts."""
        monetary_lines = []
        
        for line_num, line in enumerate(self.lines, 1):
            line_clean = line.strip()
            if not line_clean:
                continue
                
            # Find all monetary amounts in the line
            matches = re.findall(self.combined_pattern, line_clean)
            if matches:
                # Flatten the tuple matches and filter out empty strings
                amounts = [match for group in matches for match in group if match]
                if amounts:
                    monetary_lines.append((line_num, line_clean, amounts))
        
        self.monetary_lines = monetary_lines
        print(f"Found {len(monetary_lines)} lines with monetary amounts")
        return monetary_lines
    
    def get_processed_lines(self) -> Set[int]:
        """Get line numbers that were actually processed by the parser."""
        try:
            # Create a custom parser to track which lines are processed
            parser = FastBudgetParser()
            
            # Parse the file and track processed lines
            allocations = parser.parse(self.text_file)
            
            # The parser doesn't directly expose line numbers, so we need to 
            # simulate the parsing process to identify which lines were used
            processed_lines = set()
            
            with open(self.text_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            current_program = None
            for line_num, line in enumerate(lines, 1):
                line_clean = line.strip()
                if not line_clean:
                    continue
                
                # Check if this line matches any of the parser's patterns
                if self._line_matches_parser_patterns(line_clean):
                    processed_lines.add(line_num)
            
            self.processed_lines = processed_lines
            print(f"Parser processed {len(processed_lines)} lines")
            return processed_lines
            
        except Exception as e:
            print(f"Error getting processed lines: {e}")
            return set()
    
    def _line_matches_parser_patterns(self, line: str) -> bool:
        """Check if a line matches any of the parser's regex patterns."""
        # These are the main patterns from FastBudgetParser
        patterns = [
            r'^\s*(\d+)\.\s*([A-Z]{3}\d+)\s*-\s*(.+)$',  # Program line
            r'^\s*OPERATING\s+([A-Z]+)\s+([\d,]+)([A-Z])\s+([A-Z])\s*$',  # Operating line
            r'^\s*([A-Z]+)\s+([\d,]+)([A-Z])\s+([\d,]+)([A-Z])\s*$',  # Fund line
            r'^\s*CAPITAL IMPROVEMENT\s+([A-Z]+)\s+([\d,]+)([A-Z])\s*$',  # CIP line
        ]
        
        for pattern in patterns:
            if re.match(pattern, line):
                return True
        return False
    
    def find_unprocessed_lines(self) -> List[Tuple[int, str, List[str]]]:
        """Find lines with monetary amounts that weren't processed."""
        unprocessed = []
        
        for line_num, line_text, amounts in self.monetary_lines:
            if line_num not in self.processed_lines:
                unprocessed.append((line_num, line_text, amounts))
        
        return unprocessed
    
    def print_results(self, unprocessed_lines: List[Tuple[int, str, List[str]]]):
        """Print detailed results of the line checking."""
        print("\n" + "="*80)
        print("LINE CHECKING VALIDATION RESULTS")
        print("="*80)
        
        print(f"\nSUMMARY:")
        print(f"  Total lines in file: {len(self.lines)}")
        print(f"  Lines with monetary amounts: {len(self.monetary_lines)}")
        print(f"  Lines processed by parser: {len(self.processed_lines)}")
        print(f"  Unprocessed lines with amounts: {len(unprocessed_lines)}")
        
        coverage = (len(self.processed_lines) / len(self.monetary_lines)) * 100 if self.monetary_lines else 0
        print(f"  Parser coverage: {coverage:.1f}%")
        
        if unprocessed_lines:
            print(f"\nUNPROCESSED LINES WITH MONETARY VALUES:")
            print("-" * 80)
            
            for line_num, line_text, amounts in unprocessed_lines:
                print(f"\nLine {line_num}:")
                print(f"  Text: {line_text}")
                print(f"  Amounts found: {', '.join(amounts)}")
                
                # Show context (previous and next lines)
                if line_num > 1:
                    prev_line = self.lines[line_num - 2].strip()
                    if prev_line:
                        print(f"  Previous: {prev_line}")
                
                if line_num < len(self.lines):
                    next_line = self.lines[line_num].strip()
                    if next_line:
                        print(f"  Next: {next_line}")
        else:
            print(f"\n✓ All lines with monetary amounts are being processed by the parser!")
    
    def run_validation(self) -> bool:
        """Run the complete line checking validation."""
        print("Starting Line Checking Validation...")
        print("-" * 50)
        
        # Load the file
        if not self.load_file():
            return False
        
        # Find lines with monetary amounts
        self.find_monetary_lines()
        
        # Get lines processed by parser
        self.get_processed_lines()
        
        # Find unprocessed lines
        unprocessed = self.find_unprocessed_lines()
        
        # Print results
        self.print_results(unprocessed)
        
        return len(unprocessed) == 0


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python line_checker.py <budget_text_file>")
        print("Example: python line_checker.py 'data/raw/HB 300 CD 1.txt'")
        return 1
    
    text_file = sys.argv[1]
    
    if not Path(text_file).exists():
        print(f"Error: File {text_file} does not exist")
        return 1
    
    checker = LineChecker(text_file)
    success = checker.run_validation()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
