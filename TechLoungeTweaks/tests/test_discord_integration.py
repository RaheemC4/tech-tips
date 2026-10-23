import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import discord_integration as integration


class DiscordIntegrationTests(unittest.TestCase):
    def test_deployment_and_reinstall_keep_cache_and_use_short_lived_integrator(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, payload = root / 'launcher.exe', root / 'nightly.asar'
            source.write_bytes(b'launcher fixture')
            payload.write_bytes(b'verified payload')
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            with patch.dict(os.environ, {'LOCALAPPDATA': str(root)}), \
                    patch.object(integration, 'launcher_source', return_value=source), \
                    patch.object(integration.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
                for _ in range(2):
                    installed = Path(integration.deploy(payload, digest))
                    self.assertEqual(installed.read_bytes(), source.read_bytes())
                    self.assertEqual((installed.parent / 'openasar.asar').read_bytes(), payload.read_bytes())
                    self.assertEqual((installed.parent / 'openasar.sha256').read_text().strip(), digest)
                    self.assertEqual(run.call_args.args[0], [str(installed), '--integrate'])
                    self.assertEqual(run.call_args.kwargs['timeout'], 20)
                self.assertEqual(sorted(p.name for p in installed.parent.iterdir()),
                                 ['DiscordLauncher.exe', 'openasar.asar', 'openasar.sha256'])

    def test_corrupt_payload_never_deploys_or_launches(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = Path(folder) / 'nightly.asar'
            payload.write_bytes(b'corrupt')
            with patch.object(integration.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'SHA-256'):
                    integration.deploy(payload, '0' * 64, folder)
            run.assert_not_called()
            self.assertFalse((Path(folder) / 'TechLoungeTweaks').exists())

    def test_failed_shortcut_integration_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source.exe'
            source.write_bytes(b'fixture')
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            with patch.dict(os.environ, {'LOCALAPPDATA': str(root)}), \
                    patch.object(integration, 'launcher_source', return_value=source), \
                    patch.object(integration.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)):
                with self.assertRaisesRegex(OSError, 'shortcut setup failed'):
                    integration.deploy(source, digest)

    def test_other_profile_is_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.exe'
            source.write_bytes(b'fixture')
            with patch.object(integration, 'launcher_source', return_value=source):
                with self.assertRaisesRegex(ValueError, 'current Windows profile'):
                    integration.deploy(source, hashlib.sha256(source.read_bytes()).hexdigest(), folder)
            self.assertFalse((Path(folder) / 'TechLoungeTweaks').exists())

    def test_frozen_build_resolves_bundled_launcher(self):
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', 'bundle', create=True):
            self.assertEqual(integration.launcher_source(), Path('bundle/discord-launcher/DiscordLauncher.exe'))


if __name__ == '__main__':
    unittest.main()
