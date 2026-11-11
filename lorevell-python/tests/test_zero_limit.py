"""Empty requests must not depend on an available embedding model."""
import json
import os
from pathlib import Path
import sysconfig
import subprocess
import sys

import pytest


@pytest.mark.parametrize(("query", "limit"), [("some query", 0), (" \t\n", 3)])
def test_empty_requests_native_and_cli_do_not_initialize_model(tmp_path, query, limit):
    blocked = tmp_path / 'model-cache-is-a-file'
    blocked.write_text('not a directory')
    env = dict(os.environ, FASTEMBED_CACHE_DIR=str(blocked))
    code = f"""
from lorevell import PyLorevell
db = PyLorevell(':memory:')
db.insert('Existing procedure', vector=[1.0, 0.0])
assert db.search(text={query!r}, limit={limit}) == []
assert len(db.search()) == 1  # No text still means recent-note browsing.
"""
    native = subprocess.run([sys.executable, '-c', code], cwd=tmp_path,
                            env=env, text=True, capture_output=True, timeout=15)
    assert native.returncode == 0, native.stderr
    cli = Path(sysconfig.get_path('scripts')) / ('lorevell.exe' if os.name == 'nt' else 'lorevell')
    assert cli.is_file()
    vault = tmp_path / 'vault'
    subprocess.run([cli, '--vault', str(vault), 'add', 'Unembedded procedure',
                    '--text-only'], cwd=tmp_path, env=env, check=True,
                   capture_output=True, text=True)
    result = subprocess.run([cli, '--vault', str(vault), 'search', query,
                             '--limit', str(limit), '--json'], cwd=tmp_path, env=env,
                            text=True, capture_output=True, timeout=15)
    if query.strip():
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == {'matches': [], 'context': []}
    else:
        assert result.returncode == 1
        assert json.loads(result.stderr)['message'] == 'search text must not be empty'
        assert 'model' not in result.stderr
