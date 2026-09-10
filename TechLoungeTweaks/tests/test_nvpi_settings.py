import sys
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from nvpi_settings import prepare_window, title_colour


class NvpiSettingsTests(unittest.TestCase):
    def test_real_bundled_file_prepares_without_losing_preferences(self):
        import shutil
        source=Path(__file__).resolve().parents[1]/'resources/tools/nvpi/NVPI Revamped App/Settings.xml'
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'Settings.xml'
            shutil.copyfile(source,target)
            prepare_window(Path(directory)/'NVPI-R.exe')
            root=ET.parse(target).getroot()
            self.assertEqual(root.findtext('WindowState'),'Normal')
            self.assertEqual(root.findtext('Theme'),'MidnightTheme.xaml')
            self.assertIsNotNone(root.find('HiddenSettingGroups/string'))

    def test_bom_and_encoding_mismatches_and_real_utf16(self):
        xml='<?xml version="1.0" encoding="utf-16"?><UserSettings><Theme>DarkTheme.xaml</Theme><Note>caf\u00e9</Note></UserSettings>'
        for encoding in ('utf-8-sig','utf-8','utf-16'):
            with self.subTest(encoding=encoding), tempfile.TemporaryDirectory() as directory:
                target=Path(directory)/'Settings.xml'
                target.write_bytes(xml.encode(encoding))
                self.assertEqual(title_colour(directory),0x202020)
                prepare_window(Path(directory)/'NVPI-R.exe')
                self.assertEqual(ET.parse(target).findtext('Note'),'caf\u00e9')

    def test_startup_keeps_preferences_but_never_restores_maximized_backdrop(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'Settings.xml'
            path.write_text('<UserSettings><WindowState>Maximized</WindowState><Theme>MidnightTheme.xaml</Theme><Win11BackdropMode>Mica</Win11BackdropMode><FavoriteSettingIds><string>123</string></FavoriteSettingIds></UserSettings>',encoding='utf-8')
            prepare_window(Path(directory)/'NVPI-R.exe')
            root=ET.parse(path).getroot()
            self.assertEqual(root.findtext('WindowState'),'Normal')
            self.assertEqual(root.findtext('Win11BackdropMode'),'Disabled')
            self.assertEqual(root.findtext('DisableSplashScreen'),'true')
            self.assertEqual(root.findtext('FavoriteSettingIds/string'),'123')
            self.assertEqual(title_colour(directory),0x15110F)
            root.find('Theme').text='CleanWhiteTheme.xaml'
            ET.ElementTree(root).write(path,encoding='utf-8')
            self.assertEqual(title_colour(directory),0xFFFFFF)

    def test_no_settings_uses_midnight_without_creating_user_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            prepare_window(Path(directory)/'NVPI-R.exe')
            self.assertEqual(title_colour(directory),0x15110F)
            self.assertFalse((Path(directory)/'Settings.xml').exists())
