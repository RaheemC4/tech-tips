# Tech Lounge Tweaks

A Windows 11 tweaking utility built for The Tech Lounge. Toggle performance,
latency and privacy tweaks, apply a tuned NVIDIA driver profile in one tap,
turn Defender on or off, install runtimes, browsers and game clients silently,
test your connection for bufferbloat, clean up junk files and check your GPU
drivers â€” all from one window.

The redesigned interface keeps every sidebar tab, the tweak-score ring and six
accent themes, with an inset workspace, a clearer navigation hierarchy, hardware
tiles and grouped setup controls. Cards, buttons and secondary text share a calmer
frosted design with one continuous theme-tinted backdrop across the sidebar and
workspace, without a separate grey workspace panel. Cards remain subtly lifted
and the selected theme also tints menus and solid accessibility surfaces.
The blue theme uses the score ring's deeper blue rather than a
pale cyan wash across the sidebar.
The workspace uses a single blur layer, with solid surfaces when Windows requests
reduced transparency or increased contrast. No animated wallpaper or idle rendering
loop is added. Sidebar navigation, category cards and individual tweak switches
support keyboard activation and visible focus. Reduced-motion preferences stop
UI animation. Keyboard focus stays inside control edges, theme choices and main
switches support Enter/Space, help text opens on focus, and confirmation dialogs
contain Tab focus, close with Escape and restore focus to their opener. Home stays permanently visible under General. Tweaks, System and Tools expand
and collapse, while compact headers/cards reduce scrolling without
hiding descriptions or warnings. All 23 tabs remain accessible, including at
940 x 640. The app catalogue retains its compact category layout. Home uses a
compact hardware summary, a larger score ring with clearly separated digits,
tighter setup controls and compact category cards. At
1280 x 800 and larger desktop viewports, all Home sections and all five Quick
Actions fit without scrolling. The restore-point action lives with the other
Quick Actions, replacing the repeated intro heading. Smaller windows retain
normal scrolling instead of clipping controls or shrinking readable text. The
score ring keeps a larger 122-pixel frame, with centred text and normal numeral
spacing so digits stay separate.
Sidebar groups now expand and collapse over 260 ms, moving the groups below
them naturally. Rapid clicks reverse from the current position. Collapsing
links leave keyboard navigation immediately; reduced motion remains instant.
Screenshots and the feature-tour video use representative demonstration data.
Loading and progress labels use encoding-safe punctuation so they remain readable in packaged WebView assets.

The native window stays hidden until Home is populated and painted, so the
centred loading logo never flashes before the app appears. Home opens directly
with a brief spring settle. No minimum splash delay is added; reduced motion
skips the entrance animation.
A recent hardware summary is retained locally for up to 24 hours, scoped to this
Windows installation, and replaced by a live read on each launch. Hardware reads
run alongside tweak detection rather than waiting behind it. The last completed tweak results are also retained, so reopening preserves the
score and category counts while a fresh live scan runs. The Home note identifies
these as last checked results during the refresh. Closing after changes saves the
updated result snapshot.

Tray connection tests run independently of navigation. Progress updates change
only the status text, leaving Back and other actions intact; return to Quick
actions or revisit the running test without starting it again. Background progress
does not rebuild the page you are using.
The full app groups cleanup categories into compact rows and keeps its action
summary visible while scrolling. Clean Up immediately changes to Cleaning with
a visible activity indicator and live status beside the action. Completion and
errors remain visible, details are expandable, and leaving the page does not
interrupt cleanup or pull you back. NVIDIA settings use compact comparison rows,
and Networking arranges activity results across columns to reduce scrolling.
Its bufferbloat legend shows the added-latency thresholds used by the test. The
grade meter fills by grade, with A+ full; it is a qualitative scale, not a percentage.
The ten NVIDIA comparison rows and all four network tweaks fit without scrolling
at the same desktop sizes as Home. Updates uses a wider, compact panel with inline
version labels so the app and all five bundled tools fit, including download/cancel
and restart-ready states. Smaller windows keep normal scrolling as needed.

![Compact full-app Disk Cleanup with demonstration data](docs/cleanup.png)
Disk cleanup retries ordinary read-only files and continues past locked or
protected files. It retains the existing app-folder and junction exclusions,
never overrides permissions or file locks, and deletes read-only files through
an exclusive Windows file handle without changing their attributes. Both the tray and full app use this shared cleanup engine.

Selecting a power plan keeps the tray on Quick actions. Its dropdown shows the
verified active plan and marks that option with a check, without a separate
success screen. The selector is disabled while switching; a failed switch is
reported inline so it does not silently appear successful.

Secondary screens use a compact Back button instead of repeating Quick actions.
Settings uses a crisp drawn cog rather than a font glyph.
The GPU-driver screen groups each GPU into a rounded card with a bold name,
installed version and status badge. Current and unknown statuses use green;
unknown remains explicitly labelled Unknown, not verified as up to date.
Available driver updates use amber and show the latest version separately.

Tray menus share the selected theme with rounded surfaces, compact line icons,
soft selection highlights and a separated exit action. Their dimensions are
measured at the monitor DPI so labels and icon padding remain visible at 150%.
The tray uses the full app's Segoe UI Variable Text family with a clearer regular
and bold hierarchy,
with a Segoe UI fallback on older Windows versions. Secondary screens use compact
rounded cleanup rows with file sizes aligned on the right and themed checkboxes.
Cleanup expands vertically within the monitor work area to show more options,
while its Clean selected action stays in the fixed footer. Short result messages
use only the height they need, keeping Review cleanup visible without scrolling. A slim scroll thumb replaces the native scrollbars;
keyboard focus scrolls options into view, and opening a page resets its scroll
position so its heading is visible. Long result messages expand above their action.

![Tray GPU drivers with preview data](docs/tray-drivers.png)
![Tray available-update indicator with preview data](docs/tray-update-indicator.png)
![Tray menu](docs/tray-menu.png)
![Tray cleanup layout with preview data](docs/tray-cleanup.png)
![Tray cleanup result with preview data](docs/tray-result.png)

Tray quick-action buttons repaint their full background before drawing their
translucent fill, preventing duplicated text and stale blocks during live Windows
repaints. Rounded corners match the popup backdrop. This was checked on screen
at 150% scaling as well as in bitmap previews.
The companion now renders at the monitor's native DPI, with a more compact
layout, lighter secondary text and theme-matched power and tray menus. Its
frosted-style gradient remains available with Windows transparency disabled;
it does not capture or refract the desktop. Clicking the tray icon or opening
its menu reloads the full app's saved theme and uses it for the active icon.
The idle glyph continues to blend with the Windows taskbar.
Tray pages and Back use a 300 ms spring entrance, with forward/back direction
and smooth reversal from the current position on rapid navigation. The cleanup
viewport grows and shrinks smoothly while keeping the footer anchored. Controls
remain live during the motion. Native redraws are batched while replacing page
controls so intermediate empty frames are not exposed. Background progress does
not restart the transition, and reduced-motion preferences switch immediately.

The tray popup opens with a restrained 320 ms spring settle and fades down on
close over 150 ms. Reopening during dismissal continues from the current pose;
reduced motion remains instant. The power menu settles its anchor before opening,
and clicking the selector again closes it without reopening on the same click.
The active tray icon is updated before activation, unchanged icons are reused,
and child controls are composited together to prevent flashing during refresh.

Each release serves its interface from a content-versioned local address, so
WebView cannot show a previous release's cached design after an update. Saved
themes are retained. Installed releases update quietly through the tray companion when the app and quick actions are idle.
Overview keeps one restore-point shortcut above the tweak controls.
The Overview connection shortcut starts testing immediately. Tests continue when
you visit another tab; returning to Networking restores progress and results for
the current app session. The run button is hidden while a test is active.
The existing feature-tour video predates the frosted surface update.
Window minimise, maximise and restore dispatch immediately through Windows'
native compositor while retaining the custom title bar. Accepted close requests
fade and lower the complete window over 160 ms after tool/save checks finish.
Reduced motion skips the close fade. Screenshots show transparency
enabled; actual appearance follows Windows accessibility preferences. The frost
uses the app's theme backdrop, not a live blur of the desktop behind the window.

Session undo is held in memory and ends when the app closes. It covers tweak
registry values and the original active power plan, boot timer flag, memory
features, service state, firewall/offload settings, USB power settings and NVIDIA
telemetry task states. It does not delete a newly created power plan or undo
separate debloat, Defender, driver-profile, installation or repair workflows.
Use a Windows restore point for wider recovery. Windows Defaults and individual
off switches still apply their documented off values; they are not a factory reset.

Bulk actions now reconcile with verified backend states and report partial failures
or unknown state instead of showing unverified success. Disk Cleanup accepts only
server-owned category IDs and skips symbolic links/junctions and protected app files.


[Watch the 83-second feature tour](docs/techlounge-feature-tour.mp4): all 23 tabs,
a close-up tweak demonstration and app-category browsing. Silent, with on-screen
instructions and sample data labels.

Rapid floating-tool drags retain movements that arrive while the host is catching up.

Tool closure hands input back to the host before hiding the tool, and slow shutdown
no longer triggers an automatic reopen. NVPI caption covers are host-owned windows,
clipped to its rounded frame without cross-process child-window parenting.
The NVPI covers use the selected publisher theme's original header colour.
NVPI starts under a hidden host-owned staging window, then transfers to the main
host once fitted. This keeps startup rendering hidden without repeatedly emptying
its window region; the extra fixed settling delay is skipped when staging succeeds.
If initial ownership needs the region fallback, that region is restored once
cloaked staging succeeds, so it cannot keep the fitted tool invisible.
Its Open button shows **Openingâ€¦** until the subwindow is ready. Driver/profile
initialization still takes time. BCU and DLSS keep their existing launch paths.
Saved maximization, splash and backdrop settings are normalized before launch;
the startup guard also handles late titles and restored bounds. NVPI retains
control of its WPF nonclient rendering rather than forcing a DWM frame reset.
NVPI settings tolerate the publisher file's mismatched UTF-8/UTF-16 declaration
and are saved with a matching encoding. BCU's native caption and system buttons
are removed, including if loading restores them, so its red X cannot cover the
host's themed close button. The tool is hidden before the host UI is activated.
Native fixtures exercise slow closure against a competing foreground window;
live compatibility with each publisher still requires verification.

The Defender chooser distinguishes installed app files from leftover Windows Security
package registrations. With the antivirus absent, remaining folders are recommended
for cleanup; Security-only removal skips antivirus and broader security changes.

Mouse back/forward buttons and Alt+Left/Right navigate between visited pages.
The main window opens centred in the usable area of the monitor containing the mouse pointer.

Every page reads the **live** system state, so the app shows what is actually
set on your machine rather than assuming. The dashboard has a curated recommended
preset, and individual pages explain the scope and undo options for their changes.

![Overview](docs/home.png)

---

## Download

**[â¬‡ Download TechLoungeTweaks.zip](https://github.com/RaheemC4/tech-tips/releases/latest/download/TechLoungeTweaks.zip)**

1. Download and extract the ZIP, then run **TechLoungeTweaks-Setup.exe**.
2. Setup installs for your Windows account and adds a Start menu shortcut and an uninstaller in Windows Settings.
3. Open **Tech Lounge Tweaks** from Start, or click its tray icon for quick actions.

Setup now has a native frosted-style interface matching the saved app theme.
It shows real stages for preparation, app files, bundled tools, tray setup and
verification. Progress follows extracted bytes, with short button reactions and
smooth minimise/close transitions. Windows reduced-motion preferences disable
these animations. There is no browser runtime, animated wallpaper or extra download.
New installations enable delayed tray startup by default; existing disabled
startup preferences are preserved. Change this later in app settings.
Cancellation stops before the new version becomes current. Once setup reaches
its final registration step it finishes that step instead of interrupting it.
Automatic app updates use the same installer with the entire interface bypassed.

![Native installer](docs/installer.png)

![Real installation progress](docs/installer-progress.jpg)

The existing download URL is unchanged. The ZIP now contains a setup program,
not a portable app folder. Existing portable users run setup once to migrate;
the old portable copy can be kept until the installed version is verified.

### Installed app and tray companion

The native tray companion runs without administrator rights. It opens a compact
frosted-style popup using the full app's saved theme, with real power-plan selection
(including creating and selecting Ultimate Performance when absent), disk cleanup,
a connection test, a restore point and GPU driver checks. Actions run inside the
popup; **Open app** opens the full interface directly. Work continues when the
popup is dismissed, and results remain available until the companion exits.
The screenshot below is rendered by the native companion using demonstration data.

![Tray quick actions](docs/companion.png)

Windows asks for elevation only for actions that need it. Cleanup scans first;
**Clean selected** immediately cleans the selected categories.

**Open on startup** schedules the tray for three minutes after sign-in. It does
not launch the full app at sign-in. Automatic update checks begin fifteen minutes
after the companion starts, then repeat every twelve hours. They validate release
metadata and SHA-256 against GitHub's asset digest, and install quietly only while
the full app and quick actions are idle. Offline or failed checks defer to the next
check. Busy or failed checks retry after fifteen minutes. The tray has no Updates page or permanent Updates button. A compact indicator
appears on Quick actions only for a verified newer release and opens the full
app's update panel. Version details and update controls remain in the full app. Third-party tools retain their
existing explicit update controls.

Setup installs under `%LOCALAPPDATA%\Programs\TechLoungeTweaks` by default.
Versioned payloads preserve the previous version during installation; older
unused versions are pruned while the app is closed. Settings,
theme and logs remain under the user's profile. The complete tools are bundled
for offline installation; there is no second payload download during setup.
The tray uses Windows' existing .NET Framework, and loads the Python/backend
process only while a quick action is running. No WebView or full app stays open
just to show the tray icon. Idle appearance has no animation loop.

### Packaging and first launch

The installer targets Intel/AMD x64 Windows 11. It contains the existing
PyInstaller app and BCU's complete x64 runtime, omitting BCU's separate ARM64
payload. Setup uses fast zlib decompression; the enclosing ZIP stores the already
compressed installer without another compression pass. Installation speed depends
on CPU, disk and antivirus scanning and is not guaranteed on every PC.
The installed app does not extract its runtime on each launch.

The Nuitka packaging experiment has been retired after testing did not resolve Defender detections. Use the standard download above.

The app is unsigned. SmartScreen reputation warnings, Smart App Control blocks,
and antivirus quarantine are different outcomes. If a file is quarantined,
record the detection name and affected file for investigation; do not assume
that every detection is a false positive. Changing ZIP extraction software or
removing a downloaded-file marker does not resolve antivirus detections.

The app requests administrator access for system-wide settings. WebView2 is
also required, as described below.

### Requirements

| | |
|---|---|
| **Windows 11** | Works out of the box |
| **Windows 10** | Needs the [WebView2 runtime](https://developer.microsoft.com/microsoft-edge/webview2/) (free, from Microsoft) â€” the app checks on launch and links you to it if it is missing |
| **NVIDIA GPU** | Only needed for the NVIDIA Profile page; everything else works on any machine |
| **App Installer / winget** | Optional. Install Apps prefers it, and falls back to direct vendor downloads when a debloated image has removed it |

---

## Before you start

**Make a restore point.** There is a button for it under *Tools â†’ System
Restore*. It takes about ten seconds and means any change here is reversible
even if something goes wrong.

Two tweaks will break games with kernel-level anti-cheat. They are marked
with a yellow warning in the app, but to be explicit:

- **Disable Memory Integrity** â€” Valorant (Vanguard) and FACEIT will refuse
  to launch.
- **Disable CPU Mitigations** â€” weakens Spectre/Meltdown protection.

Read each option before applying it. App removal and clearing Start pins are
not reversed by the dashboard's Restore Session Changes button.

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
| **GPU** | NVIDIA and AMD driver-level tweaks â€” only the ones for your card are shown |
| **Networking** | Nagle's algorithm, network throttling, offloads, firewall popups |
| **Power** | Dynamic tick, timer coalescing, USB selective suspend and power management |
| **Advanced** | Memory compression, page combining, CPU mitigations |
| **System** | Sticky/Filter/Toggle keys (the Shift x5 pop-up), shutdown speed, menu delay, startup delay, SysMain, telemetry service |
| **Privacy** | Telemetry, activity history, advertising ID, error reporting, typing/speech/ink collection |
| **Explorer & UI** | Classic context menu, Bing in Start, snap layouts, lock screen, widgets, ads |

### One-click setup

Four buttons on the dashboard, for when you do not want to work through nine
categories by hand:

| Button | What it does |
|---|---|
| **Apply Recommended** | Curated privacy settings, Windows Updates paused until 31 December 2051, optional bundled-app removal and the customization choices listed below. Leaves gaming tweaks, Xbox, Game Bar, NVIDIA settings, Defender and virtualization alone. |
| **Apply All** | Asks for confirmation, then applies the legacy tweaks (including Windows Updates paused until 2051 and risky ones), NVIDIA profile, Defender off and the curated Debloat & Customization options. |
| **Restore Session Changes** | Restores values captured before this session changed a tweak, including original registry types and missing values. Leaves untouched tweaks alone. Does not undo other tools, app removals or Start pins. |
| **Windows Defaults** | Turns legacy tweaks off, restores NVIDIA settings and enables Defender. Does not undo the new debloat actions. |

Apply All checks for an NVIDIA GPU before applying its driver profile. Recommended
uses the same preset from the dashboard and the Debloat & Customization page.

### Pause Windows Updates

**System â†’ Pause Windows Updates** pauses feature and security updates until
31 December 2051 using the pause-date settings from
[Aetherinox/pause-windows-updates](https://github.com/Aetherinox/pause-windows-updates#registry-scripts).
Both **Apply Recommended** and **Apply All** include it. The toggle reads the
current registry pause dates/status; Windows can override them after servicing
or organization policy changes. Turn the toggle off, use Windows Defaults or
choose Resume updates in Windows Settings to resume updates.

This integration changes the pause dates and pause-duration limit; it does not
change update services, active hours, WSUS or driver-update policy. Security
fixes are paused too, so resume updates when you want to install them. The
reviewed source revision and MIT licence are bundled; no script is downloaded
or run from the internet when applying a preset.

![Pause Windows Updates](docs/pause-windows-updates.png)

### Debloat & Customization

![Debloat & Customization](docs/debloat.png)

This page integrates selected helpers and settings from
[Win11Debloat](https://github.com/Raphire/Win11Debloat). It does not run the
upstream default preset. Existing options such as Bing search remain in their
original tabs instead of appearing twice.

**Apply Recommended** selects these customization changes: show file extensions
and hidden files, hide Home from Explorer navigation, align the taskbar left,
hide the taskbar search icon, show clock seconds, enable dark theme, hide
"Learn about this picture", clear existing Start pins once, use the Start All
Apps list, hide Start recommendations, disable Bing and Copilot in search, hide
Task View and enable the taskbar End Task option.

It also applies selected privacy and advertising settings and disables Copilot,
Recall, Click to Do and AI additions in Paint, Notepad and Edge. The optional
packaged apps selected for removal are Clipchamp, Cortana, Bing Finance, News,
Sports and Weather, Get Started, the Microsoft 365 promotional hub, Mixed Reality
Portal, Skype and the packaged Copilot app. Missing apps are already satisfied.
Xbox, Game Bar, Gaming Services, Microsoft Store, printing and Windows framework
packages are excluded. Gaming settings are not changed by Recommended.

The switches select what the next **Apply selected** action will do; the status
beside each option reports its detected state. **Apply all** asks for confirmation.
Hide Gallery and hide duplicate drives are optional and off in Recommended.
Unavailable options show their minimum Windows build and are skipped. Some Start
policies depend on edition and feature rollout: a stored policy does not guarantee
that every Windows build will change its appearance. Sign out or restart manually
if Windows has not refreshed the interface.

**Clearing Start pins is a one-time action per existing user profile** with a
Start layout file. It does not lock the layout or change the default profile;
users can pin apps again. Successfully processed profiles are recorded so later
runs preserve newly added pins. The upstream helper backs up the old layout beside
the profile's `start2.bin` file.

Registry changes have individual **Undo** actions using upstream undo settings.
Registry backups and the last run log are kept under
`%LOCALAPPDATA%\TechLoungeTweaks\Debloat`. Undo is not offered for removed apps or
cleared pins; reinstall wanted apps through Microsoft Store and repin them yourself.

### NVIDIA Profile

![NVIDIA Profile](docs/nvidia.png)

One toggle applies a tuned set of global NVIDIA driver settings â€” the same
profile for everyone, so there is no "what did you set yours to" in chat.

**NVIDIA Profile Inspector (Revamped) ships inside the zip**, in the
`resources` folder. Tools & Updates can install newer official Inspector releases.

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
is live you get *"Partly applied â€” 7 of 39 settings match"* rather than a
toggle that quietly lies. The read is warmed on startup, so the page is
already filled in by the time you click the tab.

Only NVIDIA driver settings are touched â€” nothing else on the PC.

**On a machine without an NVIDIA card** the page seals itself and names the GPU
it actually found, so nobody applies a driver profile that cannot do anything.
Every other tab keeps working normally.

![No NVIDIA GPU](docs/nvidia-amd.png)

### Windows Defender

![Defender](docs/defender.png)

One toggle for the whole of Microsoft Defender, with the live state of each
component listed underneath.

**Tamper Protection.** Since Windows 10 1903, Windows blocks *every* app â€”
this one included â€” from switching real-time protection off while Tamper
Protection is on. There is no legitimate way around that, and anything
claiming otherwise is using a malware technique. So the toggle opens the exact
Windows Security page for you to flip that one switch yourself, then finishes
the rest. The same toggle turns everything back on.

**The antimalware service stays in memory.** With everything switched off you
will still see `MsMpEng.exe` running, and Windows still reports the service as
enabled. That is normal and not a failed toggle â€” Windows keeps the service
resident for as long as Defender is the installed antivirus, and nothing can
unload it. What matters is real-time protection, which is what the toggle
follows and what actually scans files. The page says as much underneath the
component list so it is not mistaken for something that did not work.

Turning Defender off leaves the PC with no antivirus until it goes back on.

**Permanently remove Defender.** The button opens a themed, mouse-operated chooser
inside the app, using a reviewed adapter for the bundled
[Defender Remover](https://github.com/ionuttbara/windows-defender-remover)
(release13-rev1). Choose Defender plus Windows Security, antivirus removal while
keeping the Security app, or remaining files after removal and restart. Each
choice requires confirmation. Antivirus removal choices also disable SmartScreen,
UAC, VBS and other protections; recovery may require reinstalling Windows.
Save work and make a system backup first.

The chooser reads this PC when opened: antivirus service, Windows Security package
registrations and manifests, remaining Defender folders and loaded engine/filter.
A package record without app files is labelled **Not installed**. When the antivirus is absent and no components remain loaded,
**Remaining Defender files** is recommended if folders remain. The combined option
is recommended only when both apps are installed. When Defender is absent, that
option becomes **Windows Security only** and runs an explicitly limited worker mode,
without antivirus registry changes or SmartScreen removal. Unknown checks stay **Unknown**.

The SHA-256-verified payload runs without a separate console. Progress and errors
appear inside the app; an operation log is retained. Returning to the Defender
page preserves progress, and the app waits for removal to finish before closing.
The Security adapter derives a validated family name even when only a provisioning
record remains, and checks the DISM removal-policy operation before attempting removal.
A failed policy step stops that package's removal attempt. There is no blind retry.
When antivirus removal is selected and its service exists, the original registry
payloads still run through `regedit /s`. Warnings remain visible rather than being
reported as a clean removal. AppX diagnostics are limited to the current operation's
time window, so earlier logon errors are not presented as this attempt's cause.
Expand **Log location** and choose **Open log folder** to inspect the operation and
servicing logs. A missing manifest or a remaining policy restriction can still
prevent Windows from removing a damaged package; this release does not claim
successful removal on the affected PC without a real post-operation check.
Restart Windows manually after completion and refresh Defender status. There is
no forced restart or scheduled logon console. The upstream CC BY-NC 4.0 licence
and attribution are included. This adapter updates through reviewed app releases.
Validation uses fixtures and mocked removal calls; actual removal is not run on
the development PC.

![Defender removal chooser](docs/defender-removal.png)

![Removal log folder](docs/defender-removal-log.png)

### Connection test

![Networking](docs/network.png)

A proper bufferbloat test â€” it measures your idle ping, then measures it
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

- **Windows setup** â€” under Resources, shows your current Windows name, edition,
  release, build and activation status. If the displayed status is already
  activated, **Activate Windows** immediately shows a dialog without loading MAS.
  Otherwise it checks licensing before opening the bundled MAS HWID tool.
  Each action clears old feedback and shows a loading indicator.
  **Change Windows Version** opens a mouse-operated chooser inside the app,
  shows the current edition and lists Windows-supported target editions. The
  scrollable list has a slim, rounded theme-accent scrollbar with room beside
  the buttons; mouse-wheel and keyboard scrolling remain available.
  A second confirmation names the selected target before applying it through a
  hidden helper. This does not upgrade Windows 10 to 11 or offer unsupported
  downgrade paths. Edition changes may need activation and a manual restart;
  the app never restarts the PC automatically. Use **Refresh status** to recheck.
- **Boot Optimizer** â€” detects your CPU and GPU, then applies startup and
  shutdown tuning that suits them. Preview shows exactly what would change
  before you commit. Secure Boot, TPM and VBS are never touched, so kernel
  anti-cheat keeps working. Every change is written to a rollback file.
- **Disk Cleanup** â€” temp files, Windows Update cache, delivery optimization,
  crash dumps, thumbnails. Shows size per item, you pick what goes.
- **Drivers** â€” checks your installed NVIDIA driver against the latest
  release from NVIDIA's own lookup service. Versions are compared as numbers,
  so a beta or hotfix that is *newer* than the public release is reported as
  ahead rather than as an update you are missing.
- **Resources** â€” SFC, DISM and a read-only disk check, each with a clear
  verdict on whether anything was actually wrong.
- **BIOS Info** â€” firmware version, boot mode, Secure Boot, TPM,
  virtualization and memory speed.
- **Install Apps** â€” runtimes, browsers and game clients, installed silently
  from the vendor. See below.
- **Virtual Machines** â€” switch the CPU between VirtualBox and Windows'
  hypervisor-backed security. See below.

### Extra Tools and updates

![Extra Tools](docs/tools.png)

This personal build also includes **IObit Driver Booster 13.5.1.400** and
**TreeSize Professional 9.8.0.2301** from the supplied archives. Open launches their
application executables directly in the host's floating tool frame. Their custom
headers remain accessible. They show an **Included version**, and TechLoungeTweaks
does not automatically replace them with a different publisher or repack version.
TreeSize's About window is verified as Professional 9.8.0.2301, and Driver Booster
is confirmed displaying 13.5 Pro (bundled executable 13.5.1.400). Both packaged
executables match the supplied archive hashes. Their duplicate window controls
are clipped while menus remain accessible; the host frame supplies the tool Close
button and keeps both tools centered during custom window movement.
Before Driver Booster opens, the repack's supplied settings are applied to disable
its own automatic product updates, automatic scans and automatic driver downloads,
and make Close exit rather than minimize to the tray. Existing unrelated preferences
are retained, with a first settings backup. Launch checks the bundled executable's
hash and refuses a different running copy, preventing a locally installed Free
version from intercepting the Open action.
Driver changes and disk cleanup are choices made inside each tool, never automatic
actions of opening a tool or applying the dashboard's presets.

The third-party portable launchers, website shortcuts, registry-import wrappers,
and the encrypted `thanks4dl.rar` payload are excluded. These two supplied builds
contain modified executables with invalid publisher signatures; integration and
window tests do not establish their safety or validate their licences.

**DLSS Swapper, Bulk Crap Uninstaller (BCU) and NVIDIA Profile Inspector Revamped
come bundled and ready to open.** No separate installation or first-run download
is needed. BCU includes its .NET runtime for this x64 distribution. Its
welcome wizard is skipped through its portable first-run setting; other existing
preferences are preserved. The integrated frame targets BCU's main window rather
than its welcome, news or legend dialogs.
Startup window events suppress the initial surface before the integrated frame
is ready, including BCU's child-process startup.
Choose **Open** to use each complete app in an integrated frame inside
TechLoungeTweaks. DLSS, BCU and NVPI native title bars and window buttons are hidden;
BCU's standard caption is removed rather than cropped using an estimated height.
the tool has no separate taskbar or Alt-Tab entry and cannot be resized independently.
Press and hold the empty frame strip above the tool, then drag to move the entire
TechLoungeTweaks window. The gesture is handed to Windows on the window UI thread
so mouse capture is released correctly. Minimize and maximize/restore also run
on that UI thread and target the current app instance. Native
movement events keep the pair together without the old position-reset loop.
Only an actual drag moves the host: programmatic tool layout, maximization and
shutdown movements do not. NVPI attaches by its main-window title and restores
saved maximized state to Normal before launch, then fits it inside the frame. Positioning uses native
monitor DPI coordinates.

Click the blurred backdrop to **hide** the tool while its work continues. Open
restores the same session. The themed **X closes only the tool**, using its normal
close request so save/busy prompts can still appear. Publisher menus and client
controls retain their own styling. Closing a tool returns focus to the host;
the close icon is a centred SVG. NVPI keeps its profile selector header visible
while its native caption and custom window buttons are hidden. The frame follows
your selected theme. Minimizing TechLoungeTweaks minimizes its visible tool without ending the session;
restoring it brings that tool back. Tools hidden using the backdrop stay hidden
until Open is pressed. Closing TechLoungeTweaks requests closure of all hosted
tools, including hidden ones. If a tool needs a save/busy prompt handled, the main
app stays open until it can close, so no tool is left orphaned on the desktop.

The official managed tools show **Current** and **Latest** versions. An older current version is
yellow with an **Update available** label; the latest release is green. **Update**
is shown when a newer official release is available. Open remains available during
checks. Updated Inspector binaries are used by the existing NVIDIA Profile page;
your curated profile and original-settings backup stay separate.

**OpenMouse** opens the [official live panel](https://control.openmouse.app/) in your default
browser. Newly published mouse support comes from that panel without an app rebuild.
Mouse access needs WebHID support, such as Edge or Chrome. If your default browser
lacks it, use a compatible browser and select your mouse in the device picker.
Remote pages never receive the local administrator API bridge.

![Update panel](docs/updates.png)

**Updates and the theme picker remain above open tools.** Their panels take
priority for both display and clicks while the rest of the tool stays visible
and running. Dismissing a panel restores the covered part of the tool.

The title-bar **Updates** button opens a compact floating panel available from any
page. It is separate from the tool modules. **App update** and **tool update** labels
identify what needs updating; an Inspector release never claims that the main app
is outdated. There is no introductory update card or automatic popup. The panel
also offers Open and Update, separate Current/Latest version tiles, and a prominent
Check for updates button. Its accent follows your selected theme. Unavailable
checks show a neutral label, never a raw release timestamp or false green version.

Checks run in the background without blocking startup or navigation. Bundled tools
remain available offline; failed checks do not claim that an update exists. Clicking
Update on a tool starts a verified background download with progress and cancellation.
Installed app releases are handled by the tray companion automatically after the
full app closes and quick actions finish. The previous version remains in the
versioned installation folder. The initial move from portable to installed requires
running setup once; the older portable updater cannot perform that migration.

Official stable tool downloads verify publisher SHA-256 checksums and archive paths
and sizes before activating a complete staged version. Unsupported packaging or
missing checksums leave the previous version intact. Cancellation during unpacking
takes effect after extraction. Close an open tool and reopen it to use its update.
Previous managed versions and their files remain under
`%LOCALAPPDATA%\TechLoungeTweaks\Updates`. The Updates panel shows Open and
available update actions without a Previous version button. There is no empty More options section. Publisher-specific portable settings are retained
with their original version; automatic settings migration is not guaranteed.

Win11Debloat and Microsoft Activation Scripts are hidden from the user-facing
update list. Their reviewed adapters still change through tested full app releases.
Windows policies and upstream interfaces can change, so future compatibility still
requires maintenance. Install Apps entries remain vendor-installed software with
their own update mechanisms.

App update identity is based on shipped contents, not a fresh packaging timestamp.
Rebuilding or republishing the same software does not count as a new app version.
A complete release ZIP is uploaded to **GitHub Releases**, with its source, README,
release notes and screenshots committed to the repository. The larger bundled ZIP
is not committed as a Git file. PUSH-TO-GITHUB.bat handles both steps; preparing a
release alone does not publish it.

### While something is running

![A scan in progress](docs/resources.png)

Scans and downloads take minutes, so the app tracks them properly rather than
freezing a button. While one is going, the **Run** / **Download** button is
replaced by **Cancel** and a progress bar showing the tool's own real
percentage, with its current output line and an elapsed timer underneath.

**Windows Image Repair legitimately takes 10â€“30 minutes** and will sit on one
percentage for long stretches â€” that is DISM working, not the app hanging. The
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
which state the PC is in. **Apply Recommended** leaves this choice unchanged.

Why this is a choice at all: VirtualBox wants the CPU's virtualisation
directly, but Windows runs its own hypervisor for Memory Integrity, WSL2,
Docker and Sandbox. Whoever holds it, the other loses out.

**Memory Integrity is left off by both modes.** Turning it on taxes every
driver load â€” an earlier build enabled it and MSI installers slowed to a crawl
on a machine that had shipped with it off. Nothing here will ever switch it on
behind your back. The one exception worth knowing: **Valorant can ask for
Memory Integrity to be on**. If Vanguard complains, turn it on yourself in
*Windows Security â†’ Device security â†’ Core isolation*, and the app will leave
it alone.

**Neither button touches Secure Boot or TPM.** Those are firmware settings and
this app has no business changing them.

The hypervisor setting is recorded the first time you open the page, so
switching back restores *your* machine's value rather than a Windows default.

**Either choice needs a restart** â€” the hypervisor setting is applied at boot.

If CPU virtualisation is switched off in your BIOS the page says so in red, with
what to turn on (Intel VT-x, or SVM Mode on AMD). No software setting can work
around that one.

### Install Apps

![Install Apps](docs/apps.png)

Choose a category above the compact app cards. Each category fits the standard
window without scrolling, with local monochrome app icons available offline.
Icons follow all six colour themes immediately, including Shiftd and runtime
tiles. Microsoft
Store and Xbox controls appear under File tools. Running installations retain
progress and cancellation when switching categories.

![Game clients](docs/apps-games.png)

![Game clients with the purple theme](docs/apps-games-purple.png)

File conversion tools, runtimes, browsers and game clients, installed silently â€” the useful half of a
toolbox like Ghost's, without the baggage.

| Group | What's in it |
|---|---|
| **File tools** | Shiftd 1.0.0: offline conversion, compression, image resizing and audio/video trimming, with a desktop app and Explorer submenu |
| **Chat & voice** | Discord with the latest OpenAsar nightly, Discord PTB |
| **Tuning tools** | MSI Afterburner (GPU overclocking/monitoring â€” installed without RivaTuner/RTSS; overclocking done in the real tool, never by this app) |
| **Runtimes** | Visual C++ Redistributables (2005â€“2022, x86 + x64), DirectX web installer, .NET Desktop Runtime 8 |
| **Browsers** | Edge & WebView2, Brave, Chrome, Firefox, Opera GX, Vivaldi |
| **Game clients** | Steam, Epic, Ubisoft Connect, EA App, GOG Galaxy, Battle.net, Rockstar, Amazon Games |

Each card shows how it will be installed. **WINGET** goes through the Windows
Package Manager, which is built into Windows 11 and keeps its own download
URLs and silent switches current â€” nothing to rot. **DIRECT** downloads
straight from the vendor's own domain. **MANUAL** means neither route is
available and the vendor page is the way in.

Downloads are checked against an allowlist of vendor domains before anything
is fetched, so a link that is not on the vendor's own domain is refused.
Installers are downloaded on demand and run silently. Vendor packages remain unmodified; Shiftd is the separate application described below.

Click **Install** on the **Shiftd** card to download the approximately 395 MB
(376 MiB) Shiftd 1.0.0 setup from this repository's pinned release. The app checks
its exact size and SHA-256 before running it silently. Shiftd requires Windows
10/11 x64 and installs for the current user under
`%LOCALAPPDATA%\Programs\ShiftdStandalone`. Its runtime and conversion engines
are included; normal conversion works offline without an account or activation.
This is the updated 11 October build, still labelled Shiftd 1.0.0.
Run the same installer again to upgrade or repair Shiftd. The setup is unsigned.

Open **Shiftd** from the Start menu for batch conversion, compression, maximum
output-size targets, image resizing and audio/video trimming. Image resizing
keeps proportions and never enlarges smaller images. Size targets apply per
output file; impossible targets fail without publishing oversized output.
Animated GIF, document and PDF output size targets are unsupported. Fast
lossless trimming uses nearby keyframes and cannot also resize or target a file
size. For quick conversion, right-click a supported file and choose **Shiftd >
format**, using **Show more options** on Windows 11 if needed. The desktop stays
closed, originals are preserved and existing outputs receive numbered names.
For visual video trimming, right-click a video and choose **Shiftd > Trim video**.
Preview the selected range with the timestamped seek bar, adjust its boundaries
with the mouse or keyboard, and use undo, redo or reset as needed. Preview volume
and mute do not change the saved audio. Save clip lets you choose a name and
folder, shows progress and supports cancellation. Copy file or drag the saved
clip into compatible apps; destination support varies. Originals are preserved
unless you explicitly choose removal.

Notifications are enabled on fresh installs and can be disabled in Shiftd's
Settings; upgrades preserve that choice. Uninstall through **Windows Settings >
Apps > Installed apps > Shiftd**.

The installer is downloaded only when requested, keeping the TechLoungeTweaks
ZIP small. The existing [TechLoungeTweaks download link](https://github.com/RaheemC4/tech-tips/releases/latest/download/TechLoungeTweaks.zip)
is unchanged. Shiftd uses a [separate pinned release](https://github.com/RaheemC4/tech-tips/releases/tag/shiftd-1.0.0-20261011-r2),
so future toolbox updates do not remove its installer. That release also provides
the matching source in nine archive parts and their checksums; source is optional
for installation. Keep all parts together and open `.001` with 7-Zip to extract.
Included dependencies retain their licence notices.

Shiftd replaces the ConvtPersonal card in this toolbox. Updating TechLoungeTweaks
does not automatically uninstall an existing ConvtPersonal installation.

The **Discord** card also installs the current unmodified OpenAsar nightly from
its official GitHub release. It finds the highest numeric `app-*` version under
`%LOCALAPPDATA%\Discord`, verifies the asset against the SHA-256 digest supplied
by GitHub, keeps Discord's stock `app.asar.backup`, and atomically replaces the
latest version's `resources\app.asar`. Running the card again repairs OpenAsar
if a later Discord update replaces it.

Before Discord restarts, the app merges these OpenAsar choices into
`%APPDATA%\discord\settings.json`: Performance focus, No Track on, Disable
Typing on, Splash Theming on, Quickstart on and Multi Instance off. Existing
Discord and unrelated OpenAsar settings are retained. The setup-complete flag
is written too, so OpenAsar does not show its first-launch configuration window.
OpenAsar is a third-party Discord modification and Discord updates can replace
it.

If the Windows Package Manager has been stripped out â€” debloated images
usually remove it â€” the page says so and falls back to direct downloads.

**Microsoft Store & Xbox apps** sit at the top of the same page: one button
removes them, another restores them by re-registering the copy Windows keeps
on disk. If the packages were only uninstalled, the app re-registers them from the copy
Windows keeps on disk. If that copy is gone, it pulls the Store and Xbox app
straight from Microsoft through winget. If even that fails (the Store framework
itself was stripped), a **Get from Microsoft** button opens the official Store
listing so there is always a way through.

---

## Themes

![Themes](docs/themes.png)

The palette button in the title bar switches the whole app between blue,
blurple, purple, red, green and cyan. Everything follows â€” the icon, the score
ring, buttons and selections. Your choice is remembered
between launches.

![Purple theme](docs/theme-purple.png)

The window is fully resizable, and drags at your monitor's refresh rate.
The sidebar opens one navigation group at a time, keeping all 23 tabs reachable
without sidebar scrolling at the supported 940 x 640 minimum. The tweak count
and administrator status remain visible in a separate footer.

---

## A note on BIOS tweaks

The BIOS page is **read-only by design**.

Dell, HP and Lenovo publish supported WMI interfaces for changing firmware
settings from Windows, and the app will use them where it finds one.
Consumer boards (ASUS, MSI, Gigabyte, ASRock) publish nothing equivalent â€”
the only route in is writing firmware NVRAM through an undocumented driver,
and a bad write bricks the board with no way back.

Change those settings in the firmware itself at POST.

---

## Undoing things

- Legacy tweaks: **Restore Session Changes** restores values captured before the first change in the current app session;
  **Windows Defaults** switches those tweaks off.
- Debloat registry settings â€” use their individual **Undo** buttons. Removed
  apps and Start pins need manual reinstalling or repinning.
- Any individual tweak â€” toggle it off.
- A whole category â€” **Revert All** at the top of the page.
- NVIDIA profile â€” toggle it off; your own pre-profile settings come back.
- Defender â€” the same toggle turns it back on.
- Microsoft Store / Xbox apps â€” the Install / restore button on the Install
  Apps page, as long as the image still holds a copy to restore from.
- Boot Optimizer â€” the **Undo** button restores from its rollback file.
- Everything, including things this app never touched â€” Windows System
  Restore, using the point you made before you started.

---

## Something not working?

`%LOCALAPPDATA%\TechLoungeTweaks\Logs\TL-api.log` records what the app did, in plain text.
If something misbehaves, that file says why â€” send it over.

---

## Preparing updates for personal PCs

In the source checkout, run **PREPARE-RELEASE.bat** to run checks, regenerate
screenshots and rebuild `TechLoungeTweaks/TechLoungeTweaks.zip`. Copy this ZIP
to your other PCs and extract the entire folder before opening the executable.

**PUSH-TO-GITHUB.bat** verifies and reuses an unchanged prepared release, or runs
the full preparation above if release files changed. It then commits and pushes the
source, README and screenshots and uploads the app ZIP to GitHub Releases. It uses the current
`RELEASE-NOTES.md` for the commit description and stops if any step fails.
It remains a single-step workflow: running PREPARE separately is optional.
ZIP replacement retries temporary Windows locks and uses a backup-and-rename
fallback for cloud-managed files. If access remains blocked, the old ZIP and
new temporary ZIP are retained and the script explains how to retry.
Both batch windows use cyan text. After a successful push, repository and direct
download links are shown, with R and D shortcuts to open them in your browser.

README wording is reviewed alongside app changes; the scripts synchronise the
reviewed copy and check its source fingerprint. They do not invent documentation
from code. See `HOW-TO-UPLOAD.txt` for setup and the developer review command.

Screenshots use sample system data to demonstrate the interface.

## Credits

The personal build bundles unmodified [Microsoft Activation Scripts 3.12](https://github.com/massgravel/Microsoft-Activation-Scripts)
HWID and Change Windows Edition scripts. Their GPL-3.0 licence and pinned source
reference are included in `_internal/vendor/mas/` beside the script source.
The native edition adapter follows the MAS edition-change approach while limiting
the chooser to targets reported by Windows DISM.

The personal build also bundles unmodified Win11Debloat source at commit
`32024662f3c602442e7af82bbf52c89143b31aeb`. Its MIT licence, source reference and
integrity manifest are in `_internal/vendor/win11debloat/`. The app's adapter
selects explicit options; clock seconds is implemented locally.

Built for The Tech Lounge Discord community. Tweaks are drawn from the
server's tech-tips archive plus documented Windows settings.

Bundles [NVIDIA Profile Inspector Revamped](https://github.com/xHybred/NVIDIAProfileInspectorRevamped)
by xHybred for the NVIDIA Profile page.

The Install Apps page installs vendor software from each vendor's own servers, or
through the Windows Package Manager. The official DLSS, BCU and NVPI bundles retain
their licences and upstream references. The two user-supplied personal tools are
separate modified builds, as described under Extra Tools above.

The Discord installer downloads unmodified [OpenAsar](https://github.com/GooseMod/OpenAsar)
on demand from its official nightly release. OpenAsar is licensed under AGPL-3.0
and is not bundled with TechLoungeTweaks.

Use at your own risk â€” read what a tweak does before applying it.

### Graphics memory reporting

System Information reads dedicated VRAM through DXGI instead of the old 32-bit WMI field that could show 4 GB on larger cards. It matches the adapter identity, supports different capacities of the same GPU model, and shows N/A if no unambiguous reading is available. Driver-reported dedicated memory can be slightly below advertised capacity; shared system memory is not counted.


Hosted tool windows defer native layout updates until Windows layout callbacks return, keeping resizing and maximize/restore handling out of re-entrant callbacks.


Restart and apply posts shutdown to the native Windows UI thread after the updater helper starts. The update dialog stops polling during this handoff; active tools and jobs must still be closed first.


Updates stage the complete replacement beside the installed folder before swapping directories. Open the regular TechLoungeTweaks folder after updating; folders named TechLoungeTweaks.previous-* are retained backups, not the current installation.

### Performance and installer reliability

The Home hardware summary and System Information reuse the same section cache.
**Re-read hardware** clears it so explicit refreshes still collect new values.
A read-only comparison on the development PC reduced the startup hardware-read
sequence from 31 PowerShell queries to 11, with the same summary. This measures
the hardware stage, not total application launch time.

Simultaneous app installs use separate temporary download folders and clean up
only their own files. Direct installers discard unused console output so a
verbose installer cannot stall on a full, unread output pipe. See the
[code review and validation notes](docs/code-review-2026-10-09.md).


### Installer build prerequisite

The release workflow compiles the tray with Windows .NET Framework and requires
NSIS 3.x. Set `MAKENSIS` to its compiler, put it on PATH, or keep it under
`%LOCALAPPDATA%\TechLoungeBuildTools\nsis`. The personal build cache is not published.
