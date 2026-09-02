# Building Tech Lounge Tweaks

## Screenshots

Regenerate **all** of them with one command:

```
node tools/make-screenshots.js
```

Do this after **any** UI change. This matters more than it looks: adding a page
to the sidebar changes every screenshot, not just the new page's, because the
sidebar is in all of them. Two releases shipped with stale shots before this
was automated.

`PUSH-TO-GITHUB.bat` checks for this before it pushes — if any file in `src/`
(`.js`, `.html`, `.css`) is newer than the oldest PNG in `docs/`, it warns and
asks before continuing.

The script drives `web/index.html` in headless Chromium with a stubbed Python
bridge, so it needs no Windows build and no real hardware. Override paths with
`PW=` (playwright module) and `CHROME=` (browser binary) if yours differ.

## App build

```
wine /tmp/winpy/python.exe -m PyInstaller --noconfirm TechLoungeTweaks.spec
```

Then, before zipping:

- delete `dist/TechLoungeTweaks/_internal/web/node_modules` if present
- copy `resources/` (NVIDIA Profile Inspector + the .nip) next to the exe

Use `--onedir`, never `--onefile`: onefile self-extracts ~46 MB to %TEMP% on
every launch, which is both slow and exactly what antivirus heuristics flag.
