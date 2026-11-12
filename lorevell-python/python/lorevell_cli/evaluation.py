"""Deterministic retrieval acceptance checks against explicitly supplied labels."""
import hashlib
import json
from pathlib import Path


def load_evaluation(path, root):
    path = Path(path).expanduser().resolve(strict=True)
    if path.is_relative_to(root.resolve()):
        raise ValueError('Evaluation labels must live outside the dream vault')
    raw = path.read_bytes()
    dataset = json.loads(raw)
    cases = dataset.get('queries') if isinstance(dataset, dict) else None
    if not isinstance(cases, list) or not cases:
        raise ValueError('Evaluation needs a nonempty queries list')
    for case in cases:
        if (not isinstance(case, dict) or not isinstance(case.get('query'), str)
                or not case['query'].strip() or not isinstance(case.get('relevant_ids'), list)
                or not case['relevant_ids'] or any(not isinstance(ident, str) or not ident
                                                for ident in case['relevant_ids'])):
            raise ValueError('Each evaluation query needs text and nonempty relevant_ids strings')
    return cases, hashlib.sha256(raw).hexdigest()


def evaluate(vault, cases, text_only):
    top1, hit_at_3, rank_units = 0, 0, 0
    for case in cases:
        hits = vault.search(case['query'], limit=3, graph_limit=0, text_only=text_only)['matches']
        rank = next((rank for rank, hit in enumerate(hits, 1)
                     if hit['note']['id'] in case['relevant_ids']), None)
        if rank is not None:
            top1 += rank == 1
            hit_at_3 += 1
            rank_units += {1: 6, 2: 3, 3: 2}[rank]
    return {'queries': len(cases), 'top1': top1, 'hit_at_3': hit_at_3,
            'reciprocal_rank_units': rank_units,
            'mrr_at_3': round(rank_units / (6 * len(cases)), 6)}


def regression(before, after):
    # Integer rank units avoid rounding away a small MRR regression.
    return [metric for metric in ('top1', 'hit_at_3', 'reciprocal_rank_units')
            if after[metric] < before[metric]]
