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
    def test_x64_resource_trim_preserves_supported_tool_and_licence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bcu = root / 'resources/tools/bcu'
            for name in ('win-x64/BCUninstaller.exe', 'win-x64/runtime.dll', 'win-arm64/runtime.dll', 'Licence.txt'):
                path = bcu / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(name.encode())
            release.trim_x64_resources(root)
            self.assertFalse((bcu / 'win-arm64').exists())
            for name in ('win-x64/BCUninstaller.exe', 'win-x64/runtime.dll', 'Licence.txt'):
                self.assertEqual((bcu / name).read_bytes(), name.encode())

    def test_resource_trim_rejects_missing_x64_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            other = Path(temp) / 'resources/tools/bcu/win-arm64'
            other.mkdir(parents=True)
            with self.assertRaises(RuntimeError): release.trim_x64_resources(temp)
            self.assertTrue(other.exists())

    def test_push_reuses_only_verified_release(self):
        with patch.object(release,'verify_release') as verify, patch.object(release,'prepare') as prepare:
            release.prepare_for_push()
            verify.assert_called_once()
            prepare.assert_not_called()

    def test_push_rebuilds_changed_release_and_propagates_failures(self):
        with patch.object(release,'verify_release',side_effect=RuntimeError('changed')), patch.object(release,'prepare') as prepare:
            release.prepare_for_push()
            prepare.assert_called_once()
        with patch.object(release,'verify_release',side_effect=RuntimeError('changed')), patch.object(release,'prepare',side_effect=RuntimeError('test failed')):
            with self.assertRaisesRegex(RuntimeError,'test failed'):
                release.prepare_for_push()

    def test_archive_retries_temporary_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            old, new = Path(temp) / 'app.zip', Path(temp) / 'app.zip.tmp'
            old.write_bytes(b'old'); new.write_bytes(b'new')
            replace = release.os.replace
            with patch.object(release.os, 'replace', side_effect=[PermissionError('locked'), None]) as mocked, patch.object(release.time, 'sleep'):
                # Delegate the second attempt so the test checks actual bytes.
                count = 0
                def action(src, dst):
                    nonlocal count
                    count += 1
                    if count == 1: raise PermissionError('locked')
                    return replace(src, dst)
                mocked.side_effect = action
                release.replace_archive(new, old)
            self.assertEqual(old.read_bytes(), b'new')

    def test_archive_cloud_fallback_and_rollback(self):
        for fail_install in (False, True):
            with self.subTest(fail_install=fail_install), tempfile.TemporaryDirectory() as temp:
                old, new = Path(temp) / 'app.zip', Path(temp) / 'app.zip.tmp'
                old.write_bytes(b'old'); new.write_bytes(b'new')
                replace = release.os.replace
                def cloud_replace(src, dst):
                    if src == new and (dst.exists() or fail_install):
                        raise PermissionError('cloud replacement blocked')
                    return replace(src, dst)
                with patch.object(release.os, 'replace', side_effect=cloud_replace), patch.object(release.time, 'sleep'):
                    if fail_install:
                        with self.assertRaises(RuntimeError): release.replace_archive(new, old)
                        self.assertEqual(old.read_bytes(), b'old')
                        self.assertEqual(new.read_bytes(), b'new')
                    else:
                        release.replace_archive(new, old)
                        self.assertEqual(old.read_bytes(), b'new')

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

    def test_same_app_review_keeps_version_and_content_changes_advance_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);app=root/'App';(app/'src').mkdir(parents=True)
            (app/'src/main.py').write_text('print(1)')
            (app/'requirements-build.txt').write_text('test')
            with patch.multiple(release,ROOT=root,APP=app,ARCHIVE=app/'app.zip',REVIEW=app/'review.json'), patch.object(release,'doc_inputs',return_value={}):
                release.record_review(update_build=True)
                before=(app/'src/build-info.json').read_bytes()
                release.record_review(update_build=True)
                self.assertEqual(before,(app/'src/build-info.json').read_bytes())
                (app/'src/main.py').write_text('print(2)')
                release.record_review(update_build=True)
                self.assertNotEqual(before,(app/'src/build-info.json').read_bytes())

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
                             'TechLoungeTweaks/_internal/vendor/win11debloat/LICENSE',
                             'TechLoungeTweaks/_internal/debloat_bridge.ps1',
                             'TechLoungeTweaks/_internal/edition_bridge.ps1',
                             'TechLoungeTweaks/_internal/debloat_catalog.json',
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
