#!/usr/bin/env python3
"""
Sort budget_parsed.csv by program_id.
"""
import pandas as pd
import sys
from pathlib import Path

# Set paths
input_file = Path('data/processed/budget_parsed.csv')
output_file = input_file  # Will overwrite the original file

# Read the CSV
print(f"Reading {input_file}...")
df = pd.read_csv(input_file)

# Original category order from the budget document
category_order = [
    'Economic Development',  # A
    'Employment',            # B
    'Transportation',        # C
    'Environment',           # D
    'Health',                # E
    'Human Services',        # F (Social Services)
    'Education',             # G (Formal Education)
    'Culture and Recreation',# H
    'Public Safety',         # I
    'Individual Rights',     # J
    'Government Operations', # K (Government-wide Support)
    'Other'                  # For any uncategorized items
]

# Create a categorical type with the desired order
from pandas.api.types import CategoricalDtype
cat_type = CategoricalDtype(categories=category_order, ordered=True)

# Convert the category column to the categorical type
df['category'] = df['category'].astype(cat_type)

# Sort by the categorical column, then by program_id
df_sorted = df.sort_values(['category', 'program_id'])

# Save the sorted data
df_sorted.to_csv(output_file, index=False)
print(f"Saved sorted data to {output_file}")
print(f"Total entries: {len(df_sorted)}")
