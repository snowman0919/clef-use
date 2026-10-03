# Validation evidence

Observed on 2026-10-04: macOS arm64, Python 3.11.15, 48 GiB unified memory,
primary screenshot 1800 x 1169, external SSD model cache. PyTorch 2.11.0,
CLEF Transformers 5.10.2; OmniParser Transformers 4.46.3. Pinned model/source
revisions are in `src/clef_use/models.py`. CUDA and other desktops are NOT_RUN.

| Gate | Evidence and boundary |
| --- | --- |
| Unit/integration tests | 35 passed in 2.37 seconds; includes real loopback HTTP and stdio MCP |
| CLI/MCP shared core | Both reach the same fixture session: two actions, four decisions, COMPLETED |
| Input cleanup | Exceptions after key/button press release all tracked input and restore failsafe |
| Runtime bounds | Confidence, safety, replan, hard budget, repeat states, abort and secret-redacted errors tested |
| Native desktop capture | Actual nonuniform screenshot captured; no private screenshot published |
| Native input permission | Screen Recording and Accessibility observed granted; permission is not a GUI task proof |
| Actual GUI task | NOT_RUN, explicitly deferred by the operator; no foreground window/input now |
| CLEF semantic text | Correct overdue invoice choice (0.9812), amount >1000 probability 0.9673; cold 56.607 seconds |
| OmniParser pixels | Found Continue button/OCR on generated pixels; empty-OCR image safely returns empty map |
| Real models, multi-action | COMPLETED: two actual model-selected actions, four decisions, two independent completion observations |
| Later real-model retries | Earlier NO_PROGRESS/ERROR preserved; semantic context fixed; later full pipeline passed. Transient MPS placeholder error not reproduced in isolated model probes |
| First/install/update | Actual offline wheel install 0.1.0, repeated CURRENT, update 0.1.1 |
| Failed update preservation | Bad checksum, missing download and wrong-version smoke all retained working 0.1.1 |
| Installed MCP | Actual stdio initialization and five high-level tools passed through installed launcher |
| Codex setup | Entry installed and `codex mcp get clef-use --json` reads enabled stdio server |
| OMP setup | Actual OMP 18.4.8 MCP client initialized and listed all five tools; unrelated settings match backup |
| Hermes setup | Entry installed; existing Hermes launcher references a missing runtime, so harness launch NOT_RUN |
| Public HTTPS hosting | install.sh, install.ps1 and latest manifest returned HTTP 403; not publicly deployed |
| Windows | Actual Windows 2022 x86_64 CI passed PowerShell first install, CMD CLI update and rollback on Python 3.11/3.13; GUI/ML NOT_RUN |

Commands:

```sh
PYTHONPATH=src .venv/bin/python -m pytest -q
.venv/bin/ruff check src tests scripts
.venv/bin/ruff format --check src tests scripts
.venv/bin/python scripts/build_installer.py
sh -n install.sh
.venv/bin/python scripts/build_release.py --output release-site
.venv/bin/python scripts/check_installation.py --site release-site
PYTHONPATH=src .venv/bin/python scripts/model_smoke.py --output model-smoke.json
clef-use doctor --no-capture
```

The disabled-capture doctor correctly returns ready=false: it does not infer
GUI readiness from models/cache/permissions. No inputs are injected by doctor.
Private configuration backups remain outside the repository. Registration is
idempotent and does not validate an entire planner/harness agent conversation.

## Measurements

Actual OmniParser cold initialization was 32.969 seconds, generated-image parse
26.824 seconds, empty-OCR image 8.731 seconds. In the first combined run, wall
latency was 358.055 seconds; per-round parser times were 39.818 (cold), 19.047,
8.285 and 7.057 seconds; CLEF times were 230.035 (cold), 15.664, 16.783 and
19.481 seconds. Four actions included two successful state transitions and two
waits. No outer planner intervention occurred. The run terminated NO_PROGRESS.
Capture/render and deterministic simulated input were milliseconds; these are
not native desktop latency measurements. There was no controlled VLM comparison
and no speedup is claimed. Concurrent foreground use and memory pressure were
not controlled; treat this as a smoke measurement, not a performance benchmark.

## Remaining limitations

Blocking for production acceptance: real desktop task success is deferred;
hosting upload
access is absent and the public bootstrap endpoints return 403. Public one-line
installation is an intended URL, not a currently verified deployment.

Non-blocking implementation limits: sessions are in memory; primary monitor only;
Wayland and Windows/CUDA model execution are untested; large CLEF is untested;
plain-text clipboard restoration cannot retain rich clipboard types; model
forward cancellation stops late input but does not immediately interrupt tensor
computation. Model constraints are probabilistic, not a security sandbox.

Future optimization: profile cold loading, context size, perception and CLEF
latency; test CUDA; compare controlled baselines; add DOM/AX fusion and temporal
tracking only with evidence. Model inference dominates observed overhead.

Raw machine-readable results use synthetic/public-safe inputs only:
[installer](installer.json), [first models](real-model-smoke-first.json),
[second models](real-model-smoke-second.json), [third models](real-model-smoke-third.json).

## Final successful model slice

[Successful real model result](real-model-smoke-completed.json): 88.643 seconds,
two clicks (Continue then Confirm), four decisions, COMPLETED, zero outer planner
interventions. Completion predictions were 0.9502 for the goal and 0.9616 for
the condition on both final observations. The final action-choice confidence
was 0.4326, but no action was required or executed after verified completion.
Action confidence before the two executed clicks was 0.8228 and 0.7671.

Parser times: 12.811 seconds cold, then 5.355, 0.852 and 0.814.
CLEF times: 46.406 seconds cold, then 7.576, 6.972 and 6.671.
Capture/render was 0.969-3.360 milliseconds; simulated actuation was below
0.061 milliseconds. These are generated-image measurements, not real GUI
measurements. Earlier failures remain published to establish the evidence
boundary. The cause of intermittent earlier MPS visual placeholder errors is
not proven; models are not claimed stable across arbitrary inputs/platforms.

The decision context now includes actual semantic action descriptions and
current objects, instead of old model probabilities and telemetry. A regression
test protects this separation. Rich per-round telemetry remains in private logs.

[OMP readback](omp-mcp.json) uses the installed harness's real client code,
not a substitute parser. Codex readback is its installed native CLI. Hermes
configuration is installed, but its missing runtime remains independent.

## Hosted platform verification

[CI run 37135794374](https://github.com/snowman0919/clef-use/actions/runs/37135794374)
passed all six jobs: macOS arm64, Linux x86_64, Windows x86_64, each on Python
3.11 and 3.13. Every job ran lint, formatting, all 35 tests, generated-bootstrap
consistency, native wheel build, and actual first install/update/rollback tests.
Windows tests exercise the actual PowerShell bootstrap and managed CMD launcher.
This is packaging/protocol validation; hosted headless CI does not prove desktop
input or actual ML compatibility on those platforms.

Canonical `clef-use models prepare --python <Python 3.11 executable>` also returned
PREPARED against the existing external SSD environments and pinned cache, without
downloading another copy of the large weights. A subsequent installed MCP doctor
passed initialization/listing. Screen capture remained deliberately disabled.

The public repository has Issues, Discussions, Actions and private vulnerability
reporting enabled, main as default branch, and automatic merged-branch deletion.
Protection recommendations are documented for collaboration; no tag or production
host deployment has been published as ready.
