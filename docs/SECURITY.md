# Security review — 1.0.0

Reviewed source boundaries: filesystem mutations, Windows integration, credential handling, external requests, local storage, UI and packaging.

- No embedded API credentials, automatic provider requests, GROK server, analytics, request logging or telemetry code.
- Credential Manager generic credentials are per-user. Keys are transiently in process memory for requests. The Windows user context is the trust boundary; malware running as the user is outside it.
- HTTPS endpoints are fixed to the supported provider hosts. TLS certificate verification is enabled by Python. Redirects are rejected to prevent forwarding authorization to another host. No automatic retries or background connection tests.
- AI output is escaped before display. No tool/function execution, shell command execution or automatic attachment. Attachment preview precedes adding content; Send transmits it.
- File names reject separators, reserved device names and Windows-invalid characters. Destinations are preflighted. Exclusive file creation prevents replacement races. Same-volume rename uses Windows refusal to overwrite.
- Folder copy/move preflight rejects symlinks/junctions/reparse points. A malicious process changing the tree during operations remains a race risk; GROK is not a filesystem sandbox. Do not use it to process adversarial concurrently mutated trees.
- Cross-volume moves copy before deleting source. Multi-item operations are not transactional. A partial directory may remain after failure; no automatic retry or rollback deletes user destinations.
- Recycling is delegated to Windows without suppressing Windows warnings. Normal use runs without elevation. Only development certificate trust needs administrator access.
- Settings are local JSON and contain paths/model IDs, not secrets. Corrupt configuration falls back to defaults. Favorites and model data are type filtered.
- Chat history is retained locally in plain JSON at the user’s request. No custom crash reporting. Windows/runtime/system diagnostics remain outside GROK control.
- Static website has no scripts, remote assets, cookies, forms or analytics. Future hosting logs must be disclosed for the selected host.

Release boundaries: no penetration test, formal security certification, malicious filesystem race hardening or real-provider privacy certification is claimed. Native shell operations, external apps and provider policies are independent trust domains.
