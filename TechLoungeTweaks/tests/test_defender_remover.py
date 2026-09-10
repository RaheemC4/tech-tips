import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import defender_remover as remover

class RemoverTests(unittest.TestCase):
    def setUp(self):
        self.state=patch.object(remover,'_state',{'running':False,'phase':'idle'})
        self.job=patch.object(remover,'_job',None)
        self.state.start();self.job.start()
        self.addCleanup(self.state.stop);self.addCleanup(self.job.stop)

    def test_requires_explicit_mode_confirmation_and_valid_payload(self):
        with patch.object(remover.subprocess,'Popen') as spawn:
            for mode,confirmed in [('all',False),('bad',True),(True,True)]:
                self.assertFalse(remover.launch(mode,confirmed)['ok'])
            with tempfile.TemporaryDirectory() as root:
                self.assertFalse(remover.launch('all',True,root)['ok'])
            spawn.assert_not_called()
        self.assertTrue((remover.validate_bundle()/'payload/runner.ps1').is_file())

    def test_launch_is_hidden_and_worker_completion_is_independent(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(remover.tempfile,'mkdtemp',return_value=folder), patch.object(remover.subprocess,'Popen') as spawn, patch.object(remover.subprocess,'run',return_value=Mock(stdout='S-1-5-21-1-2-3-1001')):
            result=remover.launch('antivirus',True)
            self.assertTrue(result['ok'])
            args=spawn.call_args.args[0]
            self.assertIn('/SW:0',args);self.assertIn('-NonInteractive',args)
            self.assertEqual(args[args.index('-Mode')+1],'antivirus')
            self.assertEqual(spawn.call_args.kwargs['creationflags'],0x08000000)
            self.assertTrue(remover.is_running())
            self.assertFalse(remover.launch('all',True)['ok'])
            Path(folder,'status.json').write_text(json.dumps({'running':False,'phase':'failed','message':'partial failure','progress':42}))
            self.assertFalse(remover.is_running())
            self.assertEqual(remover.status()['message'],'partial failure')

    def test_adapter_has_no_forced_restart_or_interactive_console(self):
        script=(remover.validate_bundle()/'payload/runner.ps1').read_text()
        for forbidden in ['shutdown /','Read-Host','cmd.exe /','Register-ScheduledTask']:
            self.assertNotIn(forbidden,script)
        self.assertIn("Report 'failed'",script)
        self.assertIn('Remove-Item -LiteralPath',script)

    def test_recommendation_uses_present_unknown_and_running_components(self):
        state={'antivirus':True,'security_app':True,'files':True,'engine_running':True}
        self.assertEqual(remover.recommend(state)[0],'all')
        state.update(antivirus=False,security_app=False)
        self.assertIsNone(remover.recommend(state)[0])
        self.assertIn('Restart',remover.recommend(state)[1])
        state['engine_running']=False
        self.assertEqual(remover.recommend(state)[0],'files')
        state['security_app']=None
        self.assertIsNone(remover.recommend(state)[0])
        self.assertIn('unavailable',remover.recommend(state)[1])
        state.update(security_app=False,files=False)
        self.assertIn('No antivirus',remover.recommend(state)[1])

    def test_original_security_script_failure_does_not_abort_later_stages(self):
        import subprocess
        with tempfile.TemporaryDirectory() as folder:
            script=Path(__file__).resolve().parents[1]/'resources/defender-remover/payload/runner.ps1'
            # Extract ONLY two function definitions. Never invoke the runner or
            # publisher script. Every AppX/native operation here is a stub.
            code = r"""
param($SourcePath,$LogPath)
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($SourcePath,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Parse failure'}
foreach($name in @('Record-Warning','Remove-SecurityApp')) {
 $fn=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name},$true)
 . ([scriptblock]::Create($fn.Extent.Text.Replace('$PSScriptRoot','$fixturePayloadRoot')))
}
$warnings=[Collections.Generic.List[string]]::new()
$logFile=$LogPath
$fixturePayloadRoot=Split-Path $SourcePath
$jobRoot=Split-Path $LogPath
function Native($program,$arguments) {
 if(-not ($arguments | Where-Object {$_ -like '*RemoveSecHealthApp.ps1'})){throw 'Wrong upstream script'}
 throw 'Fixture AppX failure'
}
function Get-WinEvent { return @() }
function Get-AppxPackage { return @() }
function Get-AppxProvisionedPackage { return @() }
Remove-SecurityApp
if($warnings.Count -ne 1 -or $warnings[0] -notlike '*Fixture AppX failure*'){throw 'Failure was swallowed or sequence aborted'}
$warnings.Clear()
function Get-AppxProvisionedPackage { [pscustomobject]@{DisplayName='Microsoft.SecHealthUI';PackageName='Microsoft.SecHealthUI_fixture'} }
function Remove-AppxProvisionedPackage { throw 'Unexpected blind retry' }
Remove-SecurityApp
if($warnings.Count -ne 2 -or $warnings[1] -notlike '*registration*'){throw 'Registration failure not reported'}
Write-Output 'PASS' 
"""
            fixture=Path(folder)/'test.ps1';fixture.write_text(code,encoding='utf-8')
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(fixture),str(script),str(Path(folder)/'log.txt')],capture_output=True,text=True,creationflags=0x08000000)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('PASS',result.stdout)

    def test_open_log_folder_only_uses_current_job(self):
        with patch.object(remover.os,'startfile') as open_folder:
            self.assertFalse(remover.open_log_folder()['ok'])
            open_folder.assert_not_called()
            with tempfile.TemporaryDirectory() as folder, patch.object(remover,'_job',Path(folder)):
                self.assertTrue(remover.open_log_folder()['ok'])
                open_folder.assert_called_once_with(folder,'open')

    def test_partial_install_recommends_files_not_combined_removal(self):
        state=dict(antivirus=False,security_app=True,files=True,engine_running=False)
        self.assertEqual(remover.recommend(state)[0],'files')
        state.update(security_app=False,security_registration_only=True)
        self.assertEqual(remover.recommend(state)[0],'files')
        state.update(files=False)
        self.assertIsNone(remover.recommend(state)[0])
        self.assertIn('registration',remover.recommend(state)[1])
        state.update(antivirus=True,security_registration_only=False)
        self.assertEqual(remover.recommend(state)[0],'antivirus')

    def test_provisioned_only_family_and_policy_failure(self):
        import subprocess
        code=r'''
param($SourcePath)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($SourcePath,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Parse failure'}
foreach($fn in $ast.EndBlock.Statements | Where-Object {$_ -is [Management.Automation.Language.FunctionDefinitionAst]}) {
 . ([scriptblock]::Create($fn.Extent.Text))
}
$script:called=@();$script:reject=$false
function Get-AppxProvisionedPackage { [pscustomobject]@{DisplayName='Microsoft.SecHealthUI';PackageName='Microsoft.SecHealthUI_1000.26100.8036.0_x64__8wekyb3d8bbwe'} }
function Get-AppxPackage { @() }
function Set-NonRemovableAppsPolicy {
 param([switch]$Online,$PackageFamilyName,$NonRemovable,$ErrorAction)
 if($PackageFamilyName -ne 'Microsoft.SecHealthUI_8wekyb3d8bbwe' -or $NonRemovable -ne 0){throw 'Wrong policy identity'}
 $script:called+='policy'
 if($script:reject){throw 'Policy fixture refusal'}
}
function Remove-AppxProvisionedPackage {
 param([switch]$Online,[switch]$AllUsers,$PackageName,$ErrorAction)
 if(-not $AllUsers -or $PackageName -ne 'Microsoft.SecHealthUI_1000.26100.8036.0_x64__8wekyb3d8bbwe'){throw 'Wrong removal target'}
 $script:called+='remove'
}
function Remove-AppxPackage {throw 'Unexpected installed package removal'}
Remove-SecurityPackages
if(($script:called -join ',') -ne 'policy,remove'){throw 'Provisioned-only policy was skipped'}
$script:reject=$true;$script:called=@();$failed=$false
try {Remove-SecurityPackages} catch {$failed=$true}
if(-not $failed -or ($script:called -join ',') -ne 'policy'){throw 'Removal continued after policy failure'}
$failed=$false
try {Get-SecurityFamily 'OtherApp_1.0.0.0_x64__8wekyb3d8bbwe'} catch {$failed=$true}
if(-not $failed){throw 'Unrelated identity accepted'}
Write-Output 'PASS'
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture=Path(folder)/'test.ps1';fixture.write_text(code,encoding='utf-8')
            source=Path(__file__).resolve().parents[1]/'resources/defender-remover/payload/RemoveSecHealthApp.ps1'
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(fixture),str(source)],capture_output=True,text=True,creationflags=0x08000000)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('PASS',result.stdout)

    def test_security_only_worker_skips_all_antivirus_actions(self):
        import subprocess
        code=r'''
param($SourcePath)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($SourcePath,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Parse failure'}
$body=($ast.EndBlock.Statements | Where-Object {$_ -is [Management.Automation.Language.TryStatementAst]} | Select-Object -Last 1).Extent.Text
$Mode='all';$warnings=[Collections.Generic.List[string]]::new();$script:security=$false;$script:complete=$false
function Get-Service {@()}
function Get-Process {param($Name,$ErrorAction);if($Name -contains 'smartscreen'){throw 'Unrelated process targeted'};@()}
function Stop-Process {}
function Remove-SecurityApp {$script:security=$true}
function Report($phase,$percent,$text){if($phase -eq 'complete'){$script:complete=$true};if($phase -eq 'failed'){throw $text}}
function Get-ChildItem {throw 'Registry stage must not execute'}
function Native {throw 'Antivirus native stage must not execute'}
function Remove-ExactDirectory {throw 'File stage must not execute'}
function Remove-Item {throw 'Deletion must not execute'}
function Record-Warning {throw 'Unexpected operation'}
. ([scriptblock]::Create($body))
if(-not $script:security -or -not $script:complete){throw 'Security-only operation failed'}
# Even if Defender appears after the UI confirmed Security-only scope, never
# broaden that confirmation into antivirus or other protection removal.
$Mode='security';$script:security=$false;$script:complete=$false
function Get-Service { [pscustomobject]@{Name='WinDefend'} }
. ([scriptblock]::Create($body))
if(-not $script:security -or -not $script:complete){throw 'Explicit Security-only scope was not preserved'}
Write-Output 'PASS'
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture=Path(folder)/'test.ps1';fixture.write_text(code,encoding='utf-8')
            source=Path(__file__).resolve().parents[1]/'resources/defender-remover/payload/runner.ps1'
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(fixture),str(source)],capture_output=True,text=True,creationflags=0x08000000)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('PASS',result.stdout)
