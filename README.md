https://github.com/user-attachments/assets/7c0ee593-4087-4d2e-9131-30cf8c78519e

# Tech Lounge Tweaks

Windows tweaks, useful tools and quick actions for The Tech Lounge.

**[Download the latest ZIP](https://github.com/RaheemC4/tech-tips/releases/latest/download/TechLoungeTweaks.zip)** | [Full guide](https://github.com/RaheemC4/tech-tips/blob/main/docs/USER-GUIDE.md) | [Release notes](https://github.com/RaheemC4/tech-tips/blob/main/RELEASE-NOTES.md) | [4K video](https://github.com/RaheemC4/tech-tips/blob/main/docs/techlounge-feature-tour.mp4)

## Get started

1. Download and extract the ZIP.
2. Run **TechLoungeTweaks-Setup.exe** and follow setup.
3. Create a restore point, then choose the changes you want.

Windows 11 recommended. Windows 10 requires [Microsoft WebView2](https://developer.microsoft.com/microsoft-edge/webview2/). NVIDIA hardware is only needed for NVIDIA-specific features.

## What it does

- **Tweaks:** performance, graphics, networking, power, privacy and Windows customisation.
- **System tools:** hardware information, disk cleanup, GPU driver checks and an NVIDIA profile.
- **Setup:** recommended presets, debloat, app installation, boot optimisation and restore points.
- **Tray companion:** compact flat action rows for power plans, connection tests, cleanup, restore points and GPU drivers. Amber **Out of date** and green **Up to date** identify driver status; unavailable checks stay neutral. **Download update** opens the official vendor download in your browser; installation remains your choice.
- **Appearance:** six themes, keyboard navigation and reduced-motion support.

## Automatic updates

With **Open on startup** enabled, the tray starts about 30 seconds after sign-in and begins its first update check about 30 seconds later. It checks again every 15 minutes. Opening the full app also starts background checks and updates.

New published app releases download without a confirmation prompt. The app restarts automatically after startup work, system actions, downloads and open tool windows have finished. If the full app is closed, the tray applies app updates quietly in the background. Failed or offline checks retry later; the app cannot stay current while publishers are unreachable.

DLSS Swapper, Bulk Crap Uninstaller and NVIDIA Profile Inspector update from their supported official stable release feeds. **Update all** in the top-right update panel runs all available app and tool updates together; downloads remain cancellable. A tool that is running is deferred. Driver Booster, TreeSize and the reviewed Windows integrations are refreshed with complete app releases rather than downloading unreviewed replacements separately.

Downloads retain the existing official-source and checksum checks, and tool updates keep previous files for rollback. These updates manage the app’s own toolbox, not every program installed on Windows. Install this build once to receive its new update behaviour; future app releases must be published to GitHub before they can be detected.

## Before applying changes

Read each setting. Disabling Memory Integrity can prevent some anti-cheat games from launching; disabling CPU mitigations reduces security. App removal and cleared Start pins need manual restoration.

Toggle a tweak off or use **Revert All** to undo a category. **Restore Session Changes** restores supported values saved during the current session; it does not undo every tool or app removal. Use a restore point for wider recovery.

## Help

Resize the main window from any edge or corner. Its initial size fits the current monitor’s available area at Windows display scaling, with a smaller minimum size and responsive content. The tray rescales when its monitor’s DPI changes. The tray uses the main app’s font, shows all cleanup items and detected GPUs together, and has no scrollbars or pagination. Its width is 380 logical pixels; page height fits its content while the Open app footer stays anchored. Windows supplies the pointer shapes.

The custom window controls preserve Windows animations and restore the original window size and position, including after rapidly minimising and maximising.

### HatchZip

**Install Apps > File tools** installs the latest stable HatchZip Windows desktop release, resolved from GitHub each time. The installer size and SHA-256 must match release metadata before it runs. If metadata is unavailable or invalid, installation stops. Its local monochrome icon follows the selected theme. HatchZip extraction consumes the source archive as files are extracted.

### Discord and OpenAsar

Installing stable Discord from **Install Apps** also installs the latest verified OpenAsar nightly and an on-demand repair launcher. Existing Discord Desktop, Start menu and taskbar shortcuts use that launcher. It checks the newest complete Discord version, restores missing OpenAsar from a verified local copy, then starts Discord and exits. It adds no Windows startup entry, scheduled task, service or background watcher. Discord's own startup preference is unchanged.

After an update, fully quit Discord from its system tray icon and reopen it through its shortcut or taskbar pin. Discord's internal update restart and its own Windows auto-start can bypass the launcher. If Windows retains an older taskbar launch target, unpin Discord and pin the **Discord** Start menu entry again. Reinstalling Discord through TechLoungeTweaks reconnects the launcher; installing it elsewhere may replace the shortcuts.

The launcher and versioned original-file backups live in `%LOCALAPPDATA%\TechLoungeTweaks\Discord`. It preserves existing OpenAsar builds and recognised renamed archives used by other client mods. If repair is blocked, it records the reason in `launcher.log` and opens Discord normally. A future incompatible Discord/OpenAsar release may still need an updated integration. To remove it, reinstall official Discord to restore its files and shortcuts, replace any remaining repair shortcut with the official Discord shortcut, then remove the helper folder.

Logs: `%LOCALAPPDATA%\TechLoungeTweaks\Logs\TL-api.log`.

See the [full guide and credits](https://github.com/RaheemC4/tech-tips/blob/main/docs/USER-GUIDE.md) for detailed features, troubleshooting, bundled software and licences. The video uses representative demonstration data.
