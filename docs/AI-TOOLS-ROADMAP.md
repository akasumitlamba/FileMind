# File-aware assistant roadmap

User direction: GROK should grow into a file assistant that organizes folders, edits documents, converts formats (for example DOCX to PDF), and can run code to complete those tasks. This is future scope, not implemented or tested in version 1.0.0.

The current app offers direct provider chat with explicitly reviewed text/file-list context. It has no AI terminal access, tool execution or automatic edits.

Proposed implementation:

1. User chooses a workspace folder and grants read access for that conversation. Show the active scope beside chat. Never imply that all drives are accessible by default.
2. Implement structured tools for listing, reading, searching, proposing changes and converting supported formats. Prefer these to arbitrary terminal commands.
3. Show a plan, affected files, proposed diff and destination before write/move/delete operations. Use backups/versioned output and require approval before destructive replacements.
4. Run document converters in isolated worker processes. Detect installed conversion engines and clearly report fidelity limitations. Preserve originals; default to a new output file.
5. If terminal/code execution is added, use a restricted environment with explicit command review, bounded runtime/output, cancellation, network controls and no inherited provider credentials. Treat file contents and tool output as untrusted instructions.
6. Separate provider adapters from tool permissions and execution. Provider selection must not silently broaden local access. Keep a local, user-controlled action history distinct from chat retention.
7. Test prompt injection, path/junction escapes, command injection, interrupted writes, recovery, provider tool-call validation and partial conversion failures before enabling this feature in a release.
