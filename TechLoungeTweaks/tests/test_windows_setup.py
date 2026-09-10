import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

SRC = Path(__file__).resolve().parents[1] / 'src'
sys.path.insert(0, str(SRC))
from windows_setup import TOOLS, WindowsSetup


class WindowsSetupTests(unittest.TestCase):
    def setUp(self):
        self.tool = WindowsSetup(SRC / 'vendor' / 'mas')
        self.status_patch = patch.object(WindowsSetup, 'status', return_value={
            'ok': True, 'name': 'Microsoft Windows 11 Pro', 'edition': 'Professional', 'activated': False})
        self.status_mock = self.status_patch.start()
        self.addCleanup(self.status_patch.stop)

    @patch('windows_setup.subprocess.Popen')
    def test_already_activated_does_not_launch(self, popen):
        self.status_mock.return_value = {'ok': True, 'activated': True, 'name': 'Windows 11 Pro'}
        self.assertTrue(self.tool.launch('activate')['already_activated'])
        popen.assert_not_called()
        self.assertTrue(self.tool.launch('edition')['ok'])
        popen.assert_called_once()

    @patch('windows_setup.subprocess.Popen')
    def test_unknown_status_does_not_launch_activation(self, popen):
        for status in ({'ok': True, 'activated': None}, {'ok': False, 'message': 'Unavailable'}):
            self.status_mock.return_value = status
            self.assertFalse(self.tool.launch('activate')['ok'])
        popen.assert_not_called()

    @patch('windows_setup.subprocess.Popen')
    def test_both_actions_and_finished_process(self, popen):
        popen.return_value.poll.return_value = 0
        for action, (filename, _) in TOOLS.items():
            self.assertTrue(self.tool.launch(action)['ok'])
            args, kwargs = popen.call_args
            self.assertIn(filename, args[0])
            self.assertIn('-qedit', args[0])
            self.assertNotIn('/HWID', args[0])
            self.assertEqual(kwargs['creationflags'], subprocess.CREATE_NEW_CONSOLE)

    @patch('windows_setup.subprocess.Popen')
    def test_blocks_overlap_between_actions(self, popen):
        popen.return_value.poll.return_value = None
        self.assertTrue(self.tool.launch('activate')['ok'])
        self.assertFalse(self.tool.launch('edition')['ok'])
        popen.assert_called_once()

    @patch('windows_setup.subprocess.Popen')
    def test_invalid_missing_tampered_and_launch_failure(self, popen):
        self.assertFalse(self.tool.launch('anything & echo injected')['ok'])
        with tempfile.TemporaryDirectory() as folder:
            tool = WindowsSetup(folder)
            self.assertFalse(tool.launch('activate')['ok'])
            (Path(folder) / TOOLS['activate'][0]).write_text('altered')
            self.assertFalse(tool.launch('activate')['ok'])
        popen.assert_not_called()
        popen.side_effect = OSError('launch denied')
        self.assertIn('launch denied', self.tool.launch('activate')['message'])

    def test_real_cmd_quoting_with_harmless_script(self):
        # Never run MAS in tests. Exercise the exact launcher with a stub that
        # only writes a marker, including spaces and shell metacharacters.
        with tempfile.TemporaryDirectory(prefix='TL setup & (test) ! ') as folder:
            payload = b'@echo off\r\necho launched>"%~dp0result.txt"\r\n'
            script = Path(folder) / 'stub.cmd'
            script.write_bytes(payload)
            entry = ('stub.cmd', hashlib.sha256(payload).hexdigest())
            original_popen = subprocess.Popen
            def hidden(*args, **kwargs):
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                return original_popen(*args, **kwargs)
            with patch.dict(TOOLS, {'test': entry}), patch('windows_setup.subprocess.Popen', side_effect=hidden):
                tool = WindowsSetup(folder)
                self.assertTrue(tool.launch('test')['ok'])
                self.assertEqual(tool._process.wait(timeout=10), 0)
            self.assertEqual((Path(folder) / 'result.txt').read_text().strip(), 'launched')


if __name__ == '__main__':
    unittest.main()
