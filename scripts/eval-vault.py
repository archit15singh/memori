"""Measure required-fact completeness of top-1 vault retrieval on explicit labels.

This deterministic lexical check is a small acceptance probe, not a semantic
truth judge. Keep consolidation inputs separate from held-out query labels.
"""
import argparse
import json
from pathlib import Path
from lorevell import PyVault

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--vault', type=Path, required=True)
parser.add_argument('--dataset', type=Path, default=Path(__file__).resolve().parents[1] / 'docs/evals/v2-held-out.json')
args = parser.parse_args()
labels = json.loads(args.dataset.read_text())
vault = PyVault(str(args.vault))
vault.index()
results = []
for case in labels['queries']:
    matches = vault.search(case['query'], limit=1, graph_limit=0)['matches']
    content = matches[0]['note']['content'].lower() if matches else ''
    results.append({
        'query': case['query'], 'required': case['required'],
        'id': matches[0]['note']['id'] if matches else None,
        'found': [term for term in case['required'] if term.lower() in content],
        'complete': all(term.lower() in content for term in case['required']),
    })
print(json.dumps({'description': labels['description'], 'complete': sum(r['complete'] for r in results), 'total': len(results), 'results': results}, indent=2))
