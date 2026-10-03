# Security policy

Do not disclose vulnerabilities in public issues or discussions. Use GitHub's
private vulnerability reporting under Security > Report a vulnerability. If the
feature is unavailable, request a private contact from the maintainer without
publishing exploit details, personal data or credentials.

The initial 0.1.x release line receives fixes while this project is maintained.
This runtime can move a mouse and enter text on the current desktop. It is not an
OS sandbox. Model decisions and screen-derived labels are untrusted. Contract
constraints are evaluated by a model and are not a formal authorization policy.
Use an isolated desktop with harmless tasks; do not submit secrets.

The local API binds loopback, requires a private random token, and rejects browser
Origin requests. The token and logs use restricted user permissions on POSIX.
Other processes with the same user privileges are within the trust boundary.
MCP clients can request screenshots and visible labels, which may be sensitive.

Releases use HTTPS and SHA-256 checked metadata/artifacts. Checksums delivered by
the same HTTPS host provide integrity but are not an independent release signature.
Pinned Hugging Face model Python code is explicitly trusted during preparation.
Old working installations and model caches are preserved during updates.
