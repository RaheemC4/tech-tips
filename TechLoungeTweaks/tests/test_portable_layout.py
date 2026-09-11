import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import cleanup
import nvprofile
import updates


class PortableLayoutTests(unittest.TestCase):
    def test_nested_runtime_keeps_tools_and_cleanup_at_portable_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(sys,'frozen',True,create=True), patch.object(sys,'_tl_app_root',str(root),create=True), patch.object(sys,'executable',str(root/'_internal/TechLoungeTweaks.exe')):
                self.assertEqual(Path(nvprofile._app_dir()),root)
                manager=updates.UpdateManager(build={'channel':'nuitka'})
                self.assertEqual(manager.bundle_root,root/'resources/tools')
                self.assertIn(os.path.normcase(str(root)),cleanup._self_dirs())
