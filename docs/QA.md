# QA report — GROK 1.0.0

Environment: Windows 11 build 26200, x64; Python 3.13.5; PySide6 6.10.2. Updated 3 October 2026.

## Executed

- **57 automated tests passed**, including attachment queue deduplication/removal and per-provider local chat restoration across window recreation.
- Real disposable-directory copy, nested copy, move, rename, folder creation, collision batch preflight, self-copy rejection and cancellation source retention.
- Windows Credential Manager synthetic-key add/read/remove. No real provider credentials used.
- Settings/favorites persistence, malformed settings recovery and navigation history branching.
- Geometry tests with positive and negative screen origins, constrained work areas and small screens.
- Qt widget navigation, invalid paths, back/forward/up, direct address Enter, local search, clipboard cut/paste and async transfer completion.
- Compact 42 × 86 dock; 420-wide panel; full-work-area split layout; returning to sidebar; discoverable chat; list/grid switching; ascending/descending sorting; adaptive column limits.
- Provider request construction and mocked successful HTTP responses for OpenAI, Gemini, xAI, Claude, DeepSeek, Groq, Mistral, OpenRouter and Together AI. Sanitized 401/403/404/429/503 and offline errors; invalid-model network prevention; redirect rejection.
- Interactive desktop observation of black UI and Settings; click-to-expand, filename search with a disposable fixture and Escape-to-collapse verified visually. Further Windows UI automation was stopped by the user with physical Escape; it was not resumed.
- Real Qt renders captured for sidebar, grid, expanded workspace and compact dock with synthetic files.
- Website loaded in the in-app browser; narrow viewport visually inspected. Static link validation is performed via tools/check_site.py after the package is copied to the download folder.
- MakeAppx successfully validated and created an MSIX. SignTool signed it using the local development certificate.
- Installation was attempted and Windows returned **0x800B0109** (untrusted development signing certificate). The user explicitly chose to leave installation pending; no system trust changes were made.

## Release gates and limits

- Installed MSIX launch/update/uninstall and packaged startup remain pending certificate trust and installation testing.
- Live provider calls require user API credentials and billing; only transport fixtures were tested.
- Cross-application drag/drop, actual Recycle Bin deletion, shell Open with/Properties, physical monitor removal, DPI/taskbar matrix, UNC/network failure, locked files and disk-full behavior still require target-machine acceptance. Do not infer these passed from unit tests.
- The first frozen executable failed to load QtWidgets because the bundler collected an incompatible ICU library from the environment. The spec now excludes that library and uses the supported Windows system ICU API. The corrected frozen executable passed its isolated smoke test: dock dimensions, folder loading, file count, expansion width, work-area bounds, icon loading and visible item count. Final repeat evidence is written to build/package-smoke-final.json.
- AI editing, conversions and terminal access are future scope, with a proposed permission model in AI-TOOLS-ROADMAP.md. They are not implemented.
- No Store submission, certification, public website deployment or externally trusted signing has been performed.

This is a functioning implementation with automated and limited interactive validation, not a claim that the entire original production acceptance matrix is complete. See MANUAL-TESTS.md for the remaining matrix.

Latest refinement: 57 automated checks passed. Nine provider adapters use mocked transport tests; live API accounts have not been tested. Explicit selection-mode checkboxes, expandable folder rows, 5px scrollbars, and a 42 x 86 dock are included. Animation quality still requires on-device visual acceptance.

Dock correction: explicit selection mode removes the unused checkbox gutter; empty folders have no branch arrow. Native Windows animated open/close cycles verified 42 x 86 window bounds and two 40 x 40 controls with 4px spacing. A queued final geometry update handles delayed native resize events, and a window mask limits the dock to its two controls.
