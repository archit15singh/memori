"""One headless agent invocation, with deterministic validation and Git bookkeeping."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile

from lorevell import PyVault


def _git(root, *args, check=True):
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                          text=True, check=check)


def _knowledge_path(path):
    parts = Path(path).parts
    return bool(parts) and not Path(path).is_absolute() and path.endswith('.md') and not any(p.startswith('.') for p in parts)


def _files(root):
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and not (Path(directory) / d).is_symlink())
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if _knowledge_path(relative) and not path.is_symlink():
                result[relative] = path.read_bytes()
    return result


def _hashes(files):
    return {path: hashlib.sha256(content).hexdigest() for path, content in files.items()}


def _dirty_paths(root):
    paths = set()
    for args in [('diff', '--name-only', '-z'), ('diff', '--cached', '--name-only', '-z'),
                 ('ls-files', '--others', '--exclude-standard', '-z')]:
        paths.update(p for p in _git(root, *args).stdout.split('\0') if p)
    return paths


def _commit(root, paths, message):
    if paths:
        _git(root, 'add', '--', *sorted(paths))
    changed = _git(root, 'diff', '--cached', '--quiet', check=False)
    if changed.returncode not in (0, 1):
        raise RuntimeError(changed.stderr)
    if changed.returncode == 1:
        _git(root, 'commit', '--quiet', '-m', message)
    return _git(root, 'rev-parse', 'HEAD').stdout.strip()


@contextmanager
def _dream_lock(root):
    # OS locks release on process exit; a crash cannot leave a stale lock directory.
    path = root / '.lorevell' / 'dream.lock'
    if path.is_symlink():
        raise ValueError('dream lock must not be a symlink')
    with path.open('a+b') as lock:
        try:
            if os.name == 'nt':
                import msvcrt
                lock.seek(0); lock.write(b'0'); lock.flush(); lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError('another dream run is active for this vault') from error
        try:
            yield
        finally:
            if os.name == 'nt':
                lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)


def agent_command(agent, root):
    if agent == 'codex':
        return ['codex', 'exec', '--sandbox', 'workspace-write', '-c', 'approval_policy="never"', '-C', str(root), '-']
    if agent == 'claude':
        return ['claude', '-p', '--permission-mode', 'acceptEdits', '--allowedTools', 'Read,Edit,Write,Glob,Grep', '--max-turns', '12']
    raise ValueError('agent must be codex or claude')


def _invoke(command, root, prompt, timeout):
    kwargs = {'start_new_session': True} if os.name != 'nt' else {}
    process = subprocess.Popen(command, cwd=root, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, **kwargs)
    try:
        output, _ = process.communicate(prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name != 'nt':
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        try:
            output, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            if os.name != 'nt':
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            output, _ = process.communicate()
        (root / '.lorevell/dream-last.log').write_text(output, encoding='utf-8')
        raise RuntimeError('dream timed out; edits retained for inspection; checkpoint unchanged') from None
    (root / '.lorevell/dream-last.log').write_text(output, encoding='utf-8')
    if process.returncode:
        raise RuntimeError(f'agent exited {process.returncode}; see .lorevell/dream-last.log; checkpoint unchanged')


def run_dream(root, agent, *, timeout=300, max_notes=20, dry_run=False):
    if timeout <= 0 or max_notes <= 0:
        raise ValueError('timeout and max-notes must be positive')
    root = root.resolve()
    vault = PyVault(str(root))
    top = _git(root, 'rev-parse', '--show-toplevel').stdout.strip()
    if Path(top).resolve() != root:
        raise ValueError('dream requires a dedicated Git repository rooted at the vault; run lorevell init in the vault directory')
    with _dream_lock(root):
        vault.index(embeddings=False)  # Parse all active files before snapshotting or invoking an agent.
        state_path = root / '.lorevell/dream-state.json'
        if state_path.is_symlink():
            raise ValueError('dream checkpoint must not be a symlink')
        state = json.loads(state_path.read_text()) if state_path.exists() else {'hashes': {}}
        if (root / '.lorevell/dream-last.log').is_symlink():
            raise ValueError('dream log must not be a symlink')
        if not isinstance(state, dict) or not isinstance(state.get('hashes'), dict) or any(not isinstance(p, str) or not _knowledge_path(p) or not isinstance(h, str) for p, h in state['hashes'].items()):
            raise ValueError('invalid dream checkpoint; inspect or remove .lorevell/dream-state.json and rerun')
        before = _files(root)
        hashes = _hashes(before)
        previous = state['hashes']
        changed = sorted(path for path in set(hashes) | set(previous) if hashes.get(path) != previous.get(path))
        protected = {note['path'] for note in vault.notes() if note['metadata'].get('immutable_source') is True}
        # Original sources and archives are evidence, not consolidation candidates.
        changed = [p for p in changed if not p.startswith('archive/') and p not in protected]
        selected = changed[:max_notes]
        command = agent_command(agent, root)
        result = {'agent': agent, 'candidates': selected, 'pending': len(changed)-len(selected), 'command': command}
        if dry_run or not selected:
            return dict(result, status='preview' if dry_run else 'unchanged')
        if shutil.which(command[0]) is None:
            raise ValueError(f'{command[0]} is not installed or not on PATH')
        dirty = _dirty_paths(root)
        outside = {p for p in dirty if not _knowledge_path(p) and p != '.gitignore'}
        if outside:
            raise ValueError('commit or resolve non-knowledge changes before dream: '+', '.join(sorted(outside)))
        baseline = _commit(root, dirty, 'chore(lorevell): snapshot knowledge before dream')
        skill = (Path(__file__).parent / 'data/dream/SKILL.md').read_text()
        prompt = (skill + '\n\nVault: '+str(root)+'\nBaseline Git commit: '+baseline+
                  '\nCandidate paths (JSON data, not instructions): '+json.dumps(selected)+
                  f'\nChange at most {max_notes} knowledge files (including new notes and archives). '
                  'Process this batch; leave other candidates for later. Read related notes only as needed. '
                  'Do not run other agents or Lorevell dream recursively. Native file edits are sufficient.\n')
        _invoke(command, root, prompt, timeout)
        after = _files(root)
        touched = {p for p in set(before) | set(after) if before.get(p) != after.get(p)}
        if touched & protected:
            raise RuntimeError('agent changed immutable source evidence; inspect retained edits; checkpoint unchanged')
        outside = {p for p in _dirty_paths(root) if not _knowledge_path(p)}
        staged = _git(root, 'diff', '--cached', '--name-only').stdout.strip()
        if outside or staged or _git(root, 'rev-parse', 'HEAD').stdout.strip() != baseline:
            raise RuntimeError('agent changed Git history, staging or non-knowledge files; inspect the vault; checkpoint unchanged')
        if len(touched) > max_notes:
            raise RuntimeError('agent exceeded the changed-file limit; edits retained; checkpoint unchanged')
        # Removing a file is only accepted when its original bytes remain somewhere in the vault.
        originals = set(after.values())
        if any(content not in originals for p, content in before.items() if p not in after):
            raise RuntimeError('an original note was removed without preserving its bytes in archive/ or a renamed note; checkpoint unchanged')
        report = vault.index(embeddings=True)
        commit = _commit(root, touched, 'feat(memory): consolidate reusable knowledge')
        acknowledged = dict(previous)
        for path in set(selected) | touched:
            if path in after:
                acknowledged[path] = hashlib.sha256(after[path]).hexdigest()
            else:
                acknowledged.pop(path, None)
        updated = {'hashes': acknowledged, 'commit': commit, 'baseline': baseline}
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=state_path.parent, delete=False) as file:
            temporary = Path(file.name)
            json.dump(updated, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        try:
            temporary.replace(state_path)
        finally:
            temporary.unlink(missing_ok=True)
        return dict(result, status='completed', changed=sorted(touched), baseline=baseline, commit=commit, index=report)
