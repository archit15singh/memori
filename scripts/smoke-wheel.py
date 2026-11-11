"""Exercise a wheel-installed CLI, native vault and bundled skills without a model."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from lorevell import PyVault

cli = shutil.which('lorevell')
if not cli:
    raise SystemExit('Installed lorevell executable is missing from PATH')
with tempfile.TemporaryDirectory(prefix='lorevell-wheel-') as directory:
    root = Path(directory)
    vault = root / 'vault'
    env = dict(os.environ, LOREVELL_VAULT=str(vault))

    def run(*args):
        result = subprocess.run([cli, *args], env=env, text=True,
                                capture_output=True, check=True)
        return json.loads(result.stdout)

    run('init', '--json')
    note = run('add', 'Use a transaction for atomic SQLite writes.',
               '--type', 'procedure', '--text-only', '--json')
    hits = run('search', 'SQLite', '--text-only', '--json')
    assert hits['matches'], hits
    assert PyVault(str(vault)).show(hits['matches'][0]['note']['id'])['note']['content']
    for agent in ('codex', 'claude'):
        run('setup', '--agent', agent, '--project', str(root), '--json')
    assert (root / '.agents/skills/lorevell/SKILL.md').is_file()
    assert (root / '.claude/skills/lorevell-dream/SKILL.md').is_file()
    preview = run('dream', '--agent', 'codex', '--dry-run', '--json')
    assert preview['status'] == 'preview', preview
    assert (vault / '.lorevell/index.sqlite').is_file()
print('PASS: installed CLI, native vault, add/search, both packaged skills and dream preview')
