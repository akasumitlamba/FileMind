# Working on GROK

Read [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) first. It is the shared human/AI handoff and describes architecture, product constraints, commands, known dock regressions and release limitations.

Inspect current source before editing. Preserve user settings/chat history and safe file-operation behavior. Use disposable test fixtures. Run relevant tests; verify native cold startup for dock changes. Keep PROJECT_CONTEXT.md and README.md accurate when behavior changes. Never commit credentials, private signing keys, user data or generated release binaries. MSIX is the primary deliverable; do not equate a standalone launch with successful MSIX installation.
