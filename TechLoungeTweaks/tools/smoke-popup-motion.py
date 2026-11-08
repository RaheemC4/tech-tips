"""Foreground, synthetic native popup checks. No app actions are invoked."""
import os
import sys
from pathlib import Path
import subprocess
import tempfile
from build_companion import APP, REFERENCES

# Compile disposable GUI checks outside cloud-synced build folders, which can
# lock or evict executables while Windows is loading them.
with tempfile.TemporaryDirectory(prefix='TechLounge-popup-checks-') as folder:
    destination = Path(folder)
    compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    target = destination / 'PopupMotionChecks.exe'
    report = destination / 'checks.txt'
    subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:x64',
                    '/main:TechLounge.PopupMotionChecks', '/out:' + str(target),
                    *['/reference:' + name for name in REFERENCES],
                    *map(str, sorted((APP / 'src/companion').glob('*.cs'))),
                    str(APP / 'tools/PopupMotionChecks.cs')], check=True)
    result = subprocess.run([str(target), str(report), *sys.argv[1:]], timeout=45)
    print(report.read_text(), flush=True)
    result.check_returncode()
