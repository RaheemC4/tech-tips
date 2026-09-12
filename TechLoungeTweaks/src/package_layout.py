"""Keep the portable launcher clear of runtime files and diagnostic logs."""
import ctypes
import os
from pathlib import Path
import sys
import tempfile


def log_path():
    for base in (os.environ.get('LOCALAPPDATA'), tempfile.gettempdir()):
        if base:
            try:
                folder = Path(base) / 'TechLoungeTweaks' / 'Logs'
                folder.mkdir(parents=True, exist_ok=True)
                return str(folder / 'TL-api.log')
            except OSError:
                continue
    return os.devnull


def hide_support_folders(root=None):
    if os.name != 'nt' or (root is None and not getattr(sys, 'frozen', False)):
        return
    root = Path(root or getattr(sys, '_tl_app_root', Path(sys.executable).parent))
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
    kernel.GetFileAttributesW.restype = ctypes.c_uint32
    kernel.SetFileAttributesW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
    for name in ('_internal', 'resources'):
        path = str(root / name)
        attributes = kernel.GetFileAttributesW(path)
        if attributes != 0xffffffff and attributes & 0x10:
            kernel.SetFileAttributesW(path, attributes | 2)
