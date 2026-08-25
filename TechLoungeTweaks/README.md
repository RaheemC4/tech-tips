# Tech Lounge Tweaks

A Windows 11 tweaking utility built for The Tech Lounge. Toggle performance,
latency and privacy tweaks, test your connection for bufferbloat, clean up
junk files and check your GPU drivers — all from one window.

Every tweak reads the live system state, so the app shows you what is
**actually** set on your machine rather than assuming. Every toggle reverts.

![Overview](docs/home.png)

---

## Download

**[⬇ Download TechLoungeTweaks.exe](https://github.com/RaheemC4/tech-tips/raw/main/TechLoungeTweaks/TechLoungeTweaks.exe)** (18 MB)

It is a single file — no installer, no Python, nothing to set up. Just
double-click it. Newer builds are also posted on the
[Releases](../../releases) page.

### First run

Windows will show a blue **"Windows protected your PC"** box, because the app
is not code-signed (a signing certificate costs a few hundred pounds a year,
which is not worth it for a free tool).

> Click **More info** → **Run anyway**

Some antivirus software may also flag it. That is a false positive caused by
the way the app is packaged — a self-extracting Python bundle looks like
packed malware to heuristic scanners.

**It needs to run as administrator** and will prompt for that automatically,
because most of these settings live in `HKEY_LOCAL_MACHINE`.

### Requirements

| | |
|---|---|
| **Windows 11** | Works out of the box |
| **Windows 10** | May need the [WebView2 runtime](https://developer.microsoft.com/microsoft-edge/webview2/) (free, from Microsoft) |

---

## Before you start

**Make a restore point.** There is a button for it under *Tools → System
Restore*. It takes about ten seconds and means any change here is reversible
even if something goes wrong.

Two tweaks will break games with kernel-level anti-cheat. They are marked
with a yellow warning in the app, but to be explicit:

- **Disable Memory Integrity** — Valorant (Vanguard) and FACEIT will refuse
  to launch.
- **Disable CPU Mitigations** — weakens Spectre/Meltdown protection.

Everything else is safe to try and safe to undo.

---

## What's in it

### Tweaks

![Tweaks](docs/tweaks.png)

Around 50 tweaks across nine categories. Each one shows whether it is
currently applied, and the toggle works both ways.

| Category | What it covers |
|---|---|
| **Performance** | GameDVR, Game Mode, fullscreen optimizations, power throttling, Ultimate Performance plan, CPU priority |
| **Graphics** | Hardware GPU scheduling, variable refresh rate, windowed optimizations, mouse acceleration |
| **GPU** | NVIDIA and AMD driver-level tweaks — only the ones for your card are shown |
| **Networking** | Nagle's algorithm, network throttling, offloads, firewall popups |
| **Power** | Dynamic tick, timer coalescing, USB selective suspend and power management |
| **Advanced** | Memory compression, page combining, CPU mitigations |
| **System** | Shutdown speed, menu delay, startup delay, SysMain, telemetry service |
| **Privacy** | Telemetry, activity history, advertising ID, error reporting, typing/speech/ink collection |
| **Explorer & UI** | Classic context menu, Bing in Start, snap layouts, lock screen, widgets, ads |

### Connection test

![Networking](docs/network.png)

A proper bufferbloat test — it measures your idle ping, then measures it
again while saturating the line in each direction. The gap between the two is
what makes games feel laggy when someone else is streaming.

Reports download and upload speed, ping, **jitter**, and a plain-English
verdict on what your connection can handle. Hover any **?** for an
explanation of what the number means and what a good value looks like.

### System information

![System Info](docs/sysinfo.png)

CPU, motherboard, memory (including whether XMP looks active), graphics,
storage health and network adapters. Read once when the app opens, so
switching tabs is instant.

### Tools

- **Boot Optimizer** — detects your CPU and GPU, then applies startup and
  shutdown tuning that suits them. Preview shows exactly what would change
  before you commit. Secure Boot, TPM and VBS are never touched, so kernel
  anti-cheat keeps working. Every change is written to a rollback file.
- **Disk Cleanup** — temp files, Windows Update cache, delivery optimization,
  crash dumps, thumbnails. Shows size per item, you pick what goes.
- **Drivers** — checks your installed NVIDIA driver against the latest
  release from NVIDIA's own lookup service.
- **Resources** — SFC, DISM and a read-only disk check, each with a clear
  verdict on whether anything was actually wrong.
- **BIOS Info** — firmware version, boot mode, Secure Boot, TPM,
  virtualization and memory speed.

---

## A note on BIOS tweaks

The BIOS page is **read-only by design**.

Dell, HP and Lenovo publish supported WMI interfaces for changing firmware
settings from Windows, and the app will use them where it finds one.
Consumer boards (ASUS, MSI, Gigabyte, ASRock) publish nothing equivalent —
the only route in is writing firmware NVRAM through an undocumented driver,
and a bad write bricks the board with no way back.

Change those settings in the firmware itself at POST.

---

## Undoing things

- Any individual tweak — toggle it off.
- A whole category — **Revert All** at the top of the page.
- Boot Optimizer — the **Undo** button restores from its rollback file.
- Everything, including things this app never touched — Windows System
  Restore, using the point you made before you started.

---

## Credits

Built for [The Tech Lounge](https://discord.gg/) Discord community.
Tweaks are drawn from the server's tech-tips archive plus documented Windows
settings.

Use at your own risk — read what a tweak does before applying it.
