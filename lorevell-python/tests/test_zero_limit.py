"""A zero-result request must not depend on an available embedding model."""
import json
import os
import shutil
import subprocess
import sys


def test_zero_limit_native_and_cli_do_not_initialize_model(tmp_path):
    blocked = tmp_path / 'model-cache-is-a-file'
    blocked.write_text('not a directory')
    env = dict(os.environ, FASTEMBED_CACHE_DIR=str(blocked))
    code = '''
from lorevell import PyLorevell
assert PyLorevell(':memory:').search(text='some query', limit=0) == []
'''
    native = subprocess.run([sys.executable, '-c', code], cwd=tmp_path,
                            env=env, text=True, capture_output=True, timeout=15)
    assert native.returncode == 0, native.stderr
    cli = shutil.which('lorevell')
    assert cli
    vault = tmp_path / 'vault'
    subprocess.run([cli, '--vault', str(vault), 'add', 'Unembedded procedure',
                    '--text-only'], cwd=tmp_path, env=env, check=True,
                   capture_output=True, text=True)
    result = subprocess.run([cli, '--vault', str(vault), 'search', 'some query',
                             '--limit', '0', '--json'], cwd=tmp_path, env=env,
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'matches': [], 'context': []}
