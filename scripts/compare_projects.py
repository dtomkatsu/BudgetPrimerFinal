#!/usr/bin/env python3
"""
Compare Section 14 capital improvement projects between two HB1800 drafts.

Produces a JSON file for the frontend that groups projects by program_id,
showing HD1 vs SD1 amounts for each project (added, removed, modified, unchanged).

Usage:
    python scripts/compare_projects.py --draft1 HD1 --draft2 SD1 --fy 2026
    python scripts/compare_projects.py --draft1 HD1 --draft2 SD1 --fy 2027 \
        --output docs/js/projects_fy27.json
"""
import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from budgetprimer.parsers.fast_parser import FastBudgetParser

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DRAFTS_DIR = PROJECT_ROOT / 'data' / 'raw' / 'drafts'
JSON_DIR = PROJECT_ROOT / 'docs' / 'js'


def resolve_draft_path(label: str) -> Path:
    """Resolve a draft label (HD1, SD1) to its file path."""
    meta_path = DRAFTS_DIR / 'metadata.json'
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        drafts = meta.get('drafts', {})
        if label in drafts:
            return DRAFTS_DIR / drafts[label]['filename']
    for candidate in [
        DRAFTS_DIR / f'HB1800_{label}.txt',
        DRAFTS_DIR / label,
        Path(label),
    ]:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f'Draft "{label}" not found. Run download_bill.py first.')


def normalize_name(name: str) -> str:
    """Normalize project name for cross-draft matching."""
    return re.sub(r'\s+', ' ', name.strip().upper())


def parse_projects(file_path: Path, fy1: int, fy2: int):
    """Parse a draft and return its projects list."""
    parser = FastBudgetParser(fy1=fy1, fy2=fy2)
    parser.parse(str(file_path))
    return parser.projects


def compare_projects(
    file1: Path,
    file2: Path,
    label1: str,
    label2: str,
    fy: int = 2026,
) -> dict:
    """Parse two drafts, diff their Section 14 projects, return structured result."""
    biennium_fy1 = fy if fy % 2 == 0 else fy - 1
    biennium_fy2 = biennium_fy1 + 1

    logger.info(f'Parsing draft 1: {file1.name}')
    projects1 = parse_projects(file1, biennium_fy1, biennium_fy2)
    projects1 = [p for p in projects1 if p.fiscal_year == fy]
    logger.info(f'  → {len(projects1)} {label1} projects for FY{fy}')

    logger.info(f'Parsing draft 2: {file2.name}')
    projects2 = parse_projects(file2, biennium_fy1, biennium_fy2)
    projects2 = [p for p in projects2 if p.fiscal_year == fy]
    logger.info(f'  → {len(projects2)} {label2} projects for FY{fy}')

    # Build lookup keys: (program_id, normalized_name, fund_type_value)
    def key(p):
        return (p.program_id, normalize_name(p.project_name), p.fund_type.value)

    d1_map = {}
    for p in projects1:
        k = key(p)
        if k in d1_map:
            # Duplicate: sum amounts (shouldn't happen for distinct projects)
            d1_map[k]['amount'] += p.amount
        else:
            d1_map[k] = {'amount': p.amount, 'project': p}

    d2_map = {}
    for p in projects2:
        k = key(p)
        if k in d2_map:
            d2_map[k]['amount'] += p.amount
        else:
            d2_map[k] = {'amount': p.amount, 'project': p}

    all_keys = set(d1_map.keys()) | set(d2_map.keys())

    # Build comparison records
    records = []
    for k in all_keys:
        d1_entry = d1_map.get(k)
        d2_entry = d2_map.get(k)
        # Use SD1 project as canonical reference when available, else HD1
        ref = (d2_entry or d1_entry)['project']
        amount_d1 = d1_entry['amount'] if d1_entry else 0.0
        amount_d2 = d2_entry['amount'] if d2_entry else 0.0
        change = amount_d2 - amount_d1

        if d1_entry is None:
            change_type = 'added'
        elif d2_entry is None:
            change_type = 'removed'
        elif change == 0:
            change_type = 'unchanged'
        else:
            change_type = 'modified'

        records.append({
            'project_id': ref.project_id,
            'project_name': ref.project_name,
            'scope': ref.scope,
            'program_id': ref.program_id,
            'program_name': ref.program_name,
            'department_code': ref.department_code,
            'category': ref.category,
            'fund_type': ref.fund_type.value,
            'fund_category': ref.fund_type.category,
            f'amount_{label1.lower()}': amount_d1,
            f'amount_{label2.lower()}': amount_d2,
            'change': change,
            'change_type': change_type,
        })

    # Group by program_id
    projects_by_program: dict[str, list] = defaultdict(list)
    for r in records:
        projects_by_program[r['program_id']].append(r)

    # Sort within each program: by project_id numerically when possible
    def sort_key(r):
        try:
            return (0, float(r['project_id']))
        except (ValueError, TypeError):
            return (1, r['project_id'])

    for pid in projects_by_program:
        projects_by_program[pid].sort(key=sort_key)

    # Summary
    added = [r for r in records if r['change_type'] == 'added']
    removed = [r for r in records if r['change_type'] == 'removed']
    modified = [r for r in records if r['change_type'] == 'modified']
    total_d1 = sum(r[f'amount_{label1.lower()}'] for r in records)
    total_d2 = sum(r[f'amount_{label2.lower()}'] for r in records)

    result = {
        'metadata': {
            'draft1': label1,
            'draft2': label2,
            'bill_number': 'HB1800',
            'fiscal_year': fy,
            'generated_at': datetime.now().isoformat(),
            'net_change': total_d2 - total_d1,
        },
        'summary': {
            f'total_{label1.lower()}': total_d1,
            f'total_{label2.lower()}': total_d2,
            'net_change': total_d2 - total_d1,
            'total_projects': len(records),
            'projects_added': len(added),
            'projects_removed': len(removed),
            'projects_modified': len(modified),
            'programs_with_projects': len(projects_by_program),
        },
        'projects_by_program': dict(projects_by_program),
    }
    return result


def main():
    ap = argparse.ArgumentParser(description='Compare Section 14 projects between drafts')
    ap.add_argument('--draft1', default='HD1')
    ap.add_argument('--draft2', default='SD1')
    ap.add_argument('--label1')
    ap.add_argument('--label2')
    ap.add_argument('--fy', type=int, default=2026)
    ap.add_argument('--output', type=Path, default=JSON_DIR / 'projects.json')
    args = ap.parse_args()

    file1 = resolve_draft_path(args.draft1)
    file2 = resolve_draft_path(args.draft2)
    label1 = args.label1 or args.draft1
    label2 = args.label2 or args.draft2

    result = compare_projects(file1, file2, label1, label2, args.fy)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    s = result['summary']
    net = result['metadata']['net_change']
    sign = '+' if net > 0 else ''
    logger.info(f'FY{args.fy} comparison: {s["total_projects"]} projects across '
                f'{s["programs_with_projects"]} programs')
    logger.info(f'  Added: {s["projects_added"]}, Removed: {s["projects_removed"]}, '
                f'Modified: {s["projects_modified"]}')
    logger.info(f'  Net change: {sign}${net:,.0f}')
    logger.info(f'Saved to {args.output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
