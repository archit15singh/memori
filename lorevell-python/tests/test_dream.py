"""Launcher contracts use actual subprocesses; live agent evidence is separate."""
import json
from pathlib import Path
import subprocess
import sys

import pytest
from lorevell import PyVault
from lorevell_cli import dream


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / 'vault'
    root.mkdir()
    subprocess.run(['git','init','-q',str(root)],check=True)
    for key,value in [('user.email','test@example.invalid'),('user.name','Lorevell Test')]:
        subprocess.run(['git','-C',str(root),'config',key,value],check=True)
    (root / '.gitignore').write_text('.lorevell/\n.fastembed_cache/\n')
    (root / 'a.md').write_text('---\nid: a\ntype: procedure\n---\n# Example\nOriginal evidence.\n')
    return root


def runner(tmp_path, monkeypatch, code):
    script = tmp_path / 'runner.py'
    script.write_text('import sys, pathlib, time\nprompt=sys.stdin.read()\n'+code)
    monkeypatch.setattr(dream, 'agent_command', lambda agent,root: [sys.executable,str(script)])


def test_success_archives_originals_commits_and_skips_unchanged(vault, tmp_path, monkeypatch):
    runner(tmp_path,monkeypatch,"""
p=pathlib.Path('a.md')
archive=pathlib.Path('archive');archive.mkdir()
(archive/'a.md').write_bytes(p.read_bytes());p.unlink()
pathlib.Path('b.md').write_text('---\\nid: b\\ntype: procedure\\n---\\n# Better\\nOriginal evidence. Reusable procedure.\\n')
""")
    result=dream.run_dream(vault,'codex',max_notes=4)
    assert result['status']=='completed' and result['baseline']!=result['commit']
    assert (vault/'archive/a.md').exists()
    assert PyVault(str(vault)).search('Reusable',text_only=True)['matches'][0]['note']['id']=='b'
    assert dream.run_dream(vault,'codex')['status']=='unchanged'
    assert subprocess.check_output(['git','-C',str(vault),'status','--porcelain'],text=True)==''
    # Rollback is ordinary Git, preserving the forward consolidation commit.
    subprocess.run(['git','-C',str(vault),'revert','--no-edit',result['commit']],check=True,capture_output=True)
    PyVault(str(vault)).index(embeddings=False)
    assert (vault/'a.md').exists() and not (vault/'b.md').exists()


def test_failed_agent_keeps_edits_and_does_not_acknowledge(vault,tmp_path,monkeypatch):
    runner(tmp_path,monkeypatch,"pathlib.Path('a.md').write_text('malformed edit')\nsys.exit(7)\n")
    with pytest.raises(RuntimeError,match='exited 7'):
        dream.run_dream(vault,'codex')
    assert (vault/'a.md').read_text()=='malformed edit'
    assert not (vault/'.lorevell/dream-state.json').exists()
    assert (vault/'.lorevell/dream-last.log').exists()


@pytest.mark.parametrize('code,reason', [
    ("pathlib.Path('a.md').unlink()",'original note was removed'),
    ("pathlib.Path('a.md').write_text('invalid frontmatter')",'invalid note'),
    ("pathlib.Path('unrelated.txt').write_text('outside knowledge')",'non-knowledge files'),
])
def test_validation_failure_does_not_commit_or_advance(vault,tmp_path,monkeypatch,code,reason):
    runner(tmp_path,monkeypatch,code)
    with pytest.raises(RuntimeError,match=reason):
        dream.run_dream(vault,'codex')
    assert not (vault/'.lorevell/dream-state.json').exists()
    assert subprocess.check_output(['git','-C',str(vault),'log','--format=%s'],text=True).strip()=='chore(lorevell): snapshot knowledge before dream'


def test_timeout_stops_agent_and_preserves_checkpoint(vault,tmp_path,monkeypatch):
    runner(tmp_path,monkeypatch,"time.sleep(30)")
    with pytest.raises(RuntimeError,match='timed out'):
        dream.run_dream(vault,'codex',timeout=.1)
    assert not (vault/'.lorevell/dream-state.json').exists()


def test_batch_checkpoint_does_not_skip_pending_files(vault,tmp_path,monkeypatch):
    (vault/'z.md').write_text('---\nid: z\n---\nPending knowledge.\n')
    runner(tmp_path,monkeypatch,"print('No consolidation needed.')")
    one=dream.run_dream(vault,'codex',max_notes=1)
    assert one['candidates']==['a.md'] and one['pending']==1
    two=dream.run_dream(vault,'codex',max_notes=1)
    assert two['candidates']==['z.md'] and two['pending']==0
    assert dream.run_dream(vault,'codex')['status']=='unchanged'


def test_original_source_is_excluded_and_edits_are_rejected(vault,tmp_path,monkeypatch):
    source = vault / 'source.md'
    source.write_text('---\nid: source\nimmutable_source: true\n---\nOriginal evidence.\n')
    preview = dream.run_dream(vault, 'codex', dry_run=True)
    assert preview['candidates'] == ['a.md']
    runner(tmp_path, monkeypatch, "pathlib.Path('source.md').write_text('damaged evidence')")
    with pytest.raises(RuntimeError, match='immutable source'):
        dream.run_dream(vault, 'codex')
    assert not (vault / '.lorevell/dream-state.json').exists()
    baseline = subprocess.check_output(['git','-C',str(vault),'show','HEAD:source.md'],text=True)
    assert 'Original evidence.' in baseline


def test_dry_run_needs_no_agent_and_makes_no_git_commit(vault):
    result=dream.run_dream(vault,'claude',dry_run=True)
    assert result['status']=='preview' and result['candidates']==['a.md']
    assert not (vault/'.lorevell/dream-state.json').exists()
    assert subprocess.run(['git','-C',str(vault),'rev-parse','--verify','HEAD'],capture_output=True).returncode!=0


def test_unrelated_dirty_files_are_never_staged(vault,tmp_path,monkeypatch):
    (vault/'private.txt').write_text('do not stage')
    runner(tmp_path,monkeypatch,"print('should not run')")
    with pytest.raises(ValueError,match='non-knowledge changes'):
        dream.run_dream(vault,'codex')
    assert subprocess.check_output(['git','-C',str(vault),'diff','--cached','--name-only'],text=True)==''


def test_nested_git_scope_is_rejected(tmp_path):
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    child=tmp_path/'nested'
    with pytest.raises(ValueError,match='dedicated Git repository'):
        dream.run_dream(child,'codex')


def test_missing_agent_is_explicit(vault,monkeypatch):
    monkeypatch.setattr(dream.shutil,'which',lambda executable:None)
    with pytest.raises(ValueError,match='not installed'):
        dream.run_dream(vault,'claude')
    assert not (vault/'.lorevell/dream-state.json').exists()


def test_agent_staging_is_not_silently_committed(vault,tmp_path,monkeypatch):
    runner(tmp_path,monkeypatch,"""
import subprocess
p=pathlib.Path('a.md');p.write_text(p.read_text()+'extra evidence\\n')
subprocess.run(['git','add','a.md'],check=True)
""")
    with pytest.raises(RuntimeError,match='staging'):
        dream.run_dream(vault,'codex')
    assert not (vault/'.lorevell/dream-state.json').exists()


@pytest.mark.parametrize('state', [[], {'hashes': []}, {'hashes': {'../outside.md': 'bad'}}])
def test_invalid_checkpoint_is_an_actionable_error(vault,state):
    PyVault(str(vault))
    (vault/'.lorevell/dream-state.json').write_text(json.dumps(state))
    with pytest.raises(ValueError,match='invalid dream checkpoint'):
        dream.run_dream(vault,'codex',dry_run=True)


@pytest.mark.parametrize('operation', [
    "p.write_text('rewritten evidence')", "p.unlink()",
    "p.rename('archive/moved.md')",
])
def test_existing_archive_is_immutable(vault, tmp_path, monkeypatch, operation):
    archive = vault / 'archive'
    archive.mkdir()
    original = b'Original archived evidence.\n'
    (archive / 'old.md').write_bytes(original)
    runner(tmp_path, monkeypatch, "p=pathlib.Path('archive/old.md')\n" + operation)
    with pytest.raises(RuntimeError, match='changed archived evidence'):
        dream.run_dream(vault, 'codex')
    assert not (vault / '.lorevell/dream-state.json').exists()
    assert subprocess.check_output(['git', '-C', str(vault), 'show', 'HEAD:archive/old.md']) == original
    assert subprocess.check_output(['git', '-C', str(vault), 'rev-list', '--count', 'HEAD'], text=True).strip() == '1'


@pytest.mark.parametrize('change', ['missing', 'ambiguous'])
def test_new_unresolved_links_do_not_commit_or_acknowledge(vault, tmp_path, monkeypatch, change):
    if change == 'missing':
        code = "p=pathlib.Path('a.md');p.write_text(p.read_text()+'[[absent]]\\n')"
    else:
        (vault / 'first').mkdir()
        (vault / 'first/target.md').write_text('---\nid: target-one\n---\nTarget.\n')
        with (vault / 'a.md').open('a') as output:
            output.write('[[target]]\n')
        code = "pathlib.Path('nested').mkdir();pathlib.Path('nested/target.md').write_text('---\\nid: target-two\\n---\\nAnother target.\\n')"
    runner(tmp_path, monkeypatch, code)
    with pytest.raises(RuntimeError, match='introduced unresolved links'):
        dream.run_dream(vault, 'codex')
    assert not (vault / '.lorevell/dream-state.json').exists()
    assert subprocess.check_output(['git', '-C', str(vault), 'rev-list', '--count', 'HEAD'], text=True).strip() == '1'


def test_existing_unresolved_link_can_be_retained_after_rename(vault, tmp_path, monkeypatch):
    with (vault / 'a.md').open('a') as output:
        output.write('[[existing-missing]]\n')
    runner(tmp_path, monkeypatch, "pathlib.Path('a.md').rename('renamed.md')")
    result = dream.run_dream(vault, 'codex')
    assert result['status'] == 'completed'
    assert len(result['index']['unresolved']) == 1


def test_due_review_runs_without_file_changes_and_does_not_verify(vault, tmp_path, monkeypatch):
    from lorevell_cli.review import run_review
    clock = [1_000_000.0]
    monkeypatch.setattr(dream.time, 'time', lambda: clock[0])
    (vault / 'a.md').write_text('---\nid: a\nreview_after_days: 1\n---\nOriginal evidence.\n')
    runner(tmp_path, monkeypatch, "print('Inspected; evidence not newly verified.')")
    assert dream.run_dream(vault, 'codex')['status'] == 'completed'
    assert dream.run_dream(vault, 'codex')['status'] == 'unchanged'
    assert not (vault / '.lorevell/review.json').exists()
    clock[0] += 2 * 86400
    result = dream.run_dream(vault, 'codex')
    assert result['status'] == 'completed' and result['candidates'] == ['a.md']
    assert result['review_reasons']['a.md']
    assert dream.run_dream(vault, 'codex')['status'] == 'unchanged'
    # Successful maintenance must not stamp the independent evidence-review queue.
    assert run_review(vault)['candidates'][0]['reasons'] == ['changed-or-never-reviewed']


def test_reviewed_note_becomes_dream_candidate_and_deferral_is_respected(vault, tmp_path, monkeypatch):
    from lorevell_cli.review import run_review
    clock = [1_000_000.0]
    monkeypatch.setattr(dream.time, 'time', lambda: clock[0])
    runner(tmp_path, monkeypatch, "print('No edits needed.')")
    dream.run_dream(vault, 'codex')
    candidate = run_review(vault)['candidates'][0]
    run_review(vault, mark='a', expected=candidate['revision'])
    clock[0] += 91 * 86400
    candidate = run_review(vault)['candidates'][0]
    run_review(vault, defer='a', expected=candidate['revision'])
    assert dream.run_dream(vault, 'codex')['status'] == 'unchanged'
    clock[0] += 86401
    result = dream.run_dream(vault, 'codex')
    assert result['review_reasons']['a.md'] == ['review-due']
    assert dream.run_dream(vault, 'codex')['status'] == 'unchanged'


def test_source_drift_wakes_dream_without_rebaselining(vault, tmp_path, monkeypatch):
    from lorevell_cli.review import run_review
    source = tmp_path / 'Makefile'
    source.write_text('build: old\n')
    run_review(vault, watch=source, note_id='a')
    # The first pass is new knowledge, before source drift is introduced.
    runner(tmp_path, monkeypatch, "print('Initial inspection.')")
    dream.run_dream(vault, 'codex')
    source.write_text('build: new\n')
    runner(tmp_path, monkeypatch, "assert 'source-drift' in prompt")
    result = dream.run_dream(vault, 'codex')
    assert 'source-drift' in result['review_reasons']['a.md']
    assert dream.run_dream(vault, 'codex')['status'] == 'unchanged'
    assert run_review(vault)['candidates'][0]['source_drift'] == [str(source)]


def test_maintenance_queue_does_not_starve_after_twenty_notes(vault, tmp_path, monkeypatch):
    for i in range(24):
        (vault / f'n{i:02}.md').write_text(f'---\nid: n{i:02}\n---\nEvidence {i}.\n')
    runner(tmp_path, monkeypatch, "print('Inspected.')")
    first = dream.run_dream(vault, 'codex', max_notes=20)
    assert first['pending'] == 5
    second = dream.run_dream(vault, 'codex', max_notes=20)
    assert len(second['candidates']) == 5 and second['pending'] == 0
    assert dream.run_dream(vault, 'codex')['status'] == 'unchanged'


def test_failed_maintenance_does_not_advance_attempt(vault, tmp_path, monkeypatch):
    clock = [1_000_000.0]
    monkeypatch.setattr(dream.time, 'time', lambda: clock[0])
    runner(tmp_path, monkeypatch, "print('Initial inspection.')")
    dream.run_dream(vault, 'codex')
    state = (vault / '.lorevell/dream-state.json').read_bytes()
    clock[0] += 91 * 86400
    runner(tmp_path, monkeypatch, "sys.exit(7)")
    with pytest.raises(RuntimeError, match='exited 7'):
        dream.run_dream(vault, 'codex')
    assert (vault / '.lorevell/dream-state.json').read_bytes() == state
    assert dream.run_dream(vault, 'codex', dry_run=True)['candidates'] == ['a.md']


def evaluation_file(tmp_path, relevant_ids=None):
    path = tmp_path / 'held-out.json'
    path.write_text(json.dumps({'queries': [{'query': 'Original evidence unique-evaluation-marker',
                                             'relevant_ids': relevant_ids or ['a']}]}))
    return path


def test_evaluation_gate_accepts_equal_quality_and_keeps_labels_out_of_prompt(vault, tmp_path, monkeypatch):
    labels = evaluation_file(tmp_path)
    runner(tmp_path, monkeypatch, "assert 'unique-evaluation-marker' not in prompt\nprint('No changes.')")
    result = dream.run_dream(vault, 'codex', eval_set=labels, eval_text_only=True)
    quality = result['evaluation']
    assert quality['before'] == quality['after']
    assert quality['before']['top1'] == 1 and quality['mode'] == 'text-only'
    state = json.loads((vault / '.lorevell/dream-state.json').read_text())
    assert state['evaluation'] == quality
    assert 'unique-evaluation-marker' not in json.dumps(state)
    assert not (vault / '.lorevell/dream-evaluation-pending.json').exists()


def test_evaluation_regression_keeps_edits_and_previous_checkpoint(vault, tmp_path, monkeypatch):
    runner(tmp_path, monkeypatch, "print('Initial inspection.')")
    dream.run_dream(vault, 'codex')
    checkpoint = (vault / '.lorevell/dream-state.json').read_bytes()
    # Make a new changed revision without changing the labeled retrievable fact.
    with (vault / 'a.md').open('a') as output:
        output.write('Additional conditions.\n')
    labels = evaluation_file(tmp_path)
    runner(tmp_path, monkeypatch, "pathlib.Path('a.md').write_text('---\\nid: a\\n---\\nBanana bread recipe.\\n')")
    with pytest.raises(RuntimeError, match='retrieval evaluation regressed'):
        dream.run_dream(vault, 'codex', eval_set=labels, eval_text_only=True)
    assert 'Banana bread' in (vault / 'a.md').read_text()
    assert (vault / '.lorevell/dream-state.json').read_bytes() == checkpoint
    assert subprocess.check_output(['git', '-C', str(vault), 'log', '-1', '--format=%s'], text=True).strip() == 'chore(lorevell): snapshot knowledge before dream'
    # An ordinary retry cannot lower the baseline to the rejected working tree.
    runner(tmp_path, monkeypatch, "print('Keep retained edits.')")
    with pytest.raises(RuntimeError, match='retrieval evaluation regressed'):
        dream.run_dream(vault, 'codex', eval_set=labels, eval_text_only=True)
    with pytest.raises(ValueError, match='unfinished retrieval gate'):
        dream.run_dream(vault, 'codex')
    assert (vault / '.lorevell/dream-state.json').read_bytes() == checkpoint
    (vault / 'a.md').write_text('---\nid: a\n---\nOriginal evidence. Additional conditions.\n')
    assert dream.run_dream(vault, 'codex', eval_set=labels, eval_text_only=True)['status'] == 'completed'
    assert not (vault / '.lorevell/dream-evaluation-pending.json').exists()


def test_evaluation_gate_accepts_improvement(vault, tmp_path, monkeypatch):
    labels = tmp_path / 'held-out.json'
    labels.write_text(json.dumps({'queries': [{'query': 'zebra', 'relevant_ids': ['a']}]}))
    runner(tmp_path, monkeypatch, "p=pathlib.Path('a.md');p.write_text(p.read_text()+'Zebra example.\\n')")
    result = dream.run_dream(vault, 'codex', eval_set=labels, eval_text_only=True)
    assert result['evaluation']['before']['top1'] == 0
    assert result['evaluation']['after']['top1'] == 1


def test_evaluation_labels_are_frozen_before_agent_execution(vault, tmp_path, monkeypatch):
    labels = evaluation_file(tmp_path)
    replacement = json.dumps({'queries': [{'query': 'Banana', 'relevant_ids': ['a']}]})
    runner(tmp_path, monkeypatch,
           f"pathlib.Path({str(labels)!r}).write_text({replacement!r})\n"
           "pathlib.Path('a.md').write_text('---\\nid: a\\n---\\nBanana bread.\\n')")
    with pytest.raises(RuntimeError, match='retrieval evaluation regressed'):
        dream.run_dream(vault, 'codex', eval_set=labels, eval_text_only=True)
    assert not (vault / '.lorevell/dream-state.json').exists()


def test_evaluation_gate_defaults_to_hybrid(vault, tmp_path, monkeypatch):
    runner(tmp_path, monkeypatch, "print('No changes.')")
    result = dream.run_dream(vault, 'codex', eval_set=evaluation_file(tmp_path))
    assert result['evaluation']['mode'] == 'hybrid'
    assert result['evaluation']['before']['top1'] == 1


@pytest.mark.parametrize('dataset', [[], {}, {'queries': []},
    {'queries': [{'query': '', 'relevant_ids': ['a']}]},
    {'queries': [{'query': 'test', 'relevant_ids': []}]},
    {'queries': [{'query': 'test', 'relevant_ids': [3]}]},
])
def test_invalid_evaluation_fails_before_snapshot_or_agent(vault, tmp_path, monkeypatch, dataset):
    labels = tmp_path / 'labels.json'
    labels.write_text(json.dumps(dataset))
    runner(tmp_path, monkeypatch, "raise AssertionError('must not run')")
    with pytest.raises(ValueError, match='Evaluation|evaluation'):
        dream.run_dream(vault, 'codex', eval_set=labels)
    assert subprocess.run(['git', '-C', str(vault), 'rev-parse', '--verify', 'HEAD'], capture_output=True).returncode != 0


def test_evaluation_rejects_labels_inside_vault_or_unknown_baseline_ids(vault, tmp_path, monkeypatch):
    labels = evaluation_file(vault)
    with pytest.raises(ValueError, match='outside'):
        dream.run_dream(vault, 'codex', eval_set=labels)
    labels.unlink()
    runner(tmp_path, monkeypatch, "raise AssertionError('must not run')")
    with pytest.raises(ValueError, match='active baseline'):
        dream.run_dream(vault, 'codex', eval_set=evaluation_file(tmp_path, ['absent']))
    with pytest.raises(ValueError, match='requires'):
        dream.run_dream(vault, 'codex', eval_text_only=True)


def test_evaluation_compares_all_three_metrics_without_rounding():
    from lorevell_cli.evaluation import regression
    baseline = {'top1': 10, 'hit_at_3': 20, 'reciprocal_rank_units': 100}
    for metric in baseline:
        after = dict(baseline)
        after[metric] -= 1
        assert regression(baseline, after) == [metric]


def test_failed_gate_requires_matching_labels_and_mode_on_retry(vault, tmp_path, monkeypatch):
    labels = evaluation_file(tmp_path)
    runner(tmp_path, monkeypatch, "sys.exit(7)")
    with pytest.raises(RuntimeError, match='exited 7'):
        dream.run_dream(vault, 'codex', eval_set=labels, eval_text_only=True)
    runner(tmp_path, monkeypatch, "raise AssertionError('must not run')")
    with pytest.raises(ValueError, match='does not match'):
        dream.run_dream(vault, 'codex', eval_set=labels)
    labels.write_text(json.dumps({'queries': [{'query': 'different', 'relevant_ids': ['a']}]}))
    with pytest.raises(ValueError, match='does not match'):
        dream.run_dream(vault, 'codex', eval_set=labels, eval_text_only=True)
    assert not (vault / '.lorevell/dream-state.json').exists()


def test_cli_accepts_evaluation_flags_and_rejects_mode_without_labels(vault, tmp_path, monkeypatch, capsys):
    from lorevell_cli import main
    labels = evaluation_file(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['lorevell', '--vault', str(vault), 'dream', '--agent', 'codex',
                                    '--eval-set', str(labels), '--eval-text-only', '--dry-run', '--json'])
    main()
    assert json.loads(capsys.readouterr().out)['status'] == 'preview'
    monkeypatch.setattr(sys, 'argv', ['lorevell', '--vault', str(vault), 'dream', '--agent', 'codex',
                                    '--eval-text-only'])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1 and 'requires' in capsys.readouterr().err
