"""Background release checks and transactional, opt-in portable tool updates.

No network or subprocess work happens at import, construction or status reads.
The app's reviewed adapters are updated only by a complete app release.
"""
import copy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import urllib.parse
import uuid
import zipfile

APP_REPO = 'RaheemC4/tech-tips'
RAW = 'https://raw.githubusercontent.com/' + APP_REPO + '/main/TechLoungeTweaks/'
TOOLS = {
    'dlss': dict(name='DLSS Swapper', repo='beeradmoore/dlss-swapper',
                 pattern=r'DLSS\.Swapper-.+-portable\.zip', exe='DLSS Swapper.exe',
                 description='Manage game upscaling libraries using the complete official DLSS Swapper app.'),
    'bcu': dict(name='Bulk Crap Uninstaller', repo='BCUninstaller/Bulk-Crap-Uninstaller',
                pattern=r'BCUninstaller_.+_portable\.7z', exe='BCUninstaller.exe',
                description='Bulk uninstall apps and review leftovers in the full BCU interface. Includes its runtime.'),
    'nvpi': dict(name='NVIDIA Profile Inspector Revamped', repo='xHybred/NVIDIAProfileInspectorRevamped',
                 pattern=r'NVPI-R\.zip', exe='NVPI-R.exe', baseline='7.2.0.0',
                 description='Updates the Inspector used by the NVIDIA Profile page. Your profile and original-settings backup stay separate.'),
}
REVIEWED = {
    'win11debloat': ('Win11Debloat', 'Raphire/Win11Debloat', '2026.08.24'),
    'mas': ('Microsoft Activation Scripts', 'massgravel/Microsoft-Activation-Scripts', '3.12'),
}
MAX_DOWNLOAD = 1024 ** 3
MAX_EXPANDED = 3 * 1024 ** 3
OPENMOUSE = dict(id='openmouse', name='OpenMouse', installed='Live web panel', action=None,
                 message='Opens the live official panel in your default browser. Mouse controls require WebHID support, such as Edge or Chrome.')


def version(value):
    text = str(value).lstrip('vV')
    if not re.fullmatch(r'\d+(?:\.\d+)*', text):
        raise ValueError('Unrecognised release version; review the publisher release.')
    parts = [int(n) for n in text.split('.')]
    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def app_channel(build):
    channel = build.get('channel', 'stable')
    if channel not in ('stable', 'nuitka'):
        raise ValueError('Unknown app update channel.')
    return channel


def app_manifest(build):
    if app_channel(build) == 'stable':
        return get_json(RAW + 'release.json')
    # Prereleases do not appear at /releases/latest. Only explicit Nuitka
    # metadata qualifies; an absent channel never falls back to stable.
    for page in range(1, 11):
        entries = get_json(f'https://api.github.com/repos/{APP_REPO}/releases?per_page=100&page={page}')
        for entry in entries:
            if entry.get('draft') or not entry.get('tag_name', '').startswith('nuitka-'):
                continue
            assets = [a for a in entry.get('assets', []) if a['name'] == 'nuitka-update.json']
            if len(assets) != 1:
                continue
            prefix = f'https://github.com/{APP_REPO}/releases/download/{entry["tag_name"]}/'
            if not assets[0]['browser_download_url'].startswith(prefix):
                raise ValueError('Unexpected Nuitka metadata source.')
            manifest = get_json(assets[0]['browser_download_url'])
            if app_channel(manifest) != 'nuitka' or not manifest['download_url'].startswith(prefix):
                raise ValueError('Nuitka release metadata has the wrong channel or source.')
            package = [a for a in entry.get('assets', []) if a['name'] == 'TechLoungeTweaks-Nuitka.zip']
            if (len(package) != 1 or package[0]['browser_download_url'] != manifest['download_url'] or
                    package[0].get('digest') != 'sha256:' + manifest['files']['TechLoungeTweaks/TechLoungeTweaks.zip']):
                raise ValueError('Nuitka release checksum does not match GitHub.')
            return manifest
        if len(entries) < 100:
            return build  # No channel release yet; stay on the current build.
    raise ValueError('Nuitka update lookup limit reached; current app unchanged.')


def newer_app(manifest, build):
    """Compare exact app contents, then release order; reject legacy ambiguity."""
    if app_channel(manifest) != app_channel(build):
        raise ValueError('App update belongs to a different channel.')
    if manifest.get('schema') != 2:
        raise ValueError('The publisher has not supplied current app update metadata yet.')
    for data in (manifest, build):
        if not re.fullmatch(r'[a-f0-9]{64}', data.get('app_revision', '')):
            raise ValueError('App release identity is unavailable.')
    if manifest['app_revision'] == build['app_revision']:
        return False
    remote = datetime.fromisoformat(manifest['built_utc'])
    local = datetime.fromisoformat(build['built_utc'])
    if remote.tzinfo is None or local.tzinfo is None:
        raise ValueError('App release timestamp must include a timezone.')
    return remote > local


def checked_url(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or p.username or p.password or p.port not in (None, 443) or p.hostname not in {
        'api.github.com', 'github.com', 'raw.githubusercontent.com',
        'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}:
        raise ValueError('Download is not from an allowed official GitHub host.')
    return url


class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def response(url):
    request = urllib.request.Request(checked_url(url), headers={
        'User-Agent': 'TechLoungeTweaks-Updater', 'Accept': 'application/vnd.github+json'})
    return urllib.request.build_opener(Redirects()).open(request, timeout=15)


def get_json(url):
    with response(url) as stream:
        data = stream.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024:
        raise ValueError('Release metadata is too large.')
    return json.loads(data)


def release(repo):
    value = get_json('https://api.github.com/repos/' + repo + '/releases/latest')
    if value.get('draft') or value.get('prerelease'):
        raise ValueError('Only stable releases are supported.')
    return value


def asset_for(tool, data):
    matches = [a for a in data.get('assets', []) if re.fullmatch(tool['pattern'], a['name'], re.I)]
    if len(matches) != 1:
        raise ValueError('Publisher packaging changed; a compatible app update is required.')
    a = matches[0]
    prefix = 'https://github.com/' + tool['repo'].lower() + '/releases/download/'
    if not a['browser_download_url'].lower().startswith(prefix):
        raise ValueError('Asset does not belong to the configured publisher repository.')
    if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}', a.get('digest') or ''):
        raise ValueError('Publisher SHA-256 is unavailable; automatic installation is disabled.')
    return dict(url=a['browser_download_url'], sha256=a['digest'][7:], name=a['name'])


def download(asset, target, progress, cancel):
    expected = asset['sha256'].lower()
    if not re.fullmatch(r'[a-f0-9]{64}', expected):
        raise ValueError('Invalid download checksum.')
    digest = hashlib.sha256()
    start = time.monotonic()
    total = 0
    with response(asset['url']) as stream, target.open('wb') as output:
        size = int(stream.headers.get('Content-Length', 0))
        if size > MAX_DOWNLOAD:
            raise ValueError('Download exceeds size limit.')
        while True:
            if cancel.is_set():
                raise InterruptedError('Download cancelled; the previous version is unchanged.')
            if time.monotonic() - start > 900:
                raise TimeoutError('Download timed out; try again later.')
            chunk = stream.read(256 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOWNLOAD:
                raise ValueError('Download exceeds size limit.')
            output.write(chunk)
            digest.update(chunk)
            progress('Downloading', total / size if size else None)
    if digest.hexdigest() != expected:
        raise ValueError('Checksum mismatch; the previous version is unchanged.')


def safe_name(name):
    p = PureWindowsPath(name)
    if not name or p.is_absolute() or p.drive or p.root or '..' in p.parts or ':' in name:
        raise ValueError('Unsafe archive path.')
    for part in p.parts:
        if part.endswith((' ', '.')) or PureWindowsPath(part).is_reserved():
            raise ValueError('Unsafe Windows filename.')


def extract(archive, destination):
    if archive.suffix == '.7z':
        import py7zr
        with py7zr.SevenZipFile(archive) as source:
            entries = source.list()
            if len(entries) > 30000 or sum(e.uncompressed or 0 for e in entries) > MAX_EXPANDED:
                raise ValueError('Archive exceeds extraction limits.')
            for entry in entries:
                safe_name(entry.filename)
            if len({str(PureWindowsPath(e.filename)).lower() for e in entries}) != len(entries):
                raise ValueError('Duplicate archive paths.')
            # Reject all link/reparse entries before extracting any files.
            for entry in source.files:
                if entry.is_symlink or entry.is_junction:
                    raise ValueError('Archive links are not supported.')
        # Windows 11's libarchive supports the ARM64 filter in current BCU
        # packages. py7zr validates metadata first but cannot decode that filter.
        tar = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/tar.exe'
        if not tar.is_file():
            raise ValueError('Windows archive support is missing (System32/tar.exe).')
        destination.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(tar), '-xf', str(archive), '-C', str(destination)],
                       check=True, capture_output=True, timeout=300, creationflags=0x08000000)
    else:
        with zipfile.ZipFile(archive) as source:
            entries = source.infolist()
            if len(entries) > 30000 or sum(e.file_size for e in entries) > MAX_EXPANDED:
                raise ValueError('Archive exceeds extraction limits.')
            seen = set()
            for entry in entries:
                safe_name(entry.filename)
                key = str(PureWindowsPath(entry.filename)).lower()
                if key in seen or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('Duplicate paths or links in archive.')
                seen.add(key)
            source.extractall(destination)


def atomic_json(path, value):
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temp.write_text(json.dumps(value), encoding='utf-8')
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def prepare_bcu_settings(exe, current_version):
    """Use BCU's portable settings to skip onboarding without resetting preferences."""
    import xml.etree.ElementTree as ET
    folder=exe.parent
    if folder.name.startswith('win-') and (folder.parent/'BCUninstaller.exe').is_file():
        folder=folder.parent
    path=folder/'BCUninstaller.settings'
    if path.exists():
        try: root=ET.parse(path).getroot()
        except ET.ParseError: return  # Leave malformed user settings to BCU's recovery.
        if root.tag!='Settings': return
    else:
        root=ET.Element('Settings')
    first=root.find('MiscFirstRun')
    if first is not None and first.text=='False': return
    if first is None: first=ET.SubElement(root,'MiscFirstRun')
    first.text='False'
    if root.find('MiscVersion') is None:
        parts=str(current_version).lstrip('vV').split('.')
        ET.SubElement(root,'MiscVersion').text='.'.join((parts+['0']*4)[:4])
    temporary=path.with_suffix('.settings.tmp')
    ET.ElementTree(root).write(temporary,encoding='utf-8',xml_declaration=True)
    os.replace(temporary,path)


class UpdateManager:
    def __init__(self, root=None, build=None, bundle_root=None, bundle_manifest=None):
        self.root = Path(root or Path(os.environ.get('LOCALAPPDATA', tempfile.gettempdir())) / 'TechLoungeTweaks' / 'Updates')
        self.build = build or self._build_info()
        self.channel = app_channel(self.build)
        if self.channel == 'nuitka':
            self.root = self.root / 'nuitka'
        app_dir = Path(getattr(sys, '_tl_app_root', Path(sys.executable).parent)) if getattr(sys, 'frozen', False) else Path(__file__).parent.parent
        self.bundle_root = Path(bundle_root) if bundle_root else app_dir / 'resources/tools' if root is None else None
        self.bundle_manifest = bundle_manifest or Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'bundled-tools.json'
        self.bundles = {}
        self.lock = threading.Lock()
        self.cancel = threading.Event()
        self.state = dict(checking=False, busy=False, checked=None, items=[dict(OPENMOUSE)], message='', progress=None)
        self.installed = {}
        self.offers = {}
        self.processes = {}
        self.startup_guards = {}
        self.started = False

    @staticmethod
    def _build_info():
        try:
            return json.loads((Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'build-info.json').read_text())
        except (OSError, ValueError):
            return {'version': '0', 'built_utc': ''}

    def status(self):
        with self.lock:
            return copy.deepcopy(self.state)

    def _set(self, **values):
        with self.lock:
            self.state.update(values)

    def start(self, manual=False):
        with self.lock:
            if self.state['busy'] or self.state['checking'] or (self.started and not manual):
                return self.status_unlocked()
            self.started = True
            self.state.update(checking=True, message='Checking official publishers in the background…')
        threading.Thread(target=self._check, daemon=True).start()
        return {'ok': True}

    def status_unlocked(self):
        return {'ok': False, 'message': 'A check or update is already active.'}

    def _load(self):
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            self.installed = json.loads((self.root / 'installed.json').read_text())
        except (OSError, ValueError):
            self.installed = {}
        if self.bundle_root:
            try:
                self.bundles = json.loads(Path(self.bundle_manifest).read_text(encoding='utf-8'))
                for key, bundle in self.bundles.items():
                    if key not in TOOLS:
                        continue
                    bundled_path = (self.bundle_root / key / bundle['exe']).resolve()
                    if not bundled_path.is_relative_to(self.bundle_root.resolve()) or not bundled_path.is_file():
                        continue
                    old = self.installed.get(key, {})
                    if (not old or old.get('bundle') or
                            not old.get('selected_previous') and version(bundle['version']) >= version(old['version'])):
                        self.installed[key] = dict(version=bundle['version'], bundle=True, folder=key, exe=bundle['exe'])
            except (OSError, ValueError, KeyError, TypeError):
                pass
        try:
            pending = json.loads((self.root / 'pending-app.json').read_text())
            path = (self.root / pending['folder']).resolve()
            if (pending['version'] > self.build.get('built_utc', '') and
                    path.is_relative_to(self.root.resolve()) and (path / 'TechLoungeTweaks.exe').is_file()):
                info = json.loads((path / '_internal/build-info.json').read_text())
                if newer_app(info, self.build):
                    self._set(ready=str(path))
        except (OSError, ValueError, KeyError, TypeError):
            pass

    def _check(self):
        items, offers = [], {}
        try:
            self._load()
            # Expose all installed launchers before the first network request.
            # Slow/offline publishers must not hold existing tools hostage.
            initial = [dict(id=k, name=t['name'], description=t['description'],
                            installed=self.installed.get(k, {}).get('version', t.get('baseline')),
                            launch=bool(self._tool_path(k)), action=None, message='Checking publisher…')
                       for k, t in TOOLS.items()] + [dict(OPENMOUSE)]
            self._set(items=copy.deepcopy(initial))
            for key, tool in TOOLS.items():
                old = self.installed.get(key, {})
                row = dict(id=key, name=tool['name'], description=tool['description'],
                           installed=old.get('version', tool.get('baseline')), available=None, action=None,
                           launch=bool(self._tool_path(key)), rollback=bool(old.get('previous')), message='')
                try:
                    data = release(tool['repo'])
                    tag = data['tag_name']
                    row['available'] = tag
                    if not row['installed'] or version(tag) > version(row['installed']) or (old and not row['launch']):
                        offers[key] = dict(asset_for(tool, data), version=tag)
                        row['action'] = 'Update' if row['installed'] else 'Repair'
                    row['message'] = ('Official stable release. Opens as a floating window above TechLoungeTweaks.' if key in ('dlss', 'bcu') else 'Official stable release used by the NVIDIA Profile page.')
                except Exception as exc:
                    row['message'] = 'Check unavailable: ' + str(exc)
                    row['check_error'] = True
                items.append(row)
                completed = {r['id'] for r in items}
                self._set(items=copy.deepcopy(items + [r for r in initial if r['id'] not in completed]))
            row = dict(id='app', name='TechLoungeTweaks', installed=self.build.get('version'), action=None, status='checking',
                       message='The full app update includes tested Windows integrations.')
            try:
                manifest = app_manifest(self.build)
                remote = manifest['built_utc']
                is_new = newer_app(manifest, self.build)
                row['available'] = manifest['version']
                row['status'] = 'ready' if self.status().get('ready') else 'available' if is_new else 'current'
                if is_new and not self.status().get('ready'):
                    sha = manifest['files']['TechLoungeTweaks/TechLoungeTweaks.zip']
                    url = manifest['download_url']
                    if not url.startswith('https://github.com/' + APP_REPO + '/releases/download/'):
                        raise ValueError('Unexpected app release download source.')
                    offers['app'] = dict(url=url, sha256=sha,
                                         version=remote, app_revision=manifest['app_revision'], name='TechLoungeTweaks.zip')
                    row['action'] = 'Update' if getattr(sys, 'frozen', False) else None
                    if not getattr(sys, 'frozen', False):
                        row['message'] = 'App replacement is available in the packaged app only.'
            except Exception as exc:
                row['message'] = 'App check unavailable: ' + str(exc)
                row.update(status='unavailable', check_error=True, available=None)
            items.append(row)
            for key, (name, repo, baseline) in REVIEWED.items():
                row = dict(id=key, name=name, installed=baseline or 'Bundled', action=None)
                try:
                    latest = release(repo)['tag_name']
                    row['available'] = latest
                    row['message'] = ('New upstream release; requires a tested TechLoungeTweaks release.'
                                      if baseline and version(latest) > version(baseline) else
                                      'Updated through tested TechLoungeTweaks releases.')
                    if baseline is None:
                        row['message'] = 'Latest publisher release shown; bundled version is not recorded. Updated with the app.'
                except Exception as exc:
                    row['message'] = 'Publisher check unavailable: ' + str(exc)
                items.append(row)
            items.append(dict(OPENMOUSE))
            with self.lock:
                self.offers = offers
                message = 'App update ready. Restart to apply when your work is finished.' if self.state.get('ready') else 'Checks finished. Downloads start only when you choose Install or Update.'
                self.state.update(items=items, checked=time.time(), message=message)
        except Exception as exc:
            self._set(message='Unable to check updates: ' + str(exc))
        finally:
            self._set(checking=False)

    def apply(self, key):
        with self.lock:
            if self.state['busy'] or self.state['checking'] or key not in self.offers:
                return {'ok': False, 'message': 'Wait for checks to finish, then choose an available update.'}
            self.state.update(busy=True, active=key, progress=None, message='Preparing download…')
            offer = copy.deepcopy(self.offers[key])
            self.cancel.clear()
        threading.Thread(target=self._install, args=(key, offer), daemon=True).start()
        return {'ok': True}

    def _progress(self, message, fraction=None):
        self._set(message=message, progress=fraction)

    def _install(self, key, offer):
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='stage-', dir=self.root) as temporary:
                stage = Path(temporary)
                archive = stage / ('download.7z' if offer['name'].endswith('.7z') else 'download.zip')
                download(offer, archive, self._progress, self.cancel)
                if self.cancel.is_set():
                    raise InterruptedError('Update cancelled.')
                self._progress('Verifying and unpacking…')
                unpacked = stage / 'payload'
                extract(archive, unpacked)
                if self.cancel.is_set():
                    raise InterruptedError('Update cancelled.')
                if key == 'app':
                    payload = unpacked / 'TechLoungeTweaks'
                    for required in ('TechLoungeTweaks.exe', '_internal/build-info.json', 'resources/TechLoungeProfile.nip'):
                        if not (payload / required).is_file():
                            raise ValueError('App package is incomplete; current app unchanged.')
                    info = json.loads((payload / '_internal/build-info.json').read_text())
                    if info['built_utc'] != offer['version']:
                        raise ValueError('App package and release metadata do not match. Check again later.')
                    if info.get('app_revision') != offer['app_revision']:
                        raise ValueError('App content identity does not match the release. Check again later.')
                    if not newer_app(info, self.build):
                        raise ValueError('App package is not a newer release in this channel.')
                    target = self.root / ('app-' + uuid.uuid4().hex)
                    shutil.move(str(payload), target)
                    atomic_json(self.root / 'pending-app.json', dict(folder=target.name, version=offer['version']))
                    self._set(ready=str(target), message='App update ready. Restart to apply when your work is finished.')
                else:
                    exe = [p for p in unpacked.rglob('*.exe') if p.name.lower() == TOOLS[key]['exe'].lower()]
                    if len(exe) > 1:
                        # Multi-architecture releases ship an official root
                        # launcher which selects the correct native binary.
                        root_exe = unpacked / TOOLS[key]['exe']
                        exe = [root_exe] if root_exe.is_file() else exe
                    if len(exe) != 1:
                        raise ValueError('Expected tool executable not found; publisher packaging may have changed.')
                    relative = exe[0].relative_to(unpacked)
                    target = self.root / (key + '-' + uuid.uuid4().hex)
                    shutil.move(str(unpacked), target)
                    old = self.installed.get(key)
                    record = dict(version=offer['version'], folder=target.name, exe=str(relative))
                    if old:
                        record['previous'] = {k: v for k, v in old.items() if k != 'previous'}
                    new = dict(self.installed, **{key: record})
                    atomic_json(self.root / 'installed.json', new)
                    self.installed = new
                    self._set(message=TOOLS[key]['name'] + ' is ready. Open it when you are ready; previous files were kept.')
                with self.lock:
                    self.offers.pop(key, None)
                    for row in self.state['items']:
                        if row['id'] == key:
                            row.update(action=None, installed=offer['version'], launch=key != 'app')
                            if key == 'app':
                                row.update(installed=self.build.get('version'), status='ready')
                            else:
                                row['rollback'] = bool(self.installed[key].get('previous'))
        except Exception as exc:
            self._set(message=str(exc))
        finally:
            self._set(busy=False, active=None, progress=None)

    def _tool_path(self, key):
        entry = self.installed.get(key)
        if not entry:
            return None
        base = self.bundle_root if entry.get('bundle') else self.root
        if not base:
            return None
        path = (base / entry['folder'] / entry['exe']).resolve()
        if not path.is_relative_to(base.resolve()) or not path.is_file():
            return None
        return path

    def launch(self, key):
        if key not in TOOLS:
            return {'ok': False, 'message': 'Unknown tool.'}
        path = self._tool_path(key)
        if not path:
            return {'ok': False, 'message': 'Install this tool first.'}
        process = self.processes.get(key)
        if process and process.poll() is None:
            return {'ok': True, 'pid': process.pid, 'folder': str(path.parent)}
        if key == 'bcu':
            prepare_bcu_settings(path,self.installed[key]['version'])
        if key == 'nvpi':
            from nvpi_settings import prepare_window
            prepare_window(path)
        options = {}
        guard = None
        if os.name == 'nt':
            from tool_startup import StartupGuard
            guard = StartupGuard(key)
            startup = subprocess.STARTUPINFO()
            startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 0  # Reveal only after the integrated surface is ready.
            options['startupinfo'] = startup
            options['creationflags'] = 0x00000004  # CREATE_SUSPENDED; guard is armed first.
        try:
            self.processes[key] = subprocess.Popen([str(path)], cwd=path.parent, **options)
            if guard:
                import ctypes
                from ctypes import wintypes
                guard.pid = self.processes[key].pid
                resume = ctypes.WinDLL('ntdll').NtResumeProcess
                resume.argtypes = [wintypes.HANDLE]; resume.restype = wintypes.LONG
                if resume(int(self.processes[key]._handle)) != 0:
                    self.processes[key].terminate()
                    raise RuntimeError('Could not start the integrated tool.')
                self.startup_guards[key] = guard
        except Exception:
            if guard: guard.close()
            raise
        return {'ok': True, 'pid': self.processes[key].pid, 'folder': str(path.parent)}

    def rollback(self, key):
        with self.lock:
            if self.state['busy'] or self.state['checking']:
                return {'ok': False, 'message': 'Wait for the current operation to finish.'}
            old = self.installed.get(key, {}).get('previous')
            if not old:
                return {'ok': False, 'message': 'No previous managed version is available.'}
            if old.get('bundle') and self.bundles.get(key, {}).get('version') != old['version']:
                return {'ok': False, 'message': 'That previous bundled version is no longer available.'}
            current = self.installed[key]
            new = dict(self.installed, **{key: dict(old, selected_previous=True, previous={k:v for k,v in current.items() if k != 'previous'})})
            atomic_json(self.root / 'installed.json', new)
            self.installed = new
        return self.start(manual=True)

    def restart(self):
        ready = self.status().get('ready')
        if not ready or not getattr(sys, 'frozen', False):
            return {'ok': False, 'message': 'No app update is ready.'}
        try:
            path = Path(ready).resolve()
            info = json.loads((path / '_internal/build-info.json').read_text())
            if not path.is_relative_to(self.root.resolve()) or not newer_app(info, self.build):
                raise ValueError('Update is not a newer release in this channel.')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return {'ok': False, 'message': 'App update rejected: ' + str(exc)}
        # Run the helper outside the app folder so none of its files are held open.
        helper = self.root / ('apply-' + uuid.uuid4().hex + '.ps1')
        shutil.copyfile(Path(sys._MEIPASS) / 'apply-update.ps1', helper)
        subprocess.Popen(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(helper),
                          '-AppProcess', str(os.getpid()), '-Source', ready,
                          '-Destination', str(getattr(sys, '_tl_app_root', Path(sys.executable).parent))],
                         creationflags=0x08000000, cwd=self.root)
        return {'ok': True}


def open_mouse():
    # WebHID needs the normal browser device permission picker. The elevated
    # local pywebview bridge must never be exposed to remote page scripts.
    import webbrowser
    if not webbrowser.open('https://control.openmouse.app/'):
        return {'ok': False, 'message': 'Could not open the default browser. Open https://control.openmouse.app/ manually.'}
    return {'ok': True}


def managed_inspector():
    """Resolve only our installed Inspector, without network access."""
    manager = UpdateManager()
    try:
        manager._load()
        return manager._tool_path('nvpi')
    except (OSError, ValueError, KeyError, TypeError):
        return None
