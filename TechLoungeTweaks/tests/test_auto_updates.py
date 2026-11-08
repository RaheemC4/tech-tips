"""Automatic updates use only disposable packages and marker-only executables."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import updates
from update_lock import update_lease
from main import Api, traced

OLD = dict(schema=2, app_revision='a'*64, version='2026.10.23.174632', built_utc='2026-10-23T17:46:32+00:00')
NEW = dict(schema=2, app_revision='b'*64, version='2026.11.08.030000', built_utc='2026-11-08T03:00:00+00:00')


class AutomaticUpdatesTests(unittest.TestCase):
    def manager(self, folder):
        manager = updates.UpdateManager(root=folder, build=OLD)
        manager.offers = {key: dict(name=key+'.zip', version='2', url='unused', sha256='a'*64, key=key) for key in ('bcu','dlss')}
        manager.state['items'] = [dict(id=key, action='Update') for key in manager.offers]
        return manager

    @staticmethod
    def package(offer, destination, progress, cancel):
        key = offer['key']
        with zipfile.ZipFile(destination, 'w') as archive:
            archive.writestr(updates.TOOLS[key]['exe'], ('new-'+key).encode())

    def test_update_all_installs_every_offer_and_keeps_inventory(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = self.manager(folder)
            with patch('updates.download', side_effect=self.package):
                result = manager.apply_all(background=False)
            self.assertTrue(result['ok'])
            self.assertEqual(set(manager.installed), {'bcu','dlss'})
            for key in ('bcu','dlss'):
                self.assertEqual(manager.installed[key]['version'], '2')
                self.assertEqual(manager._tool_path(key).read_bytes(), ('new-'+key).encode())
            self.assertEqual(json.loads((Path(folder)/'installed.json').read_text()), manager.installed)
            self.assertFalse(manager.status()['busy'])
            self.assertEqual(manager.offers, {})

    def test_two_managers_preserve_each_others_installed_records(self):
        with tempfile.TemporaryDirectory() as folder:
            first = self.manager(folder);second = self.manager(folder)
            first.offers = {'dlss':first.offers['dlss']}
            second.offers = {'bcu':second.offers['bcu']}
            with patch('updates.download', side_effect=self.package):
                self.assertTrue(first.apply_all(background=False)['ok'])
                self.assertTrue(second.apply_all(background=False)['ok'])
            inventory = json.loads((Path(folder)/'installed.json').read_text())
            self.assertEqual(set(inventory), {'bcu','dlss'})
            self.assertEqual(inventory['dlss']['version'], '2')
            self.assertEqual(inventory['bcu']['version'], '2')

    def test_unknown_publisher_is_not_reported_as_up_to_date(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = updates.UpdateManager(root=folder, build=OLD)
            manager.state['items'] = [dict(id='dlss', check_error=True, message='Offline')]
            result = manager.apply_all(background=False)
            self.assertFalse(result['ok'])
            self.assertIn('could not be checked', manager.status()['message'])

    def test_restart_waits_for_open_tools_and_system_jobs(self):
        api = Api.__new__(Api)
        api._updates = Mock();api._updates.processes = {};api._updates.status.return_value = {'busy':False}
        api._floating_tools = Mock();api._floating_tools.has_open_windows.return_value = False
        api.active_jobs = Mock(return_value=[]);api.close = Mock(return_value={'ok':True})
        api._updates.restart.return_value = {'ok':True}
        with patch('main.defender_remover.is_running', return_value=False):
            api._floating_tools.has_open_windows.return_value = True
            self.assertFalse(api.updates_restart()['ok'])
            api._floating_tools.has_open_windows.return_value = False
            api.active_jobs.return_value = [{'state':'running'}]
            self.assertFalse(api.updates_restart()['ok'])
            api.active_jobs.return_value = []
            self.assertTrue(api.updates_restart()['ok'])
        api._updates.restart.assert_called_once()
        api.close.assert_called_once()

    def test_failed_offer_does_not_prevent_other_updates(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = self.manager(folder)
            def download(offer, *args):
                if offer['key']=='bcu': raise ValueError('Checksum mismatch')
                self.package(offer, *args)
            with patch('updates.download', side_effect=download):
                result = manager.apply_all(background=False)
            self.assertFalse(result['ok'])
            self.assertEqual(manager._tool_path('dlss').read_bytes(), b'new-dlss')
            self.assertNotIn('bcu', manager.installed)
            self.assertEqual(manager.status()['update_errors'], {'bcu':'Checksum mismatch'})
            self.assertIn('bcu', manager.offers)

    def test_running_tool_is_deferred_without_interrupting_it(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = self.manager(folder)
            process = Mock(); process.poll.return_value = None
            manager.processes['bcu'] = process
            with patch('updates.download', side_effect=self.package):
                result = manager.apply_all(background=False)
            self.assertFalse(result['ok'])
            self.assertIn('bcu', manager.offers)
            self.assertEqual(manager._tool_path('dlss').read_bytes(), b'new-dlss')
            process.terminate.assert_not_called()

    def test_cancel_stops_remaining_batch(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = self.manager(folder)
            def download(offer, target, progress, cancel):
                self.package(offer, target, progress, cancel)
                cancel.set()
            with patch('updates.download', side_effect=download) as fetch:
                result = manager.apply_all(background=False)
            self.assertFalse(result['ok'])
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(manager.installed, {})
            self.assertFalse(manager.status()['busy'])

    def test_other_process_cannot_enter_update_transaction(self):
        with tempfile.TemporaryDirectory() as folder:
            code = "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[2]);from update_lock import update_lease;\nwith update_lease(Path(sys.argv[1])): print('acquired')"
            args = [sys.executable, '-c', code, folder, str(Path(updates.__file__).parent)]
            with update_lease(Path(folder)):
                blocked = subprocess.run(args, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn('Another updater is running', blocked.stderr)
            free = subprocess.run(args, capture_output=True, text=True, timeout=10)
            self.assertEqual(free.returncode, 0, free.stderr)
            self.assertEqual(free.stdout.strip(), 'acquired')

    def test_installer_is_staged_and_recovered_with_verified_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = updates.UpdateManager(root=Path(folder)/'updates', build=OLD)
            payload = Path(folder)/'payload';payload.mkdir()
            data = b'MZharmless fixture'
            (payload/'TechLoungeTweaks-Setup.exe').write_bytes(data)
            (payload/'installer.json').write_text(json.dumps(dict(NEW, sha256=hashlib.sha256(data).hexdigest())))
            manager.root.mkdir()
            manager._stage_app(payload, dict(distribution='installer', version=NEW['built_utc'], app_revision=NEW['app_revision']))
            recovered = updates.UpdateManager(root=manager.root, build=OLD)
            recovered._load()
            self.assertEqual(recovered.status()['ready_kind'], 'installer')
            self.assertEqual(Path(recovered.status()['ready']).joinpath('TechLoungeTweaks-Setup.exe').read_bytes(), data)
            recovered.install_root = Path(folder)/'installed'
            with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', str(Path(updates.__file__).parent), create=True), patch('updates.subprocess.Popen') as launch:
                self.assertTrue(recovered.restart()['ok'])
                self.assertTrue(recovered.restart()['ok'])
                self.assertEqual(launch.call_count, 1)
                self.assertIn('-Installer', launch.call_args.args[0])
                arguments = launch.call_args.args[0]
                self.assertEqual(arguments[arguments.index('-Destination')+1], str(recovered.install_root))

    def test_mismatched_github_digest_never_becomes_installable(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = updates.UpdateManager(root=folder, build=OLD)
            manager.install_root = Path(folder)/'installed'
            manifest = dict(NEW, distribution='installer', download_url='https://github.com/RaheemC4/tech-tips/releases/download/test/TechLoungeTweaks.zip', files={'TechLoungeTweaks/TechLoungeTweaks.zip':'c'*64})
            with patch('updates.app_manifest', return_value=manifest), patch('updates.release', return_value={'tag_name':'1','assets':[]}), patch.object(sys, 'frozen', True, create=True):
                manager._check()
            self.assertNotIn('app', manager.offers)
            app = next(row for row in manager.status()['items'] if row['id']=='app')
            self.assertEqual(app['status'], 'unavailable')
            self.assertIsNone(app['action'])

    def test_automatic_checks_apply_batch_and_schedule_without_import_side_effects(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = updates.UpdateManager(root=folder, build=OLD)
            with patch.object(manager, 'start') as start, patch('updates.threading.Timer') as timer:
                manager.start_automatic()
                start.assert_called_once_with(manual=True, automatic=True)
                self.assertEqual(timer.call_args.args[0], 900)
                manager.stop_automatic()
                timer.return_value.cancel.assert_called_once()
            manager.automatic = True
            with patch.object(manager, '_load'), patch('updates.release', side_effect=OSError('offline')), patch('updates.app_manifest', side_effect=OSError('offline')), patch.object(manager, 'apply_all', return_value={'ok':True}) as batch:
                manager._check(automatic=True)
            batch.assert_called_once()

    def test_silent_restart_waits_for_activity_and_blocks_new_actions(self):
        api = Api.__new__(Api)
        api._auto_restart_lock = threading.Lock()
        api._activity_lock = threading.Lock()
        api._startup_updates_ready = True
        api._auto_restart_committed = False
        api._active_calls = 1
        api.updates_restart = Mock(return_value={'ok':True})
        api._auto_restart_lock.acquire();api._restart_automatically()
        api.updates_restart.assert_not_called()
        api._active_calls = 0
        api._auto_restart_lock.acquire();api._restart_automatically()
        api.updates_restart.assert_called_once()
        @traced
        def mutate(owner):
            return {'ok':True, 'changed':True}
        self.assertFalse(mutate(api)['ok'])
        api._auto_restart_committed = False
        self.assertTrue(mutate(api)['changed'])
        self.assertEqual(api._active_calls, 0)


if __name__ == '__main__': unittest.main()
