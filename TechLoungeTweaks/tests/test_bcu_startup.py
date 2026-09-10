from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from updates import prepare_bcu_settings
from tool_windows import is_main_tool_window

class BcuStartupTests(unittest.TestCase):
    def test_fresh_settings_skip_welcome_with_valid_version(self):
        with tempfile.TemporaryDirectory() as folder:
            exe=Path(folder)/'BCUninstaller.exe'
            prepare_bcu_settings(exe,'v6.3')
            root=ET.parse(exe.with_suffix('.settings')).getroot()
            self.assertEqual(root.findtext('MiscFirstRun'),'False')
            self.assertEqual(root.findtext('MiscVersion'),'6.3.0.0')
    def test_existing_preferences_survive(self):
        with tempfile.TemporaryDirectory() as folder:
            exe=Path(folder)/'BCUninstaller.exe';path=exe.with_suffix('.settings')
            path.write_text('<Settings><MiscFirstRun>True</MiscFirstRun><MiscVersion>6.2.0.0</MiscVersion><FilterHideMicrosoft>True</FilterHideMicrosoft></Settings>')
            prepare_bcu_settings(exe,'v6.3')
            root=ET.parse(path).getroot()
            self.assertEqual(root.findtext('MiscFirstRun'),'False')
            self.assertEqual(root.findtext('MiscVersion'),'6.2.0.0')
            self.assertEqual(root.findtext('FilterHideMicrosoft'),'True')
    def test_only_main_bcu_window_is_hosted(self):
        self.assertTrue(is_main_tool_window('bcu','Bulk Crap Uninstaller v6.3 Portable x64'))
        for title in ('Welcome to BCUninstaller','News','Color legend',''):
            self.assertFalse(is_main_tool_window('bcu',title))
