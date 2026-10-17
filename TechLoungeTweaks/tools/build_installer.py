"""Make the offline per-user installer. NSIS is a build dependency only."""
import json
import os
from pathlib import Path
import shutil
import subprocess

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
    subprocess.run([compiler, '/WX', '/V2', '/DVERSION=' + info['version'],
                    '/DPAYLOAD=' + str(Path(payload).resolve()),
                    '/DOUTPUT=' + str(Path(output).resolve()),
                    str(APP / 'src/companion/installer.nsi')], check=True)
    return Path(output)
