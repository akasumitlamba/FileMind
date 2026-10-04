# GROK 1.0.0 handoff

Made by akasumitlamba. Graphical Resource Organization Kit.

## Implemented

Python/PySide6 desktop application with native Windows integrations, neutral black styling and original line icons. Compact two-button Files/Chat dock (42 × 86 logical pixels). Configurable sidebar width, monitor/work-area handling, pin/auto-hide, global shortcut, and side-arrow expansion into a full-work-area file-and-chat split layout.

File browsing supports list/grid, metadata selection (Name plus one detail at narrow width, two at intermediate width, three in wide/full workspace), sorting by name/type/size/modified in both directions, path entry, breadcrumbs, history, favorites, known folders and drives. File operations remain in context menus and keyboard shortcuts; the footer is dedicated to views and sorting.

OpenAI, Gemini, xAI, Claude, DeepSeek, Groq, Mistral, OpenRouter and Together AI provider adapters; Windows Credential Manager; model configuration, test/disconnect, conversational UI and reviewed plain-text attachments. Chat is discoverable even when external AI is disabled. File-changing AI tools, conversions and terminal access are future scope, documented separately.

Static website with homepage, download, about, privacy and terms. All assets are local. No GROK backend, accounts, telemetry or automatic external file processing.

## Build and output

- Development: `python src/main.py`
- Tests: `.venv\Scripts\python -m pytest -q`
- Build: `tools\build.ps1`
- Package: `tools\package.ps1 -CertificateThumbprint <your local signing thumbprint>`
- Executable: `dist/GROK/GROK.exe`; keep `_internal` beside it.
- MSIX: `release/GROK.msix`
- Public development certificate: `release/GROK-development.cer`
- Website: `website/index.html`
- Isolated executable validation: `dist\GROK\GROK.exe --smoke-test build\package-smoke-final.json`

The spec excludes an incompatible ICU DLL that the bundler otherwise discovers through the machine environment. Windows 10 19041+ supplies the required system ICU API.

## Validation and remaining gates

57 automated tests pass. The corrected frozen executable passed an isolated launch/file-model/dock/geometry/icon test. Interactive expansion, search and Escape were checked before the user stopped desktop automation. See QA.md for evidence and the unexecuted physical interoperability matrix.

MSIX is locally development-signed. Installation was attempted and blocked by Windows certificate trust (0x800B0109). The user chose to leave installation pending. Installed-app behavior is therefore unverified; no administrator trust settings were changed. Live provider requests were not tested with real keys. Store identity/signing, full drag/drop/device testing and third-party licensing review remain release gates.

This handoff distinguishes implemented software from production certification. Do not describe the original full acceptance checklist as complete.

UI refinement: compact 42 x 86 dock, header expansion control, tight breadcrumbs, one bottom navigation/view bar, trigger-anchored sort menus, integrated chat composer, removable multi-file attachment chips and highlighted selection-to-chat action. Chat is saved locally per provider; sent attachment text is retained with the conversation. Supported attachment content remains UTF-8 text and folder listings.
