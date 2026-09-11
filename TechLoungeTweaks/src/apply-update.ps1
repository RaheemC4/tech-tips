param([int]$AppProcess, [string]$Source, [string]$Destination)
$ErrorActionPreference = 'Stop'
$sourcePath = [IO.Path]::GetFullPath($Source).TrimEnd('\')
$targetPath = [IO.Path]::GetFullPath($Destination).TrimEnd('\')
$updateRoot = Join-Path $env:LOCALAPPDATA 'TechLoungeTweaks\Updates'
$updateRoot = [IO.Path]::GetFullPath($updateRoot).TrimEnd('\')
$backupPath = $targetPath + '.previous-' + [guid]::NewGuid().ToString('N')
$stagePath = $targetPath + '.staged-' + [guid]::NewGuid().ToString('N')
$moved = $false
try {
    if (-not $sourcePath.StartsWith($updateRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or
        $targetPath -eq [IO.Path]::GetPathRoot($targetPath).TrimEnd('\') -or
        $sourcePath.StartsWith($targetPath + '\', [StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath (Join-Path $targetPath 'TechLoungeTweaks.exe')) -or
        -not (Test-Path -LiteralPath (Join-Path $sourcePath 'TechLoungeTweaks.exe'))) {
        throw 'Invalid update source or destination.'
    }
    $running = Get-Process -Id $AppProcess -ErrorAction SilentlyContinue
    if ($running -and -not $running.WaitForExit(60000)) { throw 'App did not close. Update was not applied.' }
    $sourceInfo = Get-Content -LiteralPath (Join-Path $sourcePath '_internal\build-info.json') -Raw | ConvertFrom-Json
    $targetInfo = Get-Content -LiteralPath (Join-Path $targetPath '_internal\build-info.json') -Raw | ConvertFrom-Json
    $sourceChannel = if ($sourceInfo.channel) { $sourceInfo.channel } else { 'stable' }
    $targetChannel = if ($targetInfo.channel) { $targetInfo.channel } else { 'stable' }
    if ($sourceChannel -notin @('stable','nuitka') -or $sourceChannel -ne $targetChannel) {
        throw 'App update channel mismatch. Current app retained.'
    }
    # Prepare the exact contents first. Copying a directory onto a destination
    # recreated by a lingering process can silently nest the app one level down.
    [IO.Directory]::CreateDirectory($stagePath) | Out-Null
    Get-ChildItem -LiteralPath $sourcePath -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $stagePath -Recurse -Force
    }
    if (-not (Test-Path -LiteralPath (Join-Path $stagePath 'TechLoungeTweaks.exe')) -or
        -not (Test-Path -LiteralPath (Join-Path $stagePath '_internal\build-info.json'))) {
        throw 'Staged update is incomplete. Current app retained.'
    }
    # WebView children and antivirus can briefly retain handles after shutdown.
    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        try { [IO.Directory]::Move($targetPath, $backupPath); $moved = $true; break }
        catch { if ($attempt -eq 9) { throw }; Start-Sleep -Milliseconds 700 }
    }
    # Directory.Move fails if the destination exists; it never nests folders.
    [IO.Directory]::Move($stagePath, $targetPath)
    Start-Process -FilePath (Join-Path $targetPath 'TechLoungeTweaks.exe') -WorkingDirectory $targetPath -WindowStyle Hidden
    "Updated successfully. Previous app kept at $backupPath" | Set-Content -LiteralPath (Join-Path $updateRoot 'last-update.txt')
} catch {
    $failure = $_.Exception.Message
    if ($moved) {
        # Retain the failed candidate for diagnostics; never delete the old app.
        if (Test-Path -LiteralPath $targetPath) {
            Move-Item -LiteralPath $targetPath -Destination ($targetPath + '.failed-' + [guid]::NewGuid().ToString('N'))
        }
        [IO.Directory]::Move($backupPath, $targetPath)
    }
    "Update failed: $failure. Previous app retained." | Set-Content -LiteralPath (Join-Path $updateRoot 'last-update.txt')
    if (-not (Get-Process -Id $AppProcess -ErrorAction SilentlyContinue) -and
        (Test-Path -LiteralPath (Join-Path $targetPath 'TechLoungeTweaks.exe'))) {
        Start-Process -FilePath (Join-Path $targetPath 'TechLoungeTweaks.exe') -WorkingDirectory $targetPath -WindowStyle Hidden
    }
}
