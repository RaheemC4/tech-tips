"""GPU driver detection and update checking.

NVIDIA exposes a public lookup endpoint (the same one their download page
uses). AMD publishes no equivalent, so for Radeon we report the installed
version and link to the official page.
"""

import json
import os
import re
import urllib.parse
import urllib.request

from tweaks_engine import ps

NV_API = ("https://gfwsl.geforce.com/services_toolkit/services/com/nvidia/"
          "services/AjaxDriverService.php")
NV_PAGE = "https://www.nvidia.com/Download/index.aspx"
AMD_PAGE = "https://www.amd.com/en/support/download/drivers.html"
INTEL_PAGE = "https://www.intel.com/content/www/us/en/download-center/home.html"


def vendor_page(vendor):
    return {"NVIDIA": NV_PAGE, "AMD": AMD_PAGE,
            "Intel": INTEL_PAGE}.get(vendor, NV_PAGE)

UA = {"User-Agent": "Mozilla/5.0 TechLoungeTweaks/1.0"}

# psid = product series, pfid = product family. osID 135 = Windows 11 64-bit.
NV_SERIES = [
    (r"RTX\s*50\d\d", 131, 1092),
    (r"RTX\s*40\d\d", 127, 979),
    (r"RTX\s*30\d\d", 120, 929),
    (r"RTX\s*20\d\d", 107, 858),
    (r"GTX\s*16\d\d", 108, 862),
    (r"GTX\s*10\d\d", 101, 815),
]


def detect_gpus():
    """[(name, driver_version, vendor)] for real display adapters."""
    rc, out = ps("Get-CimInstance Win32_VideoController | Select-Object "
                 "Name,DriverVersion | ConvertTo-Json -Compress")
    try:
        data = json.loads((out or "").strip())
    except Exception:
        return []
    if isinstance(data, dict):
        data = [data]
    gpus = []
    for g in data:
        name = (g.get("Name") or "").strip()
        if not name or re.search(r"(?i)basic display|remote|virtual|meta",
                                 name):
            continue
        ver = (g.get("DriverVersion") or "").strip()
        vendor = "Other"
        if re.search(r"(?i)nvidia|geforce|quadro|rtx|gtx", name):
            vendor = "NVIDIA"
        elif re.search(r"(?i)\bamd\b|radeon|\brx\s?\d", name):
            vendor = "AMD"
        elif re.search(r"(?i)intel", name):
            vendor = "Intel"
        gpus.append((name, ver, vendor))
    return gpus


def nvidia_marketing_version(driver_version):
    """32.0.15.6094 -> 560.94 (NVIDIA's own numbering)."""
    digits = re.sub(r"\D", "", driver_version or "")
    if len(digits) < 5:
        return driver_version or "Unknown"
    tail = digits[-5:]
    return f"{tail[:3]}.{tail[3:]}"


def _series_ids(name):
    for pattern, psid, pfid in NV_SERIES:
        if re.search(pattern, name, re.I):
            return psid, pfid
    return NV_SERIES[0][1], NV_SERIES[0][2]


def version_tuple(v):
    """'616.56' -> (616, 56). Used for real ordering, never string equality."""
    parts = re.findall(r"\d+", str(v or ""))
    return tuple(int(p) for p in parts) if parts else ()


def compare_versions(installed, latest):
    """-1 installed older, 0 same, 1 installed newer. None if uncomparable."""
    a, b = version_tuple(installed), version_tuple(latest)
    if not a or not b:
        return None
    n = max(len(a), len(b))
    a += (0,) * (n - len(a))
    b += (0,) * (n - len(b))
    return (a > b) - (a < b)


def nvidia_latest(gpu_name):
    """Newest Game Ready driver as (version, url), or None.

    Asks for several results and picks the highest version rather than
    trusting the API's ordering - requesting a single result was handing
    back an older driver than the one already installed.
    """
    psid, pfid = _series_ids(gpu_name)
    params = {
        "func": "DriverManualLookup", "psid": psid, "pfid": pfid,
        "osID": 135, "languageCode": 1033, "isWHQL": 1, "beta": "null",
        "dltype": -1, "dch": 1, "upCRD": 0, "qnf": 0, "ctk": "null",
        "sort1": 0, "numberOfResults": 10,
    }
    url = NV_API + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return None

    best = None
    for entry in (data.get("IDS") or []):
        info = entry.get("downloadInfo") or {}
        ver = str(info.get("Version") or "").strip()
        dl = str(info.get("DownloadURL") or "").strip()
        if not ver or not dl:
            continue
        if best is None or version_tuple(ver) > version_tuple(best[0]):
            best = (ver, dl)
    return best


def is_official(url, vendor):
    """Only ever hand back a download that really is on the vendor's host."""
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except Exception:
        return False
    host = host.lower()
    allowed = {
        "NVIDIA": ("nvidia.com", "nvidia.cn", "geforce.com"),
        "AMD": ("amd.com", "ati.com"),
    }.get(vendor, ())
    return url.lower().startswith("https://") and any(
        host == d or host.endswith("." + d) for d in allowed)


def download(url, vendor, progress=None):
    """Download an installer into Downloads. Returns the path, or raises."""
    if not is_official(url, vendor):
        raise ValueError("Refusing to download - not a %s URL" % vendor)

    dest_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(dest_dir, exist_ok=True)
    name = os.path.basename(urllib.parse.urlparse(url).path) or "driver.exe"
    dest = os.path.join(dest_dir, name)

    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        got = 0
        with open(dest, "wb") as fh:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                fh.write(chunk)
                got += len(chunk)
                if progress and total:
                    progress(got / total)
    return dest


def reveal(path):
    """Open Explorer with the file selected."""
    try:
        os.startfile(os.path.dirname(path))
    except Exception:
        pass
