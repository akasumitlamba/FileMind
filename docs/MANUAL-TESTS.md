# Manual acceptance matrix

Use a disposable directory with text files, nested folders and a second destination. Never use personal files for destructive checks. Record Windows version, scaling, monitors, build hash and expected/actual result.

| Workflow | Expected result |
|---|---|
| Click dock, collapse icon, Escape, Ctrl+Alt+G | Right edge remains fixed; compact dock returns |
| Narrow/medium/wide | Controls fit; metadata appears at wide widths |
| Auto-hide, pin | Focus loss collapses only when auto-hide enabled and unpinned |
| Monitor removal/reconnection, 100/125/150/200% DPI, taskbar edges | Panel remains entirely in selected/fallback work area |
| Path, invalid path, UNC, Back/Forward/Up | Correct folder; error preserves current location |
| Search, empty folder, 10k+ files | Local results; responsive UI; clear result state |
| Copy/cut/paste, move, rename, new folder | Correct contents; originals retained on copy, moved only on successful move |
| Collision, lock, permission denial, disk full, cancellation | No overwrite; error/progress visible; inspect partial results |
| Recycle | Windows confirms as applicable; fixture disappears and is recoverable where supported |
| Ctrl/Shift multiselect | Correct selection; operations act on selected items |
| Drag out to Explorer, Explorer into GROK, onto GROK folder | Correct copy/move modifiers; no duplicate deletion |
| Open, Open with, Properties | Appropriate Windows application/dialog opens |
| Favorites, restart, corrupt settings | Persistence; safe fallback without crash |
| Shortcut conflict | Useful error; alternate shortcut works |
| AI disabled/offline | Full browser remains functional; no provider requests |
| Each provider with real account | Key save/test/remove, correct model and answer; errors for bad key/quota/offline |
| Attachment cancel / add / send | No request on cancel/add; reviewed content sent only on Send |
| Clear chat/change provider/disable | History survives provider changes and disabling; Clear removes the selected provider’s local transcript |
| Signed MSIX install/launch/update/uninstall | Windows package lifecycle works; no Python installation needed |
| Start with Windows | Opt-in launches at sign-in; turning off stops it |
| Keyboard and screen reader | Focus visible; labeled icon controls; file shortcuts do not fire in text fields |

Automated Qt tests supplement but do not replace this physical interoperability matrix. Consult QA.md for what has actually been executed.
