param([ValidateSet('prepare', 'push')][string]$Mode = 'prepare')
$ErrorActionPreference = 'Stop'
try {
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
