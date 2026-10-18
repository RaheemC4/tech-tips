"""Reopening uses local hardware data without caching tweak state."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import startup_summary

class StartupSummaryTests(unittest.TestCase):
    def test_roundtrip_expiry_corruption_and_failed_read(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "summary.json"
            with patch.object(startup_summary, "cache_path", return_value=target):
                self.assertEqual(startup_summary.load(), {})
                with patch.object(startup_summary.time, "time", return_value=100000):
                    startup_summary.save({"CPU": "Test CPU", "Memory": "32 GB"})
                    self.assertEqual(startup_summary.load(), {"CPU": "Test CPU", "Memory": "32 GB"})
                with patch.object(startup_summary.time, "time", return_value=200000):
                    self.assertEqual(startup_summary.load(), {})
                target.write_text("broken")
                self.assertEqual(startup_summary.load(), {})
                target.write_text(json.dumps({"saved": 1, "specs": {"CPU": 42}}))
                self.assertEqual(startup_summary.load(), {})
                startup_summary.save({"Error": "Read failed"})
                self.assertEqual(startup_summary.load(), {})
            with patch.object(startup_summary, "cache_path", side_effect=OSError):
                startup_summary.save({"CPU": "Test"})
                self.assertEqual(startup_summary.load(), {})

    def test_recent_tweak_results_survive_reopening_and_expire(self):
        tweaks = [{"key": "game_mode", "name": "Game Mode", "category": "Performance", "applied": True}]
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(startup_summary, "cache_path", return_value=Path(folder) / "tweaks.json"):
                with patch.object(startup_summary.time, "time", return_value=100000):
                    startup_summary.save_tweaks(tweaks)
                    self.assertEqual(startup_summary.load_tweaks(), tweaks)
                with patch.object(startup_summary.time, "time", return_value=200000):
                    self.assertEqual(startup_summary.load_tweaks(), [])
