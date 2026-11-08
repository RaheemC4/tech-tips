import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


@unittest.skipUnless(os.name == 'nt', 'Windows silent installer handoff')
class InstalledHandoffTests(unittest.TestCase):
    def test_real_helper_waits_verifies_installs_and_reopens_without_real_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root/'TechLoungeTweaks/Updates/candidate'
            target = root/'installed app with spaces'
            source.mkdir(parents=True);target.mkdir()
            old = dict(schema=2, version='2026.10.23.174632', built_utc='2026-10-23T17:46:32+00:00', app_revision='a'*64)
            new = dict(schema=2, version='2026.11.08.030000', built_utc='2026-11-08T03:00:00+00:00', app_revision='b'*64)
            current = target/'versions'/old['version']/'_internal';current.mkdir(parents=True)
            (current/'build-info.json').write_text(json.dumps(old))
            (target/'current.txt').write_text(old['version'])
            compiler = Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
            code = root/'Fixture.cs'
            code.write_text('using System;using System.IO;class Fixture { static int Main(string[] a) { if(a.Length>0 && a[0]=="--open")File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"opened.txt"),"opened"); return 0; }}')
            subprocess.run([str(compiler),'/nologo','/target:winexe','/out:'+str(target/'TechLounge.exe'),str(code)],capture_output=True,check=True)
            code.write_text('using System;using System.IO;class Fixture { static int Main(string[] a) { var all=Environment.CommandLine;var i=all.IndexOf("/D=");if(i<0)return 2;var d=all.Substring(i+3).Trim();File.WriteAllText(Path.Combine(d,"current.txt"),"2026.11.08.030000");File.WriteAllText(Path.Combine(d,"installer-arguments.txt"),all);return 0; }}')
            setup = source/'TechLoungeTweaks-Setup.exe'
            subprocess.run([str(compiler),'/nologo','/target:winexe','/out:'+str(setup),str(code)],capture_output=True,check=True)
            (source/'installer.json').write_text(json.dumps(dict(new,sha256=hashlib.sha256(setup.read_bytes()).hexdigest())))
            script=Path(__file__).resolve().parents[1]/'src/apply-update.ps1'
            result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),'-AppProcess','2147483000','-Source',str(source),'-Destination',str(target),'-Installer'],env=dict(os.environ,LOCALAPPDATA=str(root)),capture_output=True,text=True,timeout=25)
            import psutil
            for process in psutil.process_iter(['exe']):
                try:
                    if process.info['exe'] and Path(process.info['exe']) in (target/'TechLounge.exe',setup):process.wait(timeout=5)
                except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            self.assertEqual(result.returncode,0,result.stdout+result.stderr+(root/'TechLoungeTweaks/Updates/last-update.txt').read_text())
            deadline=time.monotonic()+5
            while not (target/'opened.txt').exists() and time.monotonic()<deadline:time.sleep(.05)
            self.assertEqual((target/'opened.txt').read_text(),'opened')
            self.assertEqual((target/'current.txt').read_text(),new['version'])
            arguments=(target/'installer-arguments.txt').read_text()
            self.assertIn('/S /UPDATE /D=',arguments)
            self.assertEqual((current/'build-info.json').read_text(),json.dumps(old))
            # A modified installer must never execute; keep the previous pointer.
            (target/'current.txt').write_text(old['version'])
            (target/'installer-arguments.txt').unlink()
            setup.write_bytes(setup.read_bytes()+b'tampered')
            rejected=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),'-AppProcess','2147483000','-Source',str(source),'-Destination',str(target),'-Installer'],env=dict(os.environ,LOCALAPPDATA=str(root)),capture_output=True,text=True,timeout=25)
            for process in psutil.process_iter(['exe']):
                try:
                    if process.info['exe'] and Path(process.info['exe']) == target/'TechLounge.exe':process.wait(timeout=5)
                except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            self.assertEqual(rejected.returncode,1)
            self.assertEqual((target/'current.txt').read_text(),old['version'])
            self.assertFalse((target/'installer-arguments.txt').exists())
            self.assertIn('checksum verification failed',(root/'TechLoungeTweaks/Updates/last-update.txt').read_text())




if __name__=='__main__':unittest.main()
