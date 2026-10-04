# GROK: shared project context

This is the handoff for human developers and AI coding assistants. Read this file before changing the project, then inspect current source and tests. Update this file when architecture, behavior, or verified status changes.

## Project identity

- Product: GROK, Graphical Resource Organization Kit; independent of xAI Grok.
- Owner: akasumitlamba.
- Repository: https://github.com/akasumitlamba/grok-files (private).
- Platform: Windows 10 build 19041+ / Windows 11, x64.
- Stack: Python 3.11+, PySide6 6.10.2, PyInstaller, Windows SDK MakeAppx and SignTool.
- Version: application 1.0.0; MSIX 1.0.0.0.
- Primary application deliverable: MSIX. The standalone build is a development/QA artifact, not proof of MSIX installation.

## Product purpose and scope

A compact right-edge desktop dock opens a black file browser or AI chat. The long-term purpose is AI-assisted organization, file editing and document conversion. Today the app supports ordinary file management and reviewed text chat attachments. AI file mutations, terminal/code execution, Office/PDF conversion and tool execution are NOT implemented. See docs/AI-TOOLS-ROADMAP.md before extending that scope.

## Current behavior to preserve

- Two independent 40 x 40 Files/Chat buttons, 4px apart, inside a 42 x 86 logical-pixel dock. No tall background below the controls.
- Files always opens the Files page; dock Chat opens Chat without attaching selected files.
- Neutral black UI, thin scrollbars, compact breadcrumbs, one bottom navigation/view toolbar, anchored menus, adaptive list columns, list/grid and full-work-area files/chat split.
- Selection mode is explicitly toggled by the checkbox action beside Search. Disabled mode reserves no checkbox gutter. Ctrl/Shift selection remains available.
- Folder arrows appear only when loaded children exist; immediate child folders are fetched asynchronously to distinguish empty folders.
- Selecting files highlights the bottom AI Chat action. Clicking it queues attachments, clears selection and opens chat. Attachments are removable and not persisted as pending attachments.
- Chat history is local, unencrypted JSON per provider. Preserve existing history; do not delete user preferences or chats to fix UI problems.
- Nine provider adapters: OpenAI, Gemini, xAI, Claude, DeepSeek, Groq, Mistral, OpenRouter, Together AI. Users supply API keys and model IDs. No bundled keys or automatic requests.
- Reviewed attachments: UTF-8 text up to 100 KB per file, or up to 500 folder names; up to ten attachments. Sent text is retained in chat history.
- File mutations refuse overwrites/merges and reject reparse-point traversal. Preserve cancellation/source-retention behavior.

## Architecture map

| Path | Purpose |
|---|---|
| src/main.py | QApplication startup and single-instance lock; isolated --smoke-test |
| src/grok/ui.py | Window/dock, views, settings, chat persistence and workflows |
| src/grok/browser.py | Proxy model, tree/grid, selection delegate, drag/drop |
| src/grok/dock.py | Monitor work-area geometry |
| src/grok/files.py | Validated file operations |
| src/grok/windows.py | Credential Manager, shell, shortcuts, known folders |
| src/grok/ai.py | HTTPS adapters, sanitized failures, redirect rejection |
| src/grok/storage.py | Preferences and navigation history |
| src/grok/workers.py | Background jobs and COM setup |
| tests/ | Pytest and offscreen Qt regression tests |
| tools/ | Build, package, assets, website and preview utilities |
| website/ | Generated static site; edit tools/site.py for generated page content |

## Setup and validation

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe src/main.py
.\tools\build.ps1
.\dist\GROK\GROK.exe --smoke-test build/package-smoke.json
.\tools\package.ps1 -CertificateThumbprint '<local signing certificate thumbprint>'
```

Use disposable fixtures for mutations and synthetic text for chat tests. Real API tests may incur charges and transmit content. Normal file browsing requires neither AI nor network access. Tests use offscreen Qt; those tests alone cannot prove native Windows rendering correctness.

## Dock failures and regression requirements

1. Shared QPushButton stylesheet min-height overrode fixed sizing. Dock-specific style now sets its full button dimensions.
2. A delayed native resize after animation left a tall window. settle_dock_bounds reapplies the compact geometry after the transition.
3. Computing a mask from child positions before the first show hid both icons on cold launch. The dock now uses fixed local rectangles (1,1,40,40) and (1,45,40,40).

For dock changes verify cold launch, repeated animated expand/collapse, Files versus Chat routing, native DPI and monitor changes. Do not declare the dock fixed from offscreen screenshots alone.

## Release state: 4 October 2026

57 automated tests passed. Native startup visibility was inspected on the rebuilt executable after the mask correction; earlier native repeated animation checks verified compact bounds. Live provider accounts and the complete device/drag-drop matrix remain unverified. Read docs/QA.md and docs/MANUAL-TESTS.md.

MSIX is signed with a local development certificate. Windows trust verification fails until the user trusts that certificate. Installation was previously blocked with 0x800B0109, and the user explicitly left installation pending. No administrator trust changes were made. Do not describe the MSIX as installed, Store-certified, or publicly trusted.

PyInstaller excludes incompatible PATH-discovered ICU DLLs in GROK.spec. Do not remove that workaround without validating a clean Windows startup. Keep the full _internal directory for standalone builds. Never include private certificate keys, API keys, local settings, chat history, .venv, build output or personal files in Git.

## Collaboration rules

Make scoped changes and preserve unrelated work. Keep source, tests, context and release notes consistent. Distinguish implemented features, automated checks, native observations and unverified behavior. Commit source before tagging a release. Release assets belong in GitHub Releases, not Git history. Do not invent a license or change repository visibility without the owner asking.

## Minor usability refinements

- The sort menu marks the currently active sort field.
