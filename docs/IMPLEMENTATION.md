# Implementation and evidence contract

Initial state (2026-10-03): Playground is not a Git repository. No existing
CLEF/OmniParser project, packaging, CI or release implementation was found in
the workspace. Existing sibling projects and user configuration are preserved.
New repository: `clef-use`, branch `main`.

Invariant: the planner submits strategy once; the resident runtime captures,
parses, builds bounded candidates, invokes CLEF, actuates and verifies until a
terminal event. CLI and MCP share that runtime and desktop ownership.

Plan: (1) pinned model adapters and bounded runtime; (2) shared local service,
CLI and MCP; (3) non-destructive harness configuration; (4) verified atomic
installer and release generation; (5) deterministic regressions, real model/GUI
smoke and measured evidence; (6) public repository and multilingual setup.

Non-goals: shell-agent capabilities, separate harness runtimes, native performance
sidecars, persistent tracking, DOM/accessibility fusion and unmeasured speed claims.

Acceptance evidence is recorded in `docs/evidence/VALIDATION.md`. Fixtures establish
control-flow and protocol correctness only. Real model and desktop runs establish
perception/decision semantics separately. Production hosting requires authorized
access to ftp.kotori9.dev; local release tests do not establish public deployment.
