"""Regression coverage for repeated hardware reads and concurrent installers."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from main import Api


class StartupAndInstallTests(unittest.TestCase):
    def test_summary_and_sections_share_hardware_reads_until_refresh(self):
        api = Api.__new__(Api)
        api._cache = {}
        api._cachelock = threading.Lock()
        rows = {
            "CPU": [[("Name", "Test CPU")]],
            "Graphics": [[("Name", "Test GPU")]],
            "Memory": [[("Total capacity", "32 GB"), ("Running at", "6000 MT/s")]],
            "Mainboard": [[("Manufacturer", "Test"), ("Product", "Board")]],
            "Windows": [[("Edition", "Windows 11 Pro"), ("Build", "26200")]],
            "Storage": [[("Model", "Test SSD")]],
        }
        readers = {key: Mock(return_value=value) for key, value in rows.items()}
        sections = [(key, "", fn) for key, fn in readers.items()]
        with patch("main.sysinfo.SECTIONS", sections):
            first = api.specs()
            # Startup emits specs, prefetches specs, then warms the sections.
            self.assertEqual(api.specs(), first)
            for name in rows:
                api.sysinfo_section(name)
            for reader in readers.values():
                reader.assert_called_once()
            self.assertEqual(first, {"CPU": "Test CPU", "Graphics": "Test GPU",
                "Memory": "32 GB @ 6000 MT/s", "Motherboard": "Test Board",
                "Windows": "Windows 11 Pro (build 26200)", "Storage": "Test SSD"})
            with patch("main.threading.Thread"):
                api.refresh_all()
            self.assertEqual(api.specs(), first)
            for reader in readers.values():
                self.assertEqual(reader.call_count, 2)

    def test_hardware_arrives_while_tweak_scan_is_still_running(self):
        api = Api.__new__(Api)
        api._cache = {}
        api._cachelock = threading.Lock()
        api._nv_startup = Mock()
        api._prefetch = Mock()
        hardware_arrived = threading.Event()
        api.specs = Mock(return_value={"CPU": "Live CPU"})
        events = []
        def emit(name, data):
            events.append((name, data))
            if name == "specs":
                hardware_arrived.set()
        api._emit = emit
        def scan():
            self.assertTrue(hardware_arrived.wait(3), "Hardware waited behind the scan")
            return []
        api.scan = scan
        with patch("main.startup_summary.save") as save:
            api._background_start()
        self.assertIn(("specs", {"CPU": "Live CPU"}), events)
        self.assertIn(("scanned", {"tweaks": [], "categories": []}), events)
        save.assert_called_once_with({"CPU": "Live CPU"})

    def test_simultaneous_installs_only_remove_their_own_downloads(self):
        api = Api.__new__(Api)
        api._dl_cancel = set()
        api._job_update = Mock()
        api._job_finish = Mock()
        entered, release = threading.Event(), threading.Event()
        paths = {}

        def install(app_id, dest, **kwargs):
            paths[app_id] = Path(dest)
            (Path(dest) / "installer.exe").write_bytes(app_id.encode())
            if app_id == "first":
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("Test synchronisation timed out")
                if not (Path(dest) / "installer.exe").exists():
                    return False, "Active download was deleted"
            return True, "Installed."

        with tempfile.TemporaryDirectory() as tmp, \
                patch.dict(os.environ, LOCALAPPDATA=tmp), \
                patch("main.apps.install", side_effect=install):
            base = Path(tmp) / "TechLoungeTweaks/installers"
            base.mkdir(parents=True)
            unrelated = base / "unrelated.txt"
            unrelated.write_text("keep")
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(api._run_app_install, "first", "app:first")
                try:
                    self.assertTrue(entered.wait(5))
                    pool.submit(api._run_app_install, "second", "app:second").result(5)
                    self.assertNotEqual(paths["first"], paths["second"])
                    self.assertTrue((paths["first"] / "installer.exe").exists())
                    self.assertFalse(paths["second"].exists())
                finally:
                    release.set()
                first.result(5)
            self.assertFalse(paths["first"].exists())
            self.assertEqual(unrelated.read_text(), "keep")
            self.assertEqual(api._job_finish.call_count, 2)
            self.assertTrue(all(call.args[1] == "done"
                                for call in api._job_finish.call_args_list))

    def test_failed_install_cleans_only_its_temporary_directory(self):
        api = Api.__new__(Api)
        api._dl_cancel = set()
        api._job_finish = Mock()
        with tempfile.TemporaryDirectory() as tmp, \
                patch.dict(os.environ, LOCALAPPDATA=tmp), \
                patch("main.apps.install", side_effect=RuntimeError("fixture failure")):
            api._run_app_install("shiftd", "app:shiftd")
            self.assertEqual(list((Path(tmp) / "TechLoungeTweaks/installers").iterdir()), [])
            self.assertEqual(api._job_finish.call_args.args[1], "error")
            self.assertIn("fixture failure", api._job_finish.call_args.kwargs["result"]["message"])
