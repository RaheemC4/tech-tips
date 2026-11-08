"""Keep separate app/tray updater processes from replacing the same inventory."""
from contextlib import contextmanager
import os


@contextmanager
def update_lease(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'update.lock').open('a+b') as stream:
        stream.seek(0, 2)
        if not stream.tell():
            stream.write(b'\0')
            stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            lock = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            unlock = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            lock = lambda: fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            unlock = lambda: fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        try:
            lock()
        except OSError as exc:
            raise RuntimeError('Another updater is running. Updates will retry automatically.') from exc
        try:
            yield
        finally:
            stream.seek(0)
            unlock()
