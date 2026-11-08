# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from pathlib import Path
import ssl

datas = [('build/discord-launcher/DiscordLauncher.exe', 'discord-launcher'), ('web', 'web'), ('app.ico', '.'), ('vendor', 'vendor'), ('build-info.json', '.'), ('bundled-tools.json', '.'), ('apply-update.ps1', '.'),
         ('debloat_catalog.json', '.'), ('debloat_bridge.ps1', '.'), ('edition_bridge.ps1', '.'), ('debloat-reg', 'debloat-reg')]
# Some build runtimes load an adjacent TLS policy file from ssl.py. Preserve
# that resource in the same frozen directory; ordinary Python needs no extra file.
ssl_policy = Path(ssl.__file__).with_name('codex-rejected-cas.pem')
if ssl_policy.is_file():
    datas.append((str(ssl_policy), '.'))
binaries = []
hiddenimports = ['proxy_tools', 'bottle', 'clr']
tmp_ret = collect_all('webview')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('clr_loader')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TechLoungeTweaks',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False,
    icon=['app.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TechLoungeTweaks',
)
