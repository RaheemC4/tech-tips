"""Virtualisation mode: make VirtualBox / VMware run at native speed, or put
Windows' hypervisor-backed security back.

The problem this solves
-----------------------
VirtualBox wants the CPU's VT-x/AMD-V directly. When Windows runs its own
hypervisor - which it does for Virtualization Based Security, Memory Integrity
(HVCI), WSL2, Docker, Windows Sandbox and Hyper-V - Windows owns VT-x, and
VirtualBox has to go through Microsoft's Hyper-V API instead. VMs still run,
but far slower, and some fail outright.

So there are two sensible states, and this module flips between them:

  vm      hypervisor off at boot + HVCI off  -> VirtualBox gets native VT-x
  gaming  hypervisor auto + HVCI on          -> Windows' kernel protection back

What it deliberately does NOT touch
-----------------------------------
Secure Boot and TPM. Those are what Riot Vanguard and similar kernel
anti-cheats actually require on Windows 11, and they are firmware-level
settings this app has no business changing. Flipping to "vm" leaves both
exactly as they are.

Both directions need a reboot, because hypervisorlaunchtype is a boot setting.
"""

import re
import winreg

from tweaks_engine import HKLM, reg_get, reg_set, run, ps

HVCI_KEY = (r"SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios"
            r"\HypervisorEnforcedCodeIntegrity")
DG_KEY = r"SYSTEM\CurrentControlSet\Control\DeviceGuard"
LSA_KEY = r"SYSTEM\CurrentControlSet\Control\Lsa"

# One CIM call for everything that is cheap to read. Deliberately avoids
# Get-WindowsOptionalFeature / DISM, which takes seconds and is not needed to
# decide which mode we are in.
_READ = r"""
$ErrorActionPreference='SilentlyContinue'
$o=[ordered]@{}
$cs = Get-CimInstance Win32_ComputerSystem
$o.hypervisor_present = [bool]$cs.HypervisorPresent
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$o.vt_firmware = [bool]$cpu.VirtualizationFirmwareEnabled
try {
  $dg = Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard `
        -ClassName Win32_DeviceGuard -ErrorAction Stop
  $o.vbs_status  = [int]$dg.VirtualizationBasedSecurityStatus
  $o.running     = @($dg.SecurityServicesRunning)
} catch { $o.vbs_status = -1; $o.running = @() }
try {
  $sb = Confirm-SecureBootUEFI -ErrorAction Stop
  $o.secureboot = [bool]$sb
} catch { $o.secureboot = $null }
try {
  $tpm = Get-Tpm -ErrorAction Stop
  $o.tpm = [bool]$tpm.TpmPresent -and [bool]$tpm.TpmReady
} catch { $o.tpm = $null }
$o | ConvertTo-Json -Compress -Depth 3
"""


def hypervisor_launchtype():
    """'off', 'auto', 'on' or None if it cannot be read."""
    rc, out = run(["bcdedit", "/enum", "{current}"])
    m = re.search(r"(?im)^\s*hypervisorlaunchtype\s+(\w+)", out or "")
    return m.group(1).lower() if m else None


def hvci_enabled():
    return reg_get(HKLM, HVCI_KEY, "Enabled") == 1


def virtualbox_info():
    """(installed, version) for VirtualBox."""
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(HKLM, r"SOFTWARE\Oracle\VirtualBox", 0,
                                winreg.KEY_READ | view) as k:
                try:
                    ver = winreg.QueryValueEx(k, "Version")[0]
                except OSError:
                    ver = None
                return True, ver
        except OSError:
            continue
    return False, None


def status():
    import json
    rc, out = ps(_READ)
    try:
        d = json.loads((out or "").strip() or "{}")
    except Exception:
        d = {}

    launch = hypervisor_launchtype()
    hvci = hvci_enabled()
    vbs_status = d.get("vbs_status", -1)
    vbs_running = vbs_status == 2
    vbox, vbox_ver = virtualbox_info()

    # Win32_Processor.VirtualizationFirmwareEnabled lies: it reports False on
    # plenty of machines where VT-x is clearly on, especially once a hypervisor
    # has already claimed it. So treat a running hypervisor or running VBS as
    # proof the firmware setting IS enabled - neither can exist without it.
    hyperv_present = bool(d.get("hypervisor_present"))
    vt = bool(d.get("vt_firmware")) or hyperv_present or vbs_running

    # "vm" once Windows is not launching its hypervisor and HVCI is off.
    # bcdedit reports nothing at all when the setting was never written, and
    # Windows treats that as auto - so a missing value is NOT vm mode.
    in_vm_mode = (launch == "off") and not hvci and not vbs_running
    in_gaming_mode = (launch in (None, "auto", "on")) and hvci

    blockers = []
    if hvci:
        blockers.append("Memory Integrity (HVCI) is on")
    if launch in (None, "auto", "on"):
        blockers.append("Windows launches its own hypervisor at boot")
    if vbs_running:
        blockers.append("Virtualization Based Security is running")

    return {
        "vt_firmware": vt,
        "vt_reported": bool(d.get("vt_firmware")),
        "hypervisor_present": bool(d.get("hypervisor_present")),
        "launchtype": launch or "auto",
        "hvci": hvci,
        "vbs_status": vbs_status,
        "vbs_running": vbs_running,
        "secureboot": d.get("secureboot"),
        "tpm": d.get("tpm"),
        "virtualbox": vbox,
        "virtualbox_version": vbox_ver,
        "mode": "vm" if in_vm_mode else ("gaming" if in_gaming_mode else "mixed"),
        "blockers": blockers,
        "reboot_required": False,
    }


def set_mode(mode):
    """Flip between 'vm' and 'gaming'. Returns (ok, message, changes)."""
    changes = []
    if mode not in ("vm", "gaming"):
        return False, "Unknown mode.", changes

    if mode == "vm":
        rc, out = run(["bcdedit", "/set", "hypervisorlaunchtype", "off"])
        if rc != 0:
            return (False,
                    "Could not change the boot setting. The app needs to be "
                    f"running as administrator. ({(out or '').strip()[:120]})",
                    changes)
        changes.append("Windows hypervisor will not start at boot")

        try:
            reg_set(HKLM, HVCI_KEY, "Enabled", 0)
            changes.append("Memory Integrity (HVCI) turned off")
        except OSError as e:
            return False, f"Could not turn Memory Integrity off: {e}", changes
        # Credential Guard pins the hypervisor on too when it is configured.
        try:
            reg_set(HKLM, DG_KEY, "EnableVirtualizationBasedSecurity", 0)
            reg_set(HKLM, LSA_KEY, "LsaCfgFlags", 0)
            changes.append("Credential Guard disabled")
        except OSError:
            pass
        return True, "Reboot to finish switching to VM mode.", changes

    # Back to gaming / protected.
    rc, out = run(["bcdedit", "/set", "hypervisorlaunchtype", "auto"])
    if rc != 0:
        return (False,
                "Could not change the boot setting. The app needs to be "
                f"running as administrator. ({(out or '').strip()[:120]})",
                changes)
    changes.append("Windows hypervisor starts at boot again")
    try:
        reg_set(HKLM, HVCI_KEY, "Enabled", 1)
        changes.append("Memory Integrity (HVCI) turned back on")
    except OSError as e:
        return False, f"Could not turn Memory Integrity on: {e}", changes
    try:
        reg_set(HKLM, DG_KEY, "EnableVirtualizationBasedSecurity", 1)
        changes.append("Virtualization Based Security re-enabled")
    except OSError:
        pass
    return True, "Reboot to finish switching back.", changes
