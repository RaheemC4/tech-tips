import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from updates import UpdateManager, TOOLS
from tool_windows import is_main_tool_window, chrome_insets
from tool_startup import should_suppress
from package_layout import log_path
from personal_tools import prepare_driverbooster
from personal_tools import conflicting_copy
import configparser
from unittest.mock import Mock


class PersonalToolsTests(unittest.TestCase):
    def test_other_installation_cannot_intercept_launch(self):
        process = Mock()
        process.info = {'name':'DriverBooster.exe'}
        process.exe.return_value = str(Path('other/DriverBooster.exe').resolve())
        with patch('psutil.process_iter',return_value=[process]):
            self.assertTrue(conflicting_copy(Path('bundle/DriverBooster.exe')))
            self.assertFalse(conflicting_copy(Path('other/DriverBooster.exe')))

    def test_changed_personal_executable_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'driverbooster/DriverBooster.exe'
            path.parent.mkdir()
            path.write_bytes(b'updated executable')
            manager = UpdateManager(root=Path(tmp)/'updates',bundle_root=tmp)
            manager.installed['driverbooster'] = dict(bundle=True,folder='driverbooster',exe=path.name)
            manager.bundles['driverbooster'] = dict(sha256='0'*64)
            with patch('updates.subprocess.Popen') as launch:
                self.assertFalse(manager.launch('driverbooster')['ok'])
                launch.assert_not_called()
    def test_driverbooster_preserves_repack_update_and_close_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'Config.ini'
            original = '[General]\nLanguage=German\nCloseAction=1\n[AutoUpdate]\nUpdateType=0\n'
            path.write_text(original, encoding='utf-16')
            prepare_driverbooster(tmp)
            settings = configparser.ConfigParser()
            settings.read(path, encoding='utf-16')
            self.assertEqual(settings['General']['Language'],'German')
            self.assertEqual(settings['General']['CloseAction'],'0')
            self.assertEqual(settings['AutoUpdate']['UpdateType'],'2')
            self.assertEqual(settings['AutoUpdate']['Enabled'],'0')
            self.assertEqual(settings['Scan']['AutoScan'],'0')
            self.assertEqual(settings['Drivers']['AutoDownload'],'0')
            self.assertEqual((Path(tmp)/'Config.ini.before-techlounge').read_text(encoding='utf-16'),original)
    def test_local_tools_work_offline_and_never_request_a_publisher_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = {}
            for key in ('driverbooster', 'treesize'):
                path = root / 'tools' / key / TOOLS[key]['exe']
                path.parent.mkdir(parents=True)
                path.write_bytes(b'fixture')
                manifest[key] = dict(version='1.0', exe=path.name)
            info = root / 'bundles.json'
            info.write_text(json.dumps(manifest))
            manager = UpdateManager(root=root/'updates', bundle_root=root/'tools', bundle_manifest=info)
            with patch('updates.release', side_effect=RuntimeError('offline')) as remote, patch('updates.app_manifest', side_effect=RuntimeError('offline')):
                manager._check()
            for key in manifest:
                row = next(r for r in manager.status()['items'] if r['id'] == key)
                self.assertTrue(row['launch'])
                self.assertTrue(row['local'])
                self.assertIsNone(row['action'])
                self.assertNotIn(key, manager.offers)
            self.assertTrue(all(call.args[0] for call in remote.call_args_list))

    def test_main_window_filters_preserve_custom_headers(self):
        for key, title in [('treesize','TreeSize'), ('driverbooster','Driver Booster')]:
            self.assertTrue(is_main_tool_window(key,title))
            self.assertFalse(is_main_tool_window(key,'Settings'))
            self.assertFalse(should_suppress(key,'',0,0,200000,False))
            self.assertEqual(chrome_insets(None,None,key,144),(0,0,0))

    def test_logs_are_outside_portable_launcher(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ', {'LOCALAPPDATA':tmp}):
            self.assertEqual(Path(log_path()),Path(tmp)/'TechLoungeTweaks/Logs/TL-api.log')
