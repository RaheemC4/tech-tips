"""Disk cleanup - find and remove safe-to-delete junk."""

import os
import shutil
import subprocess
import sys
import stat

from tweaks_engine import CREATE_NO_WINDOW

def _self_dirs():
    """Folders belonging to this running app - never scan or delete these.

    A PyInstaller one-file build unpacks itself into a %TEMP% _MEI folder, so
    without this the app counts its own ~100 MB of extracted files as
    reclaimable and then cannot delete a single one of them.
    """
    out = set()
    if getattr(sys, '_tl_app_root', None):
        out.add(os.path.normcase(os.path.abspath(sys._tl_app_root)))
    mei = getattr(sys, "_MEIPASS", None)
    if mei:
        out.add(os.path.normcase(os.path.abspath(mei)))
    try:
        out.add(os.path.normcase(os.path.dirname(os.path.abspath(
            sys.executable))))
    except Exception:
        pass
    return out


SELF_DIRS = _self_dirs()


def _is_self(path):
    try:
        n = os.path.normcase(os.path.abspath(path))
    except Exception:
        return False
    return any(n == d or n.startswith(d + os.sep) for d in SELF_DIRS)


LOCAL = os.environ.get("LOCALAPPDATA", "")
WIN = os.environ.get("SystemRoot", r"C:\Windows")
TEMP = os.environ.get("TEMP", "")


def _paths():
    return [
        ("Your temp files", TEMP, "files", True,
         "Everything apps dumped in %TEMP% and never cleaned up."),
        ("Windows temp files", os.path.join(WIN, "Temp"), "files", True,
         "System-wide scratch folder. Safe to empty."),
        ("Windows Update cache", os.path.join(WIN, "SoftwareDistribution",
                                              "Download"), "files", True,
         "Installers for updates that are already applied."),
        ("Delivery Optimization", os.path.join(
            WIN, "ServiceProfiles", "NetworkService", "AppData", "Local",
            "Microsoft", "Windows", "DeliveryOptimization"), "files", True,
         "Peer-to-peer update chunks cached for other PCs."),
        ("Crash dumps", os.path.join(LOCAL, "CrashDumps"), "files", True,
         "Memory dumps written when an app crashed."),
        ("Thumbnail cache", os.path.join(
            LOCAL, "Microsoft", "Windows", "Explorer"), "thumbs", True,
         "Explorer rebuilds these automatically."),
        ("Windows error reports", os.path.join(
            LOCAL, "Microsoft", "Windows", "WER"), "files", True,
         "Queued crash reports waiting to be sent to Microsoft."),
        ("Prefetch data", os.path.join(WIN, "Prefetch"), "files", False,
         "Helps apps start faster. Windows rebuilds it, but there is no "
         "real benefit to clearing it."),
        ("Recycle Bin", "<recycle>", "recycle", False,
         "Permanently deletes everything currently in the bin."),
    ]


CATEGORY_IDS = ('user_temp', 'windows_temp', 'update_cache', 'delivery_cache',
                'crash_dumps', 'thumbnails', 'error_reports', 'prefetch', 'recycle')


def resolve_categories(selected):
    """Only server-owned catalogue entries may reach the deletion code."""
    if not isinstance(selected, list) or any(not isinstance(x, str) for x in selected):
        raise ValueError('Select cleanup category IDs, not paths.')
    catalogue = dict(zip(CATEGORY_IDS, _paths()))
    if any(x not in catalogue for x in selected):
        raise ValueError('Unknown cleanup category.')
    return [catalogue[x][:3] for x in dict.fromkeys(selected)]


def _unsafe_path(path):
    """Do not traverse links/junctions, including ancestors of a selected root."""
    current = os.path.abspath(path)
    while True:
        try:
            info = os.lstat(current)
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                return True
        except OSError:
            return True
        parent = os.path.dirname(current)
        if parent == current:
            return False
        current = parent


def _dir_size(path, match=None):
    total = 0
    files = 0
    if _unsafe_path(path):
        return 0, 0
    for root, dirs, names in os.walk(path):
        if _is_self(root) or _unsafe_path(root):
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not _is_self(os.path.join(root, d)) and not _unsafe_path(os.path.join(root, d))]
        for n in names:
            if match and not n.lower().startswith(match):
                continue
            try:
                if _unsafe_path(os.path.join(root, n)):
                    continue
                total += os.path.getsize(os.path.join(root, n))
                files += 1
            except OSError:
                pass
    return total, files


def _recycle_size():
    cmd = ("$s=0; foreach($d in (Get-PSDrive -PSProvider FileSystem)) { "
           "$p = Join-Path $d.Root '$Recycle.Bin'; if (Test-Path $p) { "
           "$s += (Get-ChildItem $p -Recurse -Force -ErrorAction "
           "SilentlyContinue | Measure-Object -Property Length -Sum)."
           "Sum } }; [long]$s")
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=90,
                           stdin=subprocess.DEVNULL,
                           creationflags=CREATE_NO_WINDOW)
        return int((p.stdout or "0").strip() or 0), 0
    except Exception:
        return 0, 0


def scan(progress=None):
    """Return [(name, path, kind, default_on, desc, bytes, files)]."""
    out = []
    items = _paths()
    for i, (name, path, kind, default, desc) in enumerate(items):
        if progress:
            progress(name, i / len(items))
        size = files = 0
        try:
            if kind == "recycle":
                size, files = _recycle_size()
            elif kind == "thumbs":
                if os.path.isdir(path):
                    size, files = _dir_size(path, match="thumbcache")
            elif path and os.path.isdir(path):
                size, files = _dir_size(path)
        except Exception:
            pass
        out.append((name, path, kind, default, desc, size, files))
    if progress:
        progress("Done", 1.0)
    return out


def _remove_file(path):
    """Delete read-only files by handle, without altering attributes or locks."""
    try:
        os.remove(path)
        return
    except PermissionError:
        info = os.lstat(path)
        if (not getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_READONLY
                or not stat.S_ISREG(info.st_mode) or _unsafe_path(path) or _is_self(path)):
            raise
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    for name in ('GetFileInformationByHandleEx', 'SetFileInformationByHandle'):
        fn = getattr(kernel, name)
        fn.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        fn.restype = wintypes.BOOL
    # DELETE | FILE_READ_ATTRIBUTES, exclusive sharing, OPEN_EXISTING,
    # FILE_FLAG_OPEN_REPARSE_POINT. No lock bypass or path-based chmod retry.
    handle = kernel.CreateFileW(path, 0x10080, 0, None, 3, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        attrs = (wintypes.DWORD * 2)()  # FILE_ATTRIBUTE_TAG_INFO, class 9
        if not kernel.GetFileInformationByHandleEx(handle, 9, ctypes.byref(attrs), ctypes.sizeof(attrs)):
            raise ctypes.WinError(ctypes.get_last_error())
        if attrs[0] & (stat.FILE_ATTRIBUTE_DIRECTORY | stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise PermissionError('Refusing a directory or reparse target.')
        # FileDispositionInfoEx: DELETE | IGNORE_READONLY_ATTRIBUTE. Windows
        # still enforces DELETE permission and sharing; attributes never change.
        flags = wintypes.DWORD(0x11)
        if not kernel.SetFileInformationByHandle(handle, 21, ctypes.byref(flags), ctypes.sizeof(flags)):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(handle)


def _purge_dir(path, match=None):
    freed = 0
    skipped = 0
    if _unsafe_path(path) or _is_self(path):
        return 0, 1
    for root, dirs, names in os.walk(path, topdown=True, followlinks=False):
        if _is_self(root) or _unsafe_path(root):
            dirs[:] = []
            continue
        safe_dirs = [d for d in dirs if not _is_self(os.path.join(root, d))
                     and not _unsafe_path(os.path.join(root, d))]
        skipped += len(dirs) - len(safe_dirs)
        dirs[:] = safe_dirs
        for n in names:
            if match and not n.lower().startswith(match):
                continue
            fp = os.path.join(root, n)
            if _is_self(fp) or _unsafe_path(fp):
                skipped += 1
                continue
            try:
                sz = os.path.getsize(fp)
                _remove_file(fp)
                freed += sz
            except OSError:
                skipped += 1
    return freed, skipped


def _empty_recycle():
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                       capture_output=True, timeout=180,
                       stdin=subprocess.DEVNULL,
                       creationflags=CREATE_NO_WINDOW)
    except Exception:
        pass


def clean(selected, progress=None, log=None):
    """selected = list of (name, path, kind).

    Returns (bytes_freed, files_skipped, per_item). Skipped files are ones
    locked by a running process - expected, and never forced.
    """
    freed = 0
    skipped = 0
    per_item = []
    for i, (name, path, kind) in enumerate(selected):
        if progress:
            progress(name, i / max(1, len(selected)))
        before_freed, before_skipped = freed, skipped
        try:
            if kind == "recycle":
                before, _ = _recycle_size()
                _empty_recycle()
                after, _ = _recycle_size()
                freed += max(0, before - after)
            elif kind == "thumbs":
                if os.path.isdir(path):
                    f, sk = _purge_dir(path, match="thumbcache")
                    freed += f
                    skipped += sk
            elif path and os.path.isdir(path):
                f, sk = _purge_dir(path)
                freed += f
                skipped += sk
        except Exception:
            pass
        item_freed = freed - before_freed
        item_skipped = skipped - before_skipped
        per_item.append((name, item_freed, item_skipped))
        if log:
            log(name, item_freed, item_skipped)
    if progress:
        progress("Done", 1.0)
    return freed, skipped, per_item


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} TB"


def drive_usage(letter="C"):
    try:
        total, used, free = shutil.disk_usage(letter + ":\\")
        return total, used, free
    except Exception:
        return 0, 0, 0
