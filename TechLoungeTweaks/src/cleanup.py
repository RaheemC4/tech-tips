"""Disk cleanup - find and remove safe-to-delete junk."""

import os
import shutil
import subprocess
import sys

from tweaks_engine import CREATE_NO_WINDOW

def _self_dirs():
    """Folders belonging to this running app - never scan or delete these.

    A PyInstaller one-file build unpacks itself into a %TEMP% _MEI folder, so
    without this the app counts its own ~100 MB of extracted files as
    reclaimable and then cannot delete a single one of them.
    """
    out = set()
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


def _dir_size(path, match=None):
    total = 0
    files = 0
    for root, dirs, names in os.walk(path):
        if _is_self(root):
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not _is_self(os.path.join(root, d))]
        for n in names:
            if match and not n.lower().startswith(match):
                continue
            try:
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


def _purge_dir(path, match=None):
    freed = 0
    skipped = 0
    for root, dirs, names in os.walk(path, topdown=False):
        if _is_self(root):
            continue
        for n in names:
            if match and not n.lower().startswith(match):
                continue
            fp = os.path.join(root, n)
            if _is_self(fp):
                continue
            try:
                sz = os.path.getsize(fp)
                try:
                    os.chmod(fp, 0o666)
                except OSError:
                    pass
                os.remove(fp)
                freed += sz
            except OSError:
                skipped += 1      # locked by a running app - never force
        if not match and root != path and not _is_self(root):
            try:
                os.rmdir(root)
            except OSError:
                pass
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
