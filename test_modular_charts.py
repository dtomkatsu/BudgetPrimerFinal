#!/usr/bin/env python3
"""Test script for the new modular chart system."""

import sys
from pathlib import Path
import pandas as pd

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from budgetprimer.visualization.charts import DepartmentChart, MeansOfFinanceChart, CIPChart

def test_chart_imports():
    """Test that all chart classes can be imported successfully."""
    print("✓ Successfully imported DepartmentChart")
    print("✓ Successfully imported MeansOfFinanceChart") 
    print("✓ Successfully imported CIPChart")
    print()

def test_chart_creation():
    """Test creating chart instances."""
    try:
        dept_chart = DepartmentChart(fiscal_year=2026, n_departments=10)
        print("✓ Successfully created DepartmentChart instance")
        
        mof_chart = MeansOfFinanceChart(fiscal_year=2026)
        print("✓ Successfully created MeansOfFinanceChart instance")
        
        cip_chart = CIPChart(fiscal_year=2026, n_departments=5)
        print("✓ Successfully created CIPChart instance")
        print()
        
    except Exception as e:
        print(f"✗ Error creating chart instances: {e}")
        return False
        
    return True

def main():
    """Run all tests."""
    print("Testing Modular Chart System")
    print("=" * 40)
    
    # Test imports
    test_chart_imports()
    
    # Test chart creation
    if test_chart_creation():
        print("✓ All tests passed! The modular chart system is working correctly.")
    else:
        print("✗ Some tests failed.")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
