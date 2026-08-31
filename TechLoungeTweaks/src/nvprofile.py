"""
NVIDIA Profile applier.

Applies a bundled NVIDIA Profile Inspector .nip (Raheem's exported global
settings) using NVPI / NVPI-Revamped, which the app finds sitting next to it.

The app does NOT download or ship the Inspector itself - it uses whatever the
distributor (Raheem) has placed in the app folder. That keeps a third-party
binary out of anything Claude fetches, and byte-accurate settings out of a
hand-written file.
"""

import os
import re
import glob
import shutil
import subprocess
import threading

CREATE_NO_WINDOW = 0x08000000

# Filenames we accept for the Inspector, in order of preference.
TOOL_NAMES = [
    "nvidiaProfileInspector.exe",
    "NvidiaProfileInspector.exe",
    "nvidiaProfileInspectorRevamped.exe",
    "NVPI.exe",
]
PROFILE_NAME = "TechLoungeProfile.nip"    # Raheem's settings (toggle ON)
DEFAULTS_NAME = "TechLoungeDefaults.nip"  # NVIDIA defaults  (fallback OFF)
BACKUP_NAME = "TechLoungeBackup.nip"     # this machine's own prior settings

RELEASES_URL = "https://github.com/xHybred/NvidiaProfileInspectorRevamped/releases"
MARKER = None  # set at import time below


def _app_dir():
    """Folder the app runs from - where the tool and .nip live."""
    import sys
    if getattr(sys, "frozen", False):
        # onedir: exe sits beside _internal; onefile: sys.executable dir
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _search_dirs():
    # Keep the top-level folder clean: the tool + data live in a "resources"
    # subfolder, so users only ever see TechLoungeTweaks.exe up top.
    app = _app_dir()
    d = [os.path.join(app, "resources"), app]
    store = os.path.join(os.environ.get("LOCALAPPDATA", ""), "TechLoungeTweaks")
    if store:
        d.append(store)
    return d


def _find(names):
    for d in _search_dirs():
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    return None


def find_tool():
    return _find(TOOL_NAMES)


def find_profile():
    return _find([PROFILE_NAME])


def find_defaults():
    return _find([DEFAULTS_NAME])


def _marker_path():
    store = os.path.join(os.environ.get("LOCALAPPDATA", ""), "TechLoungeTweaks")
    try:
        os.makedirs(store, exist_ok=True)
    except Exception:
        pass
    return os.path.join(store, "nvprofile.applied")


def is_applied():
    return os.path.exists(_marker_path())


def _store_dir():
    d = os.path.join(os.environ.get("LOCALAPPDATA", ""), "TechLoungeTweaks")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


def backup_path():
    return os.path.join(_store_dir(), BACKUP_NAME)


def _backup_marker():
    return os.path.join(_store_dir(), "nvbackup.done")


def find_backup():
    p = backup_path()
    return p if os.path.exists(p) else None


def ensure_backup(has_nvidia):
    """Snapshot this machine's current NVIDIA customizations - ONCE, ever.

    Runs on startup only when: there's an NVIDIA GPU, the Inspector is present,
    and we've not already done it (a marker file or the backup itself exists).
    The backup lives in %LOCALAPPDATA% (per user, per machine) - it is NEVER
    shipped to friends; each machine captures its own. Best-effort: any failure
    just means the revert falls back to a defaults file if one is bundled.
    """
    if not has_nvidia:
        return {"done": False, "reason": "no-nvidia"}
    if os.path.exists(_backup_marker()) or os.path.exists(backup_path()):
        return {"done": True, "reason": "exists"}
    tool = find_tool()
    if not tool:
        return {"done": False, "reason": "no-tool"}

    tdir = os.path.dirname(tool)
    before = set(glob.glob(os.path.join(tdir, "*.nip")))
    try:
        subprocess.run([tool, "-exportCustomized"], cwd=tdir,
                       capture_output=True, text=True, timeout=60,
                       creationflags=CREATE_NO_WINDOW)
    except Exception as e:
        return {"done": False, "reason": "export-failed", "error": str(e)}

    after = set(glob.glob(os.path.join(tdir, "*.nip")))
    new = sorted(after - before, key=lambda x: os.path.getmtime(x), reverse=True)

    # Mark the attempt so we never export again, whatever the result.
    try:
        open(_backup_marker(), "w").write("1")
    except Exception:
        pass

    if new:
        try:
            shutil.move(new[0], backup_path())
            return {"done": True, "reason": "captured"}
        except Exception as e:
            return {"done": False, "reason": "move-failed", "error": str(e)}
    # No new file: the machine had no NVIDIA customizations to back up.
    return {"done": True, "reason": "no-customizations"}


def status():
    tool = find_tool()
    prof = find_profile()
    return {
        "tool": bool(tool),
        "profile": bool(prof),
        "defaults": bool(find_defaults()),
        "backup": bool(find_backup()),
        "applied": is_applied(),
        "releases_url": RELEASES_URL,
        "tool_names": TOOL_NAMES,
        "profile_name": PROFILE_NAME,
    }


def _run_nip(tool, nip):
    """Apply a .nip silently. Returns (ok, message)."""
    # NVPI / Revamped: passing a .nip path imports+applies it. -silent suppresses UI.
    for args in ([tool, "-silentImport", nip], [tool, nip, "-silent"], [tool, nip]):
        try:
            p = subprocess.run(args, capture_output=True, text=True, timeout=60,
                               creationflags=CREATE_NO_WINDOW)
            out = ((p.stdout or "") + (p.stderr or "")).strip()
            if p.returncode == 0:
                return True, out or "Applied."
            last = f"exit {p.returncode}: {out[:200]}"
        except Exception as e:
            last = str(e)
    return False, last


def apply_profile(on):
    st = status()
    if not st["tool"]:
        return {"ok": False, "need_tool": True,
                "message": "NVIDIA Profile Inspector isn't in the app folder yet."}
    tool = find_tool()

    if on:
        nip = find_profile()
        if not nip:
            return {"ok": False, "need_profile": True,
                    "message": f"{PROFILE_NAME} isn't in the app folder yet."}
    else:
        # Prefer this machine's own captured backup; fall back to a bundled
        # defaults file only if there's no backup.
        nip = find_backup() or find_defaults()
        if not nip:
            return {"ok": False, "need_defaults": True,
                    "message": ("No backup was captured and no defaults file is "
                                "bundled, so the app won't guess. Use the "
                                "Inspector's own Restore.")}

    ok, msg = _run_nip(tool, nip)
    if ok:
        try:
            if on:
                open(_marker_path(), "w").write("1")
            elif os.path.exists(_marker_path()):
                os.remove(_marker_path())
        except Exception:
            pass
    return {"ok": ok, "message": msg, "applied": on if ok else is_applied()}


# Human-readable view of what the bundled profile applies. Only the settings
# whose meaning is well-established are shown, so nothing misleading appears.
# Display names we prefer over the tool's internal ones. The VALUE labels are
# never hardcoded - they come from the Inspector's own reference XMLs at
# runtime (see _value_names), because hand-written maps went stale and showed
# raw numbers like "G-SYNC 0" instead of what the setting actually is.
NV_LABELS = {
    "274197361": "Power Management Mode",
    "277041152": "Low Latency Mode",
    "11041231":  "Vertical Sync",
    "5912412":   "V-Sync Tear Control",
    "6600001":   "Preferred Refresh Rate",
    "279476687": "G-SYNC",
    "294973784": "G-SYNC Mode",
    "13510289":  "Texture Filtering - Quality",
    "15151633":  "Texture Filtering - Aniso Sample Optimization",
    "8102046":   "Max Pre-Rendered Frames",
}
NV_ORDER = ["274197361", "277041152", "11041231", "5912412", "6600001",
            "279476687", "294973784", "13510289", "15151633", "8102046"]

# A few values read better in plain English than in the tool's own wording.
NV_VALUE_OVERRIDES = {
    "279476687": {"0": "On (allowed)", "1": "Force off", "2": "Off (disallowed)",
                  "3": "Ultra Low Motion Blur", "4": "Fixed refresh rate"},
    "294973784": {"0": "Off", "1": "Fullscreen only", "2": "Fullscreen & windowed"},
    "6600001":   {"0": "Application-controlled", "1": "Highest available"},
    "11041231":  {"138504007": "Off", "1199655232": "On",
                  "1620202130": "Application-controlled"},
    "274197361": {"0": "Normal", "1": "Prefer maximum performance",
                  "5": "Optimal power"},
}

_REF_FILES = ("Reference.xml", "CustomSettingNames.xml")
_ref_cache = None
_ref_lock = threading.Lock()


def _load_reference():
    """SettingID -> (name, {value: label}) straight from the Inspector's XMLs.

    These ship beside the tool, define every setting the driver exposes, and
    are the same source the Inspector's own UI reads, so the labels we show
    always match what the user sees in Profile Inspector.
    """
    global _ref_cache
    with _ref_lock:
        if _ref_cache is not None:
            return _ref_cache
    out = {}
    tool = find_tool()
    tdir = os.path.dirname(tool) if tool else None
    for fname in _REF_FILES:
        path = os.path.join(tdir, fname) if tdir else None
        if not path or not os.path.exists(path):
            continue
        try:
            raw = open(path, "rb").read().decode("utf-8", "replace")
        except Exception:
            continue
        for block in re.findall(r"<CustomSetting>(.*?)</CustomSetting>", raw, re.S):
            m = re.search(r"<HexSettingID>0x([0-9A-Fa-f]+)</HexSettingID>", block)
            if not m:
                continue
            sid = str(int(m.group(1), 16))
            if sid in out:               # first file wins
                continue
            nm = re.search(r"<UserfriendlyName>([^<]*)</UserfriendlyName>", block)
            values = {}
            for label, hexval in re.findall(
                    r"<UserfriendlyName>([^<]*)</UserfriendlyName>\s*"
                    r"<HexValue>0x([0-9A-Fa-f]+)</HexValue>", block):
                values[str(int(hexval, 16))] = label.strip()
            out[sid] = ((nm.group(1).strip() if nm else sid), values)
    with _ref_lock:
        _ref_cache = out
    return out


def _friendly(sid, raw):
    """(row label, value label) for one setting."""
    ref = _load_reference()
    ref_name, values = ref.get(sid, (None, {}))
    label = NV_LABELS.get(sid) or ref_name or sid
    key = str(raw).strip()
    text = NV_VALUE_OVERRIDES.get(sid, {}).get(key)
    if text is not None:
        return label, text
    text = values.get(key)
    if text is None:
        text = str(raw)
    else:
        # The XMLs spell some values as sentences; trim to the useful half.
        text = text.split(" - ")[0].strip()
    return label, text


GLOBAL_NAMES = ("base profile", "_global_driver_profile", "global")


def _global_block(raw):
    """The GLOBAL profile block out of a .nip that may hold many profiles.

    -exportCustomized writes EVERY customized profile - the global one plus a
    <Profile> block per game that has overrides. Reading setting IDs straight
    off the whole file merged them all together, so a per-game override could
    masquerade as the machine's global value. The global profile is the one
    with no executables attached (and, when named, "Base Profile").
    """
    import re
    blocks = re.findall(r"<Profile>(.*?)</Profile>", raw, re.S)
    if not blocks:
        return raw
    named = []
    for b in blocks:
        m = re.search(r"<ProfileName>([^<]*)</ProfileName>", b)
        name = (m.group(1) if m else "").strip().lower()
        if name in GLOBAL_NAMES:
            return b
        named.append((b, name))
    # No name matched: the global profile is the one with no executables.
    for b, _name in named:
        if not re.search(r"<Executeables\s*>\s*<", b):
            return b
    return blocks[0]


def _parse_nip_values(path):
    import re
    try:
        raw = open(path, "rb").read().decode("utf-8-sig", "replace")
    except Exception:
        return {}
    vals = {}
    for m in re.finditer(
            r"<SettingID>(\d+)</SettingID>\s*<SettingValue>([^<]*)</SettingValue>",
            _global_block(raw)):
        vals[m.group(1)] = m.group(2).strip()
    return vals


def current_values():
    """The machine's CURRENT NVIDIA values (customized ones), via the tool.

    Returns (ran, {sid: value}). ran=False means the export could not run, so
    the UI should not claim to know current values.
    """
    tool = find_tool()
    if not tool:
        return (False, {})
    tdir = os.path.dirname(tool)
    before = set(glob.glob(os.path.join(tdir, "*.nip")))
    try:
        subprocess.run([tool, "-exportCustomized"], cwd=tdir,
                       capture_output=True, text=True, timeout=60,
                       creationflags=CREATE_NO_WINDOW)
    except Exception:
        return (False, {})
    after = set(glob.glob(os.path.join(tdir, "*.nip")))
    new = sorted(after - before, key=lambda x: os.path.getmtime(x), reverse=True)
    if not new:
        # Export ran but produced nothing = machine has no customizations.
        return (True, {})
    vals = _parse_nip_values(new[0])
    try:
        os.remove(new[0])          # do not leave the temp export lying around
    except Exception:
        pass
    return (True, vals)




def compare_to_profile(ran, cur):
    """How much of the profile is live on this machine right now.

    Returns (state, matched, total) where state is one of
    "applied" / "partial" / "off" / "unknown".
    """
    nip = find_profile()
    if not nip or not ran:
        return ("unknown", 0, 0)
    target = _parse_nip_values(nip)
    total = len(target)
    if not total:
        return ("unknown", 0, 0)
    matched = sum(1 for sid, v in target.items() if cur.get(sid) == v)
    if matched == total:
        return ("applied", matched, total)
    if matched == 0:
        return ("off", matched, total)
    return ("partial", matched, total)


def scan_state():
    """One silent export -> real status + the settings table.

    This is what keeps the page honest across restarts: the marker file only
    records what THIS app did, so anything changed in the NVIDIA Control Panel,
    in Profile Inspector directly, or by a driver reinstall would otherwise
    still show as "applied". Here we read what the driver actually holds and
    reconcile the marker to match.
    """
    ran, cur = current_values()
    state, matched, total = compare_to_profile(ran, cur)

    # Reconcile our marker with what the driver actually has.
    try:
        if state == "applied" and not os.path.exists(_marker_path()):
            open(_marker_path(), "w").write("1")
        elif state in ("off", "partial") and os.path.exists(_marker_path()):
            os.remove(_marker_path())
    except Exception:
        pass

    st = status()
    st["applied"] = (state == "applied")
    st["state"] = state
    st["matched"] = matched
    st["total"] = total
    st["checked"] = ran
    return {"status": st, "settings": profile_settings(ran, cur)}


def profile_settings(ran=None, cur=None):
    """[(name, current, target)] - what each setting is now vs after applying."""
    nip = find_profile()
    if not nip:
        return []
    target = _parse_nip_values(nip)
    if cur is None:
        ran, cur = current_values()

    out = []
    for sid in NV_ORDER:
        if sid not in target:
            continue
        label, target_text = _friendly(sid, target[sid])
        if not ran:
            cur_text = None                     # unknown - hide the current col
        elif sid in cur:
            _, cur_text = _friendly(sid, cur[sid])
        else:
            cur_text = "Default"                # at NVIDIA's default
        out.append({"name": label, "current": cur_text, "target": target_text})
    return out
