"""Evaluate frozen, manually labeled project questions against an actual vault.

This small maintainer acceptance set measures ranked note IDs, not semantic truth,
answer correctness, or generalization to other projects. Labels stay outside dream.
"""
import argparse
import hashlib
import json
from pathlib import Path

from lorevell import PyVault

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--vault', type=Path, required=True)
parser.add_argument('--questions', type=Path, required=True)
parser.add_argument('--text-only', action='store_true')
args = parser.parse_args()
raw = args.questions.read_bytes()
labels = json.loads(raw)
vault = PyVault(str(args.vault))
vault.index(embeddings=not args.text_only)
results = []
for case in labels['queries']:
    hits = vault.search(case['query'], limit=3, graph_limit=0,
                        text_only=args.text_only)['matches']
    ids = [hit['note']['id'] for hit in hits]
    rank = next((i for i, ident in enumerate(ids, 1)
                 if ident in case['relevant_ids']), None)
    results.append(dict(query=case['query'], expected=case['relevant_ids'],
                        retrieved=ids, first_relevant_rank=rank))
count = len(results)
if not count:
    raise SystemExit('Question set must not be empty')
print(json.dumps({
    'description': labels['description'],
    'questions_sha256': hashlib.sha256(raw).hexdigest(),
    'mode': 'text-only' if args.text_only else 'hybrid',
    'questions': count,
    'top1': sum(r['first_relevant_rank'] == 1 for r in results),
    'hit_at_3': sum(r['first_relevant_rank'] is not None for r in results),
    'mrr_at_3': round(sum(1 / r['first_relevant_rank']
                          for r in results if r['first_relevant_rank']) / count, 4),
    'results': results,
}, indent=2))
