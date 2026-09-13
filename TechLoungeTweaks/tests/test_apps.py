import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import apps


class AppInstallTests(unittest.TestCase):
    def _discord_version(self, root, version, payload=b"stock"):
        folder = Path(root) / "Discord" / f"app-{version}"
        (folder / "resources").mkdir(parents=True)
        (folder / "Discord.exe").write_bytes(b"exe")
        (folder / "resources" / "app.asar").write_bytes(payload)
        return folder

    def test_latest_discord_folder_uses_numeric_version_and_complete_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._discord_version(tmp, "1.0.9999")
            newest = self._discord_version(tmp, "1.0.10000")
            incomplete = Path(tmp) / "Discord" / "app-9.0.0"
            incomplete.mkdir()
            self.assertEqual(Path(apps.latest_discord_app(tmp)), newest)

    def test_openasar_settings_merge_without_first_launch_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "discord" / "settings.json"
            path.parent.mkdir()
            path.write_text(json.dumps({"IS_MAXIMIZED": True,
                                        "openasar": {"customFlags": "--test"}}),
                            encoding="utf-8")
            apps.configure_openasar(tmp)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(saved["IS_MAXIMIZED"])
            self.assertEqual(saved["openasar"]["customFlags"], "--test")
            self.assertEqual(saved["openasar"], {
                "customFlags": "--test", "setup": True, "cmdPreset": "perf",
                "noTrack": True, "noTyping": True, "themeSync": True,
                "quickstart": True, "multiInstance": False,
            })

    def test_nightly_download_requires_and_checks_github_digest(self):
        payload = b"verified-openasar" * 100
        asset = {"name": "app.asar", "size": len(payload),
                 "digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
                 "browser_download_url": apps.OPENASAR_ASSET_URL}
        release = json.dumps({"tag_name": "nightly", "assets": [asset]}).encode()

        class Response:
            def __init__(self, body, url):
                self.body, self.url, self.pos = body, url, 0
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def geturl(self): return self.url
            def read(self, size=-1):
                if size < 0:
                    size = len(self.body) - self.pos
                chunk = self.body[self.pos:self.pos + size]
                self.pos += len(chunk)
                return chunk

        def urlopen(req, timeout=0):
            url = req.full_url
            return Response(release if url == apps.OPENASAR_RELEASE_API else payload, url)

        with tempfile.TemporaryDirectory() as tmp, patch("apps.urllib.request.urlopen", side_effect=urlopen):
            path, details = apps._download_openasar(tmp)
            self.assertEqual(Path(path).read_bytes(), payload)
            self.assertEqual(details["sha256"], hashlib.sha256(payload).hexdigest())

    def test_discord_install_always_runs_openasar_post_install(self):
        with patch("apps.winget_path", return_value=None), \
                patch("apps.install_direct", return_value=(True, "Installed.")), \
                patch("apps.install_openasar", return_value=(True, "Both ready.")) as openasar:
            self.assertEqual(apps.install("discord", "C:/temp"), (True, "Both ready."))
            openasar.assert_called_once()

    def test_openasar_replaces_newest_asar_and_keeps_stock_backup(self):
        payload = b"openasar" * 2048
        with tempfile.TemporaryDirectory() as local, tempfile.TemporaryDirectory() as roaming, \
                tempfile.TemporaryDirectory() as downloads:
            older = self._discord_version(local, "1.0.9256", b"x" * (2 << 20))
            newest = self._discord_version(local, "1.0.9257", b"y" * (2 << 20))
            source = Path(downloads) / "nightly.asar"
            source.write_bytes(payload)
            with patch("apps._download_openasar", return_value=(str(source), {"sha256": "0" * 64})), \
                    patch("apps._stop_discord"), patch("apps.subprocess.Popen"):
                ok, message = apps.install_openasar(downloads, local_appdata=local,
                                                     appdata=roaming)
            self.assertTrue(ok, message)
            self.assertEqual((newest / "resources" / "app.asar").read_bytes(), payload)
            self.assertEqual((newest / "resources" / "app.asar.backup").stat().st_size,
                             2 << 20)
            self.assertEqual((older / "resources" / "app.asar").stat().st_size, 2 << 20)
            settings = json.loads((Path(roaming) / "discord" / "settings.json").read_text())
            self.assertEqual(settings["openasar"], apps.OPENASAR_SETTINGS)


if __name__ == "__main__":
    unittest.main()
