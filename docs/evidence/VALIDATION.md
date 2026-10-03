# Validation evidence

Observed on 2026-10-04: macOS arm64, Python 3.11.15, 48 GiB unified memory,
primary screenshot 1800 x 1169, external SSD model cache. PyTorch 2.11.0,
CLEF Transformers 5.10.2; OmniParser Transformers 4.46.3. Pinned model/source
revisions are in `src/clef_use/models.py`. CUDA and other desktops are NOT_RUN.

| Gate | Evidence and boundary |
| --- | --- |
| Unit/integration tests | 34 passed in 8.95 seconds; includes real loopback HTTP and stdio MCP |
| CLI/MCP shared core | Both reach the same fixture session: two actions, four decisions, COMPLETED |
| Input cleanup | Exceptions after key/button press release all tracked input and restore failsafe |
| Runtime bounds | Confidence, safety, replan, hard budget, repeat states, abort and secret-redacted errors tested |
| Native desktop capture | Actual nonuniform screenshot captured; no private screenshot published |
| Native input permission | Screen Recording and Accessibility observed granted; permission is not a GUI task proof |
| Actual GUI task | NOT_RUN, explicitly deferred by the operator; no foreground window/input now |
| CLEF semantic text | Correct overdue invoice choice (0.9812), amount >1000 probability 0.9673; cold 56.607 seconds |
| OmniParser pixels | Found Continue button/OCR on generated pixels; empty-OCR image safely returns empty map |
| Real models, multi-action | Reached generated final state after correct Continue/Confirm selections; terminal NO_PROGRESS, not COMPLETED |
| Later real-model retries | ERROR at model boundary; diagnostics retained, compatibility investigation ongoing |
| First/install/update | Actual offline wheel install 0.1.0, repeated CURRENT, update 0.1.1 |
| Failed update preservation | Bad checksum, missing download and wrong-version smoke all retained working 0.1.1 |
| Installed MCP | Actual stdio initialization and five high-level tools passed through installed launcher |
| Codex setup | Entry installed and `codex mcp get clef-use --json` reads enabled stdio server |
| OMP setup | Entry installed in actual MCP JSON; other settings semantically identical to private backup |
| Hermes setup | Entry installed; existing Hermes launcher references a missing runtime, so harness launch NOT_RUN |
| Public HTTPS hosting | install.sh, install.ps1 and latest manifest returned HTTP 403; not publicly deployed |
| Windows | Canonical PowerShell/CMD activation implemented, native execution NOT_RUN on this macOS host |

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
combined visual CLEF completion/compatibility needs resolution; hosting upload
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
