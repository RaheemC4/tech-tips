"""Publish a prepared Nuitka prerelease without moving the stable channel."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.parse
import zipfile

from publish_asset import token, request, REPO
from release import check_review

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'TechLoungeTweaks'


def publish():
    check_review()
    metadata = APP / 'nuitka-update.json'
    manifest = json.loads(metadata.read_text())
    archive = APP / 'TechLoungeTweaks-Nuitka.zip'
    expected = hashlib.sha256(archive.read_bytes()).hexdigest()
    if manifest.get('channel') != 'nuitka' or manifest['files']['TechLoungeTweaks/TechLoungeTweaks.zip'] != expected:
        raise RuntimeError('Nuitka package identity/checksum mismatch.')
    with zipfile.ZipFile(archive) as z:
        identity = json.loads(z.read('TechLoungeTweaks/_internal/build-info.json'))
        if z.testzip() or any(identity.get(k) != manifest.get(k) for k in ('channel','app_revision','built_utc')):
            raise RuntimeError('Nuitka package does not match its manifest.')
    current = json.loads((APP / 'src/build-info.json').read_text())
    if identity['app_revision'] != current['app_revision']:
        raise RuntimeError('Rebuild the candidate from the reviewed sources.')
    auth = token(ROOT)
    base = '/repos/' + REPO + '/releases'
    latest = request(auth, 'GET', base + '/latest')
    tag = manifest['release_tag']
    body = '''Nuitka test build with a clean portable folder and dedicated app update channel.

Download TechLoungeTweaks-Nuitka.zip, extract the whole folder, and open TechLoungeTweaks.exe. Existing users of the first Nuitka candidate need this manual download once to acquire the channel fix.

The top level now contains only TechLoungeTweaks.exe, _internal and resources. The small launcher opens the compiled backend inside _internal. This Intel/AMD x64 package omits BCU's separate ARM64 payload (about 211 MiB), while retaining its full x64 runtime and keeping the other bundled tools available offline.

App updates now discover only explicitly marked Nuitka releases. Packages from the standard channel are rejected during staging and again before replacement. Pending updates use a separate cache. Missing/offline Nuitka releases never trigger a fallback to the standard package. Bundled tools continue using their official publisher updates.

No intentional feature removals. Python installation is not required; administrator access and WebView2 are still required. Fresh-Windows Defender/SmartScreen acceptance remains unverified. This unsigned prerelease does not replace the stable download.

The tag anchors the existing main branch; this is a locally prepared packaging candidate.
'''
    release = request(auth, 'GET', base + '/tags/' + urllib.parse.quote(tag, safe=''))
    if not release:
        commit = request(auth, 'GET', '/repos/' + REPO + '/branches/main')['commit']['sha']
        release = request(auth, 'POST', base, dict(tag_name=tag, target_commitish=commit,
            name='TechLoungeTweaks - smaller Nuitka build with channel updates', body=body,
            draft=True, prerelease=True, make_latest='false'))
    assets = request(auth, 'GET', base + f'/{release["id"]}/assets') or []
    for file in (archive, metadata):
        digest = 'sha256:' + hashlib.sha256(file.read_bytes()).hexdigest()
        existing = next((a for a in assets if a['name'] == file.name), None)
        if existing:
            if existing.get('digest') != digest:
                raise RuntimeError('Existing release asset differs; it was not replaced.')
        else:
            print('Uploading ' + file.name, flush=True)
            asset = request(auth, 'POST', base + f'/{release["id"]}/assets?name=' + urllib.parse.quote(file.name), archive=file)
            if asset.get('digest') != digest:
                raise RuntimeError('Upload checksum mismatch; release remains a draft.')
    if release['draft']:
        release = request(auth, 'PATCH', base + f'/{release["id"]}', dict(draft=False, prerelease=True, make_latest='false'))
    after = request(auth, 'GET', base + '/latest')
    if latest and after['id'] != latest['id']:
        raise RuntimeError('Stable latest release changed unexpectedly.')
    print(release['html_url'])
    print(manifest['download_url'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', required=True, action='store_true')
    parser.parse_args()
    publish()
