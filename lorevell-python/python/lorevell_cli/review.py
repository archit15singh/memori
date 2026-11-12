"""Bounded revision-aware triage, never an automatic semantic reviewer."""
import hashlib
import json
from pathlib import Path
import re
import time

from lorevell import PyVault
from .local_state import locked, read_json, write_json


def revision(note, sources=None):
    return hashlib.sha256(json.dumps([note, sources or {}], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def fingerprint(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None
    except OSError:
        return None


def run_review(root, limit=3, mark=None, defer=None, expected=None, watch=None, note_id=None, clock=None):
    now = time.time() if clock is None else clock
    # Internal consumers can inspect the complete queue before applying their own budget.
    if limit is not None and not 1 <= limit <= 20:
        raise ValueError('Review limit must be between 1 and 20')
    root = Path(root).expanduser()
    vault = PyVault(str(root))
    root = root.resolve()
    state_path = root / '.lorevell' / 'review.json'
    with locked(root / '.lorevell' / 'review.lock'):
        notes = vault.notes()
        by_id = {note['id']: note for note in notes}
        state = read_json(state_path, {'version': 1, 'reviews': {}, 'watches': {}})
        if not isinstance(state, dict) or state.get('version') != 1 or not all(isinstance(state.get(k), dict) for k in ('reviews', 'watches')):
            raise ValueError('Unsupported review state version')
        reviews, watches = state['reviews'], state['watches']
        observed = {ident: {path: fingerprint(path) for path in sources} for ident, sources in watches.items()}
        def current_revision(note):
            return revision(note, observed.get(note['id']))
        if mark or defer:
            ident = mark or defer
            if ident not in by_id or expected != current_revision(by_id[ident]):
                raise ValueError('Review must match the current full note ID and revision; scan again')
            previous = reviews.get(ident, {})
            reviews[ident] = {'revision': expected, 'attempted_at': now,
                             'outcome': 'deferred' if defer else 'reviewed',
                             'reviewed_at': previous.get('reviewed_at') if defer else now}
            write_json(state_path, state)
            return {'id': ident, 'revision': expected, 'outcome': reviews[ident]['outcome']}
        if watch:
            if note_id not in by_id:
                raise ValueError('--watch needs an existing full --note ID')
            path = Path(watch).expanduser().resolve()
            value = fingerprint(path)
            if value is None:
                raise ValueError('Watched source must be an existing file')
            watches.setdefault(note_id, {})[str(path)] = value
            write_json(state_path, state)
            return {'id': note_id, 'watched': str(path), 'notice': 'Baseline the source only after checking its claim.'}
        candidates, deferred_count = [], 0
        for note in notes:
            ident, current = note['id'], current_revision(note)
            prior = reviews.get(ident, {})
            changed = prior.get('revision') != current
            age = (now - prior.get('attempted_at', 0)) / 86400
            if not changed and prior.get('outcome') == 'deferred' and age < 1:
                deferred_count += 1
                continue
            due_days = note['metadata'].get('review_after_days', 90)
            if isinstance(due_days, bool) or not isinstance(due_days, (int, float)) or not 1 <= due_days <= 3650:
                raise ValueError(f'{ident}: review_after_days must be between 1 and 3650')
            reasons = []
            if changed:
                reasons.append('changed-or-never-reviewed')
            elif age >= due_days or prior.get('outcome') == 'deferred':
                reasons.append('review-due')
            drift = [path for path, value in watches.get(ident, {}).items() if observed[ident][path] != value]
            if drift:
                reasons.append('source-drift')
            if reasons:
                words = len(note['content'].split())
                immutable = note['metadata'].get('immutable_source') is True
                if words > 800 and not immutable:
                    reasons.append('over-word-budget')
                paragraphs = [' '.join(p.split()) for p in re.split(r'\n\s*\n', note['content'])]
                paragraphs = [p for p in paragraphs if len(p) >= 100]
                if len(set(paragraphs)) < len(paragraphs) and not immutable:
                    reasons.append('exact-duplicate-passages')
                candidates.append({'id': ident, 'path': note['path'], 'revision': current,
                                   'reasons': reasons, 'words': words, 'immutable_source': immutable,
                                   'review_after_days': due_days,
                                   'source_drift': drift, 'last_attempt_at': prior.get('attempted_at')})
        candidates.sort(key=lambda n: (n['last_attempt_at'] or 0, -('source-drift' in n['reasons']), n['id']))
        return {'candidates': candidates[:limit], 'remaining': max(0, len(candidates)-(limit or len(candidates))),
                'deferred': deferred_count, 'notice': 'Heuristic triage, not proof of staleness or semantic verification.'}
