"""System information via CIM/WMI, grouped the way people expect to read it."""

import json

from tweaks_engine import ps


def _q(cmd):
    """Run a PowerShell expression and return parsed JSON (list of dicts)."""
    rc, out = ps(cmd + " | ConvertTo-Json -Depth 3 -Compress")
    out = (out or "").strip()
    if rc != 0 or not out or out.startswith("SUBPROCESS_ERROR"):
        return []
    try:
        data = json.loads(out)
    except Exception:
        return []
    if isinstance(data, dict):
        return [data]
    return data if isinstance(data, list) else []


def _gb(v, digits=1):
    try:
        return f"{float(v) / (1024 ** 3):.{digits}f} GB"
    except Exception:
        return "N/A"


def _s(v):
    if v is None or v == "":
        return "N/A"
    return str(v).strip()


def cpu():
    rows = _q("Get-CimInstance Win32_Processor | Select-Object Name,"
              "NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,"
              "L2CacheSize,L3CacheSize,SocketDesignation")
    out = []
    for r in rows:
        out.append([
            ("Name", _s(r.get("Name"))),
            ("Cores", _s(r.get("NumberOfCores"))),
            ("Logical processors", _s(r.get("NumberOfLogicalProcessors"))),
            ("Max clock speed", f"{_s(r.get('MaxClockSpeed'))} MHz"),
            ("L3 cache", f"{int(r.get('L3CacheSize') or 0) // 1024} MB"
             if r.get("L3CacheSize") else "N/A"),
            ("Socket", _s(r.get("SocketDesignation"))),
        ])
    return out


def mainboard():
    bb = _q("Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,"
            "Product,SerialNumber")
    bios = _q("Get-CimInstance Win32_BIOS | Select-Object SMBIOSBIOSVersion,"
              "Manufacturer,ReleaseDate")
    b = bb[0] if bb else {}
    v = bios[0] if bios else {}
    date = _s(v.get("ReleaseDate"))
    if date and len(date) >= 8 and date[:8].isdigit():
        date = f"{date[6:8]}/{date[4:6]}/{date[0:4]}"
    return [[
        ("Manufacturer", _s(b.get("Manufacturer"))),
        ("Product", _s(b.get("Product"))),
        ("BIOS vendor", _s(v.get("Manufacturer"))),
        ("BIOS version", _s(v.get("SMBIOSBIOSVersion"))),
        ("BIOS date", date),
    ]]


def memory():
    total = _q("Get-CimInstance Win32_ComputerSystem "
               "| Select-Object TotalPhysicalMemory")
    sticks = _q("Get-CimInstance Win32_PhysicalMemory | Select-Object "
                "BankLabel,DeviceLocator,Capacity,Speed,ConfiguredClockSpeed,"
                "Manufacturer,PartNumber")
    out = []
    if total:
        out.append([("Total capacity",
                     _gb(total[0].get("TotalPhysicalMemory"), 0)),
                    ("Modules", str(len(sticks)))])
    for s in sticks:
        out.append([
            ("Slot", _s(s.get("DeviceLocator") or s.get("BankLabel"))),
            ("Capacity", _gb(s.get("Capacity"), 0)),
            ("Rated speed", f"{_s(s.get('Speed'))} MT/s"),
            ("Running at", f"{_s(s.get('ConfiguredClockSpeed'))} MT/s"),
            ("Manufacturer", _s(s.get("Manufacturer"))),
            ("Part number", _s(s.get("PartNumber"))),
        ])
    return out


def graphics():
    rows = _q("Get-CimInstance Win32_VideoController | Select-Object Name,"
              "DriverVersion,DriverDate,AdapterRAM,VideoProcessor,"
              "CurrentHorizontalResolution,CurrentVerticalResolution,"
              "CurrentRefreshRate")
    out = []
    for r in rows:
        res = "N/A"
        if r.get("CurrentHorizontalResolution"):
            res = (f"{r['CurrentHorizontalResolution']}"
                   f" x {r['CurrentVerticalResolution']}"
                   f" @ {_s(r.get('CurrentRefreshRate'))} Hz")
        vram = r.get("AdapterRAM")
        out.append([
            ("Name", _s(r.get("Name"))),
            ("Driver version", _s(r.get("DriverVersion"))),
            ("VRAM (reported)", _gb(vram, 0) if vram else "N/A"),
            ("Processor", _s(r.get("VideoProcessor"))),
            ("Current mode", res),
        ])
    return out


def storage():
    disks = _q("Get-CimInstance Win32_DiskDrive | Select-Object Model,Size,"
               "InterfaceType,MediaType,Partitions,SerialNumber")
    phys = _q("Get-PhysicalDisk | Select-Object FriendlyName,MediaType,"
              "BusType,HealthStatus")
    kind = {}
    for p in phys:
        kind[_s(p.get("FriendlyName"))] = (
            _s(p.get("MediaType")), _s(p.get("BusType")),
            _s(p.get("HealthStatus")))
    out = []
    for d in disks:
        model = _s(d.get("Model"))
        mt, bus, health = kind.get(model, ("N/A", "N/A", "N/A"))
        out.append([
            ("Model", model),
            ("Size", _gb(d.get("Size"), 0)),
            ("Type", mt if mt != "N/A" else _s(d.get("MediaType"))),
            ("Bus", bus if bus != "N/A" else _s(d.get("InterfaceType"))),
            ("Health", health),
            ("Partitions", _s(d.get("Partitions"))),
        ])
    vols = _q("Get-Volume | Where-Object DriveLetter | Select-Object "
              "DriveLetter,FileSystemLabel,FileSystem,Size,SizeRemaining")
    for v in vols:
        out.append([
            ("Volume", f"{_s(v.get('DriveLetter'))}:  "
                       f"{_s(v.get('FileSystemLabel')) or ''}".strip()),
            ("File system", _s(v.get("FileSystem"))),
            ("Capacity", _gb(v.get("Size"))),
            ("Free", _gb(v.get("SizeRemaining"))),
        ])
    return out


def network():
    rows = _q("Get-NetAdapter | Where-Object Status -eq 'Up' "
              "| Select-Object Name,InterfaceDescription,MacAddress,"
              "LinkSpeed,MediaType,DriverVersion")
    out = []
    for r in rows:
        out.append([
            ("Name", _s(r.get("Name"))),
            ("Adapter", _s(r.get("InterfaceDescription"))),
            ("MAC address", _s(r.get("MacAddress"))),
            ("Link speed", _s(r.get("LinkSpeed"))),
            ("Driver", _s(r.get("DriverVersion"))),
        ])
    return out


def windows():
    rows = _q("Get-CimInstance Win32_OperatingSystem | Select-Object Caption,"
              "Version,BuildNumber,OSArchitecture,InstallDate,LastBootUpTime")
    r = rows[0] if rows else {}
    return [[
        ("Edition", _s(r.get("Caption"))),
        ("Version", _s(r.get("Version"))),
        ("Build", _s(r.get("BuildNumber"))),
        ("Architecture", _s(r.get("OSArchitecture"))),
    ]]


SECTIONS = [
    ("CPU", "▣", cpu),
    ("Mainboard", "▦", mainboard),
    ("Memory", "▤", memory),
    ("Graphics", "◧", graphics),
    ("Storage", "◫", storage),
    ("Network", "⊕", network),
    ("Windows", "■", windows),
]
