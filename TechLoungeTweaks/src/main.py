"""Tech Lounge Tweaks - native window, web UI.

The UI is HTML/CSS rendered by the WebView2 runtime that ships with
Windows 11. Every bit of the logic below is the same backend the previous
build used - only the presentation layer changed.
"""

import ctypes
import functools
import re
import os
import json
import sys
import threading
import time
import traceback
import tempfile
from concurrent.futures import ThreadPoolExecutor

import webview

import bootparse
import nvprofile
import cleanup
import drivers
import nettest
import sysinfo
from tweaks_engine import (build_tweaks, CATEGORY_ORDER, CATEGORY_ICONS, run, ps)

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
        self._tweaks_cache = None
        self._tlock = threading.Lock()
        # build_tweaks() shells out to PowerShell for GPU detection and takes
        # seconds. Start it NOW, on its own thread, so that by the time the UI
        # asks for anything it is either ready or still safely off the bridge
        # thread. Nothing user-facing waits on this.
        threading.Thread(target=self._warm_tweaks, daemon=True).start()
        self._window = None
        self._locked = set()
        self._applied = set()
        self._cache = {}
        self._pending = {}          # user changes made during a scan
        self._cachelock = threading.Lock()
        self._nv_checked = 0.0      # when the NVIDIA state was last verified
        self._nv_scanning = False
        self._running = {}          # key -> Popen, for cancellable tasks
        self._busy = set()          # guards double-clicks
        # Long-running jobs (SFC, DISM, disk check, driver download, boot,
        # restore point). Kept server-side so the UI can leave the tab and
        # come back to find the job still running with its live progress.
        self._jobs = {}             # key -> job dict
        self._jobslock = threading.Lock()
        self._snapshot = None       # applied-state of each tweak at first open
        self._dl_cancel = set()     # driver-download job keys asked to cancel

    # NOTE: deliberately a private method, NOT a @property.
    #
    # pywebview builds its JS bridge with `for name in dir(api): getattr(api, name)`.
    # Every public property is therefore EVALUATED while the bridge is being
    # injected. As a property, this ran build_tweaks() - which shells out to
    # PowerShell for GPU detection - on the injection thread. If that was slow
    # or hung, window.pywebview.api was never created: the window rendered but
    # no bridge call ever reached Python. Keeping it underscored means dir()
    # skips it and nothing expensive runs during injection.
    def _warm_tweaks(self):
        try:
            self._tweaks()
            log("tweaks: built")
        except Exception:
            log("tweaks: build FAILED\n" + traceback.format_exc())

    def _tweaks(self):
        with self._tlock:
            if self._tweaks_cache is None:
                self._tweaks_cache = {t.key: t for t in build_tweaks()}
            return self._tweaks_cache

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
    def start_drag(self):
        """Hand the window drag to Windows itself.

        pywebview's built-in drag region round-trips JS -> Python -> Win32 on
        EVERY mousemove event. On a high-refresh screen with a high-polling
        mouse that is hundreds of IPC calls a second, and the window visibly
        lags behind the cursor.

        WM_SYSCOMMAND / SC_MOVE hands the whole gesture to the OS: one single
        message, then Windows runs its own move loop and the compositor draws
        it at the monitor's full refresh rate. No further JS or Python.
        """
        h = self._hwnd()
        if not h:
            return False
        WM_SYSCOMMAND = 0x0112
        SC_MOVE_BY_MOUSE = 0xF012      # SC_MOVE | HTCAPTION
        user32 = ctypes.windll.user32
        user32.ReleaseCapture()
        user32.PostMessageW(h, WM_SYSCOMMAND, SC_MOVE_BY_MOUSE, 0)
        return True

    @traced
    def minimize(self):
        h = self._hwnd()
        if h:
            ctypes.windll.user32.ShowWindow(h, 6)          # SW_MINIMIZE
            return True
        try:
            self._window.minimize()
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
            self._window.destroy()
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
            for key, ok in pool.map(one, list(self._tweaks().items())):
                if ok:
                    applied.add(key)

        # A toggle the user flipped while this scan was running wins - the
        # scan started before their change and would otherwise undo it.
        for key, want in list(self._pending.items()):
            applied.add(key) if want else applied.discard(key)
        self._applied = applied
        self._locked = set()
        return [self._payload(t) for t in self._tweaks().values()]

    @traced
    def init(self):
        _close_splash()
        """Return instantly. The scan runs behind it and pushes results."""
        self._applied = getattr(self, "_applied", set())
        payload = {
            # Deliberately does NOT call _tweaks(): building the tweak list
            # runs PowerShell, and doing that inside a bridge call froze the
            # whole window. The list is pushed by the "scanned" event instead.
            "categories": list(CATEGORY_ORDER),
            "tweaks": [],
            "admin": is_admin(),
            "specs": {},
            "scanning": True,
        }
        threading.Thread(target=self._background_start, daemon=True).start()
        return payload

    def _background_start(self):
        # The NVIDIA read shells out to Profile Inspector and is the slowest
        # thing at startup, so give it its own thread right away - it must not
        # sit behind the tweak scan, specs and every sysinfo section. Backup
        # then warm run in sequence on this thread so the two -exportCustomized
        # calls never overlap.
        threading.Thread(target=self._nv_startup, daemon=True).start()
        try:
            tweaks = self.scan()
            cats = [c for c in CATEGORY_ORDER
                    if any(t["category"] == c for t in tweaks)]
            # Snapshot how the machine was when the app opened - this is what
            # "Revert all" puts things back to. Captured once.
            if self._snapshot is None:
                self._snapshot = {t["key"]: bool(t["applied"]) for t in tweaks}
            self._emit("scanned", {"tweaks": tweaks, "categories": cats})
        except Exception:
            log("background scan FAILED\n" + traceback.format_exc())
        try:
            self._emit("specs", self.specs())
        except Exception:
            pass
        self._prefetch()
        self._emit("prefetched", {})

    def _nv_startup(self):
        try:
            has_nv = any(v == "NVIDIA" for _, _, v in drivers.detect_gpus())
            res = nvprofile.ensure_backup(has_nv)
            log(f"nv backup: {res}")
            self._emit("nvbackup", res)
        except Exception:
            log("nv backup FAILED\n" + traceback.format_exc())
        try:
            self._warm_nvidia()
        except Exception:
            log("nv warm FAILED\n" + traceback.format_exc())

    @traced
    def toggle(self, key, want):
        t = self._tweaks().get(key)
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

    # Tweaks excluded from "Apply recommended": the two that break kernel
    # anti-cheat / weaken security, plus GameDVR and Fullscreen Optimizations
    # (they interfere with the Xbox app, Game Bar overlay and some controllers).
    RECOMMENDED_SKIP = {"mem_integrity", "mitigations", "gamedvr", "fse"}

    @traced
    def bulk_tweaks(self, mode):
        """Apply/revert many tweaks at once. mode:
             all         - apply every tweak
             recommended - apply every tweak except the risky/compat ones
             revert      - back to how the machine was when the app opened
             defaults    - Windows-stock: turn every tweak off
        Returns the resulting applied-state map so the UI can repaint at once.
        """
        tweaks = self._tweaks()
        targets = {}
        if mode in ("all", "recommended"):
            for key, t in tweaks.items():
                if mode == "recommended" and key in self.RECOMMENDED_SKIP:
                    continue
                targets[key] = True
        elif mode == "revert":
            snap = self._snapshot or {}
            for key in tweaks:
                targets[key] = bool(snap.get(key, False))
        elif mode == "defaults":
            for key in tweaks:
                targets[key] = False
        else:
            return {"ok": False, "message": "Unknown bulk mode."}

        for key, want in targets.items():
            t = tweaks.get(key)
            if not t:
                continue
            try:
                if want:
                    t.apply(); self._applied.add(key)
                else:
                    t.revert(); self._applied.discard(key)
            except Exception:
                log(f"bulk {mode}: {key} failed\n" + traceback.format_exc())

        applied = {}
        for key, t in tweaks.items():
            try:
                applied[key] = bool(t.check())
            except Exception:
                applied[key] = key in self._applied
        return {"ok": True, "mode": mode, "applied": applied,
                "skipped": sorted(self.RECOMMENDED_SKIP)
                           if mode == "recommended" else []}

    @traced
    def bulk(self, category, want):
        for key, t in self._tweaks().items():
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

    def _warm_nvidia(self):
        """Silently re-read the machine's real NVIDIA state, in the background.

        Runs at every startup (and again when the page is opened), so settings
        changed outside this app - NVIDIA Control Panel, Profile Inspector, a
        driver reinstall - are reflected instead of trusting our own marker.
        """
        if self._nv_scanning:
            return
        self._nv_scanning = True
        try:
            st = self._nv_status()
            if not st.get("nvidia"):
                with self._cachelock:
                    self._cache["nv:status"] = st
                    self._cache["nv:settings"] = []
                    self._nv_checked = time.time()
                self._emit("nvready", {})
                return
            try:
                res = nvprofile.scan_state()
                st = dict(res["status"])
                st["nvidia"] = True
                with self._cachelock:
                    self._cache["nv:status"] = st
                    self._cache["nv:settings"] = res["settings"]
                    self._nv_checked = time.time()
                log(f"nv state: {st.get('state')} "
                    f"{st.get('matched')}/{st.get('total')}")
            except Exception:
                log("nv scan FAILED\n" + traceback.format_exc())
                with self._cachelock:
                    self._cache.setdefault("nv:status", st)
                    self._cache.setdefault("nv:settings", [])
            self._emit("nvready", {})
        finally:
            self._nv_scanning = False

    def _nv_recheck(self, max_age=45):
        """Kick a silent re-scan if the cached state is stale. Never blocks."""
        with self._cachelock:
            fresh = (time.time() - self._nv_checked) < max_age
        if fresh or self._nv_scanning:
            return
        threading.Thread(target=self._warm_nvidia, daemon=True).start()

    def _nv_status(self):
        st = nvprofile.status()
        try:
            gpus = drivers.detect_gpus()
            st["nvidia"] = any(v == "NVIDIA" for _, _, v in gpus)
            # Name the non-NVIDIA card so the block can say what it found.
            non_nv = [n for n, _i, v in gpus if v != "NVIDIA" and n]
            st["gpu_name"] = non_nv[0] if (non_nv and not st["nvidia"]) else None
        except Exception:
            st["nvidia"] = True
            st["gpu_name"] = None
        return st

    def _nv_drop_cache(self):
        with self._cachelock:
            self._cache.pop("nv:status", None)
            self._cache.pop("nv:settings", None)
            self._nv_checked = 0.0

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
        if not self._window:
            return
        import json
        script = (f"window.onPy && window.onPy({json.dumps(event)},"
                  f"{json.dumps(data)})")
        try:
            if hasattr(self._window, "run_js"):
                self._window.run_js(script)
            else:
                self._window.evaluate_js(script)
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
                latest_ver = latest[0] if latest else None
                # Decide the verdict here, with a real numeric comparison.
                # The UI used to do `latest === installed`, so ANY difference
                # - including an installed driver NEWER than the one the
                # vendor lists - was reported as "update available".
                cmp = drivers.compare_versions(installed, latest_ver)
                status = {None: "unknown", -1: "update",
                          0: "current", 1: "ahead"}[cmp]
                out.append({"name": name, "vendor": vendor,
                            "installed": installed,
                            "latest": latest_ver,
                            "status": status,
                            "url": latest[1] if latest else None,
                            "page": drivers.vendor_page(vendor)})
        except Exception as e:
            return {"error": str(e)}
        return {"gpus": out}

    @traced
    def download_driver(self, url, vendor, idx=0):
        """Start a driver download as a job. Returns immediately; the UI
        follows it through the job registry."""
        jobkey = "driver:" + str(idx)
        with self._jobslock:
            existing = self._jobs.get(jobkey)
            if existing and existing.get("state") == "running":
                return {"started": False, "job": dict(existing)}
        self._job_new(jobkey, "driver", "Driver download", indeterminate=False)
        self._dl_cancel.discard(jobkey)
        threading.Thread(target=self._run_download,
                         args=(url, vendor, jobkey), daemon=True).start()
        return {"started": True, "key": jobkey}

    def _run_download(self, url, vendor, jobkey):
        try:
            path = drivers.download(
                url, vendor,
                progress=lambda f: self._job_update(jobkey, throttle=0.2,
                    progress=f, line=f"{int(f*100)}%"),
                should_cancel=lambda: jobkey in self._dl_cancel)
            drivers.reveal(path)
            self._job_finish(jobkey, "done",
                             result={"ok": True, "path": path},
                             line="Saved to Downloads")
        except drivers.Cancelled:
            self._job_finish(jobkey, "cancelled",
                             result={"ok": False, "cancelled": True},
                             line="Cancelled")
        except Exception as e:
            self._job_finish(jobkey, "error",
                             result={"ok": False, "error": str(e)},
                             line="Failed")
        finally:
            self._dl_cancel.discard(jobkey)

    @traced
    def cancel_download(self, jobkey):
        self._dl_cancel.add(jobkey)
        return {"ok": True}

    # ---------------------------------------------------------- defender
    _DEF_READ = r"""
$ErrorActionPreference='SilentlyContinue'
$s = Get-MpComputerStatus
if ($null -eq $s) { '{"present":false}'; exit }
$o = [ordered]@{
  present     = $true
  realtime    = [bool]$s.RealTimeProtectionEnabled
  antispyware = [bool]$s.AntispywareEnabled
  behavior    = [bool]$s.BehaviorMonitorEnabled
  onaccess    = [bool]$s.OnAccessProtectionEnabled
  ioav        = [bool]$s.IoavProtectionEnabled
  nis         = [bool]$s.NISEnabled
  tamper      = [bool]$s.IsTamperProtected
  amservice   = [bool]$s.AMServiceEnabled
}
$o | ConvertTo-Json -Compress
"""

    # Only ever runs when Tamper Protection is OFF - otherwise Windows refuses
    # these and we never call it. Every line here is reversed by _DEF_ENABLE.
    _DEF_DISABLE = r"""
$ErrorActionPreference='SilentlyContinue'
Set-MpPreference -DisableRealtimeMonitoring $true
Set-MpPreference -DisableBehaviorMonitoring $true
Set-MpPreference -DisableOnAccessProtection $true
Set-MpPreference -DisableIOAVProtection $true
Set-MpPreference -DisableScriptScanning $true
Set-MpPreference -DisableIntrusionPreventionSystem $true
reg add "HKLM\SOFTWARE\Microsoft\Windows Defender Security Center\Notifications" /v DisableNotifications /t REG_DWORD /d 1 /f | Out-Null
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows Defender Security Center\Notifications" /v DisableEnhancedNotifications /t REG_DWORD /d 1 /f | Out-Null
'done'
"""

    _DEF_ENABLE = r"""
$ErrorActionPreference='SilentlyContinue'
Set-MpPreference -DisableRealtimeMonitoring $false
Set-MpPreference -DisableBehaviorMonitoring $false
Set-MpPreference -DisableOnAccessProtection $false
Set-MpPreference -DisableIOAVProtection $false
Set-MpPreference -DisableScriptScanning $false
Set-MpPreference -DisableIntrusionPreventionSystem $false
reg delete "HKLM\SOFTWARE\Microsoft\Windows Defender Security Center\Notifications" /v DisableNotifications /f | Out-Null
reg delete "HKLM\SOFTWARE\Policies\Microsoft\Windows Defender Security Center\Notifications" /v DisableEnhancedNotifications /f | Out-Null
'done'
"""

    def _defender_payload(self, d):
        present = bool(d.get("present"))
        realtime = bool(d.get("realtime"))
        active = present and (realtime or bool(d.get("amservice")))
        items = [
            {"label": "Real-time protection", "on": realtime},
            {"label": "Behaviour monitoring", "on": bool(d.get("behavior"))},
            {"label": "On-access scanning", "on": bool(d.get("onaccess"))},
            {"label": "Downloaded-file & web scanning", "on": bool(d.get("ioav"))},
            {"label": "Network inspection", "on": bool(d.get("nis"))},
            {"label": "Antimalware engine", "on": bool(d.get("antispyware"))},
        ]
        return {"present": present, "active": active,
                "tamper": bool(d.get("tamper")), "items": items}

    @traced
    def defender_status(self):
        rc, out = ps(self._DEF_READ)
        try:
            d = json.loads((out or "").strip() or "{}")
        except Exception:
            d = {}
        return self._defender_payload(d)

    @traced
    def defender_set(self, on):
        st = self.defender_status()
        if not st.get("present"):
            return {"ok": True, "status": st,
                    "message": "Defender is not installed on this PC."}
        if on:
            ps(self._DEF_ENABLE)
            return {"ok": True, "status": self.defender_status()}

        # Turning OFF. Windows forbids this while Tamper Protection is on, and
        # no tool can flip that switch - only the user, in the Windows Security
        # UI. Open that exact page and tell them.
        if st.get("tamper"):
            try:
                os.startfile("windowsdefender://threatsettings")
            except Exception:
                pass
            return {"ok": False, "tamper": True, "status": st,
                    "message": ("Tamper Protection is on. Turn it off in the "
                                "Windows Security window that just opened "
                                "(Virus & threat protection > Manage settings), "
                                "then tap the toggle again.")}
        ps(self._DEF_DISABLE)
        return {"ok": True, "status": self.defender_status()}

    # ---------------------------------------------------------- nvidia profile
    @traced
    def nvprofile_status(self):
        # Answer instantly from the startup scan, then quietly re-verify in the
        # background - the page updates itself via the "nvready" event.
        st = self._cached("nv:status", self._nv_status)
        self._nv_recheck()
        return st

    @traced
    def nvprofile_set(self, on):
        res = nvprofile.apply_profile(bool(on))
        # The machine's values just changed - re-read them in the background.
        self._nv_drop_cache()
        threading.Thread(target=self._warm_nvidia, daemon=True).start()
        return res

    @traced
    def nvprofile_settings(self):
        return self._cached("nv:settings", nvprofile.profile_settings)

    @traced
    def nvprofile_refresh(self):
        """Force an immediate re-read (the page's Refresh)."""
        self._nv_drop_cache()
        threading.Thread(target=self._warm_nvidia, daemon=True).start()
        return True

    @traced
    def nvprofile_ready(self):
        """True once the NVIDIA page can be filled with no waiting."""
        with self._cachelock:
            return "nv:settings" in self._cache

    @traced
    def open_url(self, url):
        import webbrowser
        webbrowser.open(url)
        return True

    # ----------------------------------------------------------- jobs
    # A job is any action that takes a while: SFC/DISM/disk check, a driver
    # download, the boot optimizer, a restore point. The registry lets the UI
    # walk away and come back to a still-running job instead of a fresh "Run"
    # button. Every job dict carries: key, kind, label, state
    # (running/done/error/cancelled), an optional 0..1 progress, a short
    # status line and, when finished, a result payload.

    def _job_new(self, key, kind, label, indeterminate=True):
        job = {"key": key, "kind": kind, "label": label, "state": "running",
               "progress": None if indeterminate else 0.0,
               "line": "", "result": None, "cancellable": True,
               "started": time.time(), "elapsed": 0}
        with self._jobslock:
            self._jobs[key] = job
        self._emit("job", dict(job))
        # A throttled update can swallow the last line of a burst, and a tool
        # that then goes quiet for minutes (DISM) leaves the page looking
        # frozen. This re-sends the current state once a second so the elapsed
        # timer keeps moving and the newest line always lands.
        threading.Thread(target=self._job_heartbeat, args=(key,),
                         daemon=True).start()
        return job

    def _job_heartbeat(self, key):
        while True:
            time.sleep(1.0)
            with self._jobslock:
                job = self._jobs.get(key)
                if not job or job.get("state") != "running":
                    return
                job["elapsed"] = int(time.time() - job.get("started", 0))
                job["_sent"] = time.time()
                snap = {k: v for k, v in job.items() if k != "_sent"}
            self._emit("job", snap)

    def _job_update(self, key, throttle=0.0, **fields):
        """Update a job. throttle caps how often the page is told - SFC emits
        a progress line several times a second and every emit costs a run_js
        hop on the GUI thread."""
        with self._jobslock:
            job = self._jobs.get(key)
            if not job:
                return
            job.update(fields)
            now = time.time()
            if throttle and (now - job.get("_sent", 0.0)) < throttle:
                return
            job["_sent"] = now
            snap = {k: v for k, v in job.items() if k != "_sent"}
        self._emit("job", snap)

    def _job_finish(self, key, state, result=None, line=""):
        with self._jobslock:
            job = self._jobs.get(key)
            if not job:
                return
            job["state"] = state
            job["result"] = result
            job["line"] = line
            job["progress"] = 1.0
            job["elapsed"] = int(time.time() - job.get("started", 0))
            snap = {k: v for k, v in job.items() if k != "_sent"}
        log(f"job {key}: {state} {snap.get('result')}")
        self._emit("job", snap)

    @traced
    def active_jobs(self):
        """Every job the UI should still be showing (running, or finished but
        not yet acknowledged). Called when a page mounts so it can restore the
        running state after a tab switch."""
        with self._jobslock:
            return [{k: v for k, v in j.items() if k != "_sent"}
                    for j in self._jobs.values()]

    @traced
    def job_state(self, key):
        with self._jobslock:
            j = self._jobs.get(key)
            return dict(j) if j else None

    @traced
    def ack_job(self, key):
        """The UI has shown the finished result - drop it from the registry."""
        with self._jobslock:
            j = self._jobs.get(key)
            if j and j.get("state") != "running":
                self._jobs.pop(key, None)
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

    @staticmethod
    def _sys32(exe):
        """Absolute path to a System32 tool.

        Never rely on PATH here: a frozen app's PATH starts with the
        PyInstaller extraction dir, and resolving 'chkdsk' through it was
        producing [WinError 5] Access is denied on CreateProcess.
        """
        root = os.environ.get("SystemRoot", r"C:\Windows")
        for sub in ("System32", "Sysnative"):
            cand = os.path.join(root, sub, exe)
            if os.path.exists(cand):
                return cand
        return exe

    def _res_cmds(self):
        return {
            "sfc": [self._sys32("sfc.exe"), "/scannow"],
            "dism": [self._sys32("dism.exe"), "/Online",
                     "/Cleanup-Image", "/RestoreHealth"],
            "chkdsk": [self._sys32("chkdsk.exe"), "C:", "/scan"],
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
            if "unable to obtain a handle" in low or "access denied" in low:
                return "problem", ("Windows would not let the scan open the "
                                   "drive. Close other disk tools and retry.")
            if ("found problems" in low or "errors found" in low
                    or "run chkdsk with the /f" in low):
                return "problem", ("Errors found on the drive. Run "
                                   "'chkdsk C: /f' from an admin prompt, "
                                   "then reboot to repair them.")
            # chkdsk's own exit codes, in plain English.
            return {
                0: ("clean", "No problems found on the drive."),
                1: ("problem", "Errors were found on the drive. Run "
                               "'chkdsk C: /f' from an admin prompt and "
                               "reboot to repair them."),
                2: ("clean", "No errors. Some tidy-up is still pending - "
                             "it needs 'chkdsk C: /f' to finish, but "
                             "nothing is wrong."),
                3: ("problem", "The scan could not complete. Usually another "
                               "program is using the drive - reboot and "
                               "try again."),
            }.get(rc, ("problem", f"Finished with an unexpected result "
                                  f"(code {rc})."))

        if rc == 0:
            return "clean", "Finished with no errors reported."
        return "problem", f"Finished with exit code {rc}."

    _RES_LABELS = {"sfc": "System File Checker",
                   "dism": "Windows Image Repair",
                   "chkdsk": "Disk Check"}

    @traced
    def resource_task(self, key):
        """Start a repair scan as a background job. Returns immediately; the
        UI follows it through the job registry / 'job' events."""
        jobkey = "res:" + key
        with self._jobslock:
            existing = self._jobs.get(jobkey)
            if existing and existing.get("state") == "running":
                return {"started": False, "job": dict(existing)}
        self._job_new(jobkey, "resource",
                      self._RES_LABELS.get(key, key), indeterminate=False)
        threading.Thread(target=self._run_resource, args=(key, jobkey),
                         daemon=True).start()
        return {"started": True, "key": jobkey}

    def _run_resource(self, key, jobkey):
        """Runs on a worker thread. EVERY exit path must finish the job with a
        real state + message, and log what happened - a silent thread here is
        what made the page show a bare 'Finished.' with no explanation."""
        import subprocess
        from tweaks_engine import CREATE_NO_WINDOW
        collected = []
        proc = None
        rc = None
        try:
            if not is_admin():
                # sfc / dism / chkdsk all refuse to do anything unelevated and
                # exit within a second. Say so instead of reporting a result.
                self._job_finish(jobkey, "error", result={
                    "ok": False, "state": "problem",
                    "message": ("This scan needs administrator rights and the "
                                "app is not elevated. Close it and reopen with "
                                "Run as administrator.")})
                log(f"resource {key}: refused, not elevated")
                return

            cmd = self._res_cmds()[key]
            # These tools write UTF-16 to a redirected pipe, so decode bytes
            # ourselves rather than letting Python assume UTF-8 - reading them
            # as UTF-8 produced NUL-riddled junk that matched none of the
            # verdict phrases, so every scan came back with a generic result.
            popen_kw = dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL,
                            creationflags=CREATE_NO_WINDOW)
            log(f"resource {key}: spawning {cmd}")
            try:
                proc = subprocess.Popen(cmd, **popen_kw)
            except OSError as e:
                if getattr(e, "winerror", None) != 5:
                    raise
                log(f"resource {key}: direct spawn denied, retrying via cmd.exe")
                proc = subprocess.Popen(
                    [self._sys32("cmd.exe"), "/c"] + cmd, **popen_kw)

            self._running[key] = proc
            # Decode FIRST, split lines second. Splitting the raw bytes on
            # b"\r" is wrong for UTF-16LE, where a newline is 0D 00 - the
            # orphaned 00 shifts every later line by one byte and the text
            # comes out as CJK gibberish.
            raw = b""            # undecoded bytes (may end mid-character)
            text_buf = ""        # decoded text not yet split into lines
            enc = None
            while True:
                # read1: hand back whatever has arrived. Plain read(n) blocks
                # until it has all n bytes, so a tool that goes quiet mid-run
                # (DISM does, for minutes) showed nothing at all.
                chunk = proc.stdout.read1(4096)
                if not chunk:
                    break
                raw += chunk
                if enc is None:
                    enc = self._sniff_encoding(raw)
                    if enc is None and len(raw) < 64:
                        continue          # not enough to tell yet
                    enc = enc or "cp1252"
                if enc == "utf-16-le":
                    usable = len(raw) - (len(raw) % 2)   # whole code units only
                else:
                    usable = len(raw)
                if usable:
                    text_buf += raw[:usable].decode(enc, "replace")
                    raw = raw[usable:]
                # Now split on real newlines in the decoded text.
                parts = re.split(r"[\r\n]+", text_buf)
                text_buf = parts.pop()          # keep the incomplete tail
                for part in parts:
                    part = self._clean_line(part)
                    if not part:
                        continue
                    collected.append(part)
                    # These tools report their own percentage ("Verification
                    # 21% complete.", DISM's [====  30.0% ====]) - use it for a
                    # real progress bar instead of a bar that just animates.
                    pct = self._parse_percent(part)
                    fields = {"line": part[:160]}
                    if pct is not None:
                        fields["progress"] = pct
                    self._job_update(jobkey, throttle=0.25, **fields)
            leftover = (text_buf + raw.decode(enc or "cp1252", "replace")
                        ).strip("\x00 \t\r\n")
            if leftover:
                collected.append(leftover)
            proc.wait()
            rc = proc.returncode
            log(f"resource {key}: exit {rc}, {len(collected)} lines")
        except Exception as e:
            self._running.pop(key, None)
            msg = str(e)
            if getattr(e, "winerror", None) == 5:
                msg = ("Windows refused to start the tool (Access denied). "
                       "Usually antivirus blocking it - "
                       f"{'the app IS elevated' if is_admin() else 'the app is NOT running as admin'}.")
            log(f"resource {key} FAILED\n" + traceback.format_exc())
            self._job_finish(jobkey, "error",
                             result={"ok": False, "state": "problem",
                                     "message": msg or "The scan could not run."})
            return

        cancelled = getattr(proc, "_tl_cancelled", False)
        self._running.pop(key, None)
        blob = " ".join(collected[-60:])
        try:
            state, message = self._verdict(key, blob, rc, cancelled)
        except Exception:
            log(f"resource {key}: verdict failed\n" + traceback.format_exc())
            state, message = "problem", f"Finished with exit code {rc}."
        if not message:
            message = f"Finished with exit code {rc}."
        log(f"resource {key}: verdict {state} - {message}")
        self._job_finish(jobkey, "cancelled" if cancelled else "done",
                         result={"ok": state in ("clean", "fixed"),
                                 "state": state, "message": message})

    _PCT = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")
    _CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

    @classmethod
    def _clean_line(cls, text):
        """DISM redraws its progress bar with backspaces and pads it with
        '=' and spaces; strip that down to something readable."""
        text = cls._CTRL.sub("", text)
        text = text.replace("\x7f", "")
        # [=========  42.0%  =========]  ->  42.0%
        bar = re.match(r"^\s*\[[=\s]*([\d.]+%)[=\s]*\]\s*$", text)
        if bar:
            return bar.group(1) + " complete"
        return text.strip(" \t")

    @classmethod
    def _parse_percent(cls, line):
        """0..1 progress out of a tool's own output line, or None."""
        m = cls._PCT.search(line)
        if not m:
            return None
        try:
            val = float(m.group(1))
        except ValueError:
            return None
        if 0.0 <= val <= 100.0:
            return val / 100.0
        return None

    @staticmethod
    def _sniff_encoding(raw):
        """Which codec this console tool is using. sfc.exe emits UTF-16LE down
        a pipe; dism and chkdsk emit the ANSI codepage. Returns None when
        there is not enough evidence yet."""
        if raw.startswith(b"\xff\xfe"):
            return "utf-16-le"
        head = raw[:256]
        if not head:
            return None
        # UTF-16LE ASCII text puts a NUL in every odd position.
        odd_nuls = sum(1 for i in range(1, len(head), 2) if head[i] == 0)
        odd_total = len(range(1, len(head), 2))
        if odd_total and odd_nuls / odd_total > 0.8:
            return "utf-16-le"
        if b"\x00" not in head:
            return "cp1252"
        return None

    @traced
    def cancel_task(self, key):
        # Accept either the raw key ("sfc") or the job key ("res:sfc").
        raw = key.split(":", 1)[1] if key.startswith("res:") else key
        proc = self._running.get(raw)
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
            log(f"cancel {raw}: {e}")
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


WEBVIEW2_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"


def webview2_version():
    """Installed Evergreen WebView2 runtime version, or None.

    pywebview silently falls back to MSHTML (Internet Explorer) when the
    runtime is missing. IE cannot render this UI, so the app comes up as a
    broken white page instead of saying what is wrong. We check first.
    """
    import winreg
    for hive, path in (
        (winreg.HKEY_LOCAL_MACHINE,
         rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_GUID}"),
        (winreg.HKEY_LOCAL_MACHINE,
         rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_GUID}"),
        (winreg.HKEY_CURRENT_USER,
         rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_GUID}"),
    ):
        try:
            with winreg.OpenKey(hive, path) as k:
                pv = winreg.QueryValueEx(k, "pv")[0]
                if pv and pv != "0.0.0.0":
                    return pv
        except OSError:
            continue
    return None


def require_webview2():
    """Return True if we can render. Otherwise explain and bail."""
    ver = webview2_version()
    if ver:
        log(f"webview2 runtime: {ver}")
        return True

    log("webview2 runtime: NOT FOUND - refusing to start on MSHTML")
    url = "https://developer.microsoft.com/microsoft-edge/webview2/"
    msg = (
        "Tech Lounge Tweaks needs the Microsoft WebView2 Runtime, "
        "which is not installed on this PC.\n\n"
        "Without it Windows falls back to Internet Explorer, which cannot "
        "display this app - you would get a broken white window.\n\n"
        "Click OK to open the Microsoft download page. Get the "
        "\"Evergreen Standalone Installer\" for x64, install it, "
        "then reboot and open this app again.\n\n"
        "Note: WebView2 is a normal Windows component used by Office, Teams "
        "and many other apps. It should not be uninstalled."
    )
    try:
        # 0x40 = MB_ICONINFORMATION, 0x1 = MB_OKCANCEL
        rc = ctypes.windll.user32.MessageBoxW(
            None, msg, "WebView2 Runtime required", 0x40 | 0x1)
        if rc == 1:
            os.startfile(url)
    except Exception:
        pass
    return False


def _close_splash():
    """Close the PyInstaller native splash. No-op in non-splash/dev runs."""
    try:
        import pyi_splash  # only present in --splash builds
        pyi_splash.close()
    except Exception:
        pass


def main():
    if not is_admin():
        relaunch_as_admin()
        return

    if not require_webview2():
        return

    log("=" * 50)
    log(f"start: frozen={getattr(sys, 'frozen', False)} exe={sys.executable}")
    api = Api()
    window = webview.create_window(
        "Tech Lounge Tweaks",
        here("web", "index.html"),
        js_api=api,
        width=1380, height=900, min_size=(940, 640),
        resizable=True,
        frameless=True, easy_drag=False,
        background_color="#0a0b12",
    )
    api._window = window
    log("window created")

    # THE fix for "hangs on first launch, works on reopen": the app runs as
    # administrator (needed to write HKLM), and WebView2's sandboxed browser
    # process deadlocks against that elevation on the GUI thread. Passing
    # --no-sandbox (plus the GPU-sandbox variant) lets WebView2 initialise
    # inside an elevated process reliably. This env var is the supported way
    # to hand extra flags to WebView2, read at start-up.
    prev = os.environ.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "")
    os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
        (prev + " " if prev else "") + "--no-sandbox --disable-gpu-sandbox").strip()

    log("starting webview…")
    webview.start(gui="edgechromium", private_mode=False, debug=False)


if __name__ == "__main__":
    main()
