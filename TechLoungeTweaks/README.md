# Tech Lounge Tweaks

A Windows 11 tweaking utility built for The Tech Lounge. Toggle performance,
latency and privacy tweaks, apply a tuned NVIDIA driver profile in one tap,
turn Defender on or off, install runtimes, browsers and game clients silently,
test your connection for bufferbloat, clean up junk files and check your GPU
drivers — all from one window.

Every page reads the **live** system state, so the app shows what is actually
set on your machine rather than assuming. Every toggle reverts, and one button
on the dashboard does the lot.

![Overview](docs/home.png)

---

## Download

**[⬇ Download TechLoungeTweaks.zip](https://github.com/RaheemC4/tech-tips/raw/main/TechLoungeTweaks/TechLoungeTweaks.zip)** (15 MB)

1. Download the zip
2. **Extract it** somewhere you keep programs — `C:\Tools\` is a good spot.
   Do not run it from inside the zip, and avoid leaving it in Downloads
   (Windows cleans that folder out and scans it hard)
3. Open the extracted folder and run **TechLoungeTweaks.exe**

Keep the whole folder together. What you will see inside it:

```
TechLoungeTweaks\
├─ TechLoungeTweaks.exe     ← run this
├─ TL-api.log               ← plain-text log, for troubleshooting
├─ _internal\               ← the app itself, leave it alone
└─ resources\               ← NVIDIA Profile Inspector + the .nip profile
```

Only the exe and the log sit at the top level, so there is nothing to click on
by mistake. Moving the exe out on its own will not work.

### Why a folder and not one .exe

An earlier version was a single self-extracting exe. It unpacked ~46 MB to
your temp folder on *every* launch, which made startup slow and unpredictable,
and the self-extracting behaviour is exactly what antivirus heuristics look
for — Defender was flagging it as a false positive. The folder build starts
almost instantly and does not trip those scanners.

### First run

Windows will show a blue **"Windows protected your PC"** box, because the app
is not code-signed (a signing certificate costs a few hundred pounds a year,
which is not worth it for a free tool).

> Click **More info** → **Run anyway**

If your browser blocks the download itself with **"Virus detected"**, that is
the same false positive — use *Downloads → Keep* in the browser, or extract
with 7-Zip, which avoids Windows tagging the extracted files as
web-downloaded.

#### "Smart App Control blocked an app that may be unsafe"

This is a **different** dialog — it only has **Okay** and **Get apps from the
Store**, with no way to run the app anyway. That is Smart App Control, not
SmartScreen, and it blocks every unsigned program with no per-app override.

Only clean Windows 11 installs have it switched on. To check:

> Windows Security → App & browser control → Smart App Control

If it says **On**, the only ways round it are to turn it off or not run the app.

⚠️ **Turning Smart App Control off is permanent.** Microsoft does not allow it
to be switched back on afterwards — the only way to re-enable it is a clean
reinstall of Windows. Do not turn it off casually, and never on someone else's
machine without telling them that first.

If it says **Evaluation** or **Off**, this dialog is not what is stopping you —
see the SmartScreen steps above.

**It needs to run as administrator** and will prompt for that automatically,
because most of these settings live in `HKEY_LOCAL_MACHINE`.

### Requirements

| | |
|---|---|
| **Windows 11** | Works out of the box |
| **Windows 10** | Needs the [WebView2 runtime](https://developer.microsoft.com/microsoft-edge/webview2/) (free, from Microsoft) — the app checks on launch and links you to it if it is missing |
| **NVIDIA GPU** | Only needed for the NVIDIA Profile page; everything else works on any machine |
| **App Installer / winget** | Optional. Install Apps prefers it, and falls back to direct vendor downloads when a debloated image has removed it |

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

### One-click setup

Four buttons on the dashboard, for when you do not want to work through nine
categories by hand:

| Button | What it does |
|---|---|
| **Apply Recommended** | Every safe tweak, plus the NVIDIA profile and Defender off. Skips the four that cause trouble: Memory Integrity and CPU Mitigations (kernel anti-cheat / security), GameDVR and Fullscreen Optimizations (Xbox app, Game Bar overlay and some controllers). |
| **Apply All** | Everything, including the risky ones, plus the NVIDIA profile and Defender off. |
| **Revert All** | Puts every tweak back to exactly how this PC was the moment you first opened the app. |
| **Windows Defaults** | Turns every tweak off, restores NVIDIA settings and turns Defender back on — Windows as it ships. |

Both apply buttons check for an NVIDIA GPU first and quietly skip the driver
profile if there isn't one. Every switch flips the moment you click, with the
registry write happening behind it, so nothing ever looks frozen mid-apply.

### NVIDIA Profile

![NVIDIA Profile](docs/nvidia.png)

One toggle applies a tuned set of global NVIDIA driver settings — the same
profile for everyone, so there is no "what did you set yours to" in chat.

**NVIDIA Profile Inspector (Revamped) ships inside the zip**, in the
`resources` folder. Nothing to download.

The table lists every setting the profile touches: what your driver holds
**right now** on the left, what it becomes on the right, with the changed ones
struck through. Highlights include Power Management on *Prefer maximum
performance*, Low Latency Mode *Ultra*, Preferred Refresh Rate *Highest
available*, and G-SYNC on for fullscreen **and** windowed.

**How reverting works.** The first time you open the app on a PC with an
NVIDIA card, it quietly exports that PC's current NVIDIA settings once and
keeps the file in `%LOCALAPPDATA%\TechLoungeTweaks`. Turning the profile off
restores *your* original settings, not a generic default. That backup is taken
once per machine, is never overwritten, and is never shared.

**It re-checks itself every launch.** The app reads your live driver settings
in the background at startup rather than trusting its own record, so anything
you changed in the NVIDIA Control Panel, in Profile Inspector directly, or
that a driver reinstall reset shows up correctly. If only part of the profile
is live you get *"Partly applied — 7 of 39 settings match"* rather than a
toggle that quietly lies. The read is warmed on startup, so the page is
already filled in by the time you click the tab.

Only NVIDIA driver settings are touched — nothing else on the PC.

**On a machine without an NVIDIA card** the page seals itself and names the GPU
it actually found, so nobody applies a driver profile that cannot do anything.
Every other tab keeps working normally.

![No NVIDIA GPU](docs/nvidia-amd.png)

### Windows Defender

![Defender](docs/defender.png)

One toggle for the whole of Microsoft Defender, with the live state of each
component listed underneath.

**Tamper Protection.** Since Windows 10 1903, Windows blocks *every* app —
this one included — from switching real-time protection off while Tamper
Protection is on. There is no legitimate way around that, and anything
claiming otherwise is using a malware technique. So the toggle opens the exact
Windows Security page for you to flip that one switch yourself, then finishes
the rest. The same toggle turns everything back on.

**The antimalware service stays in memory.** With everything switched off you
will still see `MsMpEng.exe` running, and Windows still reports the service as
enabled. That is normal and not a failed toggle — Windows keeps the service
resident for as long as Defender is the installed antivirus, and nothing can
unload it. What matters is real-time protection, which is what the toggle
follows and what actually scans files. The page says as much underneath the
component list so it is not mistaken for something that did not work.

Turning Defender off leaves the PC with no antivirus until it goes back on.

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
storage health and network adapters. Read once in the background while the app
opens, so switching tabs is instant.

### Tools

- **Boot Optimizer** — detects your CPU and GPU, then applies startup and
  shutdown tuning that suits them. Preview shows exactly what would change
  before you commit. Secure Boot, TPM and VBS are never touched, so kernel
  anti-cheat keeps working. Every change is written to a rollback file.
- **Disk Cleanup** — temp files, Windows Update cache, delivery optimization,
  crash dumps, thumbnails. Shows size per item, you pick what goes.
- **Drivers** — checks your installed NVIDIA driver against the latest
  release from NVIDIA's own lookup service. Versions are compared as numbers,
  so a beta or hotfix that is *newer* than the public release is reported as
  ahead rather than as an update you are missing.
- **Resources** — SFC, DISM and a read-only disk check, each with a clear
  verdict on whether anything was actually wrong.
- **BIOS Info** — firmware version, boot mode, Secure Boot, TPM,
  virtualization and memory speed.
- **Install Apps** — runtimes, browsers and game clients, installed silently
  from the vendor. See below.
- **Virtual Machines** — switch the CPU between VirtualBox and Windows'
  hypervisor-backed security. See below.

### While something is running

![A scan in progress](docs/resources.png)

Scans and downloads take minutes, so the app tracks them properly rather than
freezing a button. While one is going, the **Run** / **Download** button is
replaced by **Cancel** and a progress bar showing the tool's own real
percentage, with its current output line and an elapsed timer underneath.

**Windows Image Repair legitimately takes 10–30 minutes** and will sit on one
percentage for long stretches — that is DISM working, not the app hanging. The
elapsed timer keeps ticking so you can tell the difference, and Cancel stops it
cleanly at any point.

The job lives in the app itself, not the page, so you can switch to another tab
and come back to find it still running at the right progress. It will not let
you start a second copy of something already going, and cancelling a download
removes the half-finished file.

### Virtual Machines

![Virtual Machines](docs/virt.png)

Two buttons, in plain English:

| | |
|---|---|
| **Virtual Machines** | Pick this to run VirtualBox, VMware or WSL properly. VMs run at full speed instead of crawling, and it fixes VirtualBox failing to start a machine. |
| **Gaming & Normal Use** | Pick this for everyday use and playing games. Memory Integrity stays off so installers and games stay fast. VMs still run, just slower. |

Whichever one is live is marked **ACTIVE NOW**, so there is never any doubt
which state the PC is in. **Apply Recommended** on the dashboard picks Gaming &
Normal Use automatically.

Why this is a choice at all: VirtualBox wants the CPU's virtualisation
directly, but Windows runs its own hypervisor for Memory Integrity, WSL2,
Docker and Sandbox. Whoever holds it, the other loses out.

**Memory Integrity is left off by both modes.** Turning it on taxes every
driver load — an earlier build enabled it and MSI installers slowed to a crawl
on a machine that had shipped with it off. Nothing here will ever switch it on
behind your back. The one exception worth knowing: **Valorant can ask for
Memory Integrity to be on**. If Vanguard complains, turn it on yourself in
*Windows Security → Device security → Core isolation*, and the app will leave
it alone.

**Neither button touches Secure Boot or TPM.** Those are firmware settings and
this app has no business changing them.

The hypervisor setting is recorded the first time you open the page, so
switching back restores *your* machine's value rather than a Windows default.

**Either choice needs a restart** — the hypervisor setting is applied at boot.

If CPU virtualisation is switched off in your BIOS the page says so in red, with
what to turn on (Intel VT-x, or SVM Mode on AMD). No software setting can work
around that one.

### Install Apps

![Install Apps](docs/apps.png)

Runtimes, browsers and game clients, installed silently — the useful half of a
toolbox like Ghost's, without the baggage.

| Group | What's in it |
|---|---|
| **Runtimes** | Visual C++ Redistributables (2005–2022, x86 + x64), DirectX web installer, .NET Desktop Runtime 8 |
| **Browsers** | Edge & WebView2, Brave, Chrome, Firefox, Opera GX, Vivaldi |
| **Game clients** | Steam, Epic, Ubisoft Connect, EA App, GOG Galaxy, Battle.net, Rockstar, Amazon Games |

Each card shows how it will be installed. **WINGET** goes through the Windows
Package Manager, which is built into Windows 11 and keeps its own download
URLs and silent switches current — nothing to rot. **DIRECT** downloads
straight from the vendor's own domain. **MANUAL** means neither route is
available and the vendor page is the way in.

Downloads are checked against an allowlist of vendor domains before anything
is fetched, so a link that is not on the vendor's own domain is refused.
Installers run with their official silent switches. Nothing is bundled with
this app, and nothing is repacked or modified.

If the Windows Package Manager has been stripped out — debloated images
usually remove it — the page says so and falls back to direct downloads.

**Microsoft Store & Xbox apps** sit at the top of the same page: one button
removes them, another restores them by re-registering the copy Windows keeps
on disk. On an image where they were stripped rather than uninstalled there is
nothing left to restore from, and the app tells you that plainly instead of
failing quietly.

---

## Themes

![Themes](docs/themes.png)

The palette button in the title bar switches the whole app between blue,
blurple, purple, red, green and cyan. Everything follows — the icon, the score
ring, buttons, selections and the background glow. Your choice is remembered
between launches.

![Purple theme](docs/theme-purple.png)

The window is fully resizable, and drags at your monitor's refresh rate.

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

- Everything at once — **Revert All** on the dashboard puts the machine back to
  how it was when you first opened the app, or **Windows Defaults** puts it back
  to stock Windows.
- Any individual tweak — toggle it off.
- A whole category — **Revert All** at the top of the page.
- NVIDIA profile — toggle it off; your own pre-profile settings come back.
- Defender — the same toggle turns it back on.
- Microsoft Store / Xbox apps — the Install / restore button on the Install
  Apps page, as long as the image still holds a copy to restore from.
- Boot Optimizer — the **Undo** button restores from its rollback file.
- Everything, including things this app never touched — Windows System
  Restore, using the point you made before you started.

---

## Something not working?

`TL-api.log` sits next to the exe and records what the app did, in plain text.
If something misbehaves, that file says why — send it over.

---

## Credits

Built for The Tech Lounge Discord community. Tweaks are drawn from the
server's tech-tips archive plus documented Windows settings.

Bundles [NVIDIA Profile Inspector Revamped](https://github.com/xHybred/NVIDIAProfileInspectorRevamped)
by xHybred for the NVIDIA Profile page.

The Install Apps page installs software from each vendor's own servers, or
through the Windows Package Manager. No third-party installer is bundled with
this app, and nothing is repacked, patched or modified. If an app is not on the
list it is because there is no legitimate automated source for it.

Use at your own risk — read what a tweak does before applying it.
