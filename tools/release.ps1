param([ValidateSet('prepare', 'push')][string]$Mode = 'prepare')
$ErrorActionPreference = 'Stop'
try {
    try { $Host.UI.RawUI.ForegroundColor = 'Cyan' } catch { }
    Write-Host 'Tech Lounge Tweaks - preparing your personal release' -ForegroundColor Cyan
    foreach ($releaseLink in @('https://github.com/RaheemC4/tech-tips', 'https://github.com/RaheemC4/tech-tips/releases/latest/download/TechLoungeTweaks.zip')) {
        if ($env:WT_SESSION) {
            $escape = [char]27
            Write-Host "$escape]8;;$releaseLink$escape\$releaseLink$escape]8;;$escape\" -ForegroundColor Cyan
        } else { Write-Host $releaseLink -ForegroundColor Cyan }
    }
    $releaseRoot = Split-Path -Parent $PSScriptRoot
    $releasePython = Join-Path $releaseRoot 'TechLoungeTweaks\.build-venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $releasePython)) {
        throw 'Build environment missing. Follow HOW-TO-UPLOAD.txt to create it first.'
    }
    & $releasePython (Join-Path $PSScriptRoot 'release.py') "--$Mode"
    exit $LASTEXITCODE
} catch {
    Write-Error $_
    exit 1
}
