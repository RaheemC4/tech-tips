"""Launch the bundled, unmodified MAS tools in a visible console."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading


TOOLS = {
    "activate": ("HWID_Activation.cmd", "6828dcb2650fffde272b3af4a3c3ce1ca85130fd210232cb1f56c8299693ea2d"),
    "edition": ("Change_Windows_Edition.cmd", "2e3d1ab1ec9120b199578bfa144106e8fadaa6b9c7fba40d3bcc6c341532bfca"),
}


class WindowsSetup:
    def __init__(self, folder):
        self.folder = Path(folder).resolve()
        self._lock = threading.Lock()
        self._process = None

    def status(self):
        query = r"""
$ErrorActionPreference = 'Stop'
$os = Get-CimInstance Win32_OperatingSystem
$cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$activated = $null
$activationError = $null
try {
    $licenses = @(Get-CimInstance SoftwareLicensingProduct -Filter "ApplicationID='55c92734-d682-4d71-983e-d6ec3f16059f'" |
        Where-Object { $_.PartialProductKey })
    $activated = @($licenses | Where-Object { $_.LicenseStatus -eq 1 }).Count -gt 0
} catch { $activationError = 'Windows licensing status could not be read.' }
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[pscustomobject]@{
    name = $os.Caption; edition = $cv.EditionID
    version = $cv.DisplayVersion; build = $os.BuildNumber
    activated = $activated; activation_error = $activationError
} | ConvertTo-Json -Compress
"""
        try:
            powershell = str(Path(os.environ['SystemRoot']) / 'System32' /
                             'WindowsPowerShell' / 'v1.0' / 'powershell.exe')
            result = subprocess.run(
                [powershell, '-NoProfile', '-NonInteractive', '-Command', query],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=20, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode:
                raise ValueError('Windows status query failed.')
            data = json.loads(result.stdout.lstrip('\ufeff').strip())
            if not isinstance(data, dict) or not data.get('name'):
                raise ValueError('Windows returned an incomplete status.')
            if data.get('activated') is not True and data.get('activated') is not False:
                data['activated'] = None
            return dict(data, ok=True)
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            return {'ok': False, 'activated': None,
                    'message': f'Could not check Windows status: {exc}'}

    def launch(self, action):
        if action not in TOOLS:
            return {"ok": False, "message": "Unknown Windows setup action."}
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return {"ok": False, "message": "A Windows setup tool is already open. Finish and close it first."}
            status = self.status()
            if not status.get('ok'):
                return status
            if action == 'activate':
                if status.get('activated') is True:
                    return {'ok': True, 'already_activated': True, 'status': status,
                            'message': 'Windows is already activated. No activation is needed.'}
                if status.get('activated') is not False:
                    return {'ok': False, 'status': status,
                            'message': 'Could not verify activation status. Use Refresh status and try again.'}
            filename, expected = TOOLS[action]
            script = self.folder / filename
            try:
                if hashlib.sha256(script.read_bytes()).hexdigest() != expected:
                    return {"ok": False, "message": "The bundled MAS script failed its integrity check. Restore it from your original build."}
                # cmd.exe expands percent variables even inside quotes. Refuse
                # those unusual install paths rather than interpret their text.
                if any(c in str(script) for c in '%"\r\n'):
                    return {"ok": False, "message": "Move the app to a folder without percent signs or quotes, then try again."}
                cmd = str(Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe")
                # -qedit prevents MAS from detaching into a second console, so
                # our process handle guards both tools against concurrent runs.
                command = f'"{cmd}" /d /v:off /s /c ""{script}" -qedit"'
                self._process = subprocess.Popen(
                    command, executable=cmd, cwd=str(self.folder),
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            except OSError as exc:
                return {"ok": False, "message": f"Could not open the bundled MAS tool: {exc}"}
            return {"ok": True, "status": status, "message": "MAS opened in a separate window. Follow its prompts and check the result there."}
