# Engineering handoff

Updated 2026-10-04. Repository: `clef-use`, branch `main`; public origin is
https://github.com/snowman0919/clef-use. Current implementation base: 7aee9ca.
The objective/invariants are in IMPLEMENTATION.md; observed acceptance evidence
and unresolved limits are in evidence/VALIDATION.md.

CLI and five high-level MCP tools share one authenticated resident runtime.
Pinned CLEF and OmniParser environments/cache live on the operator-authorized
external SSD. Preserve all unrelated SSD data and harness configuration.
The operator explicitly deferred GUI testing: do not change the foreground or
inject desktop input until a later operator-provided test window.

35 tests, lint and formatting pass locally. Hosted CI passed six native
macOS/Linux/Windows jobs across Python 3.11 and 3.13, including actual packaged
bootstrap/install/update/corruption/download/smoke rollback. Real local
OmniParser CPU plus CLEF MPS on generated multi-stage pixels completed two
actions and four decisions in 88.643 seconds. This is not real desktop proof.
Earlier failed model runs are retained, including an intermittent MPS placeholder
failure not reproduced in isolated probes. A second repeated model run is pending.

Codex native config readback and OMP's actual MCP client passed. Hermes's existing
launcher points to a missing environment; config is installed, harness runtime
not validated. Unrelated configurations match their private pre-change backups.
Production HTTPS bootstrap/manifest endpoints return 403. Release tree is ready;
upload credentials/access have not been supplied. The user has an optional
question pending about an existing deployment route; do not infer an answer.

Next bounded action: collect repeated ML results, generate/verify all platform
release artifacts with the dispatch workflow, merge checksums/manifests, refresh
installed local artifacts, commit final evidence. Keep GUI and production
publishing acceptance separate and never label them observed while deferred.
