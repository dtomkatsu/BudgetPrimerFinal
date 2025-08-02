#!/usr/bin/env python3
"""
Test script to isolate the display error in departmental reports generation.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Set backend before importing pyplot
import matplotlib.pyplot as plt
import numpy as np
import traceback
import sys

def test_single_department():
    """Test generating a report for a single department to isolate the error."""
    try:
        # Load data
        df = pd.read_csv('data/processed/budget_allocations_fy2026_post_veto.csv')
        print(f"Loaded {len(df)} budget allocations")
        
        # Get first department
        dept_code = df['department_code'].iloc[0]
        print(f"Testing department: {dept_code}")
        
        # Filter data for this department
        dept_data = df[df['department_code'] == dept_code].copy()
        print(f"Found {len(dept_data)} records for {dept_code}")
        
        # Test chart creation
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Simple test chart
        amounts = [100, 200, 50, 75]
        colors = ['#1f77b4', '#2ca02c', '#2c3e50', '#17a2b8']
        labels = ['General Funds', 'Special Funds', 'Federal Funds', 'Other Funds']
        
        left = 0
        for amount, color, label in zip(amounts, colors, labels):
            if amount > 0:
                ax.barh(0, amount, left=left, color=color, label=label, height=0.6)
                left += amount
        
        ax.set_xlim(0, sum(amounts) * 1.1)
        ax.set_ylim(-0.5, 0.5)
        ax.set_xlabel('Amount (Millions of Dollars)', fontsize=12)
        ax.set_title(f'{dept_code} Operating Budget', fontsize=14, fontweight='bold')
        
        # Remove y-axis
        ax.set_yticks([])
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        
        # Add legend
        ax.legend(loc='upper right', bbox_to_anchor=(1, 1))
        
        plt.tight_layout()
        plt.close()
        
        print("Chart creation successful!")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        print("Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_single_department()
