# Native UI adapter for the supported DISM/SPP edition-change paths used by MAS.
# MAS 3.12 source/credit: vendor/mas/UPSTREAM.md. Unlike its CLI, no forced reboot.
param([ValidateSet('query','apply')][string]$Mode, [string]$Target)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
function Result($data) { Write-Output ('TL_RESULT:' + ($data | ConvertTo-Json -Compress -Depth 5)) }
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $current = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').EditionID
    if ([int]$os.ProductType -ne 1 -or [int]$os.BuildNumber -lt 22000) { throw 'The integrated edition chooser supports Windows 11 desktop editions.' }
    $dism = Join-Path $env:SystemRoot 'System32\dism.exe'
    $output = & $dism /English /Online /Get-TargetEditions 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'Windows could not list target editions. Run as administrator and check Windows servicing.' }
    $targets = @($output | ForEach-Object {
        if ([string]$_ -match 'Target Edition\s*:\s*([A-Za-z0-9]+)') { $matches[1] }
    } | Where-Object { $_ -ne $current } | Select-Object -Unique)
    if ($Mode -eq 'query') { Result @{ok=$true;current=$current;name=$os.Caption;targets=$targets}; exit 0 }
    if ($Target -notin $targets) { throw 'That edition is no longer an available target. Refresh the edition list.' }
    foreach ($path in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending',
                       'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired')) {
        if (Test-Path $path) { throw 'Windows has a pending restart. Restart the PC before changing edition.' }
    }
    # Same pkeyhelper entry points and channel order as the bundled MAS script.
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class TLEdition {
 [DllImport("pkeyhelper.dll", CharSet=CharSet.Unicode)]
 public static extern int GetEditionIdFromName(string name, out int id);
 [DllImport("pkeyhelper.dll", CharSet=CharSet.Unicode)]
 public static extern int SkuGetProductKeyForEdition(int id, string channel, out string key, out string extra);
 [DllImport("DismApi.dll", CharSet=CharSet.Unicode)]
 public static extern int DismInitialize(int level, string log, string scratch);
 [DllImport("DismApi.dll", CharSet=CharSet.Unicode)]
 public static extern int DismOpenSession(string path, string windows, string system, out uint session);
 [DllImport("DismApi.dll", CharSet=CharSet.Unicode)]
 public static extern int _DismSetEdition(uint session, string edition, string key, IntPtr cancel, IntPtr progress, IntPtr data);
 [DllImport("DismApi.dll")] public static extern int DismCloseSession(uint session);
 [DllImport("DismApi.dll")] public static extern int DismShutdown();
}
'@
    $sku=0
    $rc=[TLEdition]::GetEditionIdFromName($Target,[ref]$sku)
    if ($rc -ne 0 -or $sku -eq 0) { throw 'Windows could not resolve the target edition.' }
    $key=''; $extra=''
    foreach ($channel in @('Retail','OEM:NONSLP','OEM:DM','Volume:MAK','Volume:GVLK','PGS:TB','Retail:TB:Eval')) {
        $candidate=''
        $rc=[TLEdition]::SkuGetProductKeyForEdition($sku,$channel,[ref]$candidate,[ref]$extra)
        if ($rc -eq 0 -and $candidate -match '^[A-Z0-9]{5}(-[A-Z0-9]{5}){4}$') { $key=$candidate; break }
    }
    if (-not $key) { throw 'Windows does not supply a suitable edition-switch key for this target.' }
    if ($current -like 'Core*') {
        $session=[uint32]0
        try {
            $rc=[TLEdition]::DismInitialize(2,$null,$null)
            if ($rc -ne 0) { throw "DISM initialization failed ($rc)." }
            $rc=[TLEdition]::DismOpenSession('DISM_{53BFAE52-B167-4E2F-A258-0A37B57FF845}',$null,$null,[ref]$session)
            if ($rc -ne 0) { throw "DISM session failed ($rc)." }
            $rc=[TLEdition]::_DismSetEdition($session,$Target,$key,[IntPtr]::Zero,[IntPtr]::Zero,[IntPtr]::Zero)
            if ($rc -notin @(0,3010)) { throw "Edition change failed ($rc)." }
        } finally {
            if ($session -ne 0) { [void][TLEdition]::DismCloseSession($session) }
            [void][TLEdition]::DismShutdown()
        }
    } else {
        $service=Get-CimInstance SoftwareLicensingService
        $result=Invoke-CimMethod -InputObject $service -MethodName InstallProductKey -Arguments @{ProductKey=$key}
        if ($result.ReturnValue -ne 0) { throw "Windows rejected the edition change ($($result.ReturnValue))." }
        Invoke-CimMethod -InputObject $service -MethodName RefreshLicenseStatus | Out-Null
    }
    Result @{ok=$true;restart_required=$true;target=$Target;message='Edition-change request accepted. Save your work and restart Windows to finish, then refresh status. The new edition may need activation.'}
} catch { Result @{ok=$false;message=$_.Exception.Message}; exit 1 }
