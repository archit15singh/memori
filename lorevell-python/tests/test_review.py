"""Evidence review is revision-bound; synchronization never stamps verification."""
from pathlib import Path
import subprocess
import sys

import pytest
from lorevell import PyVault
from lorevell_cli.review import run_review


def add(vault, text, **metadata):
    return vault.add(text, metadata=metadata)['id']


def test_fair_bounded_queue_deferral_and_changed_revision_wakes(tmp_path):
    v = PyVault(str(tmp_path))
    ids = [add(v, f'# Lesson {i}\nVerified procedure {i}.') for i in range(4)]
    first = run_review(tmp_path, limit=1, clock=1000)['candidates'][0]
    run_review(tmp_path, defer=first['id'], expected=first['revision'], clock=1001)
    next_batch = run_review(tmp_path, limit=2, clock=1002)
    assert len(next_batch['candidates']) == 2 and next_batch['deferred'] == 1
    assert first['id'] not in [n['id'] for n in next_batch['candidates']]
    v.update(first['id'], content='# Corrected lesson\nNew evidence.')
    awakened = run_review(tmp_path, limit=20, clock=1003)
    changed = next(n for n in awakened['candidates'] if n['id'] == first['id'])
    assert changed['revision'] != first['revision']
    with pytest.raises(ValueError, match='current'):
        run_review(tmp_path, mark=first['id'], expected=first['revision'], clock=1004)
    run_review(tmp_path, mark=changed['id'], expected=changed['revision'], clock=1005)
    assert changed['id'] not in [n['id'] for n in run_review(tmp_path, limit=20, clock=1006)['candidates']]
    # Reviewed notes return after their configured review interval, without deletion.
    assert changed['id'] in [n['id'] for n in run_review(tmp_path, limit=20, clock=1006+91*86400)['candidates']]
    assert len(v.notes()) == len(ids)


def test_watched_source_drift_invalidates_scan_revision_and_stays_explicit(tmp_path):
    v = PyVault(str(tmp_path / 'vault'))
    ident = add(v, '# Build command\nUse the documented build target.')
    source = tmp_path / 'Makefile'; source.write_text('build: old\n')
    run_review(tmp_path / 'vault', watch=source, note_id=ident, clock=1000)
    before = run_review(tmp_path / 'vault', clock=1001)['candidates'][0]
    source.write_text('build: new\n')
    after = run_review(tmp_path / 'vault', clock=1002)['candidates'][0]
    assert after['revision'] != before['revision']
    assert after['source_drift'] == [str(source)]
    with pytest.raises(ValueError):
        run_review(tmp_path / 'vault', mark=ident, expected=before['revision'], clock=1003)
    run_review(tmp_path / 'vault', defer=ident, expected=after['revision'], clock=1004)
    assert not run_review(tmp_path / 'vault', clock=1005)['candidates']
    source.write_text('build: newer\n')
    assert run_review(tmp_path / 'vault', clock=1006)['candidates']


def test_original_evidence_and_word_budgets_are_not_auto_shortened(tmp_path):
    v = PyVault(str(tmp_path))
    body = '# Original evidence\n' + 'Keep unique source evidence. ' * 300
    ident = add(v, body, immutable_source=True)
    original = v.notes()[0]['content']
    candidate = run_review(tmp_path, clock=1000)['candidates'][0]
    assert candidate['immutable_source'] is True and candidate['words'] > 800
    assert 'over-word-budget' not in candidate['reasons']
    assert v.show(ident)['note']['content'] == original
    with pytest.raises(ValueError):
        run_review(tmp_path, mark=ident, expected='invented', clock=1001)
    assert v.show(ident)['note']['content'] == original


def test_real_cli_review_outputs_revisions_and_rejects_a_stale_mark(tmp_path):
    v = PyVault(str(tmp_path))
    ident = add(v, '# Procedure\nRead evidence first.')
    cli = str(Path(sys.executable).parent / 'lorevell')
    scan = subprocess.run([cli, '--vault', str(tmp_path), 'review', '--json'], capture_output=True, text=True, check=True)
    import json
    revision = json.loads(scan.stdout)['candidates'][0]['revision']
    v.update(ident, content='# Procedure\nCorrected evidence.')
    failed = subprocess.run([cli, '--vault', str(tmp_path), 'review', '--mark', ident, '--revision', revision], capture_output=True, text=True)
    assert failed.returncode != 0 and 'current' in failed.stderr
