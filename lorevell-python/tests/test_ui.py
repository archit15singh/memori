"""Real loopback HTTP, native retrieval and Markdown persistence; no model required."""
from http.client import HTTPConnection
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

import pytest

from lorevell_cli.ui import CompanionServer


def write_note(root, path, mid, body):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f'---\nid: {mid}\ntype: procedure\n---\n{body}\n')
    return target


@pytest.fixture
def companion(tmp_path):
    server = CompanionServer(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
    assert not thread.is_alive()


def request(server, path, body=None, headers=None, token=True):
    connection = HTTPConnection('127.0.0.1', server.server_port, timeout=10)
    supplied = {'X-Lorevell-Token': server.token} if token else {}
    if body is not None:
        supplied['Content-Type'] = 'application/json'
    supplied.update(headers or {})
    connection.request('POST' if body is not None else 'GET', path,
                       body=json.dumps(body) if body is not None else None, headers=supplied)
    response = connection.getresponse()
    data = response.read()
    result = (response.status, dict(response.getheaders()),
              json.loads(data) if response.getheader('Content-Type').startswith('application/json') else data.decode())
    connection.close()
    return result


def test_recall_read_connections_and_external_edits(companion):
    root = companion.root
    first = write_note(root, 'bisect.md', 'bisect', '# Regression\nUse bisect for quasar regressions. [[rollback]]')
    write_note(root, 'rollback.md', 'rollback', '# Undo\nUse git revert.')
    write_note(root, 'archive/old.md', 'old', '# Old\nquasar')
    write_note(root, '.hidden/private.md', 'private', '# Hidden\nquasar')
    status, _, catalog = request(companion, '/api/catalog')
    assert status == 200 and catalog['total'] == 2
    assert [n['path'] for n in catalog['notes']] == ['bisect.md', 'rollback.md']
    status, _, hits = request(companion, '/api/search?q=quasar')
    assert status == 200 and hits['matches'][0]['id'] == 'bisect'
    assert hits['context'][0]['id'] == 'rollback'
    status, _, view = request(companion, '/api/note?id=rollback')
    assert status == 200 and view['backlinks'][0]['id'] == 'bisect'
    assert view['absolute_path'] == str(root / 'rollback.md')
    assert 'git revert' in view['note']['content']
    first.write_text(first.read_text().replace('quasar', 'canary'))
    assert request(companion, '/api/index', {})[0] == 200
    assert request(companion, '/api/search?q=quasar')[2]['matches'] == []
    assert request(companion, '/api/search?q=canary')[2]['matches'][0]['id'] == 'bisect'
    assert request(companion, '/api/search?q=canary&type=decision')[2]['matches'] == []


def test_capture_is_markdown_and_recalled_after_reopening(companion):
    status, _, saved = request(companion, '/api/notes', {
        'title': 'Bound retries', 'content': 'Retry idempotent requests with jitter.', 'type': 'procedure'})
    assert status == 201 and saved['warning'] is None
    note = saved['note']
    source = (companion.root / note['path']).read_text()
    assert '# Bound retries' in source and 'id: ' in source
    assert request(companion, '/api/search?q=jitter')[2]['matches'][0]['id'] == note['id']
    # A separate native instance sees ordinary files, not server-local state.
    from lorevell import PyVault
    reopened = PyVault(str(companion.root))
    reopened.index(embeddings=False)
    assert reopened.search('jitter', text_only=True)['matches'][0]['note']['id'] == note['id']


def test_saved_note_is_not_reported_as_failed_when_another_file_breaks_index(companion):
    (companion.root / 'broken.md').write_text('no frontmatter')
    status, _, saved = request(companion, '/api/notes', {'title': 'Evidence', 'content': 'Keep original bytes.'})
    assert status == 201 and 'saved' in saved['warning']
    assert (companion.root / saved['note']['path']).exists()
    assert 'Keep original bytes.' in saved['note']['content']


@pytest.mark.parametrize('payload', [[], {'title': '', 'content': 'body'},
    {'title': 'two\nlines', 'content': 'body'}, {'title': 'Fine', 'content': ''},
    {'title': 'Fine', 'content': 'body', 'type': 'unknown'}])
def test_invalid_capture_never_writes(companion, payload):
    assert request(companion, '/api/notes', payload)[0] == 422
    assert list(companion.root.glob('*.md')) == []


def test_loopback_boundary_and_static_assets(companion):
    assert companion.server_address[0] == '127.0.0.1'
    assert request(companion, '/api/catalog', token=False)[0] == 403
    assert request(companion, '/api/catalog', headers={'Origin': 'https://evil.example'})[0] == 403
    assert request(companion, '/', headers={'Host': 'evil.example'})[0] == 403
    assert request(companion, '/api/notes', {'title': 'Injected', 'content': 'body'}, token=False)[0] == 403
    assert list(companion.root.glob('*.md')) == []
    status, headers, html = request(companion, '/', token=False)
    assert status == 200 and companion.token in html and '__TOKEN__' not in html
    assert "default-src 'none'" in headers['Content-Security-Policy']
    assert "frame-ancestors 'none'" in headers['Content-Security-Policy']
    assert headers['Cache-Control'] == 'no-store'
    assert request(companion, '/app.js')[0] == 200
    assert request(companion, '/style.css')[0] == 200
    assert request(companion, '/../ui.py')[0] == 404
    assert request(companion, '/api/search?q=')[0] == 422
    assert request(companion, '/api/search?q=hello&mode=bogus')[0] == 422


def test_malformed_source_returns_actionable_error_and_recovers(companion):
    broken = companion.root / 'broken.md'
    broken.write_text('not a note')
    status, _, error = request(companion, '/api/catalog')
    assert status == 422 and error['error']
    broken.unlink()
    assert request(companion, '/api/catalog')[2]['total'] == 0


def test_cli_launches_packaged_workspace_without_opening_a_browser(tmp_path):
    cli = str(Path(sys.executable).parent / 'lorevell')
    invalid = subprocess.run([cli, 'ui', '--port', '-1', '--no-open'], capture_output=True, text=True)
    assert invalid.returncode != 0 and 'port' in invalid.stderr
    log = tmp_path / 'server.log'
    with log.open('w') as output:
        process = subprocess.Popen([cli, '--vault', str(tmp_path / 'vault'), 'ui', '--port', '0', '--no-open'],
                                   stdout=output, stderr=output)
        try:
            deadline = time.monotonic() + 15
            match = None
            while time.monotonic() < deadline:
                match = re.search(r'http://127.0.0.1:(\d+)', log.read_text())
                if match or process.poll() is not None:
                    break
                time.sleep(0.05)
            assert match, log.read_text()
            connection = HTTPConnection('127.0.0.1', int(match[1]), timeout=5)
            connection.request('GET', '/')
            response = connection.getresponse()
            html = response.read().decode()
            connection.close()
            assert response.status == 200 and 'Search your knowledge' in html
            assert '__TOKEN__' not in html
        finally:
            process.terminate()
            process.wait(timeout=5)
