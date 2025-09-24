#!/usr/bin/env python3
"""
Sync department reports and assets to the gh-pages directory.
"""

import os
import shutil
from pathlib import Path
import json

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
GH_PAGES_DIR = PROJECT_ROOT / 'gh-pages'
REPORTS_SRC_DIR = PROJECT_ROOT / 'data' / 'output' / 'departmental_reports'
ASSETS_SRC_DIR = PROJECT_ROOT / 'data' / 'output' / 'assets'

# Create necessary directories
(GH_PAGES_DIR / 'pages').mkdir(parents=True, exist_ok=True)
(GH_PAGES_DIR / 'assets').mkdir(parents=True, exist_ok=True)

def sync_department_pages():
    """Convert and sync department HTML pages to the SPA format."""
    print("Syncing department pages...")
    
    # Get all department report files
    report_files = list(REPORTS_SRC_DIR.glob('*_budget_report.html'))
    
    departments = []
    
    for report_file in report_files:
        dept_id = report_file.stem.split('_')[0].lower()
        dept_name = f"Department of {dept_id.upper()}"  # This would come from your data
        
        # Simple conversion - in a real app, you'd parse the HTML and extract content
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create a simple page that will be loaded into the SPA
        page_content = f"""
        <div class="department-detail">
            <a href="#/departments" class="back-button">← Back to Departments</a>
            <div class="department-header">
                <h2>{dept_name}</h2>
                <p>This is a placeholder for the {dept_name} budget report.</p>
                <p>In a real implementation, this would contain the full report content.</p>
            </div>
            <div class="chart-container">
                <canvas id="deptBudgetChart"></canvas>
            </div>
        </div>
        <script>
        // This would be initialized by the SPA router
        document.addEventListener('DOMContentLoaded', function() {{
            const ctx = document.getElementById('deptBudgetChart').getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: ['Program 1', 'Program 2', 'Program 3', 'Program 4'],
                    datasets: [{{
                        label: 'Budget Allocation',
                        data: [12, 19, 3, 5],
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.7)',
                            'rgba(54, 162, 235, 0.7)',
                            'rgba(255, 206, 86, 0.7)',
                            'rgba(75, 192, 192, 0.7)'
                        ]
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: '{dept_name} Budget Allocation'
                        }}
                    }}
                }}
            }});
        }});
        </script>
        """
        
        # Save the page
        with open(GH_PAGES_DIR / 'pages' / f"{dept_id}.html", 'w', encoding='utf-8') as f:
            f.write(page_content)
        
        departments.append({
            'id': dept_id,
            'name': dept_name,
            'budget': '$0',  # This would come from your data
            'path': f'/pages/{dept_id}.html'
        })
    
    # Save departments data for the SPA
    with open(GH_PAGES_DIR / 'js' / 'departments.json', 'w', encoding='utf-8') as f:
        json.dump(departments, f, indent=2)
    
    print(f"Synced {len(departments)} department pages.")

def sync_assets():
    """Sync chart images and other assets."""
    print("Syncing assets...")
    
    # Copy all assets from source to destination
    if ASSETS_SRC_DIR.exists():
        for item in ASSETS_SRC_DIR.iterdir():
            if item.is_file():
                shutil.copy2(item, GH_PAGES_DIR / 'assets' / item.name)
    
    print("Assets synced.")

def main():
    print("Starting sync to gh-pages directory...")
    
    # Sync all content
    sync_department_pages()
    sync_assets()
    
    print("\n✅ Sync complete!")
    print(f"Deploy by pushing the contents of '{GH_PAGES_DIR}' to your GitHub Pages repository.")
    print("See README.md for deployment instructions.")

if __name__ == "__main__":
    main()
