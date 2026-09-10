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

`PREPARE-RELEASE.bat` and `PUSH-TO-GITHUB.bat` regenerate screenshots and build
the ZIP before publishing. Both stop on failed checks. The uploader excludes
build outputs, environments, logs and scratch files.

After reviewing/updating the canonical `TechLoungeTweaks/README.md` and
`RELEASE-NOTES.md`, record the review from `github-upload/`:

```
TechLoungeTweaks\.build-venv\Scripts\python.exe tools\release.py --record-doc-review
```

Then run PREPARE-RELEASE.bat for a local ZIP, or PUSH-TO-GITHUB.bat to prepare
and publish. Root README is synchronised from the app README automatically.
Source hashes prevent publishing changed code with an unreviewed README.

The script drives `web/index.html` in headless Chromium with a stubbed Python
bridge, so it needs no Windows build and no real hardware. Override paths with
`PW=` (playwright module) and `CHROME=` (browser binary) if yours differ.

## App build

For the personal Windows build, use Python 3.12 with PyInstaller 6.22.2 and
pywebview 6.2.1 (pythonnet 3.1.0, clr_loader 0.3.1). From `src/`:

```
python -m PyInstaller --noconfirm TechLoungeTweaks.spec
```

The spec includes `vendor/mas/` with the two unmodified MAS scripts, licence
and upstream commit notice. Copy the existing NVIDIA `resources/` folder next
to the executable before packaging. Keep the full folder together.

The Windows setup tests use mocked launches and a harmless marker script;
they do not activate Windows or change its edition:

```
python -m unittest discover -s tests -v
node tools/test-windows-setup-ui.js
```

Run these from the project directory. Set `PW` to the Playwright module path
and `CHROME` to a Chromium/Edge executable for the UI tests and screenshots.

Original Linux/Wine build command:

```
wine /tmp/winpy/python.exe -m PyInstaller --noconfirm TechLoungeTweaks.spec
```

Then, before zipping:

- delete `dist/TechLoungeTweaks/_internal/web/node_modules` if present
- copy `resources/` (NVIDIA Profile Inspector + the .nip) next to the exe

Use `--onedir`, never `--onefile`: onefile self-extracts ~46 MB to %TEMP% on
every launch, which is both slow and exactly what antivirus heuristics flag.
