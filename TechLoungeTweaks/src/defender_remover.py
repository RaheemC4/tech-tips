"""Confirmed adapter for a pinned payload; no removal on import or status reads."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

VERSION = 'release13-rev1'
SHA256 = '64ea442286170f73a9083b52ded50a2edf8b0f3708fdcbc8b5855c4183b2ce2f'
MANIFEST_SHA256 = '67cab6b0c02f0e68ccde92ed43ee90a2f1440404a043d26acce752fc7cd0ff89'
MODES = ('all', 'antivirus', 'files', 'security')
MACHINE_PROBE = r'''
$ErrorActionPreference='Stop'
$state=@{antivirus=$null;security_app=$null;security_registered=$null;security_registration_only=$null;files=$null;engine_running=$null;errors=@()}
try { $state.antivirus=[bool](Get-Service | Where-Object Name -eq 'WinDefend') } catch { $state.errors += 'Antivirus service check failed.' }
try {
 $names=@('Microsoft.SecHealthUI','Microsoft.Windows.SecHealthUI')
 $installed=@(Get-AppxPackage -AllUsers | Where-Object Name -in $names)
 $provisioned=@(Get-AppxProvisionedPackage -Online | Where-Object DisplayName -in $names)
 $state.security_registered=[bool]($installed.Count -or $provisioned.Count)
 $manifests=@($installed | Where-Object InstallLocation | ForEach-Object { Join-Path $_.InstallLocation 'AppxManifest.xml' })
 foreach($package in $provisioned) {
  if($package.PackageName -match '^Microsoft\.(Windows\.)?SecHealthUI_[0-9.]+_(x64|x86|arm64|neutral)_[^\\/]*_[a-z0-9]{13}$') {
   $manifests += Join-Path $env:ProgramW6432 ('WindowsApps\'+$package.PackageName+'\AppxManifest.xml')
  }
 }
 $manifests += Join-Path $env:SystemRoot 'SystemApps\Microsoft.Windows.SecHealthUI_cw5n1h2txyewy\AppxManifest.xml'
 $state.security_app=[bool](@($manifests | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf -ErrorAction Stop }).Count)
 $state.security_registration_only=$state.security_registered -and -not $state.security_app
} catch { $state.errors += 'Windows Security package check failed.' }
try {
 $state.engine_running=[bool]((Get-Process -Name MsMpEng -ErrorAction SilentlyContinue) -or (Get-CimInstance Win32_SystemDriver -Filter "Name='WdFilter'" | Where-Object State -eq 'Running'))
} catch { $state.errors += 'Running components check failed.' }
try {
 $paths=@((Join-Path $env:ProgramData 'Microsoft\Windows Defender'),(Join-Path $env:ProgramW6432 'Windows Defender'),(Join-Path ${env:ProgramFiles(x86)} 'Windows Defender'),(Join-Path $env:ProgramW6432 'Windows Defender Advanced Threat Protection'))
 $state.files=[bool](@($paths | Where-Object { Test-Path -LiteralPath $_ }).Count)
} catch { $state.errors += 'Remaining folders check failed.' }
$state | ConvertTo-Json -Compress
'''


def recommend(machine):
    if any(machine.get(k) is None for k in ('antivirus','security_app','files','engine_running')):
        return None, 'Some checks are unavailable. Refresh the state before choosing a removal step.'
    if machine['antivirus'] and machine['security_app']:
        return 'all', 'For full removal, remove Defender + Windows Security first, then restart and refresh this state.'
    if machine['antivirus']:
        return 'antivirus', 'Only the antivirus is installed. Remove Defender antivirus, then restart and refresh.'
    if machine['engine_running']:
        return None, 'Defender components are still loaded. Restart Windows, then refresh before removing remaining files.'
    if machine['files']:
        return 'files', 'Defender antivirus is absent. Remove its remaining folders next. Windows Security is checked separately.'
    if machine['security_app']:
        return None, 'Defender is absent. The Windows Security option will remove only the Security app.'
    if machine.get('security_registration_only'):
        return None, 'The Security app files are missing, but Windows retains a package registration. This is not a working installation.'
    return None, 'No antivirus service, Windows Security package, loaded engine or remaining Defender folders were detected.'


def machine_state():
    import base64
    try:
        code=base64.b64encode(MACHINE_PROBE.encode('utf-16le')).decode('ascii')
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',code],capture_output=True,text=True,timeout=35,creationflags=0x08000000,check=True)
        machine=json.loads(result.stdout)
    except Exception:
        machine={'antivirus':None,'security_app':None,'files':None,'engine_running':None,'errors':['Could not read the current machine state.']}
    machine['recommended'],machine['guidance']=recommend(machine)
    machine['checked']=time.time()
    return machine
_lock = threading.RLock()
_job = None
_started = 0
_state = {'running': False, 'phase': 'idle', 'progress': 0, 'message': 'Choose what to remove.'}


def validate_bundle(root=None):
    base = Path(root) if root else (Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent.parent)
    bundle = base / 'resources/defender-remover'
    raw = (bundle / 'payload-hashes.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Removal payload verification failed. Extract a fresh app ZIP.')
    for name, expected in json.loads(raw).items():
        path = (bundle / 'payload' / name).resolve()
        if not path.is_relative_to((bundle / 'payload').resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Removal payload verification failed. Extract a fresh app ZIP.')
    return bundle


def status():
    global _state
    with _lock:
        if _job and _state.get('running'):
            try:
                data=json.loads((_job/'status.json').read_text(encoding='utf-8-sig'))
                if data.get('phase') in ('running','complete','failed'):
                    _state=data
            except (OSError,ValueError):
                if time.monotonic()-_started>65 and _state.get('phase')=='starting':
                    _state.update(running=False,phase='failed',message='The worker did not report startup. Check the log before retrying.')
            if _state.get('running') and _state.get('pid'):
                import psutil
                if not psutil.pid_exists(_state['pid']):
                    try: _state=json.loads((_job/'status.json').read_text(encoding='utf-8-sig'))
                    except (OSError,ValueError): pass
                    if _state.get('running'):
                        _state.update(running=False,phase='failed',message='The worker stopped before completing. Changes may be partial; review the log.')
            _state['log_path']=str(_job/'operation.log')
        return dict(_state)


def launch(mode=None, confirmed=False, root=None):
    global _job, _state, _started
    if mode not in MODES or confirmed is not True:
        return {'ok':False,'message':'Choose and confirm a removal option first.'}
    with _lock:
        if is_running(): return {'ok':False,'message':'A removal is already running.'}
        try:
            bundle=validate_bundle(root)
            _job=Path(tempfile.mkdtemp(prefix='TechLounge-removal-'))
            _started=time.monotonic()
            _state={'running':True,'phase':'starting','progress':0,'mode':mode,'message':'Starting the removal worker…','log_path':str(_job/'operation.log')}
            powershell=str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe')
            subprocess.Popen([str(bundle/'payload/PowerRun.exe'),'/SW:0',powershell,
                '-NoProfile','-NonInteractive','-WindowStyle','Hidden','-ExecutionPolicy','Bypass',
                '-File',str(bundle/'payload/runner.ps1'),'-Mode',mode,'-JobPath',str(_job),
                '-StartDeadline',str(int(time.time())+60)],
                cwd=bundle/'payload',creationflags=0x08000000)
            return {'ok':True,**_state}
        except Exception as exc:
            _state={'running':False,'phase':'failed','message':str(exc),'progress':0}
            return {'ok':False,**_state}


def is_running():
    return status().get('running',False)


def open_log_folder():
    # No arbitrary caller-supplied path: only the current removal's directory.
    with _lock:
        folder = _job
    if not folder or not folder.is_dir():
        return {'ok':False,'message':'No removal log folder is available yet.'}
    try:
        os.startfile(str(folder), 'open')
        return {'ok':True}
    except OSError as exc:
        return {'ok':False,'message':'Could not open the log folder: '+str(exc)}
