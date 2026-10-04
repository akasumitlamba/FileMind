# Installation and signing

## Portable build

Run `dist/GROK/GROK.exe`. Keep `_internal` next to it. This application does not require administrator privileges for normal use. A development executable may show a Windows reputation warning; a public release should use appropriate signing/distribution.

## MSIX

`release/GROK.msix` targets Windows x64 with version 1.0.0.0. Local development publisher: `CN=akasumitlamba`. Application ID: `GROK`. Package name: `akasumitlamba.GROK`.

Build with `tools/build.ps1`, then `tools/package.ps1`. The latter uses MakeAppx validation and supports `-CertificateThumbprint`, `-Publisher` and `-IdentityName` overrides.

### Local development signing

1. Run `tools/development-certificate.ps1` once. It creates a non-exportable code-signing key in `Cert:\CurrentUser\My` and exports only its public certificate to `release/GROK-development.cer`.
2. Run `tools/package.ps1 -CertificateThumbprint '<printed thumbprint>'`.
3. On a test machine you control, verify the public certificate’s subject and thumbprint. Trust requires an **administrator PowerShell**:

```powershell
Import-Certificate -FilePath '.\release\GROK-development.cer' -CertStoreLocation 'Cert:\LocalMachine\TrustedPeople'
```

4. From a normal PowerShell window, install for your user:

```powershell
Add-AppxPackage -Path '.\release\GROK.msix'
```

5. Launch **GROK** from Start. Verify the dock, shortcut, file browsing and Settings/About. Test changes only in disposable folders.

Trusting this certificate permits installation of other packages signed with its key too. Trust only your own test certificate. Do not add it to Trusted Root Certification Authorities. Never distribute private keys. The development script does not automatically change system trust.

Official reference: [Microsoft MSIX signing guide](https://learn.microsoft.com/en-us/windows/msix/package/sign-msix-package-guide).

### Remove

Disconnect AI keys in Settings before uninstalling; Credential Manager entries can survive removal. Uninstall GROK through Windows Settings → Apps. Delete residual local settings only if no longer needed. Remove the exact development certificate from Local Machine Trusted People when testing is finished, after checking no other intended package depends on it.

### Microsoft Store preparation

Reserve the app in Partner Center, use its exact package identity and publisher, and regenerate the package. Explain `runFullTrust` as necessary for a user-permission Windows desktop file browser. Complete current certification requirements, privacy/support URLs, screenshots, age ratings and target-device QA. The local certificate is not Store signing, and this build is not a submitted or certified Store product.

## Startup

The executable can register a per-user Run entry when explicitly enabled in Settings. MSIX registry virtualization/startup policy can affect this path; packaged startup needs target-machine validation. An approved StartupTask extension is a future Store packaging improvement. Startup is off by default.
