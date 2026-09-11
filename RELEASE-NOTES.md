Fix hosted-tool layout handling and retire the Nuitka experiment.

- Defer window fitting until native layout notifications return, avoiding re-entrant resizing during maximize/restore and scaling changes. Extend native smoke coverage with repeated NVPI maximize/restore and resize cycles.
- Remove Nuitka download links, candidate build/publish scripts and distributable. The two GitHub test releases and tags are removed; the main repository remains.
- Include the dedicated VRAM reporting fix in the standard package.

Fix dedicated VRAM reporting for graphics cards above 4 GB.

- Replace truncated WMI AdapterRAM with DXGI dedicated memory and PCI adapter matching. Preserve 8 GB and 16 GB variants without guessing from the model name, and report N/A if unavailable or ambiguous.

Show only the Nuitka launcher in Explorer by default.

- Mark _internal and resources as hidden support folders in the portable package and explicit ZIP directory entries. Windows Explorer extraction preserves these attributes.
- Restore only those folder attributes on launch if another extractor drops them, without changing Explorer settings or blocking startup when the folder is read-only.
- Preserve hidden support files during app replacement. Keep antivirus scanning unchanged; this presentation change does not resolve the reported bundled-component detections.

Smaller main x64 release and current test-download links.

- Apply the verified BCU architecture reduction to the main release: omit its separate ARM64 files while retaining the complete x64 runtime, official launcher, licences and all other offline tools.
- Add packaging identity metadata so existing main-release users can receive this smaller package through the updater.
- Keep the latest-download button on the main release and expose the cleaned, channel-isolated Nuitka prerelease separately in the README.

Cleaner, smaller Nuitka portable package.

- Put runtime DLLs, extension modules and the compiled backend inside _internal. A small Windows .NET Framework launcher remains at the top level beside _internal and resources.
- Preserve portable-root resolution for tool resources, NVIDIA files, cleanup exclusions and app replacement. Forward launcher arguments for diagnostics.
- Omit BCU's separate ARM64 payload from this Intel/AMD x64 package, retaining its official launcher, full x64 runtime, licences and other bundled tools. Do not remove required DLSS Swapper runtimes or make tools online-only.
- Combine this packaging change with the dedicated Nuitka update channel below.

Keep Nuitka app updates on Nuitka.

- Discover only explicitly marked Nuitka GitHub releases; never fall back to the standard update feed.
- Reject cross-channel metadata and packages at download staging, pending-update recovery and restart, including a final check in the replacement helper.
- Isolate the Nuitka update cache. Preserve official bundled-tool update sources.
- Generate channel metadata with the Nuitka ZIP and add a dedicated prerelease publisher which leaves the stable latest release unchanged.
- First-candidate users need one manual download to acquire the corrected updater. Fresh-Windows antivirus acceptance remains unverified.

Separate Nuitka packaging candidate.

- Add a reproducible Nuitka 4.2.1 standalone build of the existing interface and backend, with a dedicated ZIP and output folder. Keep the standard PyInstaller release and publishing workflow.
- Preserve the existing packaged resource and update layout through a dedicated entry point. End users do not install Python.
- Correct first-launch documentation: folder packaging is not a guarantee against quarantine; distinguish Windows reputation checks from antivirus detections.
- Add a read-only packaged runtime check and more diagnostic context for the intermittent floating-window foreground test. Full release preparation remains blocked when that desktop assertion fails.
- Fresh-Windows Defender acceptance remains unverified. No certificate purchase, review submission, security exclusion or protection change is part of this work.

Reliable publishing of an already-prepared release.

- The push script verifies and reuses an unchanged prepared release instead of rebuilding and repeating desktop focus tests on every upload. Changed or missing files still require full preparation; failed checks still stop publication.
- Supply the native close fixture's missing host-activation callback, matching the actual app's post-hide activation step. Retain the foreground, hidden-window and shutdown assertions.
- Verify both prepared-release reuse and rebuild/failure handling. No app window behaviour or NVPI settings changed.

NVPI startup presentation and feedback.

- Stage NVPI beneath a host-owned DWM-cloaked window while preparing its integrated frame, then transfer it to the main host. Use the previous region guard as fallback if staging is unavailable. Do not modify driver profiles or global graphics settings.
- Skip the extra fixed settling delay for staged NVPI windows. Show Opening… immediately and retain it until the tool is visible, preventing repeated launch clicks.
- Exercise region resets, resizing, uncloaking, temporary-owner cleanup and full host attachment in a separate-process native fixture. Preserve the working BCU close behaviour and verify its existing regression checks.
- Actual monitor flicker on the user's graphics hardware still requires live confirmation; native fixtures verify window presentation, not a display-driver response.
- Refresh README, screenshots and the personal ZIP.

NVPI launch encoding and BCU's exposed native close button.

- Read the actual bundled NVPI settings even when UTF-8 bytes declare UTF-16. Preserve settings and write a matching encoding. Regression checks use both the real bundled file and UTF-8/UTF-16 fixtures.
- Remove BCU's standard caption and system buttons entirely; reapply after publisher style changes and refit the body below the host controls. This addresses the red native X covering the themed X and bypassing the host close route.
- Limit late-title/location startup monitoring to NVPI, restoring the previous BCU/DLSS event range. Activate the host UI after hiding a closing tool.
- Preserve Windows' runtime minimized/maximized state when repairing publisher title-bar styles.
- Native fixtures restore BCU caption styles, verify their removal and body placement, and exercise slow close with a competing window. Publisher-specific live behaviour still needs confirmation.
- Keep Pause Windows Updates enabled by both dashboard apply presets. Refresh documentation, screenshots and the personal ZIP.

Verified update-pause presets, NVPI presentation and simpler Security status.

- Verify that Apply Recommended and Apply All enable Pause Windows Updates from an off state and return the live checked state as On. Browser checks verify the visible System switch and Applied badge after both dashboard actions, without changing this PC's registry.
- Match NVPI caption covers to its saved theme's original header colour, instead of a screenshot-derived grey. Normalize saved maximization, splash and backdrop settings before launch; catch late title and bounds changes during startup and stop forcing NVPI's DWM nonclient frame to reset.
- Native movement/closure checks pass. Elevated NVPI rendering and first-launch flashing still require live confirmation; automated fixtures do not establish publisher compatibility.
- Show **Not installed** when Windows Security app files are absent, including when a package registration remains. Keep underlying detection and removal behaviour unchanged.
- Refresh README, screenshots and the distribution package.

Tool close focus, NVPI corners and component-aware Defender removal.

- Transfer input from the active tool to the host before hiding it; hide without changing activation or owner z-order. Remove the timer that reopened a tool during slow shutdown. Test a separate-process delayed close with a competing window.
- Replace NVPI cross-process child caption covers with nonactivating owned windows, clipped to the tool's rounded outline and shell-panel exclusions. Normalize maximized startup styling while hidden.
- Distinguish Windows Security app files from residual provisioning records. Recommend file cleanup when Defender is absent; recommend the combined removal only when both apps are installed.
- Use an explicit Security-only worker mode so it cannot apply antivirus registry changes or remove SmartScreen, even if machine state changes after confirmation.
- Resolve package families from provisioned-only identities and check the DISM policy step before removal. Remove blind retries and exclude earlier AppX logon events from current-operation diagnostics.
- Refresh README and screenshot fixtures. System-removal execution remains mocked; actual removal and elevated publisher rendering require live verification.

Pause Windows Updates in both dashboard presets.

- Add a System toggle using Aetherinox's pause-date registry settings, with expiry 31 December 2051 and a current UTC start date.
- Include it in Apply All and Apply Recommended, with explicit dashboard copy, live registry checks and resume through toggle-off/Windows Defaults.
- Preserve service, active-hours, WSUS and driver policies. Bundle pinned source provenance and MIT licence.
- Test preset parity and pause/resume/partial registry states with fake registry storage; do not change this PC's update settings.

Tool input, host focus, NVPI caption covers and removal logs.

- Limit startup suppression to known tool windows and BCU splash surfaces. Do not suppress XAML input helpers or normal dialogs; release DLSS/NVPI guards after attachment.
- Return focus through the host WinForms UI thread when closing tools. Do not unminimize the host or activate it during shutdown.
- Replace NVPI's transparent caption cut-outs with solid client-area covers and remove the decorative drag line.
- Add Open log folder inside Log location; only opens the current job's folder.
- Correct the upstream Security-app script's stale/malformed package-family references and collect AppX deployment events. Windows refusal 0x80073CFA remains unverified until actual removal is tested on the affected machine.
- Add input-helper, focus-dispatch and log-folder regressions; fail the native smoke check on worker-thread exceptions. Refresh docs/screenshots and distribution.

BCU startup/close handling and compact Defender state panel.

- Keep the separate startup splash suppressed after attaching the main tool, including publisher region resets. Reapply main-window clipping when the publisher replaces it.
- Hide tools before requesting close and returning host focus; restore a still-running tool if closure is vetoed.
- Place Defender status beside removal choices, with expandable log paths and no scrolling at tested desktop viewport sizes.
- Retry remaining Windows Security provisioning once after the original installed-package removal stage, retaining HRESULT and DISM diagnostics on refusal. Actual removal remains unverified on the user's machine.
- Added native splash and viewport regressions. Refreshed README and screenshot fixtures.

Corrected tool movement classification and Defender removal sequencing.

- Programmatic tool movement and shutdown no longer move the host. Close teardown is excluded from movement handling, with focus returned after closure.
- NVPI filters out helper windows, waits for stable main-window bounds and normalizes saved maximized state. Placement uses per-monitor native coordinates.
- Defender now executes the unchanged upstream Security-app script and registry files with regedit /s, continuing the publisher's sequence when AppX reports errors. Full errors and warnings are retained.
- Added live antivirus, Security-app, remaining-folder and loaded-component status with a suggested next step for full removal. Unavailable checks remain Unknown.
- Added regressions for programmatic movement, original-script failure handling and state-based guidance. No actual removal was executed during validation.

Integrated tool-window fixes and in-app Defender removal.

- Startup visibility guard is armed before tool execution, covering BCU's launcher and child windows until attachment.
- Closing a tool hands focus to TechLoungeTweaks first. The close button uses a centred, rounded SVG icon.
- NVPI's client header is preserved; native caption and custom window buttons are masked separately.
- Main window centres on the pointer monitor's usable work area before showing.
- Added themed removal choices, explicit confirmation, in-app progress and failure reporting using a pinned Defender Remover adapter. No separate console, forced restart or logon task. Actual removal was not executed during validation.
- Refreshed README/screenshots and release workflow checks.

Refined the Windows edition chooser scrollbar.

- Replaced the bright system track and arrow buttons with a slim, rounded scrollbar that follows the selected accent theme.
- Added space between edition buttons and the scrollbar, with keyboard and mouse-wheel scrolling retained.
- Refreshed screenshots with the actual edition chooser using safe fixture data.

Fixed native window controls and BCU startup integration.

- Minimize and maximize/restore now run on the current window UI thread, alongside the corrected drag handoff.
- BCU skips its welcome wizard through the portable first-run setting, preserving other preferences.
- The BCU frame waits for the main application window and ignores startup/news/legend windows.
- Added real hidden-WebView checks for window states and UI-thread dispatch, plus BCU startup regressions.

Fixed the unresponsive tool-frame drag grip.

- Dragging now releases WebView mouse capture and starts native window movement on the owning UI thread.
- Window controls target this exact app instance instead of searching by window title.
- A quick released click does not start a sticky move gesture. Added regression coverage for dispatch, capture release and cursor coordinates.

Subapps now follow the host lifecycle.

- Closing TechLoungeTweaks closes all hosted tools, including backdrop-hidden sessions, instead of detaching and revealing them.
- Tool save/busy prompts keep the host open until resolved; shutdown does not force-kill active operations.
- Minimizing/restoring the host preserves tool sessions. Backdrop-hidden tools remain hidden until Open.

Updates and theme controls stay above integrated tools.

- Native tool surfaces now yield the popup area to Updates and the theme picker, including mouse input. The rest of the tool stays visible and running.
- Popup areas track panel size, window movement and display scaling, and restore when dismissed.
- Added browser and native-region regression checks for panel priority and restoration.

Integrated tool frames and a fix for movement flicker.

- Replaced the snap-back position loop with native movement events. Dragging the frame grip moves TechLoungeTweaks and the open tool together.
- Hidden native tool title bars, captions, window buttons and separate taskbar/Alt-Tab entries. Tool surfaces cannot be resized independently.
- Added a theme-matched frame and glowing close button. X requests closure of only the tool; clicking the blurred backdrop hides it without ending its session. Open restores hidden work.
- Added regression coverage for movement feedback, hidden launches, frame styles, taskbar suppression, close targeting and hide/restore.

A clearer update panel and integrated tool sessions.

- Redesigned Updates with a theme-accent button, readable version tiles and a prominent check action. Removed More options and misleading timestamps when checks fail.
- Mouse back/forward buttons and Alt+Left/Right navigate visited pages.
- Native tools stay inset with the host over a blurred backdrop. Clicking the backdrop hides the session without terminating work; Open restores it. Tool close controls affect only the tool.
- OpenMouse now opens directly at https://control.openmouse.app/ in the default browser.
- Bundled verified Defender Remover release13-rev1 with explicit confirmation and its official interactive controls. Its broader security-removal scope is explained before launch. No removal was executed during validation.

Bundled tools, a simpler update panel and clearer version status.

- Bundled the full official DLSS Swapper, BCU (with runtime) and NVIDIA Profile Inspector Revamped, ready to open without installation.
- All three open as floating owned windows above TechLoungeTweaks, retaining their native interfaces.
- Removed the introductory update card. Extra Tools offers Open and Update; a compact title-bar panel separates updates from regular modules.
- Hidden Win11Debloat and MAS from the update display. Older current versions are yellow, latest versions green, with explicit text labels.
- App and tool update notifications are distinct. Content-based app identity prevents unchanged rebuilds from appearing as new software.
- Fixed sidebar crowding with independent menu scrolling and a spaced, fixed-height status footer.
- The push batch publishes the larger bundled ZIP as a verified GitHub Release asset and commits updated source, README, release notes and screenshots together.


