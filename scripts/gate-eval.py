"""Reject changed labels, metric regressions, and changes without measured gains.

Pass baseline/candidate JSON reports in pairs for every frozen set and mode.
This gates a small acceptance evaluation, not statistical significance or truth.
"""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('reports', nargs='+', type=Path)
args = parser.parse_args()
if len(args.reports) % 2:
    parser.error('Provide baseline/candidate report pairs')
improved = False
failures = []
for baseline_path, candidate_path in zip(args.reports[::2], args.reports[1::2]):
    baseline = json.loads(baseline_path.read_text())
    candidate = json.loads(candidate_path.read_text())
    for key in ('questions_sha256', 'questions', 'mode'):
        if baseline[key] != candidate[key]:
            failures.append(f'{candidate_path}: changed {key}')
    for key in ('top1', 'hit_at_3', 'mrr_at_3'):
        before, after = baseline[key], candidate[key]
        if after < before:
            failures.append(f'{candidate_path}: {key} regressed {before} -> {after}')
        improved |= after > before
if not improved:
    failures.append('No measured improvement')
print(json.dumps({'accepted': not failures, 'failures': failures}, indent=2))
raise SystemExit(bool(failures))
