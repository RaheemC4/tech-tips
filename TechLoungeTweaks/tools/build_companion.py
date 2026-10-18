"""Compile the native .NET Framework companion without bundling another runtime."""
import os
from pathlib import Path
import subprocess

APP = Path(__file__).resolve().parents[1]
REFERENCES = ['System.dll', 'System.Core.dll', 'System.Drawing.dll', 'System.Windows.Forms.dll',
              'System.Web.Extensions.dll', 'System.IO.Compression.dll', 'System.IO.Compression.FileSystem.dll', 'Microsoft.CSharp.dll']


def build(destination, checks=False):
    compiler = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    target = Path(destination) / ('CompanionChecks.exe' if checks else 'TechLounge.exe')
    target.parent.mkdir(parents=True, exist_ok=True)
    sources = sorted((APP / 'src/companion').glob('*.cs'))
    options = []
    if checks:
        sources.append(APP / 'tools/CompanionChecks.cs')
        options.append('/main:TechLounge.CompanionChecks')
    subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:x64', '/optimize+', *options,
                    '/out:' + str(target), '/win32icon:' + str(APP / 'src/app.ico'),
                    *['/reference:' + r for r in REFERENCES],
                    *map(str, sources)], check=True)
    return target


if __name__ == '__main__':
    import sys
    build(sys.argv[1])
