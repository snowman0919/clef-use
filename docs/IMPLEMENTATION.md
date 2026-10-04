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
a real Windows native-GUI/model vertical slice is now observed (see WINDOWS_INPUT.md). These open gates are not
converted into completion by passing fixtures, model pixels or packaging tests.

## Requirement audit

References correspond to the numbered uploaded goal. OBSERVED applies only to
the stated boundary, never to native input quality from fixture tests.

| Goal | Canonical implementation / acceptance boundary |
| --- | --- |
| 1-3 | runtime/service own multiple actions; CLI and five MCP tools share IPC; fixture, generated-pixel and real Windows GUI model loops completed |
| 4 | Python runtime; upstream ML environments isolated; no native optimization sidecar |
| 5-6 | pinned OmniParser V2 source/assets, objects.py normalized map and geometry; real pixels parsed |
| 7-8 | bounded candidates and joint CLEF choices/score/noul; real Flash MPS decisions; controlled 0.1.5 visual GUI variants completed 10/10 warm trials plus cold; earlier intermittent failures retained; larger CLEF untested |
| 9-11 | strict small Contract, explicit states, hard budget, visual/repeat-state and independent completion verification; regression tests |
| 12 | deterministic whitelist input, safe object centers, tracked keys/buttons and cleanup retries; real Windows Unicode/click/scroll/foreground/cleanup readback observed; macOS input deferred |
| 13-14 | five canonical MCP tools and thin CLI; real stdio/HTTP tests, fresh idle observe without decision/action counts |
| 15 | configuration-only Codex readback, OMP native client; isolated official Hermes CLI MCP connection and native handler completed 0.1.5 fixture; user launcher interpreter still missing |
| 16-19 | hashed offline bundles, native five-platform/Python matrix, shared atomic POSIX/update installer; public HTTPS 0.1.3 install passed; 0.1.5 upload pending |
| 20-22 | pinned SSD cache/provisioning, one config, doctor and acceleration probes; actual MPS CLEF/CPU Omni, CUDA/Windows ML not run |
| 23-24 | private structured latency/action/terminal logs, benchmark with explicit fixture vs desktop modes; no comparative speed claim |
| 25-26 | unit regressions and actual packaged installs/stdio/IPC; concrete replacement interfaces for capture/perception/decision/action/verifier |
| 27 | documented extension boundaries; DOM/AX/tracking/remote control intentionally future work |
| 28 | abort, cleanup, bounded confidence/steps/no-progress, safe errors and escalation logs; no shell execution capability in executor |
| 29-30 | required docs/community files, generated/cache exclusions, coherent commits; unowned concurrent edits preserved separately |
| 31-32 | shared vertical slice and model semantics observed; real Windows native GUI observed with Mac inference; public 0.1.3 one-line installation passed; 0.1.5 controlled visual GUI trials passed 10/10 and no-effect stopped after one input; new public upload remains open |
| 33-34 | architectural choices and measured limits recorded here, ARCHITECTURE.md and evidence/VALIDATION.md; twelve delivery categories linked above |
| 35 | public main, Issues/Discussions/Actions/security, CI/release machinery, four locale setup trees; command/config parity verified |
| 36 | first-class PowerShell 5.1/CMD flow, no security policy change, per-user Unicode paths and preservation on three failed update cases observed on ssh win |

Blocking deployment: new 0.1.5 public upload route is unavailable. Controlled
owned-GUI visual trials now passed 10/10, without worker restarts; this does not
resolve the cause of earlier MPS failures or establish arbitrary-input stability.
Public HTTPS 0.1.3 metadata and
Mac/Windows installs passed; the previous HTTP 404 blocker is resolved.
Windows GUI was explicitly authorized and observed on 2026-10-04; macOS native
input remains deferred. Non-blocking limitations: user Hermes launcher interpreter
unavailable (isolated official CLI validated), larger CLEF and CUDA/Windows ML untested, cross-volume custom Unicode
Windows bin paths require an ASCII target or the bin directory inside the install.
Future optimization: measured VLM baseline comparison, temporal/incremental
perception, native input/capture acceleration only after profiling.
