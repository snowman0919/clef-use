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

Public end-to-end installation is observed separately from loopback tests.
The latest public version is 0.1.20. Public one-line installation, preparation,
doctor, real stdio MCP, native Windows GUI and monad Xvfb GUI, upgrade from
0.1.18, repeat installation and scoped removal were exercised. Exact installed
source hashes match the release tag. See evidence/e2e-windows-monad-0.1.20.json.
Monad's recovery trial required one continue call after delayed rendering safely
caused NEEDS_REPLAN. Model caches were reused; this does not establish cache-empty
installation or arbitrary-application stability.

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
| 15 | installed 0.1.20: Codex native app-server discovered five tools; OMP native client and isolated official Hermes CLI/handler completed fixture tasks; agent model conversations NOT_RUN; user Hermes launcher interpreter still missing |
| 16-19 | hashed offline bundles, native five-platform/Python matrix, shared atomic POSIX/update installer; public HTTPS install/update/failure-preservation/removal evidence; 0.1.20 all 15 installer targets and dev deployment passed; Windows/monad lifecycle and real GUI exercised; public 0.1.18 terminal Y preparation passed on both |
| 20-22 | pinned SSD cache/provisioning, one config, doctor and acceleration probes; actual MPS CLEF/CPU Omni and experimental native Windows ROCm/NF4 plus CPU Omni observed; canonical0.1.8 Windows Radeon890M profile installed fresh ROCm/NF4 CLEF and CPU Omni environments and initialized both workers; installed normal CLI GUI passed2inputs/4decisions; doctor checks real imports/device/NF4 arithmetic and pinned cache/source prerequisites |
| 23-24 | private structured latency/action/terminal logs, benchmark with explicit fixture vs desktop modes; no comparative speed claim |
| 25-26 | unit regressions and actual packaged installs/stdio/IPC; concrete replacement interfaces for capture/perception/decision/action/verifier |
| 27 | documented extension boundaries; DOM/AX/tracking/remote control intentionally future work |
| 28 | abort, cleanup, bounded confidence/steps/no-progress, safe errors and escalation logs; no shell execution capability in executor |
| 29-30 | required docs/community files, generated/cache exclusions, coherent commits; unowned concurrent edits preserved separately |
| 31-32 | shared vertical slice and model semantics observed; real Windows native GUI passed with earlier Mac inference and later Windows-local ROCm/CPU inference (2 actions/4 decisions/118.6999s after initialization); public one-line installation passed through 0.1.20; 0.1.5 controlled visual GUI trials passed 10/10 and no-effect stopped after one input; full real-model GUI evidence is version-specific |
| 33-34 | architectural choices and measured limits recorded here, ARCHITECTURE.md and evidence/VALIDATION.md; twelve delivery categories linked above |
| 35 | public main, Issues/Discussions/Actions/security, CI/release machinery, four locale setup trees; command/config parity verified |
| 36 | PowerShell 5.1/CMD installation-to-removal observed; 0.1.6 fixes OpenSSH OWNER RIGHTS limited-token access; user PATH/launcher/cache preserved; prior Unicode/update failure checks retained |

Current audit (2026-10-05, public 0.1.20): deployment is no longer blocked.
The dedicated dev runner published all 15 checked artifacts; latest/immutable
metadata and bootstrap byte checks passed. CI 37295561731 passed 190 tests in
six jobs. Its test-only commit 1f4a538 corrects the native lock fixture; runtime
bytes match release tag de87e47. Release 37295470437 completed assembly/deployment.
GitHub v0.1.20 is published. Hardware acceptance remains profile-specific.

Final public Windows ROCm/NF4 CLEF plus CPU Omni GUI completed two actions/four
decisions, independent Task complete readback, held-key/pointer cleanup, endpoint
removal and task exit 0. Monad CUDA/NF4 plus CPU Omni recovery completed two
actions/five decisions with one continue after delayed rendering. Its initial
attempt safely stopped NEEDS_REPLAN and remains in the evidence. Doctor and real
five-tool stdio MCP passed on both machines. Both runtime installs were removed
while existing installs, settings and shared models remained. Final Windows SSH
terminal wrapper completion was unverified; installed source, direct canonical
prepare and noninteractive public reinstall were verified instead. Mac input
remains deferred; Mac/SSD is not needed for Windows/monad E2E.

External SSD /Volumes/SSD/AI/clef-use returned. Installed 0.1.20 completed
an actual MPS CLEF/CPU Omni task on generated pixels (two actions/four decisions,
90.247s), without desktop capture or input. Three native harness clients were
rechecked at 0.1.20 with existing user settings preserved. Codex acceptance is
catalog discovery; OMP and isolated official Hermes acceptance includes fixture
tool execution. No agent model conversation was run. The original user Hermes
launcher still lacks its interpreter. See evidence/harnesses-0.1.20.json and
evidence/model-smoke-0.1.20.json.

Single-trial later decision means were 17.532s on Windows, 0.816s on monad and
6.760s on MPS generated pixels. These tasks/hardware differ and do not establish
a comparative improvement. Fast decision latency remains an unmet performance
hypothesis; profile the canonical path before integrating optimization drafts.
Concise/debug log behavior and command parity across four locales were checked
against installed 0.1.20 and canonical source, respectively.

Known non-blocking limitations: larger CLEF remains untested. NVIDIA CUDA Flash
execution was observed on monad, with CPU output embedding rows under low free
VRAM; model initialization must still fit. Broad arbitrary-app coverage and
unassisted stability are not established; intermittent earlier
MPS failures retain their evidence without a general stability claim. A custom
Windows bin directory on another volume with Unicode requires an ASCII target
or a bin directory inside the installation. Fresh preparation across all ten
OS/backend profiles and every hardware class is not established by CI.

Pre-existing MLX/residency/quantization drafts remain separate and unpublished.
GGUF/model-serving deployment was deferred by the user; do not absorb these
prototypes into current release acceptance. Future optimization remains measured
VLM baseline comparison, temporal/incremental perception and native acceleration
only after profiling. Overall goal completion remains unproven until the full
acceptance audit is current; passing fixtures and release tests alone is insufficient.
