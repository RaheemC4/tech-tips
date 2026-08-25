# Building from source

The published `TechLoungeTweaks.exe` is built from exactly these files.

```
pip install pywebview pyinstaller
pyinstaller --onefile --windowed --name TechLoungeTweaks --uac-admin ^
  --icon app.ico --add-data "web;web" --add-data "app.ico;." ^
  --collect-all webview --collect-all clr_loader ^
  --hidden-import proxy_tools --hidden-import bottle --hidden-import clr ^
  main.py
```

The UI is plain HTML/CSS/JS in `web/`, rendered by the WebView2 runtime that
ships with Windows 11. `tweaks_engine.py` holds every tweak — each one is an
apply/revert/check triple, so you can read exactly what any toggle writes
before you run it.
