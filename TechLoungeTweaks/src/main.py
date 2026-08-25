"""Tech Lounge Tweaks - native window, web UI.

The UI is HTML/CSS rendered by the WebView2 runtime that ships with
Windows 11. Every bit of the logic below is the same backend the previous
build used - only the presentation layer changed.
"""

import ctypes
import functools
import os
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import webview

import bootparse
import cleanup
import drivers
import nettest
import sysinfo
from tweaks_engine import (build_tweaks, CATEGORY_ORDER, CATEGORY_ICONS, run)

ICON_FOR = {
    "Performance": "bolt", "Graphics": "gpu", "GPU": "gpu",
    "Networking": "net", "Power": "bolt", "Advanced": "cpu",
    "System": "wrench", "Privacy": "shield", "Explorer & UI": "folder",
}


def here(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False



# --------------------------------------------------------------------------
# Diagnostics
# --------------------------------------------------------------------------

def _log_path():
    for folder in (os.path.dirname(os.path.abspath(sys.executable)),
                   os.environ.get("LOCALAPPDATA", ""), os.getcwd()):
        if folder:
            try:
                os.makedirs(folder, exist_ok=True)
                return os.path.join(folder, "TL-api.log")
            except Exception:
                continue
    return "TL-api.log"


LOGFILE = _log_path()
_loglock = threading.Lock()


def log(msg):
    try:
        with _loglock:
            with open(LOGFILE, "a", encoding="utf-8") as fh:
                fh.write(time.strftime("%H:%M:%S ") + msg + "\n")
    except Exception:
        pass


def traced(fn):
    """Log every bridge call and never let an exception cross into JS.

    A raised exception rejects the JS promise, which the front end could
    only see as a null - so failures looked like nothing happening.
    """
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        t0 = time.time()
        log(f"-> {fn.__name__}{args!r}")
        try:
            out = fn(self, *args, **kwargs)
            log(f"<- {fn.__name__} ok in {time.time() - t0:.1f}s")
            return out
        except Exception:
            tb = traceback.format_exc()
            log(f"!! {fn.__name__} FAILED after {time.time() - t0:.1f}s\n{tb}")
            return {"__error__": tb.strip().splitlines()[-1], "trace": tb}
    return wrapper


class Api:
    def __init__(self):
        self._tweaks = None
        self._tlock = threading.Lock()
        self.window = None
        self._locked = set()
        self._applied = set()
        self._cache = {}
        self._pending = {}          # user changes made during a scan
        self._cachelock = threading.Lock()
        self._running = {}          # key -> Popen, for cancellable tasks
        self._busy = set()          # guards double-clicks

    @property
    def tweaks(self):
        """Built lazily - GPU vendor detection shells out to PowerShell and
        must not run before the window has painted."""
        with self._tlock:
            if self._tweaks is None:
                self._tweaks = {t.key: t for t in build_tweaks()}
            return self._tweaks

    # ---------------------------------------------------------- window
    # Driven through Win32 rather than pywebview's own helpers: those run on
    # pywebview's thread and were not reliably reaching the native window.
    def _hwnd(self):
        try:
            h = ctypes.windll.user32.FindWindowW(None, "Tech Lounge Tweaks")
            return h or None
        except Exception:
            return None

    @traced
    def minimize(self):
        h = self._hwnd()
        if h:
            ctypes.windll.user32.ShowWindow(h, 6)          # SW_MINIMIZE
            return True
        try:
            self.window.minimize()
        except Exception:
            pass
        return True

    @traced
    def maximize(self):
        h = self._hwnd()
        if h:
            zoomed = ctypes.windll.user32.IsZoomed(h)
            ctypes.windll.user32.ShowWindow(h, 9 if zoomed else 3)
            return True
        return False

    @traced
    def close(self):
        h = self._hwnd()
        if h:
            ctypes.windll.user32.PostMessageW(h, 0x0010, 0, 0)   # WM_CLOSE
            return True
        try:
            self.window.destroy()
        except Exception:
            pass
        return True

    # ---------------------------------------------------------- tweaks
    def _payload(self, t):
        return {
            "key": t.key, "name": t.name, "desc": t.desc,
            "category": t.category, "warning": t.warning,
            "icon": ICON_FOR.get(t.category, "cpu"),
            "restart": t.needs_restart,
            "applied": t.key in getattr(self, "_applied", set()),
            "locked": False,
        }

    @traced
    def scan(self):
        """Run every detection check in parallel.

        Serially this took ~15 s - most checks shell out to PowerShell, and
        that blocked the UI thread hard enough for Windows to show the
        'not responding' dialog.
        """
        applied = set()

        def one(item):
            key, t = item
            try:
                return key, t.check()
            except Exception:
                return key, False

        with ThreadPoolExecutor(max_workers=12) as pool:
            for key, ok in pool.map(one, list(self.tweaks.items())):
                if ok:
                    applied.add(key)

        # A toggle the user flipped while this scan was running wins - the
        # scan started before their change and would otherwise undo it.
        for key, want in list(self._pending.items()):
            applied.add(key) if want else applied.discard(key)
        self._applied = applied
        self._locked = set()
        return [self._payload(t) for t in self.tweaks.values()]

    @traced
    def init(self):
        """Return instantly. The scan runs behind it and pushes results."""
        self._applied = getattr(self, "_applied", set())
        payload = {
            "categories": [c for c in CATEGORY_ORDER
                           if any(t.category == c
                                  for t in self.tweaks.values())],
            "tweaks": [self._payload(t) for t in self.tweaks.values()],
            "admin": is_admin(),
            "specs": {},
            "scanning": True,
        }
        threading.Thread(target=self._background_start, daemon=True).start()
        return payload

    def _background_start(self):
        try:
            self._emit("scanned", {"tweaks": self.scan()})
        except Exception:
            pass
        try:
            self._emit("specs", self.specs())
        except Exception:
            pass
        self._prefetch()
        self._emit("prefetched", {})

    @traced
    def toggle(self, key, want):
        t = self.tweaks.get(key)
        if not t:
            return {"ok": False, "message": "Unknown tweak."}
        self._pending[key] = want
        try:
            t.apply() if want else t.revert()
        except Exception as e:
            self._pending.pop(key, None)
            return {"ok": False, "message": str(e)}

        self._applied.add(key) if want else self._applied.discard(key)

        # Confirm against the system rather than assuming the write took.
        verified = None
        try:
            verified = bool(t.check())
        except Exception:
            pass
        self._pending.pop(key, None)
        if verified is not None and verified != want:
            self._applied.add(key) if verified else self._applied.discard(key)
            return {"ok": False, "applied": verified,
                    "message": ("Windows did not accept that change. It may "
                                "need a reboot, or another policy is "
                                "enforcing it.")}
        return {"ok": True, "applied": want}

    @traced
    def bulk(self, category, want):
        for key, t in self.tweaks.items():
            if t.category != category:
                continue
            try:
                t.apply() if want else t.revert()
                self._applied.add(key) if want else self._applied.discard(key)
            except Exception:
                pass
        return True

    # ------------------------------------------------------------ info
    @traced
    def specs(self):
        def first(groups, k):
            for rows in groups or []:
                for a, b in rows:
                    if a == k and b and b != "N/A":
                        return b
            return "Unknown"
        try:
            mem = sysinfo.memory()
            mb = sysinfo.mainboard()
            win = sysinfo.windows()
            return {
                "CPU": first(sysinfo.cpu(), "Name"),
                "Graphics": first(sysinfo.graphics(), "Name"),
                "Memory": f'{first(mem, "Total capacity")} @ '
                          f'{first(mem, "Running at")}',
                "Motherboard": f'{first(mb, "Manufacturer")} '
                               f'{first(mb, "Product")}',
                "Windows": f'{first(win, "Edition")} '
                           f'(build {first(win, "Build")})',
                "Storage": first(sysinfo.storage(), "Model"),
            }
        except Exception as e:
            return {"Error": str(e)}

    def _cached(self, key, producer):
        """Read once, keep it. Hardware does not change while the app is open."""
        with self._cachelock:
            if key in self._cache:
                return self._cache[key]
        value = producer()
        with self._cachelock:
            self._cache[key] = value
        return value

    @traced
    def sysinfo_section(self, name):
        fn = dict((n, f) for n, _i, f in sysinfo.SECTIONS).get(name)
        if not fn:
            return []

        def build():
            try:
                return [[list(r) for r in group] for group in fn()]
            except Exception as e:
                return [[["Error", str(e)]]]
        return self._cached("sys:" + name, build)

    @traced
    def refresh_all(self):
        """Explicit re-read, for the Refresh button."""
        with self._cachelock:
            self._cache.clear()
        threading.Thread(target=self._prefetch, daemon=True).start()
        return True

    def _prefetch(self):
        """Warm the read-only pages in the background so they open instantly."""
        try:
            self._cached("specs", self.specs.__wrapped__.__get__(self, Api)
                         if hasattr(self.specs, "__wrapped__") else self.specs)
        except Exception:
            pass
        for name, _i, _f in sysinfo.SECTIONS:
            try:
                self.sysinfo_section(name)
            except Exception:
                pass
        try:
            self.bios_info()
        except Exception:
            pass
        log("prefetch complete")

    @traced
    def sysinfo_sections(self):
        return [n for n, _i, _f in sysinfo.SECTIONS]

    # --------------------------------------------------------- network
    @traced
    def nettest(self):
        try:
            res = nettest.run_test(
                progress=lambda label, frac: self._emit(
                    "netprogress", {"label": label, "frac": frac}),
                on_partial=lambda stage, r: self._emit(
                    "netpartial", {"stage": stage, "res": _clean(r)}))
            return _clean(res)
        except Exception as e:
            return {"error": str(e)}

    def _emit(self, event, data):
        """Push an event to the page.

        Uses run_js, not evaluate_js: evaluate_js waits for a return value
        from the GUI thread, and calling it from a worker thread is what
        makes the window stop responding.
        """
        if not self.window:
            return
        import json
        script = (f"window.onPy && window.onPy({json.dumps(event)},"
                  f"{json.dumps(data)})")
        try:
            if hasattr(self.window, "run_js"):
                self.window.run_js(script)
            else:
                self.window.evaluate_js(script)
        except Exception as e:
            log(f"emit {event} failed: {e}")

    # --------------------------------------------------------- cleanup
    @traced
    def clean_scan(self):
        items = cleanup.scan()
        total, used, free = cleanup.drive_usage("C")
        return {
            "items": [{"name": n, "path": p, "kind": k, "default": d,
                       "desc": ds, "bytes": b, "files": f,
                       "human": cleanup.human(b)}
                      for n, p, k, d, ds, b, f in items],
            "disk": {"total": total, "used": used, "free": free,
                     "totalH": cleanup.human(total),
                     "usedH": cleanup.human(used),
                     "freeH": cleanup.human(free)},
        }

    @traced
    def clean_run(self, selected):
        sel = [(i["name"], i["path"], i["kind"]) for i in selected]
        freed, skipped, per = cleanup.clean(
            sel, log=lambda n, f, s: self._emit(
                "cleanlog", {"name": n, "freed": cleanup.human(f),
                             "skipped": s}))
        return {"freed": cleanup.human(freed), "skipped": skipped}

    # --------------------------------------------------------- drivers
    @traced
    def check_drivers(self):
        out = []
        try:
            for name, ver, vendor in drivers.detect_gpus():
                latest = None
                installed = ver or "Unknown"
                if vendor == "NVIDIA":
                    installed = drivers.nvidia_marketing_version(ver)
                    latest = drivers.nvidia_latest(name)
                out.append({"name": name, "vendor": vendor,
                            "installed": installed,
                            "latest": latest[0] if latest else None,
                            "url": latest[1] if latest else None,
                            "page": drivers.vendor_page(vendor)})
        except Exception as e:
            return {"error": str(e)}
        return {"gpus": out}

    @traced
    def download_driver(self, url, vendor):
        try:
            path = drivers.download(
                url, vendor,
                lambda f: self._emit("dlprogress", {"frac": f}))
            drivers.reveal(path)
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @traced
    def open_url(self, url):
        import webbrowser
        webbrowser.open(url)
        return True

    # ----------------------------------------------------------- tools
    @traced
    def restore_point(self):
        if "restore" in self._busy:
            return {"ok": False,
                    "message": "A restore point is already being created."}
        self._busy.add("restore")
        try:
            rc, out = run(["powershell", "-NoProfile", "-Command",
                           "Enable-ComputerRestore -Drive 'C:\\'; "
                           "Checkpoint-Computer -Description "
                           "'TechLoungeTweaks' -RestorePointType "
                           "'MODIFY_SETTINGS'"])
            low = (out or "").lower()
            if rc == 0:
                return {"ok": True, "message": "Restore point created."}
            if "already been created" in low or "1440" in low:
                # Windows refuses more than one restore point per 24 hours
                return {"ok": True,
                        "message": ("Windows already made one in the last 24 "
                                    "hours - that one still protects you.")}
            return {"ok": False,
                    "message": ("Could not create one. System Protection is "
                                "probably off for C:.")}
        finally:
            self._busy.discard("restore")

    @traced
    def boot_optimizer(self, mode="preview"):
        import base64
        import subprocess
        import tempfile
        import boot_payload
        from tweaks_engine import CREATE_NO_WINDOW
        events = []
        try:
            folder = os.path.join(os.environ.get("LOCALAPPDATA",
                                                 tempfile.gettempdir()),
                                  "TechLoungeTweaks")
            os.makedirs(folder, exist_ok=True)
            ps1 = os.path.join(folder, "Optimize-Boot.ps1")
            with open(ps1, "w", encoding="utf-8", newline="") as fh:
                fh.write(base64.b64decode(boot_payload.B64).decode("utf-8"))
            args = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", ps1, "-RollbackFilePath",
                    os.path.join(folder, "boot-rollback.json")]
            if mode == "undo":
                args.append("-Rollback")
            if mode == "preview":
                args.append("-WhatIf")
            p = subprocess.Popen(args, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, text=True,
                                 bufsize=1, encoding="utf-8",
                                 errors="replace",
                                 creationflags=CREATE_NO_WINDOW)
            section = ""
            for line in p.stdout:
                ev = bootparse.parse_line(line)
                if not ev:
                    continue
                if ev[0] == "step":
                    section = ev[1]
                events.append([ev[0], ev[1], ev[2], section])
                self._emit("bootline", {"kind": ev[0], "text": ev[1],
                                        "detail": ev[2]})
            p.wait()
        except Exception as e:
            return {"error": str(e)}
        planned, done, skipped, attention, findings = bootparse.summarise(
            [tuple(e) for e in events])
        return {"planned": planned, "done": done, "skipped": skipped,
                "attention": attention, "findings": findings}

    RES_CMDS = {
        "sfc": ["sfc", "/scannow"],
        "dism": ["dism", "/Online", "/Cleanup-Image", "/RestoreHealth"],
        "chkdsk": ["chkdsk", "C:"],
    }

    @staticmethod
    def _verdict(key, text, rc, cancelled):
        """Turn tool output into a plain answer: was anything wrong or not."""
        if cancelled:
            return "cancelled", "Cancelled before it finished."
        low = (text or "").lower()

        if key == "sfc":
            if "did not find any integrity violations" in low:
                return "clean", "No problems found. All protected system files are intact."
            if "found corrupt files and successfully repaired" in low:
                return "fixed", "Found corrupt files and repaired them all."
            if "unable to fix" in low:
                return "problem", ("Found corrupt files it could NOT repair. "
                                   "Run Windows Image Repair, then run this again.")
            if "could not perform" in low:
                return "problem", "Could not run the repair operation."
        elif key == "dism":
            if "the restore operation completed successfully" in low or \
                    "the operation completed successfully" in low:
                return "clean", "Component store is healthy. Repair completed successfully."
            if "the component store is repairable" in low:
                return "fixed", "Damage found and repaired."
            if "error" in low or rc not in (0, None):
                return "problem", f"DISM reported an error (exit code {rc})."
        elif key == "chkdsk":
            if "found no problems" in low or "no further action is required" in low:
                return "clean", "No problems found on the drive."
            if "found problems" in low or "errors found" in low:
                return "problem", ("Errors found. Run 'chkdsk C: /f' from an "
                                   "admin prompt and reboot to repair them.")

        if rc == 0:
            return "clean", "Finished with no errors reported."
        return "problem", f"Finished with exit code {rc}."

    @traced
    def resource_task(self, key):
        import subprocess
        from tweaks_engine import CREATE_NO_WINDOW
        if key in self._running:
            return {"ok": False, "state": "busy",
                    "message": "That check is already running."}
        collected = []
        try:
            proc = subprocess.Popen(self.RES_CMDS[key], stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, text=True,
                                    bufsize=1, encoding="utf-8",
                                    errors="replace",
                                    creationflags=CREATE_NO_WINDOW)
            self._running[key] = proc
            for line in proc.stdout:
                line = line.strip()
                if line:
                    collected.append(line)
                    self._emit("resline", {"key": key, "text": line[:160]})
            proc.wait()
            rc = proc.returncode
        except Exception as e:
            self._running.pop(key, None)
            return {"ok": False, "state": "problem", "message": str(e)}

        cancelled = getattr(proc, "_tl_cancelled", False)
        self._running.pop(key, None)
        blob = " ".join(collected[-40:])
        state, message = self._verdict(key, blob, rc, cancelled)
        return {"ok": state in ("clean", "fixed"), "state": state,
                "message": message}

    @traced
    def cancel_task(self, key):
        proc = self._running.get(key)
        if not proc:
            return {"ok": False}
        try:
            setattr(proc, "_tl_cancelled", True)
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        except Exception as e:
            log(f"cancel {key}: {e}")
        return {"ok": True}

    @traced
    def bios_info(self):
        import biosinfo

        def build():
            try:
                rows = [list(r) for r in biosinfo.collect()]
                supported, label, _ns = biosinfo.vendor_support()
                return {"rows": rows, "supported": supported, "label": label}
            except Exception as e:
                return {"rows": [["Error", str(e)]], "supported": False}
        return self._cached("bios", build)


def _clean(d):
    """Make results JSON-safe."""
    if isinstance(d, dict):
        return {k: _clean(v) for k, v in d.items()}
    if isinstance(d, (list, tuple)):
        return [_clean(v) for v in d]
    if isinstance(d, float):
        return round(d, 2)
    return d


def relaunch_as_admin():
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable,
            " ".join(f'"{a}"' for a in sys.argv), None, 1)
    except Exception:
        pass


def main():
    if not is_admin():
        relaunch_as_admin()
        return

    log("=" * 50)
    log(f"start: frozen={getattr(sys, 'frozen', False)} exe={sys.executable}")
    api = Api()
    window = webview.create_window(
        "Tech Lounge Tweaks",
        here("web", "index.html"),
        js_api=api,
        width=1380, height=900, min_size=(1100, 720),
        frameless=True, easy_drag=False,
        background_color="#0a0b12",
    )
    api.window = window
    webview.start(gui="edgechromium", private_mode=False, debug=False)


if __name__ == "__main__":
    main()
