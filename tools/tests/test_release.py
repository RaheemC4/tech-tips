import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('release', Path(__file__).resolve().parents[1] / 'release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_hashes_tolerate_text_newlines_but_preserve_cmd_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'file.py'
            path.write_bytes(b'line\n')
            expected = release.digest(path)
            path.write_bytes(b'line\r\n')
            self.assertEqual(expected, release.digest(path))
            cmd = path.with_suffix('.cmd')
            cmd.write_bytes(b'line\r\n')
            self.assertNotEqual(expected, release.digest(cmd))

    def test_publish_list_excludes_builds_logs_and_scratch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative in ['src/main.py', 'src/build/junk.exe', 'src/__pycache__/junk.pyc',
                             'src/dist/app.exe', 'docs/_to_delete/old.png', 'docs/new.png',
                             '.build-venv/private.txt', 'src/TL-api.log']:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('test')
            self.assertEqual({p.relative_to(root).as_posix() for p in release.files(root)},
                             {'src/main.py', 'docs/new.png'})

    def test_doc_review_detects_changes_and_missing_review(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(release, 'doc_inputs', return_value={'src': 'a'}) as inputs:
            with patch.object(release, 'REVIEW', Path(temp) / 'review.json'):
                with self.assertRaises(RuntimeError):
                    release.check_review()
                release.record_review()
                release.check_review()
                inputs.return_value = {'src': 'b'}
                with self.assertRaises(RuntimeError):
                    release.check_review()

    def test_release_verification_rejects_changed_or_added_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / 'app.zip'
            manifest = root / 'release.json'
            readme = root / 'README.md'
            readme.write_text('Reviewed content')
            with zipfile.ZipFile(archive, 'w') as z:
                for name in ['TechLoungeTweaks/TechLoungeTweaks.exe',
                             'TechLoungeTweaks/_internal/vendor/mas/LICENSE',
                             'TechLoungeTweaks/resources/TechLoungeProfile.nip']:
                    z.writestr(name, 'test')
            manifest.write_text(json.dumps({'files': {p.name: release.digest(p) for p in [archive, readme]}}))
            with patch.multiple(release, ROOT=root, MANIFEST=manifest, ARCHIVE=archive), \
                 patch.object(release, 'check_review'), \
                 patch.object(release, 'publish_files', return_value=[archive, readme, manifest]) as listing:
                release.verify_release()
                listing.return_value.append(root / 'new.py')
                with self.assertRaises(RuntimeError):
                    release.verify_release()
                listing.return_value.pop()
                readme.write_text('Unreviewed content')
                with self.assertRaises(RuntimeError):
                    release.verify_release()

    def test_resource_extraction_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'upload'
            app = root / 'TechLoungeTweaks'
            app.mkdir(parents=True)
            archive = app / 'old.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('TechLoungeTweaks/resources/../../escape.txt', 'bad')
            with patch.multiple(release, ROOT=root, APP=app, ARCHIVE=archive):
                with self.assertRaises(RuntimeError):
                    release.copy_resources(root / 'output')
            self.assertFalse((root / 'escape.txt').exists())

    def test_push_to_local_bare_repo_preserves_unrelated_files(self):
        with tempfile.TemporaryDirectory(prefix='TL local publish ') as temp:
            base = Path(temp)
            root = base / 'upload'
            app = root / 'TechLoungeTweaks'
            (app / 'docs').mkdir(parents=True)
            names = ['AGENTS.md', 'README.md', 'RELEASE-NOTES.md', 'HOW-TO-UPLOAD.txt', 'PUSH-TO-GITHUB.bat',
                     'PREPARE-RELEASE.bat', '.gitignore', '.gitattributes', 'tools/release.py',
                     'TechLoungeTweaks/src/main.py', 'TechLoungeTweaks/docs/new.png']
            for name in names:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('Current release\n')
            seed = base / 'seed'
            remote = base / 'test.git'
            def git(*args, cwd=None):
                return subprocess.run(['git', *map(str, args)], cwd=cwd, check=True,
                                      capture_output=True, text=True).stdout
            git('init', '--bare', remote)
            git('init', '-b', 'main', seed)
            git('config', 'user.name', 'Release Test', cwd=seed)
            git('config', 'user.email', 'release-test@example.invalid', cwd=seed)
            (seed / 'unrelated.txt').write_text('keep')
            (seed / 'TechLoungeTweaks').mkdir()
            (seed / 'TechLoungeTweaks/old.txt').write_text('old')
            git('add', '.', cwd=seed)
            git('commit', '-m', 'seed', cwd=seed)
            git('remote', 'add', 'origin', remote, cwd=seed)
            git('push', 'origin', 'main', cwd=seed)
            with patch.multiple(release, ROOT=root, APP=app), \
                 patch.object(release, 'verify_release'), \
                 patch.object(release, 'publish_files', return_value=[root / n for n in names]):
                release.push(str(remote))
                # Repeating a prepared push should be a no-op, not an empty commit.
                first = git('--git-dir', remote, 'rev-parse', 'main')
                release.push(str(remote))
                self.assertEqual(first, git('--git-dir', remote, 'rev-parse', 'main'))
            tracked = git('--git-dir', remote, 'ls-tree', '-r', '--name-only', 'main').splitlines()
            self.assertIn('unrelated.txt', tracked)
            self.assertIn('TechLoungeTweaks/src/main.py', tracked)
            self.assertIn('docs/new.png', tracked)
            self.assertNotIn('TechLoungeTweaks/old.txt', tracked)


if __name__ == '__main__':
    unittest.main()
