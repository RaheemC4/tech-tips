"""Build the short-lived Discord launcher using Windows' .NET Framework."""
import os
from pathlib import Path
import subprocess

APP = Path(__file__).resolve().parents[1]


def build(destination, checks=False):
    compiler = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    target = Path(destination) / ('DiscordLauncherChecks.exe' if checks else 'DiscordLauncher.exe')
    target.parent.mkdir(parents=True, exist_ok=True)
    sources = sorted((APP / 'src/discord-launcher').glob('*.cs'))
    options = []
    if checks:
        sources.append(APP / 'tools/DiscordLauncherChecks.cs')
        options.append('/main:TechLounge.DiscordRepair.Checks')
    subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:x64', '/optimize+',
                    *options, '/out:' + str(target), '/reference:System.dll', '/reference:System.Core.dll',
                    '/reference:Microsoft.CSharp.dll', '/reference:System.Web.Extensions.dll',
                    *map(str, sources)], check=True)
    return target


if __name__ == '__main__':
    import sys
    build(sys.argv[1])
