import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

SRC = Path(__file__).resolve().parents[1] / 'src'
sys.path.insert(0, str(SRC))
import debloat
import main


class DebloatTests(unittest.TestCase):
    def test_recommended_customization_is_exact(self):
        expected = {'ShowKnownFileExt','HideHome','TaskbarAlignLeft','HideSearchTb','EnableDarkMode',
                    'HideDesktopSpotlightIcon','StartAllAppsList','DisableStartRecommended','HideTaskview',
                    'EnableEndTask','ShowHiddenFolders','ShowSecondsClock','ClearStartOnce'}
        actual = {i['id'] for i in debloat.CATALOG['items'] if i['recommended'] and i['group']=='Customization'}
        self.assertEqual(expected, actual)
        self.assertIn('bing_search', debloat.RECOMMENDED_EXISTING)

    def test_no_duplicate_features_or_protected_packages(self):
        blocked = {'DisableBing','DisableSuggestions','DisableTelemetry','DisableWidgets','RevertContextMenu',
                   'DisableMouseAcceleration','DisableStickyKeys','DisableSnapLayouts','DisableDVR',
                   'DisableGameBarIntegration','RemoveGamingApps','DisableDeviceAutoAppDownload'}
        self.assertFalse(blocked.intersection(debloat.ITEMS))
        for item in debloat.CATALOG['items']:
            if item['kind'] == 'app':
                value = item['package'].lower()
                for protected in ['xbox','gaming','store','printing','printer','desktopappinstaller',
                                  'vclibs','ui.xaml','onedrive','edge','photos','calculator','notepad','paint']:
                    self.assertNotIn(protected, value)
                self.assertNotIn('*', value)

    def test_selection_validation_and_registry_paths(self):
        for invalid in ['RemoveGamingApps', 'anything; exit']:
            with self.assertRaises(ValueError): debloat.selection('selected', [invalid])
        with self.assertRaises(ValueError): debloat.selection('undo', ['ClearStartOnce'])
        base = SRC / 'vendor/win11debloat/Regfiles'
        for item in debloat.CATALOG['items']:
            if item['kind'] != 'registry': continue
            self.assertTrue((base / item['registry']).is_file(), item['id'])
            self.assertTrue((base / item['undo']).is_file() or (base/'Undo'/item['undo']).is_file(), item['id'])

    def test_real_plan_is_read_only_and_can_capture_registry_backup(self):
        result = debloat.execute('plan', debloat.selection('recommended'))
        self.assertTrue(result['ok'], result)
        self.assertGreater(result['backup_keys'], 0)
        self.assertEqual(set(debloat.selection('recommended')), {x['id'] for x in result['items']})

    def test_recommended_backend_only_touches_allowlist(self):
        api = main.Api.__new__(main.Api)
        tweaks = {key: Mock() for key in ['bing_search','ad_id','gamedvr','game_mode','hags','mitigations','context_menu','lockscreen']}
        api._tweaks = lambda: tweaks
        api._applied = set()
        result = main.Api.bulk_tweaks.__wrapped__(api, 'recommended')
        self.assertTrue(result['ok'])
        for key, tweak in tweaks.items():
            self.assertEqual(tweak.apply.call_count, int(key in debloat.RECOMMENDED_EXISTING))
            tweak.revert.assert_not_called()
        self.assertFalse(main.Api.bulk_tweaks.__wrapped__(api, 'all')['ok'])

    def test_pin_clear_runs_once_and_preserves_new_pins(self):
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder)/'pins-test.ps1'
            script.write_text(r'''
param($Source, $Folder)
$ErrorActionPreference='Stop'
$ast=[System.Management.Automation.Language.Parser]::ParseFile($Source,[ref]$null,[ref]$null)
$fn=$ast.Find({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Clear-StartPinsOnce'},$true)
. ([scriptblock]::Create($fn.Extent.Text))
function Replace-StartMenu { param($startMenuBinFile) Set-Content -LiteralPath $startMenuBinFile -Value 'empty'; return $true }
$one=Join-Path $Folder 'one.bin'; $two=Join-Path $Folder 'two.bin'; $marker=Join-Path $Folder 'marker.json'
$targets=@([pscustomobject]@{Sid='user1';Path=$one},[pscustomobject]@{Sid='user2';Path=$two})
Clear-StartPinsOnce $targets $marker
Set-Content -LiteralPath $one -Value 'my new pins'
Clear-StartPinsOnce $targets $marker
if((Get-Content $one) -ne 'my new pins') { throw 'Pins were erased on a repeat run' }
$saved=Get-Content $marker -Raw | ConvertFrom-Json
if($saved.Count -ne 2) { throw 'Incorrect per-user markers' }
''',encoding='utf-8')
            subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),
                            '-Source',str(SRC/'debloat_bridge.ps1'),'-Folder',folder],check=True,capture_output=True,text=True)


if __name__=='__main__': unittest.main()
