"""Small atomic local-state helpers; state is not canonical knowledge."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile


def read_json(path, default):
    if path.is_symlink():
        raise ValueError(f'State must not be a symlink: {path.name}')
    return json.loads(path.read_text()) if path.exists() else default


def write_json(path, value):
    if path.is_symlink():
        raise ValueError(f'State must not be a symlink: {path.name}')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False, encoding='utf-8') as output:
            temporary = Path(output.name)
            json.dump(value, output, ensure_ascii=False, sort_keys=True)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


@contextmanager
def locked(path):
    if path.is_symlink():
        raise ValueError(f'Lock must not be a symlink: {path.name}')
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
            raise RuntimeError('local state is busy; retry after the other operation finishes') from error
        try:
            yield
        finally:
            if os.name == 'nt':
                lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)
