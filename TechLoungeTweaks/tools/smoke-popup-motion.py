"""Foreground, synthetic native popup checks. No app actions are invoked."""
import os
import sys
from pathlib import Path
import subprocess
from build_companion import APP, REFERENCES

destination = APP / 'src/build/popup-motion-checks'
destination.mkdir(parents=True, exist_ok=True)
compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
target = destination / 'PopupMotionChecks.exe'
report = destination / 'checks.txt'
subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:x64',
                '/main:TechLounge.PopupMotionChecks', '/out:' + str(target),
                *['/reference:' + name for name in REFERENCES],
                *map(str, sorted((APP / 'src/companion').glob('*.cs'))),
                str(APP / 'tools/PopupMotionChecks.cs')], check=True)
result = subprocess.run([str(target), str(report), *sys.argv[1:]], timeout=20)
print(report.read_text(), flush=True)
result.check_returncode()
