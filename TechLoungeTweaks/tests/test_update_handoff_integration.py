"""Run the real helper against disposable folders and a marker-only executable."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


@unittest.skipUnless(os.name == 'nt', 'Windows update helper')
class HandoffTests(unittest.TestCase):
    def test_replaces_folder_and_launches_new_executable_without_nesting(self):
        compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'TechLoungeTweaks/Updates/candidate/TechLoungeTweaks'
            target = root / 'installed/TechLoungeTweaks'
            for folder in (source, target):
                (folder / '_internal').mkdir(parents=True)
                (folder / '_internal/build-info.json').write_text(json.dumps({'channel':'stable'}))
            code = root / 'Marker.cs'
            code.write_text('class Marker { static void Main() { System.IO.File.WriteAllText(System.IO.Path.Combine(System.AppDomain.CurrentDomain.BaseDirectory,"launched.txt"),"new"); } }')
            subprocess.run([str(compiler), '/nologo', '/target:winexe',
                            '/out:' + str(source / 'TechLoungeTweaks.exe'), str(code)], check=True, capture_output=True)
            (target / 'TechLoungeTweaks.exe').write_bytes(b'old fixture')
            helper = Path(__file__).resolve().parents[1] / 'src/apply-update.ps1'
            subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                            '-File', str(helper), '-AppProcess', '2147483000',
                            '-Source', str(source), '-Destination', str(target)],
                           env=dict(os.environ, LOCALAPPDATA=str(root)), check=True,
                           capture_output=True, timeout=20)
            deadline = time.monotonic() + 5
            while not (target / 'launched.txt').exists() and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue((target / 'launched.txt').exists())
            # Writing the marker precedes process exit; wait before TemporaryDirectory
            # tries to remove its still-mapped executable on fast test machines.
            import psutil
            for process in psutil.process_iter(['exe']):
                try:
                    if process.info['exe'] and Path(process.info['exe']) == target / 'TechLoungeTweaks.exe':
                        process.wait(timeout=5)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            self.assertFalse((target / 'TechLoungeTweaks').exists())
            backups = list(target.parent.glob('TechLoungeTweaks.previous-*'))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / 'TechLoungeTweaks.exe').read_bytes(), b'old fixture')
