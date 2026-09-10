"""Publish the large app ZIP as a release asset, only from an explicit push."""
import http.client
import json
import os
import subprocess
import urllib.parse

REPO = 'RaheemC4/tech-tips'


def token(repo):
    value = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if value:
        return value
    result = subprocess.run(['git', 'credential', 'fill'], cwd=repo,
                            input='protocol=https\nhost=github.com\n\n',
                            capture_output=True, text=True, timeout=120)
    fields = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if result.returncode or not fields.get('password'):
        raise RuntimeError('GitHub release authentication is unavailable. Sign into Git Credential Manager or set GH_TOKEN with repository Contents write access.')
    return fields['password']


def request(auth, method, path, payload=None, archive=None):
    host = 'uploads.github.com' if archive else 'api.github.com'
    headers = {'Authorization': 'Bearer ' + auth, 'User-Agent': 'TechLoungeTweaks-Release',
               'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2026-03-10'}
    body = json.dumps(payload).encode() if payload is not None else b''
    headers['Content-Type'] = 'application/zip' if archive else 'application/json'
    headers['Content-Length'] = str(archive.stat().st_size if archive else len(body))
    connection = http.client.HTTPSConnection(host, timeout=300)
    try:
        connection.putrequest(method, path)
        for key, value in headers.items():
            connection.putheader(key, value)
        connection.endheaders()
        if archive:
            with archive.open('rb') as stream:
                while chunk := stream.read(1024 * 1024):
                    connection.send(chunk)
        elif body:
            connection.send(body)
        response = connection.getresponse()
        data = response.read()
        if response.status == 404 and method == 'GET':
            return None
        if response.status >= 300:
            raise RuntimeError(f'GitHub release request failed (HTTP {response.status}). The source push may have succeeded; rerun PUSH-TO-GITHUB.bat to retry the release upload.')
        return json.loads(data) if data else None
    finally:
        connection.close()


def publish(repo, manifest, archive):
    auth = token(repo)
    tag = manifest['release_tag']
    base = '/repos/' + REPO + '/releases'
    release = request(auth, 'GET', base + '/tags/' + urllib.parse.quote(tag, safe=''))
    if not release:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
        release = request(auth, 'POST', base, dict(tag_name=tag, target_commitish=commit,
            name='TechLoungeTweaks ' + manifest['version'], body=manifest['notes'], draft=True, prerelease=False))
    expected = 'sha256:' + manifest['files']['TechLoungeTweaks/TechLoungeTweaks.zip']
    assets = request(auth, 'GET', base + f'/{release["id"]}/assets') or []
    existing = next((a for a in assets if a['name'] == archive.name), None)
    if existing and release.get('draft') and existing.get('state') == 'starter':
        # An interrupted GitHub upload can leave an empty draft placeholder.
        # Remove only that incomplete placeholder; never replace published data.
        request(auth, 'DELETE', base + '/assets/' + str(existing['id']))
        existing = None
    if existing and existing.get('digest') != expected:
        raise RuntimeError('An asset with a different checksum already exists for this release. It was not replaced.')
    if not existing:
        print('Uploading bundled app ZIP to GitHub Releases…', flush=True)
        asset = request(auth, 'POST', base + f'/{release["id"]}/assets?name=' + urllib.parse.quote(archive.name), archive=archive)
        if asset.get('digest') != expected:
            raise RuntimeError('GitHub did not confirm the uploaded ZIP checksum. The release remains a draft.')
    if release.get('draft'):
        request(auth, 'PATCH', base + f'/{release["id"]}', dict(draft=False, make_latest='true'))
    print('Release ZIP published and checksum verified.')
