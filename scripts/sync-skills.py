"""Package the canonical shared agent skills. CI uses --check to catch drift."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
for name in ('lorevell', 'dream'):
    source = root / 'skills' / name / 'SKILL.md'
    target = root / 'lorevell-python/python/lorevell_cli/data' / name / 'SKILL.md'
    content = source.read_bytes()
    if args.check:
        if not target.exists() or target.read_bytes() != content:
            raise SystemExit(f'Packaged skill differs: {target}; run scripts/sync-skills.py')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
