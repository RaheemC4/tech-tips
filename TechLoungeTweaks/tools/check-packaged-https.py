"""Check HTTPS in the actual frozen worker, through its existing restricted pipe."""
import os
from pathlib import Path
import subprocess
import sys

app = Path(__file__).resolve().parents[1]
built = Path(sys.argv[1]).resolve(strict=True)
output = app / 'src/build/https-check'
output.mkdir(parents=True, exist_ok=True)
checker = output / 'PackagedHttpsChecks.exe'
compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
subprocess.run([str(compiler), '/nologo', '/target:exe', '/platform:x64',
                '/reference:System.dll', '/reference:System.Core.dll',
                '/reference:System.Web.Extensions.dll', '/out:' + str(checker),
                str(app / 'tools/PackagedHttpsChecks.cs')], check=True)
subprocess.run([str(checker), str(built / 'TechLoungeTweaks.exe'),
                str(output / 'result.json')], check=True, timeout=70)
