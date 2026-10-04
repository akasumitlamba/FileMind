# Explicit developer action. Does not silently trust or export a private key.
$ErrorActionPreference = 'Stop'
$certificate = New-SelfSignedCertificate -Type Custom -Subject 'CN=akasumitlamba' -FriendlyName 'GROK local development' -CertStoreLocation 'Cert:\CurrentUser\My' -KeyUsage DigitalSignature -KeyExportPolicy NonExportable -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3','2.5.29.19={text}')
New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot '..\release') -Force | Out-Null
Export-Certificate -Cert $certificate -FilePath (Join-Path $PSScriptRoot '..\release\GROK-development.cer') | Out-Null
Write-Host "Development signing thumbprint: $($certificate.Thumbprint)"
Write-Host 'Trust only on your own test machine. See docs/INSTALL.md. This is not a Store certificate.'
