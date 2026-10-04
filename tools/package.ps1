param([string]$CertificateThumbprint = '', [string]$Publisher = 'CN=akasumitlamba', [string]$IdentityName = 'akasumitlamba.GROK')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$sdkRoot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
$sdk = Get-ChildItem -LiteralPath $sdkRoot -Directory | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'x64\makeappx.exe') } | Sort-Object Name -Descending | Select-Object -First 1
if (-not $sdk) { throw 'Install Windows SDK with MakeAppx and SignTool.' }
if (-not (Test-Path -LiteralPath 'dist\GROK\GROK.exe')) { throw 'Run tools/build.ps1 first.' }
$stagingRoot = Join-Path $projectRoot ('build\msix-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stagingRoot -Force | Out-Null
Copy-Item -LiteralPath 'dist\GROK\GROK.exe' -Destination $stagingRoot
Copy-Item -LiteralPath 'dist\GROK\_internal' -Destination $stagingRoot -Recurse
Copy-Item -LiteralPath 'assets' -Destination $stagingRoot -Recurse
[xml]$manifest = Get-Content -LiteralPath 'packaging\AppxManifest.xml'
$manifest.Package.Identity.Publisher = $Publisher
$manifest.Package.Identity.Name = $IdentityName
$manifest.Save((Join-Path $stagingRoot 'AppxManifest.xml'))
New-Item -ItemType Directory -Path 'release' -Force | Out-Null
& (Join-Path $sdk.FullName 'x64\makeappx.exe') pack /d $stagingRoot /p (Join-Path $projectRoot 'release\GROK.msix') /o
if ($LASTEXITCODE -ne 0) { throw 'MSIX validation or packing failed.' }
if ($CertificateThumbprint) {
    & (Join-Path $sdk.FullName 'x64\signtool.exe') sign /fd SHA256 /sha1 $CertificateThumbprint (Join-Path $projectRoot 'release\GROK.msix')
    if ($LASTEXITCODE -ne 0) { throw 'Signing failed.' }
    & (Join-Path $sdk.FullName 'x64\signtool.exe') verify /pa (Join-Path $projectRoot 'release\GROK.msix')
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Signature created, but trust verification failed. See installation instructions.' }
}
Get-FileHash -Algorithm SHA256 -LiteralPath 'release\GROK.msix' | Format-List
