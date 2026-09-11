import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import updates


class Response(io.BytesIO):
    headers = {}


class UpdatesTests(unittest.TestCase):
    def test_versions_do_not_downgrade_or_compare_as_strings(self):
        self.assertGreater(updates.version('v1.10'), updates.version('1.9'))
        self.assertEqual(updates.version('v6.3.0'), updates.version('6.3'))
        with self.assertRaises(ValueError): updates.version('v1.4-beta')

    def test_publisher_asset_selection_fails_closed(self):
        tool = updates.TOOLS['dlss']
        asset = dict(name='DLSS.Swapper-1.2-portable.zip', digest='sha256:' + 'a'*64,
                     browser_download_url='https://github.com/beeradmoore/dlss-swapper/releases/download/v1.2/file.zip')
        self.assertEqual(updates.asset_for(tool, {'assets':[asset]})['sha256'], 'a'*64)
        for invalid in (dict(asset, digest=None), dict(asset, browser_download_url='https://github.com/evil/repo/releases/download/a.zip')):
            with self.assertRaises(ValueError): updates.asset_for(tool, {'assets':[invalid]})
        with self.assertRaises(ValueError): updates.asset_for(tool, {'assets':[asset,asset]})

    def test_urls_and_archive_paths(self):
        for url in ('http://github.com/x', 'https://github.com.evil.test/x', 'https://evil@github.com/x', 'https://github.com:444/x'):
            with self.assertRaises(ValueError): updates.checked_url(url)
        for name in ('../evil', '/root', '\\root', 'C:\\evil', 'ok:stream', 'NUL.txt', 'folder./file', 'folder/../file'):
            with self.assertRaises(ValueError, msg=name): updates.safe_name(name)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'bad.zip'
            with zipfile.ZipFile(path,'w') as z: z.writestr('../escape.exe', b'bad')
            with self.assertRaises(ValueError): updates.extract(path, Path(temp)/'out')
            self.assertFalse((Path(temp)/'escape.exe').exists())

    def test_download_checksum_cancel_and_size(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)/'file.zip'
            asset = dict(url='https://github.com/test', sha256=hashlib.sha256(b'good').hexdigest())
            with patch.object(updates,'response',return_value=Response(b'bad')):
                with self.assertRaises(ValueError): updates.download(asset,target,lambda *a:None,threading.Event())
            cancel = threading.Event(); cancel.set()
            with patch.object(updates,'response',return_value=Response(b'good')):
                with self.assertRaises(InterruptedError): updates.download(asset,target,lambda *a:None,cancel)
            with patch.object(updates,'response',return_value=Response(b'good')):
                updates.download(asset,target,lambda *a:None,threading.Event())
                self.assertEqual(target.read_bytes(),b'good')

    def test_checks_are_background_single_flight_and_offline_tolerant(self):
        with tempfile.TemporaryDirectory() as temp:
            entered, unblock = threading.Event(), threading.Event()
            def slow(*a): entered.set(); unblock.wait(3); raise OSError('offline')
            manager = updates.UpdateManager(temp)
            with patch.object(updates,'release',side_effect=slow), patch.object(updates,'get_json',side_effect=OSError('offline')):
                before=time.monotonic(); manager.start()
                self.assertLess(time.monotonic()-before,0.5)
                self.assertTrue(entered.wait(1))
                self.assertTrue(manager.status()['checking'])
                self.assertIn('openmouse', [r['id'] for r in manager.status()['items']])
                self.assertIn('bcu', [r['id'] for r in manager.status()['items']])
                self.assertFalse(manager.start(manual=True)['ok'])
                self.assertFalse(manager.apply('dlss')['ok'])
                unblock.set()
                deadline=time.monotonic()+3
                while manager.status()['checking'] and time.monotonic()<deadline: time.sleep(.01)
                self.assertFalse(manager.status()['checking'])
                self.assertEqual(len(manager.status()['items']),7)
                self.assertTrue(any('offline' in r['message'] for r in manager.status()['items']))

    def test_transaction_success_failure_and_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            manager=updates.UpdateManager(temp)
            old=Path(temp)/'old';old.mkdir();(old/'DLSS Swapper.exe').write_bytes(b'old')
            manager.installed={'dlss':dict(version='1',folder='old',exe='DLSS Swapper.exe')}
            updates.atomic_json(Path(temp)/'installed.json',manager.installed)
            def fake_download(asset,target,*args):
                with zipfile.ZipFile(target,'w') as z:z.writestr('DLSS Swapper.exe',b'new')
            offer=dict(name='tool.zip',version='2')
            with patch.object(updates,'download',side_effect=OSError('failed')):
                manager._install('dlss',offer)
                self.assertEqual(manager.installed['dlss']['version'],'1')
            with patch.object(updates,'download',side_effect=fake_download): manager._install('dlss',offer)
            self.assertEqual(manager.installed['dlss']['version'],'2')
            self.assertEqual(manager._tool_path('dlss').read_bytes(),b'new')
            self.assertEqual((old/'DLSS Swapper.exe').read_bytes(),b'old')
            with patch.object(manager,'start',return_value={'ok':True}): manager.rollback('dlss')
            self.assertEqual(manager._tool_path('dlss').read_bytes(),b'old')
            self.assertFalse(list(Path(temp).glob('stage-*')))

    def test_7z_portable_extraction(self):
        import py7zr
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'BCUninstaller.exe').write_bytes(b'MZfixture')
            archive=root/'tool.7z'
            with py7zr.SevenZipFile(archive,'w') as z:z.write(root/'BCUninstaller.exe','BCUninstaller.exe')
            updates.extract(archive,root/'out')
            self.assertEqual((root/'out/BCUninstaller.exe').read_bytes(),b'MZfixture')

    def test_failed_metadata_commit_preserves_installed_version(self):
        with tempfile.TemporaryDirectory() as temp:
            manager=updates.UpdateManager(temp)
            manager.installed={'dlss':dict(version='1',folder='old',exe='DLSS Swapper.exe')}
            def fake_download(asset,target,*args):
                with zipfile.ZipFile(target,'w') as z:z.writestr('DLSS Swapper.exe',b'new')
            with patch.object(updates,'download',side_effect=fake_download), patch.object(updates,'atomic_json',side_effect=OSError('disk full')):
                manager._install('dlss',dict(name='tool.zip',version='2'))
            self.assertEqual(manager.installed['dlss']['version'],'1')
            self.assertIn('disk full',manager.status()['message'])

    def test_pending_app_update_is_recovered(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'candidate').mkdir();(root/'candidate/TechLoungeTweaks.exe').write_bytes(b'MZ')
            updates.atomic_json(root/'pending-app.json',dict(folder='candidate',version='2026-10-01'))
            build=dict(schema=2,app_revision='a'*64,built_utc='2026-09-01T00:00:00+00:00')
            (root/'candidate/_internal').mkdir()
            updates.atomic_json(root/'candidate/_internal/build-info.json',dict(build,app_revision='b'*64,built_utc='2026-10-01T00:00:00+00:00'))
            manager=updates.UpdateManager(temp,build);manager._load()
            self.assertTrue(manager.status()['ready'])
            newer=updates.UpdateManager(temp,{'built_utc':'2026-10-01'});newer._load()
            self.assertFalse(newer.status().get('ready'))

    def test_openmouse_uses_default_browser(self):
        with patch('webbrowser.open', return_value=True) as browser:
            self.assertTrue(updates.open_mouse()['ok'])
            browser.assert_called_once_with('https://control.openmouse.app/')

    def test_app_identity_ignores_republishing_and_blocks_downgrades(self):
        build=dict(schema=2,app_revision='a'*64,built_utc='2026-09-10T10:00:00+00:00')
        self.assertFalse(updates.newer_app(dict(build,built_utc='2026-09-11T10:00:00+00:00'),build))
        self.assertFalse(updates.newer_app(dict(build,app_revision='b'*64,built_utc='2026-09-09T10:00:00+00:00'),build))
        self.assertTrue(updates.newer_app(dict(build,app_revision='b'*64,built_utc='2026-09-11T10:00:00+00:00'),build))
        with self.assertRaises(ValueError):updates.newer_app({'built_utc':'2026-10-01'},build)

    def test_bundled_tool_available_offline_and_newer_managed_version_wins(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);bundles=root/'bundles';(bundles/'dlss').mkdir(parents=True)
            (bundles/'dlss/DLSS Swapper.exe').write_bytes(b'bundled')
            manifest=root/'bundled.json';updates.atomic_json(manifest,{'dlss':dict(version='2',exe='DLSS Swapper.exe')})
            manager=updates.UpdateManager(root/'updates',bundle_root=bundles,bundle_manifest=manifest)
            manager._load()
            self.assertEqual(manager._tool_path('dlss').read_bytes(),b'bundled')
            self.assertEqual(manager.installed['dlss']['version'],'2')
            (manager.root/'new').mkdir();(manager.root/'new/DLSS Swapper.exe').write_bytes(b'new')
            updates.atomic_json(manager.root/'installed.json',{'dlss':dict(version='3',folder='new',exe='DLSS Swapper.exe')})
            manager._load()
            self.assertEqual(manager._tool_path('dlss').read_bytes(),b'new')

if __name__ == '__main__': unittest.main()
