"""Read-only source recall through a real native index and installed CLI."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from lorevell_cli.recall import recall


def snapshot(*entries, status='current'):
    return {'version': 1, 'source_id': 'test-source', 'complete': True,
            'sync_status': status, 'synced_at': '2026-11-12T00:00:00Z',
            'records': [{'id': ident, 'title': ident.title(), 'content': content,
                         'source_url': f'https://example.test/{ident}', 'source_revision': 'r1',
                         'updated_at': 1_700_000_000} for ident, content in entries]}


def test_snapshot_recall_provenance_refresh_and_removed_content(tmp_path):
    source = snapshot(('retry', 'Use jitter for idempotent requests.'), ('bisect', 'Use bisect for regressions.'))
    original = copy.deepcopy(source)
    result = recall(source, tmp_path / 'index', 'jitter', text_only=True)
    assert source == original
    assert result['matches'][0]['id'] == 'retry'
    assert result['matches'][0]['source_revision'] == 'r1'
    assert result['matches'][0]['source_url'].endswith('/retry')
    assert result['matches'][0]['immutable_source'] is True
    assert result['rebuilt'] is True
    assert not recall(source, tmp_path / 'index', 'jitter', text_only=True)['rebuilt']
    source['records'][0]['content'] = 'Honor Retry-After.'
    source['records'][0]['source_revision'] = 'r2'
    assert recall(source, tmp_path / 'index', 'jitter', text_only=True)['matches'] == []
    assert recall(source, tmp_path / 'index', 'Retry-After', text_only=True)['matches'][0]['source_revision'] == 'r2'
    source['records'] = []  # complete projection removes withheld/forgotten notes, without archives
    assert recall(source, tmp_path / 'index', 'bisect', text_only=True)['matches'] == []
    assert not list((tmp_path / 'index').glob('*.md'))
    assert not (tmp_path / 'index' / 'archive').exists()


def test_status_is_not_promoted_to_verification_and_index_loss_rebuilds(tmp_path):
    source = snapshot(('one', 'canary procedure'), status='offline')
    result = recall(source, tmp_path, 'canary', text_only=True)
    assert result['sync_status'] == 'offline' and 'not semantic verification' in result['notice']
    (tmp_path / 'recall.sqlite').unlink()
    assert recall(source, tmp_path, 'canary', text_only=True)['matches']
    assert recall(source, tmp_path, index_only=True)['matches'] == []
    assert recall(source, tmp_path, 'canary', limit=0)['matches'] == []


def test_partial_snapshot_invalid_sources_and_foreign_cache_cannot_mutate(tmp_path):
    source = snapshot(('one', 'retained canary'))
    recall(source, tmp_path / 'cache', index_only=True)
    for bad in [dict(source, complete=False), dict(source, source_id='another'),
                dict(source, records=source['records'] * 2), dict(source, version=2),
                dict(source, records=[{k: v for k, v in source['records'][0].items() if k != 'updated_at'}])]:
        with pytest.raises(ValueError):
            recall(bad, tmp_path / 'cache', 'canary', text_only=True)
    assert recall(source, tmp_path / 'cache', 'canary', text_only=True)['matches']
    foreign = tmp_path / 'foreign'; foreign.mkdir()
    protected = foreign / 'important.md'; protected.write_text('Keep me')
    with pytest.raises(ValueError, match='dedicated'):
        recall(source, foreign, index_only=True)
    assert protected.read_text() == 'Keep me'


def test_failed_first_build_recovers_and_failed_replacement_does_not_return_old_records(tmp_path, monkeypatch):
    import lorevell_cli.recall as module
    original = module.PyLorevell
    def fail(_):
        raise RuntimeError('interrupted build')
    source = snapshot(('one', 'old quasar'))
    monkeypatch.setattr(module, 'PyLorevell', fail)
    with pytest.raises(RuntimeError):
        recall(source, tmp_path, index_only=True)
    monkeypatch.setattr(module, 'PyLorevell', original)
    assert recall(source, tmp_path, 'quasar', text_only=True)['matches']
    source['records'] = []
    monkeypatch.setattr(module, 'PyLorevell', fail)
    with pytest.raises(RuntimeError):
        recall(source, tmp_path, index_only=True)
    assert not (tmp_path / 'recall.sqlite').exists()
    monkeypatch.setattr(module, 'PyLorevell', original)
    assert recall(source, tmp_path, 'quasar', text_only=True)['matches'] == []


@pytest.mark.skipif(sys.platform == 'win32', reason='symlink permission differs on Windows')
def test_symlinks_cannot_redirect_projection_writes(tmp_path):
    victim = tmp_path / 'victim'; victim.write_text('original')
    cache = tmp_path / 'cache'; cache.mkdir()
    (cache / 'source.json').symlink_to(victim)
    with pytest.raises(ValueError):
        recall(snapshot(('one', 'canary')), cache, index_only=True)
    assert victim.read_text() == 'original'


def test_actual_cli_reads_stdin_snapshot_and_cross_process_recall(tmp_path):
    cli = str(Path(sys.executable).parent / 'lorevell')
    source = snapshot(('canary', 'A repeatable canary catches regressions.'))
    command = [cli, 'recall', 'regressions', '--snapshot', '-', '--cache-dir', str(tmp_path / 'cache'), '--text-only', '--json']
    first = subprocess.run(command, input=json.dumps(source), text=True, capture_output=True, check=True)
    second = subprocess.run(command, input=json.dumps(source), text=True, capture_output=True, check=True)
    assert json.loads(first.stdout)['matches'][0]['id'] == 'canary'
    assert json.loads(second.stdout)['rebuilt'] is False


def test_hybrid_backfills_the_same_read_only_snapshot(tmp_path):
    from lorevell import PyLorevell
    source = snapshot(('regression', 'Use git bisect for a reproducible regression.'),
                      ('cooking', 'Bake bread with flour and yeast.'))
    recall(source, tmp_path, index_only=True)
    result = recall(source, tmp_path, 'git bisect regression')
    assert result['matches'][0]['id'] == 'regression'
    assert result['rebuilt'] is False
    assert PyLorevell(str(tmp_path / 'recall.sqlite')).embedding_stats()['embedded'] == 2


def test_interrupted_rebuild_after_index_loss_never_acknowledges_partial_rows(tmp_path, monkeypatch):
    import lorevell_cli.recall as module
    source = snapshot(('first', 'First retained procedure'), ('second', 'Unique canary'))
    recall(source, tmp_path, index_only=True)
    (tmp_path / 'recall.sqlite').unlink()
    original = module.PyLorevell
    class Interrupted:
        def __init__(self, path):
            self.inner = original(path)
            self.count = 0
        def insert_with_id(self, *args, **kwargs):
            self.count += 1
            if self.count == 2:
                raise RuntimeError('interrupted after first row')
            return self.inner.insert_with_id(*args, **kwargs)
    monkeypatch.setattr(module, 'PyLorevell', Interrupted)
    with pytest.raises(RuntimeError):
        recall(source, tmp_path, index_only=True)
    assert json.loads((tmp_path / 'source.json').read_text())['fingerprint'] is None
    monkeypatch.setattr(module, 'PyLorevell', original)
    assert recall(source, tmp_path, 'canary', text_only=True)['matches'][0]['id'] == 'second'
