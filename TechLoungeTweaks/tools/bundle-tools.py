"""Refresh official portable tools before reviewing and preparing a release."""
import base64
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP / 'src'))
sys.path.insert(0, str(APP.parent / 'tools'))
import updates
import release
import defender_remover


def bundle_remover():
    target = APP / 'resources/defender-remover'
    target.mkdir(parents=True, exist_ok=True)
    name = 'Defender.Remover.13.exe'
    url = 'https://github.com/ionuttbara/windows-defender-remover/releases/download/' + defender_remover.VERSION + '/' + name
    updates.download(dict(url=url,sha256=defender_remover.SHA256),target/name,lambda *args: None,threading.Event())
    data = updates.get_json('https://api.github.com/repos/ionuttbara/windows-defender-remover/license?ref=' + defender_remover.VERSION)
    (target/'LICENSE').write_bytes(base64.b64decode(data['content']))
    (target/'UPSTREAM.json').write_text(json.dumps(dict(version=defender_remover.VERSION,sha256=defender_remover.SHA256,
        source='https://github.com/ionuttbara/windows-defender-remover/tree/' + defender_remover.VERSION,
        download=url),indent=2),encoding='utf-8')
    print('Bundled reviewed Defender Remover; never executed.',flush=True)


def bundle():
    if not (APP / 'resources').exists():
        release.copy_resources(APP)
    resources = APP / 'resources/tools'
    resources.mkdir(parents=True, exist_ok=True)
    manifest_path = APP / 'src/bundled-tools.json'
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        manifest = {}
    for key, tool in updates.TOOLS.items():
        if tool.get('local'):
            print(f'{tool["name"]}: keeping the supplied personal bundle.', flush=True)
            continue
        data = updates.release(tool['repo'])
        asset = updates.asset_for(tool, data)
        previous = manifest.get(key, {})
        target = resources / key
        if (previous.get('sha256') == asset['sha256'] and
                (target / previous.get('exe', 'missing')).is_file()):
            print(f'{tool["name"]}: {data["tag_name"]} already bundled.', flush=True)
            continue
        with tempfile.TemporaryDirectory(prefix='tl-bundle-') as temporary:
            stage = Path(temporary)
            archive = stage / ('tool.7z' if asset['name'].endswith('.7z') else 'tool.zip')
            updates.download(asset, archive, lambda *args: None, threading.Event())
            payload = stage / 'payload'
            updates.extract(archive, payload)
            executables = [p for p in payload.rglob('*.exe') if p.name.lower() == tool['exe'].lower()]
            if (payload / tool['exe']).is_file():
                executables = [payload / tool['exe']]
            if len(executables) != 1:
                raise RuntimeError(f'{tool["name"]}: expected executable not found.')
            relative = executables[0].relative_to(payload).as_posix()
            license_data = updates.get_json('https://api.github.com/repos/' + tool['repo'] + '/license?ref=' + data['tag_name'])
            (payload / 'UPSTREAM-LICENSE.txt').write_bytes(base64.b64decode(license_data['content']))
            record = dict(version=data['tag_name'], exe=relative, repo=tool['repo'], **asset)
            (payload / 'UPSTREAM.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
            if target.exists():
                if not target.resolve().is_relative_to(resources.resolve()):
                    raise RuntimeError('Unexpected bundle destination.')
                shutil.move(str(target), stage / 'previous')
            try:
                shutil.move(str(payload), target)
            except Exception:
                if (stage / 'previous').exists():
                    shutil.move(str(stage / 'previous'), target)
                raise
            manifest[key] = record
            updates.atomic_json(manifest_path, manifest)
            print(f'{tool["name"]}: bundled {data["tag_name"]}, verified SHA-256 and included licence.', flush=True)


if __name__ == '__main__':
    bundle()
    bundle_remover()
