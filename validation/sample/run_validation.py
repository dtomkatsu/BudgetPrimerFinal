#!/usr/bin/env python3
"""
Run the complete validation workflow:
1. Generate sample budget PDF
2. Extract text from PDF
3. Parse the text with the budget parser
4. Compare results against expected totals
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{description}...")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False

def main():
    """Run the complete validation workflow."""
    sample_dir = Path(__file__).parent
    
    print("="*60)
    print("BUDGET PARSER VALIDATION WORKFLOW")
    print("="*60)
    
    # Step 1: Generate sample budget PDF
    if not run_command([sys.executable, str(sample_dir / "generate_sample_budget.py")], 
                      "Step 1: Generating sample budget PDF"):
        print("Failed to generate sample budget PDF")
        return 1
    
    # Step 2: Extract text from PDF
    if not run_command([sys.executable, str(sample_dir / "extract_sample_text.py")],
                      "Step 2: Extracting text from PDF"):
        print("Failed to extract text from PDF")
        return 1
    
    # Step 3: Validate parser
    if not run_command([sys.executable, str(sample_dir / "validate_parser.py")],
                      "Step 3: Validating parser against sample budget"):
        print("Parser validation failed")
        return 1
    
    print("\n" + "="*60)
    print("VALIDATION WORKFLOW COMPLETED SUCCESSFULLY")
    print("="*60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
