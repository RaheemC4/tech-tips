"""On-demand companion work. No listener, service or background polling."""
import base64
import ctypes
import csv
import json
import re
import subprocess

THEMES = ('blue', 'blurple', 'purple', 'red', 'green', 'cyan')
ULTIMATE = 'e9a42b02-d5df-448d-aa00-03f14749eb61'
MANAGED_ULTIMATE = 'c4b4b5f7-6c83-4b22-89d9-227f0831e32a'
GUID = r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}'


def theme(value=None):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\TechLoungeTweaks') as key:
        if value is not None:
            if value not in THEMES:
                raise ValueError('Unknown theme')
            winreg.SetValueEx(key, 'Theme', 0, winreg.REG_SZ, value)
        try:
            saved = winreg.QueryValueEx(key, 'Theme')[0]
            return saved if saved in THEMES else None
        except FileNotFoundError:
            return None


def power(command):
    result = subprocess.run(['powercfg.exe', *command], capture_output=True,
                            text=True, errors='replace', creationflags=0x08000000, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stdout.strip() or result.stderr.strip() or 'Windows refused this power plan.')
    return result.stdout


def plans():
    result = []
    for line in power(['/list']).splitlines():
        match = re.search(GUID, line)
        if match:
            name = re.search(r'\((.*)\)', line)
            label = name.group(1) if name else match.group()
            if match.group().lower() == MANAGED_ULTIMATE:
                label = 'Ultimate Performance'
            result.append(dict(id=match.group().lower(), name=label,
                               active='*' in line))
    if not result:
        raise RuntimeError('Windows returned no power plans.')
    return result


def select_plan(value):
    available = plans()
    if value == 'ultimate':
        # Localised names are irrelevant: use a fixed, known destination GUID.
        target = next((p['id'] for p in available if p['id'] in (ULTIMATE, MANAGED_ULTIMATE) or
                       p['name'].casefold() == 'ultimate performance'), None)
        if target is None:
            power(['/duplicatescheme', ULTIMATE, MANAGED_ULTIMATE])
        value = target or MANAGED_ULTIMATE
    elif not any(p['id'] == value for p in available):
        raise ValueError('Choose a power plan available on this PC.')
    power(['/setactive', value])
    result = plans()
    if not any(p['id'] == value and p['active'] for p in result):
        raise RuntimeError('Windows did not activate the selected plan.')
    return {'plans': result, 'message': 'Power plan selected.'}


def execute(action, payload, emit):
    if action == 'plans':
        return {'plans': plans()}
    if action == 'power':
        return select_plan(payload)
    if action not in ('scan', 'clean', 'restore', 'connection', 'drivers'):
        raise ValueError('Unknown quick action')
    from main import Api
    api = Api.__new__(Api)
    api._window = None
    api._busy = set()
    api._emit = lambda name, data: emit({'event': name, 'data': data})
    if action == 'clean':
        import cleanup
        cleanup.resolve_categories(payload)  # Validate before any deletion.
        return api.clean_run(payload)
    return {'scan': api.clean_scan, 'restore': api.restore_point,
            'connection': api.nettest, 'drivers': api.check_drivers}[action]()


def entry(args):
    """Write results only to a randomly named local pipe owned by the tray.

    Elevated workers accept a small allowlist of actions, never script text or
    arbitrary output paths. The pipe carries results, not privileged commands.
    """
    if len(args) != 3 or not re.fullmatch(r'TLT-[a-f0-9]{32}', args[0]):
        return 2
    pipe_name, action, encoded = args
    if len(encoded) > 8192:
        return 2
    request = json.loads(base64.b64decode(encoded, validate=True))
    if not isinstance(request, dict) or set(request) != {'value', 'user_sid'}:
        return 2
    payload = request['value']
    path = '\\\\.\\pipe\\' + pipe_name
    ctypes.windll.kernel32.WaitNamedPipeW(path, 10000)
    with open(path, 'wb', buffering=0) as stream:
        def emit(data):
            stream.write((json.dumps(data, allow_nan=False) + '\n').encode('utf-8'))
        try:
            if action == 'clean':
                identity = subprocess.run(['whoami.exe', '/user', '/fo', 'csv', '/nh'], capture_output=True,
                                          text=True, creationflags=0x08000000, timeout=10, check=True)
                sid = next(csv.reader(identity.stdout.splitlines()))[1]
                if sid != request['user_sid']:
                    raise ValueError('Cleanup must run as the same Windows account that scanned the files.')
            result = execute(action, payload, emit)
            emit({'done': True, 'data': result})
        except Exception as exc:
            emit({'done': True, 'data': {'ok': False, 'error': str(exc)}})
    return 0
