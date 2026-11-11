"""Freshness follows content/revalidation, never popularity or tag edits."""
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest
from memori import PyMemori


def seed(db, name, age_days, vector=None):
    timestamp = time.time() - age_days * 86400
    db.insert_with_id(name, name, vector=vector or [1., 0.], created_at=timestamp, updated_at=timestamp)
    return timestamp


def test_never_accessed_old_memory_decays(tmp_path):
    db = PyMemori(str(tmp_path / 'age.db'))
    seed(db, 'old', 200)
    seed(db, 'new', 0)
    results = db.search(vector=[1., 0.])
    assert [m['id'] for m in results] == ['new', 'old']
    assert results[1]['score'] < results[0]['score'] / 5


def test_age_never_improves_a_negative_similarity(tmp_path):
    db = PyMemori(str(tmp_path / 'age.db'))
    seed(db, 'old', 200)
    seed(db, 'new', 0)
    results = db.search(vector=[-1., 0.])
    assert [m['id'] for m in results] == ['new', 'old']
    assert results[1]['score'] < results[0]['score']


def test_reads_metadata_and_identical_content_do_not_refresh(tmp_path):
    db = PyMemori(str(tmp_path / 'age.db'))
    old = seed(db, 'old', 200)
    db.get('old')
    db.update('old', metadata={'type': 'fact'}, vector=[1., 0.])
    db.update('old', content='old', vector=[1., 0.])
    record = db.get_readonly('old')
    assert record['content_updated_at'] == old
    assert record['validated_at'] is None
    assert record['updated_at'] > old
    assert record['access_count'] == 1
    db.revalidate('old')
    assert db.get_readonly('old')['validated_at'] > old
    db.update('old', content='changed fact', vector=[1., 0.])
    record = db.get_readonly('old')
    assert record['content_updated_at'] > old
    assert record['validated_at'] is None


def test_revalidation_is_explicit_and_does_not_count_as_access(tmp_path):
    db = PyMemori(str(tmp_path / 'age.db'))
    old = seed(db, 'old', 200)
    seed(db, 'new', 1)
    db.revalidate('old')
    record = db.get_readonly('old')
    assert record['content_updated_at'] == old
    assert record['validated_at'] > time.time() - 60
    assert record['access_count'] == 0
    assert db.search(vector=[1., 0.])[0]['id'] == 'old'
    with pytest.raises(RuntimeError, match='not found'):
        db.revalidate('missing')


def test_popularity_boost_is_bounded(tmp_path):
    db = PyMemori(str(tmp_path / 'age.db'))
    seed(db, 'strong', 0)
    seed(db, 'weak', 0, [0.6, 0.8])
    db.set_access_stats('weak', last_accessed=time.time(), access_count=2**63 - 1)
    results = db.search(vector=[1., 0.])
    assert results[0]['id'] == 'strong'
    assert results[1]['score'] <= 0.9 + 1e-6


def test_text_only_freshness_applies_before_top_k(tmp_path):
    db = PyMemori(str(tmp_path / 'age.db'))
    old = time.time() - 200 * 86400
    db.insert_with_id('old', 'old architecture', vector=[1., 0.], created_at=old, updated_at=old)
    db.insert('new architecture', vector=[1., 0.])
    assert db.search(text='architecture', text_only=True, limit=1)[0]['content'] == 'new architecture'


def test_context_stale_review_survives_reads_and_tags(tmp_path):
    path = str(tmp_path / 'age.db')
    db = PyMemori(path)
    seed(db, 'old', 200)
    db.get('old')
    db.update('old', metadata={'type': 'fact'}, vector=[1., 0.])
    cli = str(Path(sys.executable).parent / 'memori')
    def context():
        result = subprocess.run([cli, '--db', path, '--json', 'context', 'unrelated'], capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)
    assert context()['stale'][0]['id'] == 'old'
    db.revalidate('old')
    assert context()['stale'] == []


def test_cli_revalidation_and_backup_roundtrip(tmp_path):
    source = str(tmp_path / 'source.db')
    db = PyMemori(source)
    old = seed(db, 'old', 200)
    cli = str(Path(sys.executable).parent / 'memori')
    def run(path, *args, stdin=None):
        return subprocess.run([cli, '--db', path, '--json', *args], input=stdin,
                              capture_output=True, text=True, timeout=120)
    result = run(source, 'revalidate', 'old')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['action'] == 'revalidated'
    backup = run(source, 'export', '--include-vectors')
    assert backup.returncode == 0, backup.stderr
    exported = json.loads(backup.stdout)
    assert exported['content_updated_at'] == old
    assert exported['validated_at'] > old
    for new_ids in [False, True]:
        destination = str(tmp_path / f'destination-{new_ids}.db')
        imported = run(destination, 'import', *(['--new-ids'] if new_ids else []), stdin=backup.stdout)
        assert imported.returncode == 0, imported.stderr
        assert json.loads(imported.stdout) == {'imported': 1, 'errors': 0}
        record = PyMemori(destination).list()[0]
        assert record['content_updated_at'] == old
        assert record['validated_at'] == exported['validated_at']
        assert (record['id'] != 'old') == new_ids


@pytest.mark.parametrize('value', [float('nan'), float('inf')])
def test_invalid_restore_clock_writes_nothing(tmp_path, value):
    db = PyMemori(str(tmp_path / 'age.db'))
    with pytest.raises(RuntimeError, match='timestamp'):
        db.insert_with_id('bad', 'bad', vector=[1., 0.], content_updated_at=value)
    assert db.count() == 0


def test_cli_newer_schema_error_is_structured(tmp_path):
    path = str(tmp_path / 'future.db')
    with sqlite3.connect(path) as conn:
        conn.execute('PRAGMA user_version=999')
    cli = str(Path(sys.executable).parent / 'memori')
    result = subprocess.run([cli, '--db', path, '--json', 'count'], capture_output=True, text=True, timeout=30)
    assert result.returncode == 2
    assert json.loads(result.stderr)['error'] == 'unsupported_schema'
    assert result.stdout == ''
