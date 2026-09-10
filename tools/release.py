"""Build, document, package and optionally publish a personal Windows release."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'TechLoungeTweaks'
REMOTE = 'https://github.com/RaheemC4/tech-tips.git'
SKIP = {'build', 'dist', '__pycache__', '_to_delete', 'node_modules', '.build-venv', '.venv'}
REVIEW = APP / 'docs-review.json'
MANIFEST = APP / 'release.json'
ARCHIVE = APP / 'TechLoungeTweaks.zip'


def run(args, cwd=None, env=None):
    print('>', subprocess.list2cmdline([str(a) for a in args]), flush=True)
    subprocess.run([str(a) for a in args], cwd=cwd or ROOT, env=env, check=True)


def digest(path):
    data = path.read_bytes()
    if path.suffix.lower() in {'.py', '.js', '.html', '.css', '.md', '.json', '.txt', '.ps1', '.bat', '.spec'} or path.name in {'.gitignore', '.gitattributes', 'LICENSE'}:
        # Git may change text line endings on another development PC. Content
        # review stays valid, while ZIP and upstream CMD hashes remain exact.
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


def files(folder):
    return sorted(p for p in folder.rglob('*') if p.is_file()
                  and not (set(p.relative_to(folder).parts) & SKIP)
                  and p.suffix not in {'.pyc', '.log', '.tmp'})


def doc_inputs():
    paths = files(APP / 'src') + files(APP / 'tools') + files(APP / 'tests')
    paths += [APP / 'README.md', ROOT / 'RELEASE-NOTES.md']
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}


def record_review():
    REVIEW.write_text(json.dumps({'reviewed_utc': datetime.now(timezone.utc).isoformat(),
                                  'inputs': doc_inputs()}, indent=2) + '\n', encoding='utf-8')
    print('Recorded documentation review for the current source and README.')


def check_review():
    if not REVIEW.exists() or json.loads(REVIEW.read_text(encoding='utf-8')).get('inputs') != doc_inputs():
        raise RuntimeError('Source/docs changed since documentation review. Review README.md and '
                           'RELEASE-NOTES.md, update as needed, then run --record-doc-review. '
                           'A batch file cannot semantically review documentation.')


def browser_env():
    env = os.environ.copy()
    bundle = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies'
    node = env.get('NODE') or shutil.which('node')
    if not node and (bundle / 'node/bin/node.exe').exists():
        node = str(bundle / 'node/bin/node.exe')
    if not node:
        raise RuntimeError('Node.js not found. Install it or set NODE to node.exe.')
    if not env.get('PW'):
        candidates = [APP / 'node_modules/playwright', bundle / 'node/node_modules/playwright']
        env['PW'] = str(next((p for p in candidates if p.exists()), 'playwright'))
    if not env.get('CHROME'):
        candidates = [Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) /
                      'Microsoft/Edge/Application/msedge.exe',
                      Path(os.environ.get('ProgramFiles', 'C:/Program Files')) /
                      'Google/Chrome/Application/chrome.exe']
        browser = next((p for p in candidates if p.exists()), None)
        if not browser:
            raise RuntimeError('Edge/Chrome not found. Set CHROME to its executable.')
        env['CHROME'] = str(browser)
    return node, env


def copy_resources(destination):
    sources = [APP / 'resources', ROOT.parent / 'TechLoungeTweaks/resources']
    source = next((p for p in sources if p.is_dir()), None)
    if source:
        shutil.copytree(source, destination / 'resources', dirs_exist_ok=True)
    elif ARCHIVE.exists():
        with zipfile.ZipFile(ARCHIVE) as archive:
            prefix = 'TechLoungeTweaks/resources/'
            for entry in archive.infolist():
                if entry.is_dir() or not entry.filename.startswith(prefix):
                    continue
                relative = Path(entry.filename[len(prefix):])
                if relative.is_absolute() or '..' in relative.parts or ':' in str(relative):
                    raise RuntimeError('Invalid resource path in existing ZIP.')
                target = destination / 'resources' / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(entry))
    if not (destination / 'resources/TechLoungeProfile.nip').exists():
        raise RuntimeError('NVIDIA resources missing. Keep the previous ZIP or provide App/resources.')


def publish_files():
    paths = []
    for folder in ('src', 'tools', 'tests', 'docs'):
        paths += files(APP / folder)
    paths += [APP / name for name in ('README.md', 'TechLoungeTweaks.zip', 'docs-review.json', 'release.json', 'requirements-build.txt')]
    paths += [ROOT / name for name in ('AGENTS.md', 'README.md', 'RELEASE-NOTES.md', 'HOW-TO-UPLOAD.txt',
                                      'PUSH-TO-GITHUB.bat', 'PREPARE-RELEASE.bat', '.gitignore', '.gitattributes')]
    paths += files(ROOT / 'tools')
    return paths


def verify_release():
    check_review()
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for relative, expected in manifest['files'].items():
        path = ROOT / relative
        if not path.is_file() or digest(path) != expected:
            raise RuntimeError(f'Release file changed: {relative}. Run --prepare again.')
    paths = {p.relative_to(ROOT).as_posix() for p in publish_files() if p != MANIFEST}
    if paths != set(manifest['files']):
        raise RuntimeError('Release file list changed. Run --prepare again.')
    with zipfile.ZipFile(ARCHIVE) as archive:
        if archive.testzip():
            raise RuntimeError('ZIP integrity check failed.')
        for name in ['TechLoungeTweaks/TechLoungeTweaks.exe',
                     'TechLoungeTweaks/_internal/vendor/mas/LICENSE',
                     'TechLoungeTweaks/resources/TechLoungeProfile.nip']:
            if name not in archive.namelist():
                raise RuntimeError(f'ZIP is missing {name}')
    print('Release hashes and ZIP integrity verified.')


def prepare():
    check_review()
    node, env = browser_env()
    run([sys.executable, '-m', 'unittest', 'discover', '-s', APP / 'tests', '-v'])
    run([sys.executable, '-m', 'unittest', 'discover', '-s', ROOT / 'tools/tests', '-v'])
    run([node, '--check', APP / 'src/web/app.js'])
    run([node, APP / 'tools/test-windows-setup-ui.js'], env=env)
    run([node, APP / 'tools/make-screenshots.js'], env=env)
    readme = APP / 'README.md'
    for relative in re.findall(r'!\[[^\]]*\]\((docs/[^)]+)\)', readme.read_text(encoding='utf-8')):
        if not (APP / relative).is_file():
            raise RuntimeError(f'README screenshot missing: {relative}')
    shutil.copy2(readme, ROOT / 'README.md')
    run([sys.executable, '-m', 'PyInstaller', '--noconfirm', 'TechLoungeTweaks.spec'], APP / 'src')
    built = APP / 'src/dist/TechLoungeTweaks'
    copy_resources(built)
    temporary = ARCHIVE.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files(built):
            archive.write(path, 'TechLoungeTweaks/' + path.relative_to(built).as_posix())
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip():
            raise RuntimeError('New ZIP failed validation; previous archive retained.')
    os.replace(temporary, ARCHIVE)
    manifest = {'built_utc': datetime.now(timezone.utc).isoformat(),
                'notes': (ROOT / 'RELEASE-NOTES.md').read_text(encoding='utf-8').strip(),
                'files': {p.relative_to(ROOT).as_posix(): digest(p)
                          for p in publish_files() if p != MANIFEST}}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    verify_release()
    if (ROOT.parent / 'TechLoungeTweaks').is_dir():
        shutil.copy2(ARCHIVE, ROOT.parent / 'TechLoungeTweaks-Personal.zip')
    print(f'READY: {ARCHIVE}\nExtract the whole folder on each personal PC.')


def push(remote=REMOTE):
    verify_release()
    workspace = Path(tempfile.mkdtemp(prefix='tech-lounge-publish-'))
    repo = workspace / 'repo'
    print(f'Publishing checkout: {repo}')
    run(['git', 'clone', '--branch', 'main', '--single-branch', remote, repo])
    run(['git', 'rm', '-r', '--ignore-unmatch', '--', 'TechLoungeTweaks', 'docs'], repo)
    for source in publish_files():
        target = repo / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for source in files(APP / 'docs'):
        target = repo / 'docs' / source.relative_to(APP / 'docs')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    run(['git', 'add', '--', 'TechLoungeTweaks', 'docs', 'AGENTS.md', 'README.md', 'RELEASE-NOTES.md',
         'HOW-TO-UPLOAD.txt', 'PUSH-TO-GITHUB.bat', 'PREPARE-RELEASE.bat', '.gitignore', '.gitattributes', 'tools'], repo)
    diff = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=repo)
    if diff.returncode == 0:
        print('Repository already matches this release. Nothing to push.')
        return
    if diff.returncode != 1:
        raise RuntimeError('Could not inspect staged changes.')
    for key, fallback in [('user.name', 'RaheemC4'), ('user.email', 'raheem@choudhurymail.com')]:
        existing = subprocess.run(['git', 'config', '--get', key], cwd=repo, capture_output=True)
        if existing.returncode:
            run(['git', 'config', key, fallback], repo)
    body = workspace / 'commit-message.txt'
    body.write_text('Tech Lounge Tweaks update ' + datetime.now().strftime('%Y-%m-%d') +
                    '\n\n' + (ROOT / 'RELEASE-NOTES.md').read_text(encoding='utf-8'), encoding='utf-8')
    run(['git', 'commit', '--file', body], repo)
    run(['git', 'push', 'origin', 'HEAD:main'], repo)
    print('Push completed successfully.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    for name in ('record-doc-review', 'prepare', 'push', 'verify', 'push-prepared'):
        modes.add_argument('--' + name, action='store_true')
    parser.add_argument('--remote', default=REMOTE, help='Override Git destination, including a local test repo.')
    args = parser.parse_args()
    try:
        if args.record_doc_review:
            record_review()
        elif args.verify:
            verify_release()
        else:
            if not args.push_prepared:
                prepare()
            if args.push or args.push_prepared:
                push(args.remote)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'RELEASE FAILED: {exc}', file=sys.stderr)
        sys.exit(1)
