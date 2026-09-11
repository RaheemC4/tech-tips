import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import updates

BUILD = dict(schema=2, channel='nuitka', version='1', app_revision='a'*64,
             built_utc='2026-09-11T00:00:00+00:00')
NEXT = dict(BUILD, version='2', app_revision='b'*64, built_utc='2026-09-12T00:00:00+00:00')


class ChannelTests(unittest.TestCase):
    def test_no_fallback_when_channel_empty_or_offline(self):
        with patch.object(updates, 'get_json', return_value=[]) as get:
            self.assertEqual(updates.app_manifest(BUILD), BUILD)
            self.assertNotIn('raw.githubusercontent.com', get.call_args.args[0])
        with patch.object(updates, 'get_json', side_effect=OSError('offline')) as get:
            with self.assertRaises(OSError): updates.app_manifest(BUILD)
            self.assertEqual(get.call_count, 1)

    def test_stable_retains_original_feed(self):
        with patch.object(updates, 'get_json', return_value={}) as get:
            updates.app_manifest({})
            get.assert_called_once_with(updates.RAW + 'release.json')

    def test_selects_nuitka_metadata_and_checks_asset(self):
        prefix=f'https://github.com/{updates.APP_REPO}/releases/download/nuitka-test-2/'
        manifest=dict(NEXT, download_url=prefix+'TechLoungeTweaks-Nuitka.zip',
                      files={'TechLoungeTweaks/TechLoungeTweaks.zip':'c'*64})
        release=dict(tag_name='nuitka-test-2', prerelease=True, draft=False, assets=[
            dict(name='nuitka-update.json',browser_download_url=prefix+'nuitka-update.json'),
            dict(name='TechLoungeTweaks-Nuitka.zip',browser_download_url=manifest['download_url'],digest='sha256:'+'c'*64)])
        with patch.object(updates,'get_json',side_effect=[[dict(tag_name='app-stable'),release],manifest]):
            self.assertEqual(updates.app_manifest(BUILD),manifest)
        for bad in (dict(manifest,channel='stable'),dict(manifest,files={'TechLoungeTweaks/TechLoungeTweaks.zip':'d'*64})):
            with patch.object(updates,'get_json',side_effect=[[release],bad]):
                with self.assertRaises(ValueError): updates.app_manifest(BUILD)

    def test_install_and_pending_cannot_cross_channels(self):
        for channel in ('stable','nuitka'):
            with self.subTest(channel=channel), tempfile.TemporaryDirectory() as tmp:
                manager=updates.UpdateManager(tmp,BUILD)
                self.assertEqual(manager.root,Path(tmp)/'nuitka')
                def download(offer,target,*args):
                    with zipfile.ZipFile(target,'w') as z:
                        z.writestr('TechLoungeTweaks/TechLoungeTweaks.exe',b'fixture')
                        z.writestr('TechLoungeTweaks/resources/TechLoungeProfile.nip',b'fixture')
                        z.writestr('TechLoungeTweaks/_internal/build-info.json',json.dumps(dict(NEXT,channel=channel)))
                offer=dict(name='candidate.zip',version=NEXT['built_utc'],app_revision=NEXT['app_revision'])
                with patch.object(updates,'download',side_effect=download): manager._install('app',offer)
                self.assertEqual(bool(manager.status().get('ready')),channel=='nuitka')
                if channel=='nuitka':
                    pending=Path(manager.status()['ready'])/'_internal/build-info.json'
                    recovered=updates.UpdateManager(tmp,BUILD);recovered._load()
                    self.assertTrue(recovered.status().get('ready'))
                    pending.write_text(json.dumps(dict(NEXT,channel='stable')))
                    recovered=updates.UpdateManager(tmp,BUILD);recovered._load()
                    self.assertFalse(recovered.status().get('ready'))
                    with patch.object(sys,'frozen',True,create=True),patch.object(updates.subprocess,'Popen') as launch:
                        self.assertFalse(manager.restart()['ok'])
                        launch.assert_not_called()

    def test_both_directions_reject_cross_channel(self):
        with self.assertRaises(ValueError): updates.newer_app(dict(NEXT,channel='stable'),BUILD)
        with self.assertRaises(ValueError): updates.newer_app(NEXT,dict(BUILD,channel='stable'))
