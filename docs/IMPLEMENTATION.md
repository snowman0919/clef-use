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


## Integrated modules and delivery map

`schema.py`, `objects.py` and `candidates.py` own the bounded behavior contract,
canonical perception map and semantic action space. `model_worker.py`,
`backends.py` and `models.py` isolate pinned upstream model implementations,
resident inference processes, capture and deterministic native input.
`runtime.py` owns sessions, action history, escalation and repeated completion
checks; `verification.py` owns visual change and repeated-state detection.

`service.py` owns the authenticated local resident core and exclusive desktop
lease. `client.py` is the shared IPC client used by `cli.py` and `mcp_server.py`.
`config.py` owns configuration; `harness.py` installs only harness-specific
configuration. `doctor.py`, `benchmark.py` and `provision.py` validate/provision
these same canonical paths. `installer.py` is shared by embedded POSIX/PowerShell
bootstraps and CLI update. `scripts/build_installer.py`, `build_release.py`,
`merge_releases.py` and `check_installation.py` generate and execute the release
flow. Model weights, private harness backups and generated bundles stay outside Git.

The detailed twelve requested deliverables are covered by this initial-state and
architecture record, `docs/evidence/VALIDATION.md`, `docs/ARCHITECTURE.md`,
`docs/MCP.md`, `docs/RELEASE.md`, the four locale setup trees and the tracked source
modules. Canonical installer commands remain:

```sh
curl -fsSL https://ftp.kotori9.dev/clef-use/install.sh | sh
```

```powershell
irm https://ftp.kotori9.dev/clef-use/install.ps1 | iex
```

Their public end-to-end acceptance remains separate from loopback installation;
real desktop acceptance remains explicitly deferred. These open gates are not
converted into completion by passing fixtures, model pixels or packaging tests.
