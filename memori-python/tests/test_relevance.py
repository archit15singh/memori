"""Relevance gating is on raw cosine, not popularity or fused RRF scores."""
import json
import threading
import subprocess
import sys
from http.server import HTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest
from memori import PyMemori
from memori_cli import DashboardHandler


@pytest.fixture
def db(tmp_path):
    return PyMemori(str(tmp_path / 'relevance.db'))


def test_vector_threshold_precedes_access_boost_and_limit(db):
    best = db.insert('best', vector=[1., 0.])['id']
    weak = db.insert('weak', vector=[0.8, 0.6])['id']
    db.set_access_stats(weak, access_count=1000000, last_accessed=2000000000.)
    assert db.search(vector=[1., 0.], limit=1)[0]['id'] == weak
    assert [m['id'] for m in db.search(vector=[1., 0.], min_similarity=0.9, limit=1)] == [best]


def test_hybrid_keeps_literal_matches_but_rejects_weak_semantic_candidates(db):
    exact = db.insert('PostgreSQL architecture', vector=[0., 1.])['id']
    db.insert('unrelated item', vector=[0., 1.])
    results = db.search(text='PostgreSQL', vector=[1., 0.], min_similarity=0.9)
    assert [m['id'] for m in results] == [exact]
    assert db.search(text='bananas', vector=[1., 0.], min_similarity=0.9) == []


def test_threshold_boundary_and_related(db):
    source = db.insert('source', vector=[1., 0.])['id']
    other = db.insert('identical vector', vector=[1., 0.])['id']
    db.insert('orthogonal', vector=[0., 1.])
    assert len(db.search(vector=[1., 0.], min_similarity=1.)) == 2
    assert [m['id'] for m in db.related(source, min_similarity=1.)] == [other]


def test_filters_still_apply_and_zero_limit_is_empty(db):
    first = db.insert('first', vector=[1., 0.], metadata={'type': 'fact'})['id']
    db.insert('second', vector=[1., 0.], metadata={'type': 'decision'})
    assert [m['id'] for m in db.search(vector=[1., 0.], filter={'type': 'fact'}, min_similarity=0.9)] == [first]
    assert db.search(vector=[1., 0.], min_similarity=0.9, limit=0) == []


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1.1, 1.1, -1.00000001, 1.00000001])
def test_invalid_threshold(db, value):
    with pytest.raises(RuntimeError, match='similarity'):
        db.search(vector=[1., 0.], min_similarity=value)
    source = db.insert('source', vector=[1., 0.])['id']
    with pytest.raises(RuntimeError, match='similarity'):
        db.related(source, min_similarity=value)


def test_threshold_requires_a_vector_search(db):
    with pytest.raises(RuntimeError, match='similarity'):
        db.search(min_similarity=0.5)
    with pytest.raises(RuntimeError, match='similarity'):
        db.search(text='hello', text_only=True, min_similarity=0.5)


def test_cli_search_and_related_threshold(tmp_path):
    path = str(tmp_path / 'cli.db')
    db = PyMemori(path)
    mid = db.insert('one', vector=[1., 0.])['id']
    db.insert('two', vector=[0., 1.])
    cli = str(Path(sys.executable).parent / 'memori')
    def run(*args):
        return subprocess.run([cli, '--db', path, '--json', *args], capture_output=True, text=True, timeout=120)
    result = run('search', '--vector', '[1,0]', '--min-similarity', '0.9')
    assert result.returncode == 0, result.stderr
    assert [m['id'] for m in json.loads(result.stdout)] == [mid]
    result = run('related', mid, '--min-similarity', '0.9')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == []
    result = run('search', '--vector', '[1,0]', '--min-similarity', 'nan')
    assert result.returncode == 2
    assert json.loads(result.stderr)['error'] == 'invalid_similarity'
    result = run('search', '--text', 'hello', '--text-only', '--min-similarity', '0.5')
    assert result.returncode == 2
    assert json.loads(result.stderr)['error'] == 'invalid_similarity'


def test_cli_context_rejects_unrelated_semantic_matches(tmp_path):
    path = str(tmp_path / 'context.db')
    db = PyMemori(path)
    mid = db.insert('PostgreSQL stores application data in a relational database')['id']
    cli = str(Path(sys.executable).parent / 'memori')
    def run(*extra):
        return subprocess.run([cli, '--db', path, '--json', 'context', 'banana bread recipe', *extra], capture_output=True, text=True, timeout=120)
    before = run()
    assert before.returncode == 0, before.stderr
    assert json.loads(before.stdout)['matches'][0]['id'] == mid
    after = run('--min-similarity', '1')
    assert after.returncode == 0, after.stderr
    data = json.loads(after.stdout)
    assert data['matches'] == []
    assert data['recent'][0]['id'] == mid  # contextual browsing is separate from search relevance


def test_dashboard_http_threshold_and_errors(db):
    source = db.insert('PostgreSQL relational database')['id']
    other = db.insert('Relational database query indexing')['id']
    class Handler(DashboardHandler):
        pass
    Handler.db = db
    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    def get(path):
        with urlopen(base + path, timeout=30) as response:
            return json.load(response)
    try:
        assert get('/api/search?text=banana%20bread')
        assert get('/api/search?text=banana%20bread&min_similarity=1') == []
        assert get('/api/search?text=PostgreSQL&min_similarity=1')[0]['id'] == source
        assert get(f'/api/related/{source}')[0]['id'] == other
        assert get(f'/api/related/{source}?min_similarity=1') == []
        for path in ['/api/search?text=test&min_similarity=nan', '/api/search?min_similarity=0.5', '/api/search?text=test&text_only=true&min_similarity=0.5', f'/api/related/{source}?min_similarity=1.1']:
            with pytest.raises(HTTPError) as exc:
                get(path)
            assert exc.value.code == 400
            assert json.load(exc.value)['error']
        assert get('/api/stats')['count'] == 2  # server remains healthy after invalid input
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
