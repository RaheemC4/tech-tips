# Win11Debloat integration

Source: https://github.com/Raphire/Win11Debloat
Pinned commit: 32024662f3c602442e7af82bbf52c89143b31aeb
Retrieved: 2026-09-10. MIT licence is included in LICENSE.

Bundled upstream files are unmodified. Tech Lounge Tweaks calls the registry,
backup, Appx removal and Start-layout helper functions from its own curated
adapter, debloat_bridge.ps1. It never invokes the default or gaming presets.
The catalog excludes settings already exposed by existing tabs.

ShowSecondsClock is a local addition using ShowSecondsInSystemClock; upstream
does not expose this option. ClearStartOnce calls upstream Replace-StartMenu
for existing profiles with start2.bin, records successful SIDs, and skips them
on future runs. It neither sets a permanent Start layout policy nor modifies
the default user profile. Newly created users are handled on a later run.

App removal is limited to explicit Appx package identifiers. WinGet removals,
gaming packages, Store components, device/printer helpers, OneDrive, Defender,
services and Windows optional features are not included in the curated catalog.
