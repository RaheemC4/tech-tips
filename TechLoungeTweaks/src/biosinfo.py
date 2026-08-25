"""Firmware / BIOS information, read-only.

Reads what Windows exposes about the firmware and reports whether the
board's vendor offers a *supported* WMI interface for changing BIOS
settings from Windows. It deliberately does not poke firmware directly.
"""

from tweaks_engine import ps, run, reg_get, HKLM
import winreg


def _ps_val(cmd):
    rc, out = ps(cmd)
    out = (out or "").strip()
    if rc != 0 or not out or "SUBPROCESS_ERROR" in out:
        return None
    return out.splitlines()[0].strip() if out else None


def collect():
    """Return a list of (label, value) plus a vendor-support verdict."""
    info = []

    board_mfr = _ps_val("(Get-CimInstance Win32_BaseBoard).Manufacturer")
    board = _ps_val("(Get-CimInstance Win32_BaseBoard).Product")
    info.append(("Motherboard",
                 " ".join(x for x in (board_mfr, board) if x) or "Unknown"))

    info.append(("CPU", _ps_val("(Get-CimInstance Win32_Processor "
                                "| Select-Object -First 1).Name") or "Unknown"))

    bios_v = _ps_val("(Get-CimInstance Win32_BIOS).SMBIOSBIOSVersion")
    bios_d = _ps_val("(Get-CimInstance Win32_BIOS).ReleaseDate")
    if bios_d and len(bios_d) >= 8 and bios_d[:8].isdigit():
        bios_d = f"{bios_d[6:8]}/{bios_d[4:6]}/{bios_d[0:4]}"
    info.append(("BIOS version",
                 " ".join(x for x in (bios_v, bios_d) if x) or "Unknown"))

    # Firmware mode: UEFI vs Legacy
    fw = reg_get(HKLM, r"SYSTEM\CurrentControlSet\Control", "PEFirmwareType")
    info.append(("Boot mode",
                 {1: "Legacy BIOS", 2: "UEFI"}.get(fw, "Unknown")))

    sb = _ps_val("try { if (Confirm-SecureBootUEFI) {'On'} else {'Off'} } "
                 "catch { 'Not supported' }")
    info.append(("Secure Boot", sb or "Unknown"))

    tpm = _ps_val("try { $t=Get-Tpm; "
                  "if ($t.TpmPresent -and $t.TpmReady) {'Present and ready'} "
                  "elseif ($t.TpmPresent) {'Present, not ready'} "
                  "else {'Not detected'} } catch { 'Could not query' }")
    info.append(("TPM", tpm or "Unknown"))

    virt = _ps_val("(Get-CimInstance Win32_ComputerSystem)."
                   "HypervisorPresent")
    vt = _ps_val("(Get-CimInstance Win32_Processor "
                 "| Select-Object -First 1).VirtualizationFirmwareEnabled")
    if vt == "True":
        vtxt = "Enabled in firmware"
    elif vt == "False":
        vtxt = "Disabled in firmware"
    else:
        vtxt = "Hypervisor running" if virt == "True" else "Unknown"
    info.append(("Virtualization (VT-x/SVM)", vtxt))

    vbs = _ps_val("try { (Get-CimInstance -ClassName Win32_DeviceGuard "
                  "-Namespace root\\Microsoft\\Windows\\DeviceGuard)."
                  "VirtualizationBasedSecurityStatus } catch { '' }")
    info.append(("VBS", {"2": "Running", "1": "Enabled, reboot pending",
                         "0": "Not running"}.get(vbs, "Unknown")))

    ram = _ps_val("[math]::Round((Get-CimInstance Win32_ComputerSystem)."
                  "TotalPhysicalMemory/1GB,1)")
    speed = _ps_val("(Get-CimInstance Win32_PhysicalMemory "
                    "| Select-Object -First 1).ConfiguredClockSpeed")
    info.append(("Memory", f"{ram} GB"
                 + (f" @ {speed} MT/s" if speed else "") if ram else "Unknown"))

    xmp = _ps_val("$a=(Get-CimInstance Win32_PhysicalMemory "
                  "| Select-Object -First 1); "
                  "if ($a.ConfiguredClockSpeed -gt $a.Speed) {'Likely on'} "
                  "elseif ($a.ConfiguredClockSpeed -eq $a.Speed) "
                  "{'At JEDEC / rated speed'} else {'Unknown'}")
    info.append(("XMP / EXPO", xmp or "Unknown"))

    return info


VENDOR_WMI = {
    "dell":   ("root\\dcim\\sysman", "Dell BIOS WMI"),
    "hp":     ("root\\hp\\instrumentedbios", "HP BIOS WMI"),
    "hewlett": ("root\\hp\\instrumentedbios", "HP BIOS WMI"),
    "lenovo": ("root\\wmi", "Lenovo_SetBiosSetting"),
}


def vendor_support():
    """Detect an officially supported WMI BIOS-settings interface."""
    mfr = (_ps_val("(Get-CimInstance Win32_ComputerSystem).Manufacturer")
           or "").lower()
    board_mfr = (_ps_val("(Get-CimInstance Win32_BaseBoard).Manufacturer")
                 or "").lower()
    both = mfr + " " + board_mfr

    for key, (namespace, label) in VENDOR_WMI.items():
        if key in both:
            found = _ps_val(
                f"try {{ if (Get-CimClass -Namespace '{namespace}' "
                f"-ErrorAction Stop) {{'yes'}} }} catch {{ 'no' }}")
            if found == "yes":
                return True, label, namespace
            return False, label + " (not present on this machine)", namespace

    return False, None, None
