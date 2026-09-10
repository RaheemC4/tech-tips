param([ValidateSet('status','plan','apply','undo')][string]$Mode,
      [string]$RequestFile)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$vendor = Join-Path $PSScriptRoot 'vendor\win11debloat'
$catalog = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'debloat_catalog.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$script:Params = @{ AppRemovalTarget = 'AllUsers' }
$script:UndoParams = @{}
$script:GuiWindow = $null
$script:CancelRequested = $false
$script:AppRemovalFailures = 0
$script:AppRemovalVerificationUnavailable = $false
$script:RegfilesPath = Join-Path $vendor 'Regfiles'
$script:AssetsPath = Join-Path $vendor 'Assets'
$script:AppsListFilePath = Join-Path $vendor 'Config\Apps.json'
$script:RegistryBackupsPath = Join-Path $env:LOCALAPPDATA 'TechLoungeTweaks\Debloat\Backups'
$script:Features = @{}
foreach ($feature in (Get-Content (Join-Path $vendor 'Config\Features.json') -Raw | ConvertFrom-Json).Features) {
    $script:Features[$feature.FeatureId] = $feature
}
# Load only function libraries, never the upstream interactive/default preset.
foreach ($group in @('Helpers','FileIO','Features','AppRemoval','Threading')) {
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $vendor "Scripts\$group") -Filter '*.ps1') {
        . $file.FullName
    }
}
foreach ($item in $catalog.items | Where-Object { $_.kind -eq 'registry' }) {
    $script:Features[$item.id] = [pscustomobject]@{
        FeatureId=$item.id; RegistryKey=$item.registry; RegistryUndoKey=$item.undo; Label=$item.title
    }
}
$build = [int](Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').CurrentBuildNumber
$markerPath = Join-Path $env:ProgramData 'TechLoungeTweaks\Debloat\cleared-start-profiles.json'
$cleared = @()
if (Test-Path -LiteralPath $markerPath) { $cleared = ConvertFrom-Json -InputObject (Get-Content -LiteralPath $markerPath -Raw) }
$cleared = @($cleared)

function Get-PinTargets {
    @(Get-CimInstance Win32_UserProfile | Where-Object { -not $_.Special -and $_.LocalPath } | ForEach-Object {
        $path = Join-Path $_.LocalPath 'AppData\Local\Packages\Microsoft.Windows.StartMenuExperienceHost_cw5n1h2txyewy\LocalState\start2.bin'
        if (Test-Path -LiteralPath $path) { [pscustomobject]@{ Sid=$_.SID; Path=$path } }
    })
}
function Write-Result($value) {
    Write-Output ('TL_RESULT:' + ($value | ConvertTo-Json -Depth 12 -Compress))
}
function Clear-StartPinsOnce {
    param([object[]]$Targets, [string]$MarkerFile)
    $done = @()
    if (Test-Path -LiteralPath $MarkerFile) { $done = ConvertFrom-Json -InputObject (Get-Content -LiteralPath $MarkerFile -Raw) }
    $done = @($done)
    foreach ($target in $Targets) {
        if ($target.Sid -in $done) { continue }
        if (-not (Replace-StartMenu -startMenuBinFile $target.Path)) { throw "Could not clear pins for $($target.Sid)." }
        $done += $target.Sid
        New-Item -ItemType Directory -Path (Split-Path $MarkerFile) -Force | Out-Null
        $temporaryMarker = $MarkerFile + '.tmp'
        ConvertTo-Json -InputObject @($done) | Set-Content -LiteralPath $temporaryMarker -Encoding UTF8
        Move-Item -LiteralPath $temporaryMarker -Destination $MarkerFile -Force
    }
}
try {
    $items = @($catalog.items)
    if ($Mode -ne 'status') {
        $requested = ConvertFrom-Json -InputObject (Get-Content -LiteralPath $RequestFile -Raw -Encoding UTF8)
        foreach ($id in $requested) {
            if ($id -notin $catalog.items.id) { throw "Unknown debloat option: $id" }
        }
        $items = @($catalog.items | Where-Object { $_.id -in $requested })
    }
    if ($Mode -eq 'plan') {
        $registryFeatures = @($items | Where-Object { $_.kind -eq 'registry' } | ForEach-Object { $script:Features[$_.id] })
        $snapshot = Get-RegistryBackupPayload -SelectedFeatures $registryFeatures -CreatedAt (Get-Date)
        Write-Result @{ok=$true; build=$build; backup_keys=@($snapshot.RegistryKeys).Count; items=@($items | Select-Object id,kind,package,registry,min_build)}
        exit 0
    }
    if ($Mode -eq 'status') {
        $packages = @(); $provisioned = @(); $appsReadable = $true
        try {
            $packages = @(Get-AppxPackage -AllUsers | Select-Object -ExpandProperty Name)
            $provisioned = @(Get-AppxProvisionedPackage -Online | Select-Object -ExpandProperty DisplayName)
        } catch { $appsReadable = $false }
        $rows = @()
        foreach ($item in $items) {
            $applied = $null
            if ($build -ge $item.min_build) {
                if ($item.kind -eq 'registry') { $applied = Test-FeatureApplied $item.id }
                elseif ($item.kind -eq 'app' -and $appsReadable) { $applied = ($item.package -notin $packages -and $item.package -notin $provisioned) }
                elseif ($item.kind -eq 'pins') {
                    $targets = @(Get-PinTargets)
                    $applied = $targets.Count -gt 0 -and @($targets | Where-Object { $_.Sid -notin $cleared }).Count -eq 0
                }
            }
            $rows += @{id=$item.id; applied=$applied; supported=($build -ge $item.min_build)}
        }
        Write-Result @{ok=$true;build=$build;items=$rows}
        exit 0
    }
    $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $admin) { throw 'Run Tech Lounge Tweaks as administrator to apply changes.' }
    $eligible = @($items | Where-Object { $build -ge $_.min_build })
    $registry = @($eligible | Where-Object { $_.kind -eq 'registry' })
    $backup = $null
    if ($registry.Count -gt 0) {
        # Abort before any changes if the upstream registry backup fails.
        $undoFeatures = @()
        if ($Mode -eq 'undo') {
            $undoFeatures = @($registry | ForEach-Object { $script:Features[$_.id] })
        }
        $backup = New-RegistrySettingsBackup -ActionableKeys @($registry.id) -ExtraFeatures $undoFeatures
        if (-not $backup) { throw 'Registry backup was not created; no changes applied.' }
    }
    $results = @(); $index = 0
    foreach ($item in $items) {
        $index++
        Write-Output ('TL_PROGRESS:' + (@{progress=($index / [double][Math]::Max(1,$items.Count));line=$item.title} | ConvertTo-Json -Compress))
        if ($build -lt $item.min_build) {
            $results += @{id=$item.id;ok=$true;skipped=$true;message="Needs Windows build $($item.min_build) or newer."}; continue
        }
        try {
            if ($item.kind -eq 'registry') {
                $regFile = if ($Mode -eq 'undo') { Resolve-UndoRegFilePath $item.undo } else { $item.registry }
                if (-not (Import-RegistryFile $item.title $regFile)) { throw 'Registry operation failed.' }
                if ($Mode -eq 'apply' -and -not (Test-FeatureApplied $item.id)) { throw 'Windows did not retain all requested registry values.' }
            } elseif ($Mode -eq 'undo') {
                $results += @{id=$item.id;ok=$true;skipped=$true;message='App removals and one-time pin clearing are not reversed by this button.'}; continue
            } elseif ($item.kind -eq 'app') {
                if (-not (Remove-SelectedApps @($item.package))) { throw 'App removal did not complete.' }
                if (@(Get-AppxPackage -Name $item.package -AllUsers).Count -gt 0 -or
                    @(Get-AppxProvisionedPackage -Online | Where-Object { $_.DisplayName -eq $item.package }).Count -gt 0) { throw 'The app is still installed or provisioned.' }
            } elseif ($item.kind -eq 'pins') {
                Clear-StartPinsOnce -Targets @(Get-PinTargets) -MarkerFile $markerPath
            }
            $results += @{id=$item.id;ok=$true;message='Completed. Sign out or restart to refresh Windows UI.'}
        } catch { $results += @{id=$item.id;ok=$false;message=$_.Exception.Message} }
    }
    Write-Result @{ok=(@($results | Where-Object {-not $_.ok}).Count -eq 0);items=$results;backup=$backup}
} catch {
    Write-Result @{ok=$false;message=$_.Exception.Message}
    exit 1
}
