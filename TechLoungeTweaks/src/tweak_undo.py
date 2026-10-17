"""In-memory undo for changes made through the tweak engine in this session.

Capture before writing, fail closed if capture fails, and never invent a default
for undo. This is intentionally separate from Windows Defaults and system restore.
"""
import contextvars
import threading
import winreg

LOCK = threading.RLock()
ACTIVE = contextvars.ContextVar('tweak_undo', default=None)


class SessionUndo:
    def __init__(self):
        self.records = {}
        self.created_keys = set()

    def remember(self, key, capture):
        if key not in self.records:
            self.records[key] = capture()

    def restore(self):
        failures = {}
        with LOCK:
            for key, restore in reversed(list(self.records.items())):
                try:
                    restore()
                except Exception as exc:
                    failures[str(key)] = str(exc)
                else:
                    del self.records[key]
            if not self.records:
                self.created_keys.clear()
        return failures


def read_value(hive, path, name):
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            return winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        return None


def capture_value(hive, path, name):
    previous = read_value(hive, path, name)
    missing = []
    cursor = path
    while cursor:
        try:
            with winreg.OpenKey(hive, cursor, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY):
                break
        except FileNotFoundError:
            missing.append(cursor)
            cursor = cursor.rpartition('\\')[0]

    session = ACTIVE.get()
    if session is not None:
        session.created_keys.update((hive, x.lower()) for x in missing)

    def restore():
        if previous is None:
            try:
                with winreg.OpenKey(hive, path, 0, winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY) as key:
                    winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass
        else:
            with winreg.CreateKeyEx(hive, path, 0, winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY) as key:
                winreg.SetValueEx(key, name, 0, previous[1], previous[0])
        if read_value(hive, path, name) != previous:
            raise OSError('The original registry value could not be restored.')
        for key_path in missing:
            try:
                # Delete only empty keys created by this session, never other values.
                with winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                    subkeys, values, _ = winreg.QueryInfoKey(key)
                if subkeys or values:
                    continue
                winreg.DeleteKeyEx(hive, key_path, winreg.KEY_WOW64_64KEY)
            except FileNotFoundError:
                pass
    return restore


def record_value(hive, path, name):
    session = ACTIVE.get()
    if session is not None:
        session.remember(('registry', hive, path.lower(), name.lower()),
                         lambda: capture_value(hive, path, name))


def record_tree(hive, path):
    """Capture every value before a tree delete, including empty keys."""
    session = ACTIVE.get()
    if session is None:
        return
    def visit(current):
        try:
            with winreg.OpenKey(hive, current, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                subcount, valcount, _ = winreg.QueryInfoKey(key)
                values = [winreg.EnumValue(key, i)[0] for i in range(valcount)]
                children = [winreg.EnumKey(key, i) for i in range(subcount)]
        except FileNotFoundError:
            return
        def restore_key():
            with winreg.CreateKeyEx(hive, current, 0, winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY):
                pass
        if (hive, current.lower()) not in session.created_keys:
            session.remember(('key', hive, current.lower()), lambda: restore_key)
        for name in values:
            record_value(hive, current, name)
        for child in children:
            visit(current + '\\' + child)
    visit(path)
