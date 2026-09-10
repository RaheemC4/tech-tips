"""Curated Win11Debloat integration; never invokes upstream default presets."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
CATALOG = json.loads((BASE / 'debloat_catalog.json').read_text(encoding='utf-8'))
ITEMS = {item['id']: item for item in CATALOG['items']}
RECOMMENDED_EXISTING = frozenset(CATALOG['existing_recommended'])


def selection(mode, selected=None):
    if mode == 'recommended':
        return [key for key, item in ITEMS.items() if item['recommended']]
    if mode == 'all':
        return list(ITEMS)
    if mode in ('selected', 'undo'):
        if not isinstance(selected, list) or any(not isinstance(key, str) or key not in ITEMS for key in selected):
            raise ValueError('Unknown debloat option.')
        keys = list(dict.fromkeys(selected))
        if mode == 'undo' and any(ITEMS[key]['kind'] != 'registry' for key in keys):
            raise ValueError('Only registry settings have an Undo option. Reinstall removed apps from Microsoft Store.')
        if not keys:
            raise ValueError('Select at least one option.')
        return keys
    raise ValueError('Unknown debloat mode.')


def verify_vendor():
    folder = BASE / 'vendor/win11debloat'
    hashes = json.loads((folder / 'SHA256SUMS.json').read_text(encoding='utf-8'))
    for relative, expected in hashes.items():
        if hashlib.sha256((folder / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Bundled Win11Debloat files changed. Restore the original app bundle.')


def execute(mode, selected=None, progress=None):
    verify_vendor()
    powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    with tempfile.TemporaryDirectory(prefix='TechLoungeDebloat-') as folder:
        request = Path(folder) / 'request.json'
        request.write_text(json.dumps(selected or []), encoding='utf-8')
        args = [str(powershell), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                '-File', str(BASE / 'debloat_bridge.ps1'), '-Mode', mode, '-RequestFile', str(request)]
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8', errors='replace',
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        # A stuck query or external tool must not leave the UI busy indefinitely.
        timed_out = threading.Event()
        def timeout():
            timed_out.set()
            process.kill()
        timer = threading.Timer(60 if mode in ('status', 'plan') else 1800, timeout)
        timer.start()
        result = None
        output = []
        try:
            for line in process.stdout:
                output.append(line.rstrip())
                if line.startswith('TL_RESULT:'):
                    result = json.loads(line[len('TL_RESULT:'):])
                elif line.startswith('TL_PROGRESS:') and progress:
                    progress(json.loads(line[len('TL_PROGRESS:'):]))
            code = process.wait()
        finally:
            timer.cancel()
            process.stdout.close()
        if timed_out.is_set():
            raise RuntimeError('Win11Debloat timed out. Some changes may have applied; refresh status before retrying.')
        if mode not in ('status', 'plan'):
            logdir = Path(os.environ['LOCALAPPDATA']) / 'TechLoungeTweaks/Debloat'
            logdir.mkdir(parents=True, exist_ok=True)
            (logdir / 'last-run.log').write_text('\n'.join(output), encoding='utf-8')
        if not result:
            raise RuntimeError('Win11Debloat returned no result: ' + '\n'.join(output[-5:]))
        if code != 0:
            result['ok'] = False
        return result


def status():
    result = execute('status')
    if not result.get('ok'):
        return result
    states = {item['id']: item for item in result['items']}
    result['items'] = [dict(item, **{k: v for k, v in states.get(item['id'], {}).items() if k != 'id'})
                       for item in CATALOG['items']]
    return result


def apply(mode, selected=None, progress=None):
    keys = selection(mode, selected)
    result = execute('undo' if mode == 'undo' else 'apply', keys, progress)
    rows = result.get('items', [])
    failures = [r for r in rows if not r.get('ok')]
    skipped = [r for r in rows if r.get('skipped')]
    if result.get('ok'):
        result['message'] = f"Finished: {len(rows) - len(skipped)} options processed, {len(skipped)} skipped. Sign out or restart to refresh Windows."
    elif failures:
        result['message'] = 'Some options failed: ' + '; '.join(ITEMS[r['id']]['title'] + ': ' + r.get('message', '') for r in failures)
    return result
