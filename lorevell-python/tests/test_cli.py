"""Lorevell 2 product interface: actual commands against disposable Markdown vaults."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from lorevell import PyVault

CLI = str(Path(sys.executable).parent / 'lorevell')


def run(root, *args, input=None, check=True):
    result = subprocess.run([CLI, '--vault', str(root), *args], input=input,
                            capture_output=True, text=True, timeout=60)
    if check:
        assert result.returncode == 0, result.stderr
    return result


def note(root, path, mid, body):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f'---\nid: {mid}\ntype: procedure\ntags: [debugging]\n---\n\n{body}\n')
    return target


def test_cross_process_learning_recall_and_human_edits(tmp_path):
    root = tmp_path / 'knowledge'
    run(root, 'init')
    saved = json.loads(run(root, 'add', '# Bisect\nUse git bisect for a known regression.', '--type', 'procedure', '--tag', 'git', '--text-only', '--json').stdout)['note']
    # This search is an independent process: session-local Python state cannot supply recall.
    found = json.loads(run(root, 'search', 'bisect', '--text-only', '--json').stdout)
    assert found['matches'][0]['note']['id'] == saved['id']
    path = root / saved['path']
    path.write_text(path.read_text().replace('bisect', 'canary').replace('Bisect', 'Canary'))
    run(root, 'index', '--text-only')
    assert json.loads(run(root, 'search', 'bisect', '--text-only', '--json').stdout)['matches'] == []
    assert json.loads(run(root, 'search', 'canary', '--text-only', '--json').stdout)['matches']
    for cache in (root / '.lorevell').glob('index.sqlite*'):
        cache.unlink()
    run(root, 'index', '--text-only')
    assert json.loads(run(root, 'search', 'canary', '--text-only', '--json').stdout)['matches'][0]['note']['id'] == saved['id']


def test_show_links_backlinks_graph_limits_and_archive(tmp_path):
    note(tmp_path, 'first.md', 'first', 'quasar [[second]]')
    original = note(tmp_path, 'second.md', 'second', 'linked procedure').read_bytes()
    run(tmp_path, 'index', '--text-only')
    show = json.loads(run(tmp_path, 'show', 'second', '--json').stdout)
    assert [n['id'] for n in show['backlinks']] == ['first']
    hits = json.loads(run(tmp_path, 'search', 'quasar', '--text-only', '--graph-limit', '1', '--json').stdout)
    assert [h['note']['id'] for h in hits['context']] == ['second']
    assert 'Linked context' in run(tmp_path, 'search', 'quasar', '--text-only').stdout
    run(tmp_path, 'delete', 'second', '--text-only')
    assert (tmp_path / 'archive/second.md').read_bytes() == original
    show = json.loads(run(tmp_path, 'show', 'first', '--json').stdout)
    assert show['outgoing'] == [] and show['unresolved'] == ['second']


def test_stdin_file_update_types_and_prefixes(tmp_path):
    saved = json.loads(run(tmp_path, 'add', '-', '--text-only', '--json', input='# Procedure\nOriginal instructions').stdout)['note']
    body = tmp_path / 'body.txt'
    body.write_text('# Procedure\nCorrected instructions')
    run(tmp_path, 'update', saved['id'][:12], '--file', str(body), '--meta', '{"verified":true}', '--text-only')
    found = json.loads(run(tmp_path, 'show', saved['id'], '--json').stdout)['note']
    assert 'Corrected' in found['content'] and found['metadata']['verified'] is True
    assert saved['metadata']['created_at'] == found['metadata']['created_at']


def test_real_hybrid_semantic_retrieval_and_literal_floor(tmp_path):
    run(tmp_path, 'add', '# Database\nPostgreSQL transactions make writes atomic.', '--type', 'fact')
    run(tmp_path, 'add', '# Cooking\nBanana bread uses ripe fruit and flour.', '--type', 'fact')
    result = json.loads(run(tmp_path, 'search', 'atomic database writes', '--min-similarity', '0.4', '--json').stdout)
    assert 'PostgreSQL' in result['matches'][0]['note']['content']
    literal = json.loads(run(tmp_path, 'search', 'PostgreSQL', '--min-similarity', '1', '--json').stdout)
    assert len(literal['matches']) == 1


@pytest.mark.parametrize('args', [
    ['show', 'missing'], ['add', '', '--text-only'], ['search', '   ', '--text-only'],
    ['search', 'q', '--text-only', '--min-similarity', '0.4'],
    ['search', 'q', '--min-similarity', 'nan'], ['add', 'x', '--meta', '[1]'],
    ['add', 'x', '--meta', '{bad'], ['update', 'missing', '--content', 'new', '--text-only'],
])
def test_structured_errors(tmp_path, args):
    result = run(tmp_path, *args, '--json', check=False)
    assert result.returncode != 0
    assert 'message' in json.loads(result.stderr)


def test_parse_errors_and_small_help_surface(tmp_path):
    assert run(tmp_path, 'search', 'q', '--limit', '-1', check=False).returncode == 2
    for command in ['init','add','update','archive','index','search','show','setup','dream']:
        assert 'usage:' in run(tmp_path, command, '--help').stdout


@pytest.mark.parametrize('agent,dirname', [('codex','.agents'), ('claude','.claude')])
def test_setup_installs_shared_skills_without_overwriting_customizations(tmp_path, agent, dirname):
    project = tmp_path / 'project'
    result = json.loads(run(tmp_path, 'setup', '--agent', agent, '--project', str(project), '--json').stdout)
    assert len(result['installed']) == 2
    learned = project / dirname / 'skills/lorevell/SKILL.md'
    assert 'After a meaningful discovery' in learned.read_text()
    learned.write_text('custom instructions')
    assert run(tmp_path, 'setup', '--agent', agent, '--project', str(project), check=False).returncode == 1
    assert learned.read_text() == 'custom instructions'
    run(tmp_path, 'setup', '--agent', agent, '--project', str(project), '--force')
    assert 'After a meaningful discovery' in learned.read_text()


def test_failed_reindex_retains_search_cache(tmp_path):
    note(tmp_path, 'a.md', 'a', 'original phrase')
    vault = PyVault(str(tmp_path)); vault.index(embeddings=False)
    note(tmp_path, 'duplicate.md', 'a', 'conflicting phrase')
    result = run(tmp_path, 'index', '--text-only', '--json', check=False)
    assert result.returncode == 1 and 'duplicate id' in json.loads(result.stderr)['message']
    (tmp_path / 'duplicate.md').unlink()
    assert vault.search('original', text_only=True)['matches'][0]['note']['id'] == 'a'


def test_packaged_skills_match_the_canonical_sources():
    root = Path(__file__).resolve().parents[2]
    for name in ['lorevell','dream']:
        assert (root / 'skills' / name / 'SKILL.md').read_bytes() == (root / 'lorevell-python/python/lorevell_cli/data' / name / 'SKILL.md').read_bytes()


@pytest.mark.skipif(os.name == 'nt', reason='symlink creation needs platform privileges')
def test_init_and_setup_do_not_write_through_external_symlinks(tmp_path):
    root = tmp_path / 'vault'
    root.mkdir()
    external = tmp_path / 'external'
    external.mkdir()
    destination = external / 'ignore'
    destination.write_text('preserve')
    (root / '.gitignore').symlink_to(destination)
    assert run(root, 'init', check=False).returncode == 1
    assert destination.read_text() == 'preserve'
    (root / '.agents').symlink_to(external, target_is_directory=True)
    assert run(root, 'setup', '--agent', 'codex', '--project', str(root), check=False).returncode == 1
    assert not (external / 'skills').exists()


def test_error_identifies_a_successful_file_write_before_index_failure(tmp_path):
    (tmp_path / 'broken.md').write_text('invalid note')
    result = run(tmp_path, 'add', 'retained lesson', '--text-only', '--json', check=False)
    assert result.returncode == 1
    assert 'Markdown was saved' in json.loads(result.stderr)['message']
    assert any('retained lesson' in p.read_text() for p in tmp_path.glob('*.md'))
