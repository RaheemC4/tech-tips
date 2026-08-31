"""One-click app installs.

Two routes, in order of preference:

1. winget (Windows Package Manager). It ships with Windows 11, the package IDs
   are stable, and Microsoft keeps the download URLs and silent switches
   current. Nothing here can rot.
2. A direct download from the vendor, for machines where winget was stripped -
   Ghost Spectre and similar debloated images usually remove App Installer.

Every direct URL is checked against an allowlist of vendor hosts before
anything is fetched, the same rule the driver downloader uses: if a URL is not
on the vendor's own domain, the app refuses to touch it.

Every entry also carries a `page` so there is always a manual route when an
install fails.
"""

import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request

CREATE_NO_WINDOW = 0x08000000
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Hosts a direct installer download may come from. Anything else is refused.
ALLOWED_HOSTS = (
    "microsoft.com", "download.microsoft.com", "go.microsoft.com",
    "aka.ms", "download.visualstudio.microsoft.com",
    "google.com", "dl.google.com",
    "mozilla.org", "download.mozilla.org",
    "brave.com", "laptop-updates.brave.com", "referrals.brave.com",
    "opera.com", "net.geo.opera.com", "download.opera.com",
    "vivaldi.com", "downloads.vivaldi.com",
    "steampowered.com", "cdn.cloudflare.steamstatic.com",
    "epicgames.com", "launcher-public-service-prod06.ol.epicgames.com",
    "epicgames-download1.akamaized.net",
    "ubi.com", "static3.cdn.ubi.com", "ubisoft.com",
    "ea.com", "origin-a.akamaihd.net",
    "gog.com", "content-system.gog.com",
    "battle.net", "downloader.battle.net", "blizzard.com",
    "rockstargames.com", "gamedownloads.rockstargames.com",
    "amazongames.com", "download.amazongames.com",
    "github.com", "objects.githubusercontent.com",
)


def host_allowed(url):
    try:
        host = (urllib.parse.urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


# --------------------------------------------------------------- catalogue
#
# To add your own entry, copy one of these dicts. Fields:
#   id      unique short key
#   name    what the page shows
#   group   which section it appears under
#   desc    one line under the name
#   winget  winget package id (preferred route), or None
#   url     direct installer URL (fallback), or None
#   silent  argument list for a silent install of that direct download
#   page    vendor page, opened when everything else fails
#   note    optional warning shown on the card
#
APPS = [
    # ------------------------------------------------------------ runtimes
    dict(id="vcredist", name="Visual C++ Redistributables (all)",
         group="Runtimes",
         desc="Every VC++ runtime from 2005 to 2022, x86 and x64. Fixes most "
              "'missing MSVCP140.dll' style errors.",
         winget=None,
         url="https://github.com/abbodi1406/vcredist/releases/latest/download/"
             "VisualCppRedist_AIO_x86_x64.exe",
         silent=["/y"],
         page="https://github.com/abbodi1406/vcredist/releases"),
    dict(id="directx", name="DirectX Runtime (web installer)",
         group="Runtimes",
         desc="The legacy DirectX 9/10/11 runtime components many older games "
              "still need. Does not touch DirectX 12.",
         winget=None,
         url="https://download.microsoft.com/download/1/7/1/"
             "1718CCC4-6315-4D8E-9543-8E28A4E18C4C/dxwebsetup.exe",
         silent=["/Q"],
         page="https://www.microsoft.com/download/details.aspx?id=35"),
    dict(id="dotnet8", name=".NET Desktop Runtime 8",
         group="Runtimes",
         desc="Runtime for modern .NET desktop apps.",
         winget="Microsoft.DotNet.DesktopRuntime.8",
         url="https://aka.ms/dotnet/8.0/windowsdesktop-runtime-win-x64.exe",
         silent=["/install", "/quiet", "/norestart"],
         page="https://dotnet.microsoft.com/download/dotnet/8.0"),

    # ------------------------------------------------------------ browsers
    dict(id="webview2", name="Microsoft Edge WebView2",
         group="Browsers",
         desc="The runtime this app itself needs, and plenty of others. "
              "Install this first on a stripped Windows.",
         winget="Microsoft.EdgeWebView2Runtime",
         url="https://go.microsoft.com/fwlink/p/?LinkId=2124703",
         silent=["/silent", "/install"],
         page="https://developer.microsoft.com/microsoft-edge/webview2/"),
    dict(id="edge", name="Microsoft Edge",
         group="Browsers",
         desc="Edge stable. Brings WebView2 with it.",
         winget="Microsoft.Edge",
         url="https://go.microsoft.com/fwlink/?linkid=2108834",
         silent=["/silent", "/install"],
         page="https://www.microsoft.com/edge"),
    dict(id="brave", name="Brave",
         group="Browsers",
         desc="Chromium based, ad and tracker blocking built in.",
         winget="Brave.Brave",
         url="https://laptop-updates.brave.com/latest/winx64",
         silent=["/silent", "/install"],
         page="https://brave.com/download/"),
    dict(id="chrome", name="Google Chrome",
         group="Browsers",
         desc="Chrome stable, 64-bit.",
         winget="Google.Chrome",
         url="https://dl.google.com/chrome/install/latest/chrome_installer.exe",
         silent=["/silent", "/install"],
         page="https://www.google.com/chrome/"),
    dict(id="firefox", name="Mozilla Firefox",
         group="Browsers",
         desc="Firefox stable, 64-bit.",
         winget="Mozilla.Firefox",
         url="https://download.mozilla.org/?product=firefox-latest-ssl"
             "&os=win64&lang=en-GB",
         silent=["/S"],
         page="https://www.mozilla.org/firefox/new/"),
    dict(id="operagx", name="Opera GX",
         group="Browsers",
         desc="The gaming-flavoured Opera build, with CPU and RAM limiters.",
         winget="Opera.OperaGX",
         url="https://net.geo.opera.com/opera_gx/stable/windows",
         silent=["/silent"],
         page="https://www.opera.com/gx"),
    dict(id="vivaldi", name="Vivaldi",
         group="Browsers",
         desc="Chromium based, heavily customisable.",
         winget="Vivaldi.Vivaldi",
         url="https://downloads.vivaldi.com/stable/Vivaldi.latest.exe",
         silent=["--vivaldi-silent"],
         page="https://vivaldi.com/download/"),

    # -------------------------------------------------------- game clients
    dict(id="steam", name="Steam", group="Game clients",
         desc="Valve's client.",
         winget="Valve.Steam",
         url="https://cdn.cloudflare.steamstatic.com/client/installer/"
             "SteamSetup.exe",
         silent=["/S"],
         page="https://store.steampowered.com/about/"),
    dict(id="epic", name="Epic Games Launcher", group="Game clients",
         desc="Epic's client, and the free weekly games.",
         winget="EpicGames.EpicGamesLauncher",
         url=None, silent=None,
         page="https://store.epicgames.com/download"),
    dict(id="ubisoft", name="Ubisoft Connect", group="Game clients",
         desc="Ubisoft's client.",
         winget="Ubisoft.Connect",
         url="https://static3.cdn.ubi.com/orbit/launcher_installer/"
             "UbisoftConnectInstaller.exe",
         silent=["/S"],
         page="https://www.ubisoft.com/ubisoft-connect"),
    dict(id="eaapp", name="EA App", group="Game clients",
         desc="Replaces Origin.",
         winget="ElectronicArts.EADesktop",
         url=None, silent=None,
         page="https://www.ea.com/ea-app"),
    dict(id="gog", name="GOG Galaxy 2.0", group="Game clients",
         desc="GOG's client, DRM free.",
         winget="GOG.Galaxy",
         url=None, silent=None,
         page="https://www.gog.com/galaxy"),
    dict(id="battlenet", name="Battle.net", group="Game clients",
         desc="Blizzard's client.",
         winget="Blizzard.BattleNet",
         url=None, silent=None,
         page="https://download.battle.net/"),
    dict(id="rockstar", name="Rockstar Games Launcher", group="Game clients",
         desc="Rockstar's client.",
         winget="RockstarGames.RockstarGamesLauncher",
         url="https://gamedownloads.rockstargames.com/public/installer/"
             "Rockstar-Games-Launcher.exe",
         silent=["/S"],
         page="https://socialclub.rockstargames.com/rockstar-games-launcher"),
    dict(id="amazon", name="Amazon Games", group="Game clients",
         desc="Amazon's client, and the Prime Gaming freebies.",
         winget="Amazon.Games",
         url="https://download.amazongames.com/AmazonGamesSetup.exe",
         silent=["-q"],
         page="https://gaming.amazon.com/"),
]

GROUP_ORDER = ["Runtimes", "Browsers", "Game clients"]


def catalog():
    """The catalogue, plus whether each entry can actually be installed."""
    have_winget = winget_path() is not None
    out = []
    for a in APPS:
        direct_ok = bool(a["url"]) and host_allowed(a["url"])
        out.append({
            "id": a["id"], "name": a["name"], "group": a["group"],
            "desc": a["desc"], "page": a["page"], "note": a.get("note"),
            "winget": bool(a["winget"]),
            "direct": direct_ok,
            # No winget and no safe direct URL means we can only open the page.
            "installable": (bool(a["winget"]) and have_winget) or direct_ok,
            "route": ("winget" if (a["winget"] and have_winget)
                      else ("direct" if direct_ok else "page")),
        })
    return {"apps": out, "groups": list(GROUP_ORDER),
            "winget": have_winget}


def by_id(app_id):
    for a in APPS:
        if a["id"] == app_id:
            return a
    return None


# ------------------------------------------------------------------ winget
def winget_path():
    """Full path to winget.exe, or None. Not on PATH inside a packed app, so
    look where App Installer actually puts it."""
    found = shutil.which("winget")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA", "")
    base = os.path.join(local, "Microsoft", "WindowsApps")
    cand = os.path.join(base, "winget.exe")
    if os.path.exists(cand):
        return cand
    # Installed for all users by App Installer.
    for root in (os.environ.get("ProgramFiles", r"C:\Program Files"),):
        pkgs = os.path.join(root, "WindowsApps")
        try:
            for name in os.listdir(pkgs):
                if name.startswith("Microsoft.DesktopAppInstaller_"):
                    cand = os.path.join(pkgs, name, "winget.exe")
                    if os.path.exists(cand):
                        return cand
        except Exception:
            pass
    return None


def install_via_winget(app, on_line=None, should_cancel=None):
    """Returns (ok, message). Streams winget's output through on_line."""
    exe = winget_path()
    if not exe:
        return False, "winget is not available on this PC."
    cmd = [exe, "install", "--id", app["winget"], "--exact", "--silent",
           "--accept-package-agreements", "--accept-source-agreements",
           "--disable-interactivity"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL,
                                creationflags=CREATE_NO_WINDOW)
    except Exception as e:
        return False, f"Could not start winget: {e}"

    tail = []
    buf = b""
    while True:
        if should_cancel and should_cancel():
            try:
                proc.terminate()
            except Exception:
                pass
            return False, "Cancelled."
        chunk = proc.stdout.read1(4096)
        if not chunk:
            break
        buf += chunk
        parts = re.split(rb"[\r\n]+", buf)
        buf = parts.pop()
        for p in parts:
            line = p.decode("utf-8", "replace").strip()
            # winget draws a spinner and a progress bar out of box characters.
            line = re.sub(r"[\u2500-\u259f\u25a0-\u25ff\\|/\-]{3,}", "", line)
            line = line.strip()
            if line:
                tail.append(line)
                if on_line:
                    on_line(line[:160])
    proc.wait()
    rc = proc.returncode
    blob = " ".join(tail[-25:]).lower()

    if rc == 0:
        return True, "Installed."
    # winget uses these for "nothing to do", which is a success for our purpose.
    if "already installed" in blob or rc in (0x8A150061, -1978335135):
        return True, "Already installed and up to date."
    if "no applicable" in blob or "no package found" in blob:
        return False, ("winget has no package for this on your machine. "
                       "Use the vendor page button instead.")
    msg = tail[-1] if tail else f"winget exited with code {rc}."
    return False, msg


# ----------------------------------------------------------- direct install
def download(url, dest_dir, on_progress=None, should_cancel=None):
    """Fetch an installer to dest_dir. Returns the path."""
    if not host_allowed(url):
        raise ValueError("Refusing to download - not a recognised vendor host.")
    os.makedirs(dest_dir, exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        # Take the real filename after redirects where the server gives one.
        name = ""
        disp = resp.headers.get("Content-Disposition") or ""
        m = re.search(r'filename="?([^";]+)"?', disp)
        if m:
            name = m.group(1).strip()
        if not name:
            name = os.path.basename(
                urllib.parse.urlparse(resp.geturl()).path) or ""
        if not name or "." not in name:
            name = "installer.exe"
        dest = os.path.join(dest_dir, name)

        total = int(resp.headers.get("Content-Length") or 0)
        got = 0
        with open(dest, "wb") as fh:
            while True:
                if should_cancel and should_cancel():
                    fh.close()
                    try:
                        os.remove(dest)
                    except Exception:
                        pass
                    raise InterruptedError("Cancelled.")
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                fh.write(chunk)
                got += len(chunk)
                if on_progress and total:
                    on_progress(got / total)
    return dest


def install_direct(app, dest_dir, on_progress=None, on_line=None,
                   should_cancel=None):
    """Download from the vendor and run the silent install. (ok, message)."""
    if not app.get("url"):
        return False, "No direct download for this one - use the vendor page."
    if on_line:
        on_line("Downloading from the vendor…")
    try:
        path = download(app["url"], dest_dir, on_progress, should_cancel)
    except InterruptedError:
        return False, "Cancelled."
    except Exception as e:
        return False, f"Download failed: {e}"

    if on_line:
        on_line("Installing…")
    args = [path] + list(app.get("silent") or [])
    if path.lower().endswith(".msi"):
        args = ["msiexec.exe", "/i", path, "/qn", "/norestart"]
    try:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL,
                                creationflags=CREATE_NO_WINDOW)
        proc.wait(timeout=1800)
        rc = proc.returncode
    except Exception as e:
        return False, f"Installer would not run: {e}"

    # 3010 = success, reboot required. 1638 = a newer version is present.
    if rc in (0, 3010):
        return True, ("Installed." if rc == 0
                      else "Installed - a reboot will finish it off.")
    if rc == 1638:
        return True, "A newer version is already installed."
    return False, f"The installer exited with code {rc}."


def install(app_id, dest_dir, on_progress=None, on_line=None,
            should_cancel=None):
    """Install one app by its catalogue id. Returns (ok, message)."""
    app = by_id(app_id)
    if not app:
        return False, "Unknown app."
    # winget first: it keeps its own URLs current and handles silent switches.
    if app.get("winget") and winget_path():
        ok, msg = install_via_winget(app, on_line, should_cancel)
        if ok:
            return True, msg
        if should_cancel and should_cancel():
            return False, "Cancelled."
        if not app.get("url"):
            return False, msg
        if on_line:
            on_line("winget could not do it - trying the vendor download…")
    return install_direct(app, dest_dir, on_progress, on_line, should_cancel)
