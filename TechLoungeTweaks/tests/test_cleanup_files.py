"""Cleanup deletes available files while preserving locks and scope guards."""
import ctypes
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import cleanup

class CleanupFileTests(unittest.TestCase):
    def test_readonly_and_writable_files_are_deleted_locked_files_are_skipped(self):
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                     ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            locked = root / 'locked.tmp'; locked.write_bytes(b'a' * 41)
            readonly_locked = root / 'readonly-locked.tmp'; readonly_locked.write_bytes(b'b' * 43)
            readonly = root / 'readonly.tmp'; readonly.write_bytes(b'c' * 37)
            writable = root / 'available-after-locked.tmp'; writable.write_bytes(b'd' * 23)
            os.chmod(readonly, stat.S_IREAD); os.chmod(readonly_locked, stat.S_IREAD)
            handles = []
            try:
                for path in (locked, readonly_locked):
                    handle = kernel.CreateFileW(str(path), 0x80000000, 0, None, 3, 0, None)
                    self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
                    handles.append(handle)
                freed, skipped = cleanup._purge_dir(folder)
                self.assertEqual((freed, skipped), (60, 2))
                self.assertFalse(readonly.exists()); self.assertFalse(writable.exists())
                self.assertTrue(locked.exists()); self.assertTrue(readonly_locked.exists())
                self.assertTrue(os.lstat(readonly_locked).st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)
            finally:
                for handle in handles: kernel.CloseHandle(handle)
                for path in (readonly_locked, readonly):
                    if path.exists(): os.chmod(path, stat.S_IWRITE)
