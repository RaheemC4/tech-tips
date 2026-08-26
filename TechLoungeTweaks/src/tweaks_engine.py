"""
Tech Lounge Tweaks - tweak definitions and state detection.

Every tweak exposes apply(), revert() and check().  check() reads the
live system state and returns True when the tweak is already in effect,
which is what lets the UI lock toggles that are already enabled.
"""

import os
import re
import subprocess
import winreg

HKCU = winreg.HKEY_CURRENT_USER
HKLM = winreg.HKEY_LOCAL_MACHINE

CREATE_NO_WINDOW = 0x08000000


# --------------------------------------------------------------------------
# Registry helpers
# --------------------------------------------------------------------------

def reg_get(hive, path, name, default=None):
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return default


_HIVE_NAME = {winreg.HKEY_LOCAL_MACHINE: "HKLM", winreg.HKEY_CURRENT_USER: "HKCU"}

# Creating a key needs KEY_CREATE_SUB_KEY on the parent, not just KEY_SET_VALUE.
# Asking for KEY_SET_VALUE alone made every tweak whose key did not already
# exist fail with [WinError 5] Access is denied.
_WRITE = winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY


def _reg_set_direct(hive, path, name, value, vtype):
    with winreg.CreateKeyEx(hive, path, 0, _WRITE) as k:
        winreg.SetValueEx(k, name, 0, vtype, value)


def _reg_set_stepwise(hive, path, name, value, vtype):
    """Create each level in turn - some parents refuse a deep one-shot create."""
    parts, cur = path.split("\\"), ""
    for part in parts:
        cur = f"{cur}\\{part}" if cur else part
        winreg.CreateKeyEx(hive, cur, 0, _WRITE).Close()
    _reg_set_direct(hive, path, name, value, vtype)


def _reg_set_regexe(hive, path, name, value, vtype):
    hn = _HIVE_NAME.get(hive)
    if not hn:
        raise OSError("unsupported hive for reg.exe fallback")
    tn = {winreg.REG_DWORD: "REG_DWORD", winreg.REG_SZ: "REG_SZ",
          winreg.REG_EXPAND_SZ: "REG_EXPAND_SZ"}.get(vtype, "REG_DWORD")
    rc, out = run(["reg", "add", f"{hn}\\{path}", "/v", name,
                   "/t", tn, "/d", str(value), "/f"])
    if rc != 0:
        raise OSError(f"reg.exe add failed: {out.strip()[:160]}")


def reg_set(hive, path, name, value, vtype=winreg.REG_DWORD):
    """Write a registry value, trying progressively more tolerant methods."""
    last = None
    for attempt in (_reg_set_direct, _reg_set_stepwise, _reg_set_regexe):
        try:
            attempt(hive, path, name, value, vtype)
            return
        except OSError as e:
            last = e
            if getattr(e, "winerror", None) not in (5, 1314, None):
                raise
    hn = _HIVE_NAME.get(hive, "?")
    raise OSError(
        5, f"Access denied writing {hn}\\{path}\\{name}. This key is "
           f"locked down by Windows or by security software. ({last})")


def reg_del_value(hive, path, name):
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, name)
    except OSError:
        pass


def reg_del_tree(hive_str, path):
    run(["reg", "delete", f"{hive_str}\\{path}", "/f"])


def run(args):
    """Run a command with no console window; return (rc, output)."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=90,
                           stdin=subprocess.DEVNULL,
                           creationflags=CREATE_NO_WINDOW)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return 1, "SUBPROCESS_ERROR: " + str(e)


def ps(cmd):
    return run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-Command", cmd])


def svc_start_value(name):
    return reg_get(HKLM, rf"SYSTEM\CurrentControlSet\Services\{name}", "Start")


def set_svc_start(name, value):
    key = rf"SYSTEM\CurrentControlSet\Services\{name}"
    if reg_get(HKLM, key, "Start") is not None:
        reg_set(HKLM, key, "Start", value)


# --------------------------------------------------------------------------
# Tweak model
# --------------------------------------------------------------------------

class Tweak:
    def __init__(self, key, name, desc, category, apply, revert, check,
                 warning=None, icon="⚙", needs_restart=False):
        self.key = key
        self.name = name
        self.desc = desc
        self.category = category
        self._apply = apply
        self._revert = revert
        self._check = check
        self.warning = warning
        self.icon = icon
        self.needs_restart = needs_restart
        self.error = None

    def apply(self):
        self._apply()

    def revert(self):
        self._revert()

    def check(self):
        self.error = None
        try:
            return bool(self._check())
        except Exception as e:
            import traceback
            self.error = traceback.format_exc(limit=3)
            return False


def simple_reg(hive, path, name, on_value, off_value,
               vtype=winreg.REG_DWORD, delete_on_revert=False):
    """Build (apply, revert, check) for a single registry value."""
    def _apply():
        reg_set(hive, path, name, on_value, vtype)

    def _revert():
        if delete_on_revert:
            reg_del_value(hive, path, name)
        else:
            reg_set(hive, path, name, off_value, vtype)

    def _check():
        cur = reg_get(hive, path, name)
        return cur is not None and str(cur) == str(on_value)

    return _apply, _revert, _check


# --------------------------------------------------------------------------
# Individual tweaks that need custom logic
# --------------------------------------------------------------------------

GAMEDVR_STORE = r"System\GameConfigStore"
GAMEDVR_POLICY = (r"SOFTWARE\Microsoft\PolicyManager\default"
                  r"\ApplicationManagement\AllowGameDVR")


def t_widgets():
    """Disable the Widgets board.

    HKLM\\SOFTWARE\\Policies\\Microsoft\\Dsh is the enterprise policy key and
    is locked on some Windows 11 builds - writing it returned Access denied.
    The per-user taskbar setting (TaskbarDa) is the one that reliably works
    and needs no policy rights, so that is the source of truth here. The
    policy key is still attempted, but never allowed to fail the tweak.
    """
    TASKBAR = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    DSH = r"SOFTWARE\Policies\Microsoft\Dsh"

    def _policy(value):
        try:
            reg_set(HKLM, DSH, "AllowNewsAndInterests", value)
        except OSError:
            pass                      # locked down - the user setting still works

    def _apply():
        reg_set(HKCU, TASKBAR, "TaskbarDa", 0)
        _policy(0)

    def _revert():
        reg_set(HKCU, TASKBAR, "TaskbarDa", 1)
        _policy(1)

    def _check():
        if reg_get(HKCU, TASKBAR, "TaskbarDa") == 0:
            return True
        return reg_get(HKLM, DSH, "AllowNewsAndInterests") == 0

    return _apply, _revert, _check


def t_gamedvr():
    def _apply():
        reg_set(HKCU, GAMEDVR_STORE, "GameDVR_Enabled", 0)
        reg_set(HKLM, GAMEDVR_POLICY, "value", 0)
        reg_set(HKCU, r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
                "AppCaptureEnabled", 0)

    def _revert():
        reg_set(HKCU, GAMEDVR_STORE, "GameDVR_Enabled", 1)
        reg_set(HKLM, GAMEDVR_POLICY, "value", 1)
        reg_set(HKCU, r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
                "AppCaptureEnabled", 1)

    def _check():
        return (reg_get(HKCU, GAMEDVR_STORE, "GameDVR_Enabled") == 0 and
                reg_get(HKLM, GAMEDVR_POLICY, "value") == 0 and
                reg_get(HKCU,
                        r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
                        "AppCaptureEnabled") == 0)

    return _apply, _revert, _check


def t_fullscreen_opt():
    p = GAMEDVR_STORE
    vals = {
        "GameDVR_FSEBehaviorMode": 2,
        "GameDVR_HonorUserFSEBehaviorMode": 1,
        "GameDVR_DXGIHonorFSEWindowsCompatible": 1,
        "GameDVR_EFSEFeatureFlags": 0,
    }

    def _apply():
        for n, v in vals.items():
            reg_set(HKCU, p, n, v)

    def _revert():
        reg_set(HKCU, p, "GameDVR_FSEBehaviorMode", 2)
        reg_set(HKCU, p, "GameDVR_HonorUserFSEBehaviorMode", 0)
        reg_set(HKCU, p, "GameDVR_DXGIHonorFSEWindowsCompatible", 0)
        reg_set(HKCU, p, "GameDVR_EFSEFeatureFlags", 0)

    def _check():
        return (reg_get(HKCU, p, "GameDVR_FSEBehaviorMode") == 2 and
                reg_get(HKCU, p, "GameDVR_HonorUserFSEBehaviorMode") == 1)

    return _apply, _revert, _check


ULTIMATE_GUID = "e9a42b02-d5df-448d-aa00-03f14749eb61"


def _guids_in(text):
    out = []
    for tok in (text or "").replace("(", " ").replace(")", " ").split():
        if len(tok) == 36 and tok.count("-") == 4:
            out.append(tok.lower())
    return out


def _ultimate_guid():
    """GUID of the Ultimate Performance scheme on this machine, if present.

    Matching the words "Ultimate Performance" breaks on non-English Windows,
    so compare scheme GUIDs instead. Duplicated schemes keep their own GUID,
    so we look for one whose entry is derived from the well-known template.
    """
    rc, out = run(["powercfg", "/list"])
    known = set()
    for line in (out or "").splitlines():
        g = _guids_in(line)
        if g:
            known.add(g[0])
    if ULTIMATE_GUID.lower() in known:
        return ULTIMATE_GUID.lower()
    for line in (out or "").splitlines():
        if "ultimate" in line.lower():
            g = _guids_in(line)
            if g:
                return g[0]
    return None


def t_ultimate_power():
    def _apply():
        # Only duplicate when it is not already there - repeat runs used to
        # pile up a new copy of the scheme every single time.
        guid = _ultimate_guid()
        if not guid:
            run(["powercfg", "-duplicatescheme", ULTIMATE_GUID])
            guid = _ultimate_guid()
        if guid:
            run(["powercfg", "/setactive", guid])

    def _revert():
        run(["powercfg", "/setactive", "381b4222-f694-41f0-9685-ff5bb260df2e"])

    def _check():
        guid = _ultimate_guid()
        if not guid:
            return False
        rc, out = run(["powercfg", "/getactivescheme"])
        return guid in [g.lower() for g in _guids_in(out)]

    return _apply, _revert, _check


def t_nagle():
    """TcpAckFrequency / TCPNoDelay on every configured interface."""
    base = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"

    def _iter_ifaces():
        out = []
        try:
            with winreg.OpenKey(HKLM, base) as k:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(k, i)
                    except OSError:
                        break
                    i += 1
                    full = base + "\\" + sub
                    if (reg_get(HKLM, full, "DhcpIPAddress") or
                            reg_get(HKLM, full, "IPAddress")):
                        out.append(full)
        except OSError:
            pass
        return out

    def _apply():
        for p in _iter_ifaces():
            reg_set(HKLM, p, "TcpAckFrequency", 1)
            reg_set(HKLM, p, "TCPNoDelay", 1)

    def _revert():
        for p in _iter_ifaces():
            reg_del_value(HKLM, p, "TcpAckFrequency")
            reg_del_value(HKLM, p, "TCPNoDelay")

    def _check():
        # Applied if any real adapter carries the values. Windows keeps
        # stale interface keys around, so all() is wrong here.
        for p in _iter_ifaces():
            if (reg_get(HKLM, p, "TcpAckFrequency") == 1 and
                    reg_get(HKLM, p, "TCPNoDelay") == 1):
                return True
        return False

    return _apply, _revert, _check


GAMES_TASK = (r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
              r"\Multimedia\SystemProfile\Tasks\Games")


def t_games_priority():
    def _apply():
        reg_set(HKLM, GAMES_TASK, "GPU Priority", 8)
        reg_set(HKLM, GAMES_TASK, "Priority", 6)
        reg_set(HKLM, GAMES_TASK, "Scheduling Category", "High", winreg.REG_SZ)
        reg_set(HKLM, GAMES_TASK, "SFIO Priority", "High", winreg.REG_SZ)

    def _revert():
        reg_set(HKLM, GAMES_TASK, "GPU Priority", 8)
        reg_set(HKLM, GAMES_TASK, "Priority", 2)
        reg_set(HKLM, GAMES_TASK, "Scheduling Category", "High", winreg.REG_SZ)
        reg_set(HKLM, GAMES_TASK, "SFIO Priority", "Normal", winreg.REG_SZ)

    def _check():
        # Category is "High" by default too, so Priority is the real signal.
        return reg_get(HKLM, GAMES_TASK, "Priority") == 6

    return _apply, _revert, _check


MM_PROFILE = (r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
              r"\Multimedia\SystemProfile")


def t_fast_shutdown():
    """Matches the Boot Optimizer's value so the two never fight.

    The optimiser writes 2000 here. Anything clearly below the 5000 default
    counts as applied, so running one does not switch the other off.
    """
    path = r"SYSTEM\CurrentControlSet\Control"

    def _apply():
        reg_set(HKLM, path, "WaitToKillServiceTimeout", "2000", winreg.REG_SZ)

    def _revert():
        reg_set(HKLM, path, "WaitToKillServiceTimeout", "5000", winreg.REG_SZ)

    def _check():
        cur = reg_get(HKLM, path, "WaitToKillServiceTimeout")
        try:
            return int(str(cur)) < 5000
        except (TypeError, ValueError):
            return False

    return _apply, _revert, _check


def t_network_throttle():
    def _apply():
        reg_set(HKLM, MM_PROFILE, "NetworkThrottlingIndex", 0xFFFFFFFF)
        # 0 starves the audio/multimedia thread reservation and is the
        # usual cause of crackling under load. 10 is the safe floor.
        reg_set(HKLM, MM_PROFILE, "SystemResponsiveness", 10)

    def _revert():
        reg_set(HKLM, MM_PROFILE, "NetworkThrottlingIndex", 10)
        reg_set(HKLM, MM_PROFILE, "SystemResponsiveness", 20)

    def _check():
        return (reg_get(HKLM, MM_PROFILE, "NetworkThrottlingIndex") == 0xFFFFFFFF
                and (reg_get(HKLM, MM_PROFILE, "SystemResponsiveness") or 20) <= 10)

    return _apply, _revert, _check


def t_mouse_accel():
    p = r"Control Panel\Mouse"

    def _apply():
        for n, v in (("MouseSpeed", "0"), ("MouseThreshold1", "0"),
                     ("MouseThreshold2", "0")):
            reg_set(HKCU, p, n, v, winreg.REG_SZ)

    def _revert():
        for n, v in (("MouseSpeed", "1"), ("MouseThreshold1", "6"),
                     ("MouseThreshold2", "10")):
            reg_set(HKCU, p, n, v, winreg.REG_SZ)

    def _check():
        return str(reg_get(HKCU, p, "MouseSpeed")) == "0"

    return _apply, _revert, _check


def t_classic_context():
    clsid = r"SOFTWARE\CLASSES\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}"

    def _apply():
        reg_set(HKCU, clsid + r"\InprocServer32", "", "", winreg.REG_SZ)

    def _revert():
        reg_del_tree("HKCU", clsid)

    def _check():
        # Key existence alone is not enough - the classic menu only comes
        # back when the (Default) value is present and empty.
        try:
            with winreg.OpenKey(HKCU, clsid + r"\InprocServer32") as k:
                val, _typ = winreg.QueryValueEx(k, "")
                return val == ""
        except OSError:
            return False

    return _apply, _revert, _check


def t_firewall_notify():
    def _apply():
        ps("Set-NetFirewallProfile -All -NotifyOnListen False")

    def _revert():
        ps("Set-NetFirewallProfile -All -NotifyOnListen True")

    def _check():
        # Set-NetFirewallProfile writes the LOCAL store, not the policy store
        # the old check read - so this reported other people's GPO settings.
        base = (r"SYSTEM\CurrentControlSet\Services\SharedAccess"
                r"\Parameters\FirewallPolicy")
        profiles = ("StandardProfile", "DomainProfile", "PublicProfile")
        vals = [reg_get(HKLM, base + "\\" + name, "DisableNotifications")
                for name in profiles]
        if all(v == 1 for v in vals):
            return True
        rc, out = ps("(Get-NetFirewallProfile -All).NotifyOnListen -join ','")
        return bool(out) and "True" not in out

    return _apply, _revert, _check


def service_tweak(svc, disabled_value=4, normal_value=2):
    def _apply():
        set_svc_start(svc, disabled_value)
        # Rewriting Start alone leaves the service running until reboot.
        run(["sc", "stop", svc])

    def _revert():
        set_svc_start(svc, normal_value)
        run(["sc", "start", svc])

    def _check():
        v = svc_start_value(svc)
        return v is not None and v == disabled_value

    return _apply, _revert, _check


def t_memory_integrity():
    p = (r"SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios"
         r"\HypervisorEnforcedCodeIntegrity")

    def _apply():
        reg_set(HKLM, p, "Enabled", 0)

    def _revert():
        reg_set(HKLM, p, "Enabled", 1)

    def _check():
        return reg_get(HKLM, p, "Enabled") == 0

    return _apply, _revert, _check


DX_PREFS = r"Software\Microsoft\DirectX\UserGpuPreferences"


def _dx_global_get():
    return str(reg_get(HKCU, DX_PREFS, "DirectXUserGlobalSettings") or "")


def _dx_global_set(pairs):
    cur = _dx_global_get()
    parts = {}
    for item in cur.split(";"):
        if "=" in item:
            k, v = item.split("=", 1)
            parts[k.strip()] = v.strip()
    parts.update(pairs)
    new = ";".join(f"{k}={v}" for k, v in parts.items() if v != "") + ";"
    reg_set(HKCU, DX_PREFS, "DirectXUserGlobalSettings", new, winreg.REG_SZ)


def dx_toggle(flag):
    def _apply():
        _dx_global_set({flag: "1"})

    def _revert():
        _dx_global_set({flag: "0"})

    def _check():
        return f"{flag}=1" in _dx_global_get()

    return _apply, _revert, _check



def bcd_flag(name, on_value="Yes"):
    """Toggle a bcdedit boolean and detect it from `bcdedit /enum`."""
    def _apply():
        run(["bcdedit", "/set", name, on_value.lower()])

    def _revert():
        run(["bcdedit", "/deletevalue", name])

    def _check():
        rc, out = run(["bcdedit", "/enum", "{current}"])
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].lower() == name.lower():
                return parts[1].strip().lower() == on_value.lower()
        return False

    return _apply, _revert, _check


def mmagent(flag):
    """Disable-MMAgent / Enable-MMAgent for memory compression etc."""
    def _apply():
        ps(f"Disable-MMAgent -{flag}")

    def _revert():
        ps(f"Enable-MMAgent -{flag}")

    def _check():
        rc, out = ps(f"(Get-MMAgent).{flag}")
        return "False" in (out or "")

    return _apply, _revert, _check



# --------------------------------------------------------------------------
# GPU vendor detection (cached - WMI is slow)
# --------------------------------------------------------------------------

_gpu_cache = None


def gpu_vendors():
    global _gpu_cache
    if _gpu_cache is None:
        rc, out = ps("(Get-CimInstance Win32_VideoController).Name -join '|'")
        text = (out or "").lower()
        _gpu_cache = {
            "nvidia": any(k in text for k in
                          ("nvidia", "geforce", "rtx", "gtx", "quadro")),
            "amd": any(k in text for k in ("radeon", "amd ", "rx ")),
        }
    return _gpu_cache


NV_KEY = r"SYSTEM\CurrentControlSet\Services\nvlddmkm"
DISPLAY_CLASS = (r"SYSTEM\CurrentControlSet\Control\Class"
                 r"\{4d36e968-e325-11ce-bfc1-08002be10318}")

_amd_key_cache = None


def amd_class_key():
    """Locate the AMD adapter's driver key.

    Hardcoding \0000 wrote these values into whichever adapter happened to
    enumerate first - on a machine with an Intel iGPU that is the wrong
    vendor's key entirely.
    """
    global _amd_key_cache
    if _amd_key_cache is not None:
        return _amd_key_cache
    fallback = DISPLAY_CLASS + r"\0000"
    try:
        with winreg.OpenKey(HKLM, DISPLAY_CLASS) as root:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                if not sub.isdigit():
                    continue
                full = DISPLAY_CLASS + "\\" + sub
                blob = " ".join(str(reg_get(HKLM, full, n) or "")
                                for n in ("DriverDesc", "ProviderName"))
                if re.search(r"(?i)\bamd\b|radeon|ati ", blob):
                    _amd_key_cache = full
                    return full
    except OSError:
        pass
    _amd_key_cache = fallback
    return fallback


AMD_CLASS = DISPLAY_CLASS + r"\0000"



NV_FTS = r"SOFTWARE\NVIDIA Corporation\Global\FTS"
NV_TELEMETRY_RIDS = ("EnableRID44231", "EnableRID64640", "EnableRID66610")
NV_TASK_PATTERNS = ("NvTmRep*", "NvTmMon*", "NvTmRepOnLogon*",
                    "NvProfileUpdater*", "NvDriverUpdateCheck*")


def t_nv_telemetry():
    """Cover every place NVIDIA telemetry lives.

    The old version only touched NvTelemetryContainer and NvTm* tasks. On
    current NVIDIA App drivers neither exists, so nothing was written and the
    toggle could never stick. The FTS registry flags are always writable, so
    they are what the check keys off.
    """
    def _tasks(action):
        names = ",".join(f"'{p}'" for p in NV_TASK_PATTERNS)
        ps(f"foreach($n in @({names})) {{ Get-ScheduledTask -TaskName $n "
           f"-ErrorAction SilentlyContinue | {action}-ScheduledTask "
           f"-ErrorAction SilentlyContinue }}")

    def _apply():
        for rid in NV_TELEMETRY_RIDS:
            reg_set(HKLM, NV_FTS, rid, 0)
        set_svc_start("NvTelemetryContainer", 4)
        _tasks("Disable")

    def _revert():
        for rid in NV_TELEMETRY_RIDS:
            reg_set(HKLM, NV_FTS, rid, 1)
        set_svc_start("NvTelemetryContainer", 2)
        _tasks("Enable")

    def _check():
        return all(reg_get(HKLM, NV_FTS, rid) == 0
                   for rid in NV_TELEMETRY_RIDS)

    return _apply, _revert, _check


# --------------------------------------------------------------------------
# Registry of all tweaks
# --------------------------------------------------------------------------

def build_tweaks():
    T = []

    def add(key, name, desc, cat, triple, warning=None, icon="⚙",
            restart=False):
        a, r, c = triple
        T.append(Tweak(key, name, desc, cat, a, r, c, warning, icon, restart))

    # ---------------- Performance ----------------
    add("gamedvr", "Disable GameDVR",
        "Turns off Xbox Game Bar background recording. One of the biggest "
        "free FPS wins on Windows 11.",
        "Performance", t_gamedvr(), icon="■")

    add("game_mode", "Enable Game Mode",
        "Tells Windows to prioritise the running game and hold back "
        "background work and driver updates.",
        "Performance",
        simple_reg(HKCU, r"Software\Microsoft\GameBar",
                   "AutoGameModeEnabled", 1, 0),
        icon="◎")

    add("fse", "Disable Fullscreen Optimizations",
        "Forces true exclusive fullscreen instead of the borderless "
        "compositor path. Lowers input lag in most games.",
        "Performance", t_fullscreen_opt(), icon="▣")

    add("power_throttle", "Disable Power Throttling",
        "Stops Windows quietly downclocking background threads, which can "
        "cause stutter in CPU-heavy games.",
        "Performance",
        simple_reg(HKLM, r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling",
                   "PowerThrottlingOff", 1, 0),
        icon="⚡")

    add("ultimate_power", "Ultimate Performance Power Plan",
        "Unlocks and activates the hidden Ultimate Performance plan. Keeps "
        "cores from parking or dropping clocks.",
        "Performance", t_ultimate_power(), icon="⚡")

    add("prio_sep", "Foreground Priority Boost",
        "Sets Win32PrioritySeparation so the focused app gets a longer, "
        "more consistent CPU time slice.",
        "Performance",
        simple_reg(HKLM, r"SYSTEM\CurrentControlSet\Control\PriorityControl",
                   "Win32PrioritySeparation", 38, 2),
        icon="↗")

    add("games_task", "Gaming Task Priority",
        "Raises the GPU and scheduling priority Windows gives the Games "
        "multimedia profile.",
        "Performance", t_games_priority(), icon="⌘")

    add("mem_integrity", "Disable Memory Integrity",
        "Turns off HVCI core isolation for 5-15% more CPU performance. Valorant/Vanguard and some anti-cheats will refuse to launch.",
        "Performance", t_memory_integrity(),
        warning="Breaks Valorant, Vanguard and some anti-cheats",
        icon="⛨", restart=True)

    # ---------------- Graphics ----------------
    add("hags", "Hardware GPU Scheduling",
        "Lets the GPU manage its own memory and scheduling instead of the "
        "CPU. If unset, Windows uses the driver default - applying "
        "this makes it explicit.",
        "Graphics",
        simple_reg(HKLM, r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
                   "HwSchMode", 2, 1, delete_on_revert=True),
        icon="◧", restart=True)

    add("vrr", "Variable Refresh Rate",
        "Enables VRR for games that do not natively support it, smoothing "
        "frame pacing on G-Sync / FreeSync displays.",
        "Graphics", dx_toggle("VRROptimizeEnable"), icon="↻")

    add("swap_effect", "Optimizations for Windowed Games",
        "Uses the modern flip presentation model for borderless and "
        "windowed games. Big latency reduction.",
        "Graphics", dx_toggle("SwapEffectUpgradeEnable"), icon="◰")

    add("mouse_accel", "Disable Mouse Acceleration",
        "Removes the pointer acceleration curve so mouse movement maps "
        "1:1. Makes aim consistent.",
        "Graphics", t_mouse_accel(), icon="➤")

    # ---------------- Networking ----------------
    add("nagle", "Disable Nagle's Algorithm",
        "Stops Windows bundling small packets together, which cuts a few "
        "ms off latency in online games.",
        "Networking", t_nagle(), icon="⊕", restart=True)

    add("net_throttle", "Network Throttling Off",
        "Removes the 10-packet-per-ms multimedia throttle and lowers the "
        "multimedia CPU reservation to 10% (0 causes audio crackle).",
        "Networking", t_network_throttle(), icon="⌒")

    add("nic_offload", "Disable Network Offloads",
        "Turns off Chimney, RSC and packet coalescing so packets are not "
        "batched by the network card.",
        "Networking",
        (lambda: ps("Set-NetOffloadGlobalSetting -Chimney Disabled; "
                    "Set-NetOffloadGlobalSetting -ReceiveSegmentCoalescing Disabled; "
                    "Set-NetOffloadGlobalSetting -PacketCoalescingFilter Disabled"),
         lambda: ps("Set-NetOffloadGlobalSetting -Chimney Enabled; "
                    "Set-NetOffloadGlobalSetting -ReceiveSegmentCoalescing Enabled; "
                    "Set-NetOffloadGlobalSetting -PacketCoalescingFilter Enabled"),
         lambda: all(x == "Disabled" for x in ps(
             "$s=Get-NetOffloadGlobalSetting; "
             "$s.ReceiveSegmentCoalescing; $s.PacketCoalescingFilter"
         )[1].split()[:2] or ["x"])),
        icon="⇄")

    add("firewall_notify", "Disable Firewall Popups",
        "Stops the 'Windows Defender Firewall has blocked some features' "
        "prompt every time a new game launches.",
        "Networking", t_firewall_notify(), icon="▤")

    # ---------------- System ----------------
    add("fast_shutdown", "Speed Up Shutdown",
        "Cuts the time Windows waits for services to close on shutdown, "
        "from 5 seconds down to 2.",
        "System", t_fast_shutdown(), icon="⏻")

    add("menu_delay", "Instant Menu Animations",
        "Drops the menu show delay from 400ms to 20ms so the UI feels "
        "immediate.",
        "System",
        simple_reg(HKCU, r"Control Panel\Desktop",
                   "MenuShowDelay", "20", "400", winreg.REG_SZ),
        icon="⚡")

    add("startup_delay", "Remove Startup App Delay",
        "Removes the artificial 10 second delay Windows adds before "
        "startup apps are allowed to run.",
        "System",
        simple_reg(HKCU,
                   r"Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize",
                   "StartupDelayInMSec", 0, 1, delete_on_revert=True),
        icon="▲")

    add("sysmain", "Disable SysMain (Superfetch)",
        "Superfetch preloads apps into RAM. Useless on an SSD and a common "
        "cause of disk spikes.",
        "System", service_tweak("SysMain"), icon="◫", restart=True)

    add("diagtrack", "Disable Telemetry Service",
        "Stops the Connected User Experiences and Telemetry service from "
        "running in the background.",
        "System", service_tweak("DiagTrack"), icon="≡", restart=True)

    # ---------------- Explorer & UI ----------------
    add("dyn_search", "Disable Dynamic Search Box",
        "Stops the Windows search box resizing and animating as you type.",
        "Explorer & UI",
        simple_reg(HKCU,
                   r"Software\Microsoft\Windows\CurrentVersion\SearchSettings",
                   "IsDynamicSearchBoxEnabled", 0, 1),
        icon="⌕")

    add("bing_search", "Remove Bing from Start",
        "Keeps Start Menu search local only, with no web results or "
        "Copilot suggestions.",
        "Explorer & UI",
        simple_reg(HKCU, r"SOFTWARE\Policies\Microsoft\Windows\Explorer",
                   "DisableSearchBoxSuggestions", 1, 0),
        icon="⊘")

    add("context_menu", "Restore Classic Context Menu",
        "Brings back the full Windows 10 right-click menu instead of the "
        "trimmed Windows 11 one.",
        "Explorer & UI", t_classic_context(), icon="➤")

    add("snap_layout", "Disable Snap Layout Flyout",
        "Removes the layout popup that appears when you hover the "
        "maximise button.",
        "Explorer & UI",
        simple_reg(HKCU,
                   r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                   "EnableSnapAssistFlyout", 0, 1),
        icon="◰")

    add("lockscreen", "Disable Lock Screen",
        "Skips the lock screen and goes straight to the sign-in prompt.",
        "Explorer & UI",
        simple_reg(HKLM, r"SOFTWARE\Policies\Microsoft\Windows\Personalization",
                   "NoLockScreen", 1, 0),
        icon="⚿")

    add("widgets", "Disable Widgets",
        "Removes the Widgets board and its background feed process from "
        "the taskbar.",
        "Explorer & UI",
        t_widgets(),
        icon="⌸")

    add("cdm_ads", "Disable Suggestions & Ads",
        "Turns off the Content Delivery Manager tips, app suggestions and "
        "Start Menu adverts.",
        "Explorer & UI",
        (lambda: [reg_set(HKCU, r"Software\Microsoft\Windows\CurrentVersion"
                          r"\ContentDeliveryManager", n, 0)
                  for n in ("SilentInstalledAppsEnabled",
                            "SystemPaneSuggestionsEnabled",
                            "SubscribedContent-338388Enabled",
                            "SubscribedContent-338389Enabled",
                            "SoftLandingEnabled")],
         lambda: [reg_set(HKCU, r"Software\Microsoft\Windows\CurrentVersion"
                          r"\ContentDeliveryManager", n, 1)
                  for n in ("SilentInstalledAppsEnabled",
                            "SystemPaneSuggestionsEnabled",
                            "SubscribedContent-338388Enabled",
                            "SubscribedContent-338389Enabled",
                            "SoftLandingEnabled")],
         lambda: all(reg_get(HKCU, r"Software\Microsoft\Windows"
                             r"\CurrentVersion\ContentDeliveryManager", n) == 0
                     for n in ("SilentInstalledAppsEnabled",
                               "SystemPaneSuggestionsEnabled",
                               "SoftLandingEnabled"))),
        icon="✇")

    # ---------------- Power ----------------
    add("dynamic_tick", "Disable Dynamic Tick",
        "Forces the kernel timer to fire at a fixed rate instead of "
        "skipping ticks while idle.",
        "Power", bcd_flag("disabledynamictick"), icon="↻", restart=True)

    add("timer_coalescing", "Disable Timer Coalescing",
        "Stops Windows grouping timer callbacks together. Timers fire on "
        "schedule at the cost of more wakeups.",
        "Power",
        simple_reg(HKLM,
                   r"SYSTEM\CurrentControlSet\Control\Session Manager\kernel",
                   "CoalescingTimerInterval", 0, 1, delete_on_revert=True),
        icon="⌒")

    add("usb_suspend", "Disable USB Selective Suspend",
        "Stops Windows powering down USB ports. Fixes mice and keyboards "
        "that stutter or drop after idle.",
        "Power",
        simple_reg(HKLM, r"SYSTEM\CurrentControlSet\Services\USB",
                   "DisableSelectiveSuspend", 1, 0),
        icon="⇄")

    add("usb_power_mgmt", "Disable USB Power Management",
        "Turns off enhanced power management on every USB hub so the "
        "controller stops aggressively idling devices.",
        "Power",
        (lambda: ps("Get-CimInstance Win32_USBHub | ForEach-Object { "
                    "$p = Get-CimInstance -ClassName MSPower_DeviceEnable "
                    "-Namespace root/wmi -ErrorAction SilentlyContinue | "
                    "Where-Object InstanceName -like ($_.PNPDeviceID + '*'); "
                    "if ($p) { $p | Set-CimInstance -Property @{Enable=$false} "
                    "-ErrorAction SilentlyContinue } }"),
         lambda: ps("Get-CimInstance Win32_USBHub | ForEach-Object { "
                    "$p = Get-CimInstance -ClassName MSPower_DeviceEnable "
                    "-Namespace root/wmi -ErrorAction SilentlyContinue | "
                    "Where-Object InstanceName -like ($_.PNPDeviceID + '*'); "
                    "if ($p) { $p | Set-CimInstance -Property @{Enable=$true} "
                    "-ErrorAction SilentlyContinue } }"),
         lambda: "TLOFF" in ps(
             "$h=Get-CimInstance Win32_USBHub; $o=$false; foreach($d in $h){"
             "$p=Get-CimInstance -ClassName MSPower_DeviceEnable -Namespace "
             "root/wmi -ErrorAction SilentlyContinue | Where-Object "
             "InstanceName -like ($d.PNPDeviceID + '*'); "
             "if($p -and -not $p.Enable){$o=$true}}; "
             "if($o){'TLOFF'}else{'TLON'}")[1]),
        icon="⊕")

    # ---------------- Advanced ----------------
    add("mem_compression", "Disable Memory Compression",
        "Turns off in-RAM compression. Lower CPU overhead, slightly higher "
        "physical memory use.",
        "Advanced", mmagent("MemoryCompression"), icon="◫")

    add("page_combining", "Disable Page Combining",
        "Disables the kernel feature that deduplicates identical memory "
        "pages. Reduces CPU overhead at rest.",
        "Advanced", mmagent("PageCombining"), icon="▦")

    add("mitigations", "Disable CPU Mitigations",
        "Turns off the Spectre and Meltdown microcode workarounds. Real "
        "CPU gains, at a genuine security cost.",
        "Advanced",
        (lambda: [reg_set(HKLM, r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                          "FeatureSettingsOverride", 3),
                  reg_set(HKLM, r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                          "FeatureSettingsOverrideMask", 3)],
         lambda: [reg_del_value(HKLM, r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                                "FeatureSettingsOverride"),
                  reg_del_value(HKLM, r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                                "FeatureSettingsOverrideMask")],
         lambda: (reg_get(HKLM, r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                          "FeatureSettingsOverride") == 3 and
                  reg_get(HKLM, r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                          "FeatureSettingsOverrideMask") == 3)),
        warning="Weakens Spectre / Meltdown protection", icon="⛨", restart=True)

    # ---------------- Privacy ----------------
    add("telemetry", "Disable Telemetry",
        "Sets diagnostic data to the lowest level Windows allows and turns "
        "off the event transcript.",
        "Privacy",
        simple_reg(HKLM, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                   "AllowTelemetry", 0, 1),
        icon="≡")

    add("ceip", "Disable Experience Program",
        "Opts out of the Customer Experience Improvement Program that "
        "uploads usage metrics to Microsoft.",
        "Privacy",
        simple_reg(HKLM, r"SOFTWARE\Microsoft\SQMClient\Windows",
                   "CEIPEnable", 0, 1),
        icon="⊘")

    add("feedback", "Disable Feedback Prompts",
        "Stops Windows periodically asking you how likely you are to "
        "recommend it.",
        "Privacy",
        simple_reg(HKCU, r"SOFTWARE\Microsoft\Siuf\Rules",
                   "NumberOfSIUFInPeriod", 0, 1),
        icon="✇")

    add("app_tracking", "Disable App Launch Tracking",
        "Stops Windows recording which apps you open for the Start menu's "
        "most-used list.",
        "Privacy",
        simple_reg(HKCU,
                   r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                   "Start_TrackProgs", 0, 1),
        icon="⌕")

    add("activity_history", "Disable Activity History",
        "Turns off Timeline collection and the upload of your activity to "
        "your Microsoft account.",
        "Privacy",
        simple_reg(HKLM, r"SOFTWARE\Policies\Microsoft\Windows\System",
                   "PublishUserActivities", 0, 1),
        icon="↻")

    add("error_reporting", "Disable Error Reporting",
        "Suppresses WerFault crash upload dialogs and background crash "
        "reporting.",
        "Privacy",
        simple_reg(HKLM, r"SOFTWARE\Microsoft\Windows\Windows Error Reporting",
                   "Disabled", 1, 0),
        icon="▲")

    add("ad_id", "Disable Advertising ID",
        "Removes the per-user advertising ID apps use to track you across "
        "sessions.",
        "Privacy",
        simple_reg(HKCU,
                   r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
                   "Enabled", 0, 1),
        icon="✇")

    add("lang_header", "Disable Language Tracking",
        "Stops websites reading your preferred language list through the "
        "Accept-Language header.",
        "Privacy",
        simple_reg(HKCU, r"Control Panel\International\User Profile",
                   "HttpAcceptLanguageOptOut", 1, 0),
        icon="⊕")

    add("typing_insights", "Disable Typing Insights",
        "Turns off the typing statistics Windows collects for personalised "
        "suggestions.",
        "Privacy",
        simple_reg(HKCU, r"SOFTWARE\Microsoft\Input\TIPC", "Enabled", 0, 1),
        icon="⌗")

    add("speech_data", "Disable Speech Collection",
        "Opts out of online speech recognition data collection.",
        "Privacy",
        simple_reg(HKCU,
                   r"SOFTWARE\Microsoft\Speech_OneCore\Settings\OnlineSpeechPrivacy",
                   "HasAccepted", 0, 1),
        icon="⌒")

    add("ink_collection", "Disable Ink & Typing Collection",
        "Stops Windows collecting handwriting and typed text samples for "
        "personalisation.",
        "Privacy",
        simple_reg(HKCU, r"SOFTWARE\Microsoft\InputPersonalization",
                   "RestrictImplicitInkCollection", 1, 0),
        icon="➤")

    # ---------------- GPU ----------------
    vendors = gpu_vendors()

    if vendors.get("nvidia"):
        add("nv_write_combine", "Disable Write Combining",
            "Turns off GPU write-combining. Can reduce micro-stutter on "
            "some driver versions.",
            "GPU",
            simple_reg(HKLM, NV_KEY, "DisableWriteCombining", 1, 0,
                       delete_on_revert=True),
            icon="◧", restart=True)

        add("nv_preempt", "Disable Preemption",
            "Lets the GPU finish each frame in one pass instead of pausing "
            "for background work. Smoother frame pacing.",
            "GPU",
            (lambda: [reg_set(HKLM, NV_KEY, "DisablePreemption", 1),
                      reg_set(HKLM, NV_KEY, "DisableCudaContextPreemption", 1)],
             lambda: [reg_del_value(HKLM, NV_KEY, "DisablePreemption"),
                      reg_del_value(HKLM, NV_KEY,
                                    "DisableCudaContextPreemption")],
             lambda: (reg_get(HKLM, NV_KEY, "DisablePreemption") == 1 and
                      reg_get(HKLM, NV_KEY,
                              "DisableCudaContextPreemption") == 1)),
            icon="↗", restart=True)

        add("nv_pstate", "Lock GPU to P0 State",
            "Keeps the GPU in its maximum performance power state instead "
            "of dropping clocks at idle. Higher idle power draw.",
            "GPU",
            simple_reg(HKLM, NV_KEY, "DisableDynamicPstate", 1, 0,
                       delete_on_revert=True),
            icon="⚡", restart=True)

        add("nv_telemetry", "Disable NVIDIA Telemetry",
            "Stops the NVIDIA telemetry container and its scheduled tasks "
            "from running in the background.",
            "GPU",
            t_nv_telemetry(),
            icon="≡")

    if vendors.get("amd"):
        add("amd_ulps", "Disable ULPS",
            "Stops the GPU dropping into Ultra Low Power State - the usual "
            "cause of idle and multi-GPU clock stutter.",
            "GPU",
            simple_reg(HKLM, amd_class_key(), "EnableUlps", 0, 1),
            icon="⚡", restart=True)

        add("amd_preempt", "Disable Compute Preemption",
            "Lets the Radeon GPU finish each frame uninterrupted instead of "
            "pausing for compute work. Tighter 1% lows.",
            "GPU",
            simple_reg(HKLM, amd_class_key(), "KMD_EnableComputePreemption", 0, 1),
            icon="↗", restart=True)

        add("amd_tess", "Override Tessellation",
            "Lets the driver override each game's tessellation level, "
            "cutting GPU geometry load.",
            "GPU",
            (lambda: [reg_set(HKLM, amd_class_key(), "DisableTessellation", 1),
                      reg_set(HKLM, amd_class_key(), "TessellationLevel", "0",
                              winreg.REG_SZ)],
             lambda: [reg_del_value(HKLM, amd_class_key(), "DisableTessellation"),
                      reg_del_value(HKLM, amd_class_key(), "TessellationLevel")],
             lambda: reg_get(HKLM, amd_class_key(), "DisableTessellation") == 1),
            icon="◧")

        add("amd_powergating", "Disable DRM DMA Power Gating",
            "Keeps the display DMA engine clocked instead of gating it "
            "during idle.",
            "GPU",
            simple_reg(HKLM, AMD_CLASS, "DisableDrmdmaPowerGating", 1, 0,
                       delete_on_revert=True),
            icon="⚡", restart=True)

    return T


CATEGORY_ORDER = ["Performance", "Graphics", "GPU", "Networking",
                  "Power", "Advanced", "System", "Privacy",
                  "Explorer & UI"]

CATEGORY_ICONS = {
    "Performance": "▲",
    "Graphics": "◧",
    "Networking": "⊕",
    "System": "⚙",
    "Explorer & UI": "⌸",
    "Power": "⚡",
    "Advanced": "↗",
    "Privacy": "⛨",
    "GPU": "◧",
}
