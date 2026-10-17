"""Make the offline per-user installer. NSIS is a build dependency only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import hashlib
import struct

APP = Path(__file__).resolve().parents[1]


def build(payload, output):
    compiler = os.environ.get('MAKENSIS') or shutil.which('makensis')
    if not compiler:
        candidates = [Path(os.environ['LOCALAPPDATA']) / 'TechLoungeBuildTools/nsis/makensis.exe',
                      Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'NSIS/makensis.exe']
        compiler = next((str(p) for p in candidates if p.is_file()), None)
    if not compiler:
        raise RuntimeError('Set MAKENSIS to the NSIS compiler before building the installer.')
    info = json.loads((APP / 'src/build-info.json').read_text())
    payload = Path(payload).resolve()
    work = APP / 'src/build/installer'
    work.mkdir(parents=True, exist_ok=True)
    engine = work / 'engine.exe'
    filelist = work / 'payload.nsh'
    items = sorted((p for p in payload.rglob('*') if p.is_file()),
                   key=lambda p: (p.parts[len(payload.parts)] == 'resources', str(p)))
    total = sum(p.stat().st_size for p in items)
    copied = 0
    reported = -1
    lines = []
    previous_directory = None
    def nsis(value):
        return str(value).replace('$', '$$').replace('"', '$\\"')
    for path in items:
        relative = path.relative_to(payload)
        directory = str(relative.parent)
        lines += ['Call CheckCancellation', 'ClearErrors']
        if directory != previous_directory:
            lines += ['SetOutPath "$INSTDIR\\versions\\${VERSION}' + ('' if directory == '.' else '\\' + nsis(directory)) + '"']
            previous_directory = directory
        lines += ['File "' + nsis(path) + '"', 'IfErrors 0 +3', 'SetErrorLevel 1',
                  'Abort "Could not extract an app file. Check available space and permissions."']
        copied += path.stat().st_size
        percent = 5 + int(83 * copied / max(total, 1))
        if percent != reported:
            stage = 2 if relative.parts[0] == 'resources' else 1
            lines += [f'Push "{stage}|{percent}"', 'Call ReportProgress']
            reported = percent
    filelist.write_text('\n'.join(lines), encoding='utf-8-sig')
    subprocess.run([compiler, '/WX', '/V2', '/DVERSION=' + info['version'],
                    '/DPAYLOAD=' + str(Path(payload).resolve()),
                    '/DFILELIST=' + str(filelist), '/DOUTPUT=' + str(engine),
                    str(APP / 'src/companion/installer.nsi')], check=True)
    metadata = work / 'SetupBuild.cs'
    def sha(name):
        return hashlib.sha256((payload / name).read_bytes()).hexdigest()
    metadata.write_text('namespace TechLoungeSetup { static class SetupBuild { public const string Version="' + info['version'] +
                        '"; public const string CoreHash="' + sha('TechLoungeTweaks.exe') +
                        '"; public const string TrayHash="' + sha('TechLounge.exe') +
                        '"; public const string EngineHash="' + hashlib.sha256(engine.read_bytes()).hexdigest() + '"; } }', encoding='utf-8')
    csc = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    subprocess.run([str(csc), '/nologo', '/target:winexe', '/platform:x64', '/optimize+',
                    '/out:' + str(Path(output).resolve()),
                    '/win32icon:' + str(APP / 'src/app.ico'),
                    '/reference:System.dll', '/reference:System.Core.dll', '/reference:System.Drawing.dll',
                    '/reference:System.Windows.Forms.dll', str(metadata),
                    str(APP / 'src/installer/Setup.cs')], check=True)
    # An overlay is streamed through ordinary file I/O. A managed resource would
    # keep hundreds of MB of payload pages mapped into the setup process.
    with Path(output).open('ab') as destination, engine.open('rb') as source:
        shutil.copyfileobj(source, destination, 1024 * 1024)
        destination.write(b'TLTSETUP' + struct.pack('<q', engine.stat().st_size))
    return Path(output)


def check(setup, screenshot=None):
    """Run real failure paths; optional visual capture opens only the welcome screen."""
    work = APP / 'src/build/installer'
    csc = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    checks = work / 'InstallerChecks.exe'
    subprocess.run([str(csc), '/nologo', '/target:winexe', '/out:' + str(checks),
                    str(APP / 'tools/InstallerChecks.cs')], check=True)
    report = work / 'checks.txt'
    subprocess.run([str(checks), str(setup), str(report)], check=True)
    print(report.read_text(), flush=True)
    if screenshot:
        capture = work / 'InstallerScreenshot.exe'
        subprocess.run([str(csc), '/nologo', '/target:winexe', '/out:' + str(capture),
                        '/reference:System.Drawing.dll', '/reference:System.Windows.Forms.dll',
                        str(APP / 'tools/InstallerScreenshot.cs')], check=True)
        subprocess.run([str(capture), str(setup), str(screenshot)], check=True)
