"""Build an isolated Nuitka candidate without replacing the standard release."""
import importlib.metadata
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import tempfile
import os

APP = Path(__file__).resolve().parents[1]
SRC = APP / 'src'
ROOT = APP.parent
OUT = SRC / 'dist' / 'nuitka'

def build():
    if importlib.metadata.version('Nuitka') != '4.2.1':
        raise RuntimeError('Install Nuitka==4.2.1 in the build environment.')
    OUT.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-m', 'nuitka', '--mode=standalone',
        '--assume-yes-for-downloads', '--windows-console-mode=disable',
        '--windows-uac-admin', '--windows-icon-from-ico=app.ico',
        '--output-filename=TechLoungeTweaks.exe', '--output-dir=' + str(OUT),
        '--company-name=Tech Lounge', '--product-name=TechLoungeTweaks',
        '--file-version=' + '.'.join(json.loads((SRC / 'build-info.json').read_text())['version'].split('.')[:3] + ['0']),
        '--include-module=webview.platforms.winforms',
        '--include-module=webview.platforms.edgechromium',
        '--include-module=clr', '--include-module=proxy_tools',
        '--report=' + str(OUT / 'compilation-report.xml'), 'nuitka_entry.py']
    subprocess.run(command, cwd=SRC, check=True)
    package()

def package():
    """Stage the current resources after a successful compilation."""
    built = OUT / 'nuitka_entry.dist'
    internal = built / '_internal'
    internal.mkdir(exist_ok=True)
    for name in ('web', 'vendor', 'debloat-reg'):
        shutil.copytree(SRC / name, internal / name, dirs_exist_ok=True)
    for name in ('app.ico', 'build-info.json', 'bundled-tools.json',
                 'apply-update.ps1', 'debloat_catalog.json', 'debloat_bridge.ps1',
                 'edition_bridge.ps1'):
        shutil.copy2(SRC / name, internal / name)
    identity = json.loads((internal / 'build-info.json').read_text())
    identity['channel'] = 'nuitka'
    (internal / 'build-info.json').write_text(json.dumps(identity, indent=2) + '\n', encoding='utf-8')
    sys.path.insert(0, str(ROOT / 'tools'))
    from release import copy_resources
    copy_resources(built)
    # Assemble a fresh portable tree. Do not relocate DLLs within Nuitka's
    # runtime tree; relocate that whole tree behind a tiny .NET launcher.
    portable = Path(tempfile.mkdtemp(prefix='portable-', dir=OUT)) / 'TechLoungeTweaks'
    runtime = portable / '_internal'
    shutil.copytree(internal, runtime)
    for item in built.iterdir():
        if item.name in ('_internal', 'resources') or item.suffix == '.log':
            continue
        if item.is_dir():
            shutil.copytree(item, runtime / item.name)
        else:
            shutil.copy2(item, runtime / item.name)
    bcu = (built / 'resources/tools/bcu').resolve()
    def omit_other_architecture(folder, names):
        return ['win-arm64'] if Path(folder).resolve() == bcu and 'win-arm64' in names else []
    shutil.copytree(built / 'resources', portable / 'resources', ignore=omit_other_architecture)
    # This release is x64, as is its Nuitka runtime. Retain BCU's official
    # launcher, licences and complete self-contained x64 payload.
    if not (portable / 'resources/tools/bcu/win-x64/BCUninstaller.exe').is_file():
        raise RuntimeError('Expected BCU x64 package is missing; review upstream layout.')
    csc = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    subprocess.run([str(csc), '/nologo', '/target:winexe', '/platform:x64',
        '/reference:System.Windows.Forms.dll', '/win32icon:' + str(SRC / 'app.ico'),
        '/out:' + str(portable / 'TechLoungeTweaks.exe'), str(SRC / 'PortableLauncher.cs')], check=True)
    archive = APP / 'TechLoungeTweaks-Nuitka.zip'
    pending = archive.with_suffix('.zip.tmp')
    with zipfile.ZipFile(pending, 'w', zipfile.ZIP_DEFLATED) as target:
        for path in sorted(portable.rglob('*')):
            if path.is_file() and path.suffix not in ('.log', '.pyc'):
                target.write(path, 'TechLoungeTweaks/' + path.relative_to(portable).as_posix())
    with zipfile.ZipFile(pending) as target:
        if target.testzip():
            raise RuntimeError('Candidate ZIP failed integrity verification.')
    pending.replace(archive)
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    tag = 'nuitka-test-' + identity['version'] + '-' + sha[:12]
    manifest = dict(identity, release_tag=tag,
        download_url=f'https://github.com/RaheemC4/tech-tips/releases/download/{tag}/{archive.name}',
        files={'TechLoungeTweaks/TechLoungeTweaks.zip': sha})
    (APP / 'nuitka-update.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (OUT / 'latest-portable.json').write_text(json.dumps({'folder': str(portable)}), encoding='utf-8')
    print('CANDIDATE (fresh-Windows acceptance not yet verified):', archive)

if __name__ == '__main__':
    build()
