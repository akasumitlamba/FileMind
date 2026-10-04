param([switch]$SkipTests)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$python = if (Test-Path -LiteralPath '.venv\Scripts\python.exe') { Join-Path $projectRoot '.venv\Scripts\python.exe' } else { 'python' }
if (-not $SkipTests) {
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
}
& $python tools/make_assets.py
& $python -m PyInstaller --noconfirm GROK.spec
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
& $python tools/collect_licenses.py
if ($LASTEXITCODE -ne 0) { throw 'License collection failed' }
Write-Host "Built: $projectRoot\dist\GROK\GROK.exe"
