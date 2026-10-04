# Validation evidence

Observed on 2026-10-04: macOS arm64, Python 3.11.15, 48 GiB unified memory,
primary screenshot 1800 x 1169, external SSD model cache. PyTorch 2.11.0,
CLEF Transformers 5.10.2; OmniParser Transformers 4.46.3. Pinned model/source
revisions are in `src/clef_use/models.py`. NVIDIA CUDA remains NOT_RUN. Native
Windows-local AMD ROCm/NF4 and CPU inference passed the narrow diagnostic below;
it is not the released default model configuration.

| Gate | Evidence and boundary |
| --- | --- |
| Unit/integration tests | Published 0.1.5: 83 passed locally and installed-wheel Windows in 7.48s; latest clean diagnostic snapshot: 86 passed in 6.02s; new worker refusal test passed natively on Windows in 0.27s; real loopback HTTP/stdio MCP |
| CLI/MCP shared core | Both reach the same fixture session: two actions, four decisions, COMPLETED |
| Input cleanup | Exceptions after key/button press release all tracked input and restore failsafe |
| Runtime bounds | Confidence, safety, replan, hard budget, repeat states, abort and secret-redacted errors tested |
| Native desktop capture | Actual nonuniform screenshot captured; no private screenshot published |
| Native input permission | Screen Recording and Accessibility observed granted; permission is not a GUI task proof |
| Actual GUI task | OBSERVED on Windows: disposable real GUI, native input, 2 model-selected actions/4 decisions; both earlier Mac inference and later Windows-local ROCm/CPU inference passed; macOS native input deferred |
| CLEF semantic text | Correct overdue invoice choice (0.9812), amount >1000 probability 0.9673; cold 56.607 seconds |
| OmniParser pixels | Found Continue button/OCR on generated pixels; empty-OCR image safely returns empty map |
| Real models, multi-action | COMPLETED: two actual model-selected actions, four decisions, two independent completion observations |
| Later real-model retries | Earlier NO_PROGRESS/ERROR preserved; semantic context fixed; later full pipeline passed. Intermittent MPS placeholder errors remain unresolved; later controlled visual variants completed 10/10 warm tasks |
| First/install/update | Native Windows 0.1.3 first install/CURRENT and isolated synthetic update 0.1.4; installed Mac version tracked in installed-update.json |
| Failed update preservation | Bad checksum, missing download and wrong-version smoke retain the previous working version, including Unicode paths |
| Installed MCP | Actual stdio initialization and five high-level tools passed through installed launcher |
| Codex setup | Entry installed and `codex mcp get clef-use --json` reads enabled stdio server |
| OMP setup | Actual OMP 18.4.8 MCP client initialized and listed all five tools; unrelated settings match backup |
| Hermes setup | Isolated official full CLI MCP connection and native discovery/handler completed 0.1.5 fixture actions; original user launcher interpreter missing; agent LLM conversation NOT_RUN |
| Public HTTPS hosting | Bootstrap scripts return HTTP 200; public 0.1.3 manifest has 15 targets and isolated Mac/Windows HTTPS installation plus self-test passed; newer 0.1.5 is not deployed |
| Windows | 0.1.5 installed wheel: 83 tests; native Unicode/click/wheel/shortcut/readiness/refusal/cleanup checks; later reporting regressions 2/2; Windows-local ML and GUI PASSED with an experimental NF4 loader |

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

Public 0.1.3 deployment is now observed working on isolated Mac and Windows
installations (public-https-013.json). Newer source/release delivery remains a
separate acceptance gate; the operator upload route is not available to this
task. Controlled actual 0.1.5 visual variants completed 10/10 warm tasks after
earlier MPS failures; arbitrary-input stability is unproven. Native input alone
is not final goal completion.

Non-blocking implementation limits: sessions are in memory; primary monitor only;
Wayland and NVIDIA CUDA model execution are untested; large CLEF is untested;
non-Windows plain-text clipboard restoration cannot retain rich clipboard types; model
forward cancellation stops late input but does not immediately interrupt tensor
computation. Model constraints are probabilistic, not a security sandbox.

## Native Windows-local inference

[Windows-local evidence](windows-local-inference.json) records Windows 11 Pro,
Python 3.12.10, Ryzen AI 9 HX 370 / Radeon 890M (`gfx1150`), PyTorch
2.11.0+rocm7.14.1, Transformers 5.10.2 and bitsandbytes 0.50.2. The isolated
OmniParser CPU environment uses PyTorch 2.11.0+cpu and Transformers 4.46.3.
Forty transferred model/cache files (20,453,821,318 bytes) matched SHA-256 on
Windows. Drivers, security settings, pagefile and UMA settings were unchanged.

Actual FP32/FP16/BF16 GPU matrix results were finite and compared against a CPU
reference. The NF4 kernel was compared against its dequantized reference and
the original weights. Language modules alone were quantized: 248 modules;
vision, output embeddings and the typed head stayed floating point. The short
`visual` exclusion failed this invariant before inference; `model.visual`
matched the actual Transformers module prefix and passed.

CLEF produced three identical positive completion results: goal 0.9444,
condition 0.9624, COMPLETED confidence 0.9018. Changing the requested condition
to absent text reduced goal/condition probabilities to 0.0082/0.0050. This
control rejects false completion; its ACT mode with no allowed action is not
claimed as correct BLOCKED behavior. Cold forward: 52.0313s; subsequent positive
forwards: 15.2816s/15.4393s; model load: 21.9039s. OmniParser found the expected
text and boxes twice: 8.4064s/7.8115s after 24.5651s initialization.

The canonical 0.1.5 runtime then completed the owned Windows GUI using Windows
models: two correct native clicks, four decisions, two fresh final observations,
`Task complete` callback readback and zero outer interventions. Task wall time
was 118.6999s, excluding worker preinitialization. Rendering was delayed 500ms.
The initial attempt refused a changed foreground before input; it remains in
the evidence. The recovery initializes both workers before one owned-window
reset; foreground/geometry guards remain active during the task. Owned workers,
GUI, task, listener and token were cleaned up. Prior foreground restoration was
requested but not independently asserted.

This is one narrow native GUI task with an experimental diagnostic loader, not
a production installer/backend support claim or a controlled speed comparison.
The wider acceleration/quantization draft is not published, and the released
default loader does not expose the NF4 path. See [Windows input](../WINDOWS_INPUT.md).

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
configuration is installed. A later isolated official full CLI MCP probe is recorded
in [Hermes process evidence](hermes-process-mcp.json); the original user launcher
still has a missing interpreter and was preserved.

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
Protection recommendations are documented for collaboration; no tag has been published as ready.
Public 0.1.3 metadata and installation are accepted; 0.1.5 upload remains separate.


## Repeated model validation

[Two resident-worker samples](real-model-repeat.json) both returned COMPLETED
with two actions, four decisions and zero outer planner interventions. First
sample: 81.661 seconds. Second, warm sample: 33.037 seconds. Native desktop input
was disabled; pixels and actuation were generated in the test harness. The result
confirms repeated execution on these inputs, not arbitrary MPS/model stability
or a measured advantage over another computer-use system.

## Operator Windows SSH validation

[Windows SSH report](windows-ssh.json) was obtained from the operator-authorized
`ssh win` machine: Windows 11 Pro x86_64, PowerShell 5.1.26100.9444, Python 3.12.10.
All 35 tests passed in 10.46 seconds initially and 3.37 seconds on the latest
0.1.1 revision. Actual packaged PowerShell installation,
CMD version/update, idempotence and all three failed-update preservation cases
passed. Doctor initialized the real stdio MCP server and listed the five tools;
ready=false correctly reports missing ML environments/weights and disabled capture.
No foreground change or native input occurred. The machine reports about 23.6 GiB
RAM and AMD Radeon 890M graphics; CUDA/model semantics were not tested.

The first SSH attempt stopped because PowerShell 5.1 treated uv's ordinary stderr
status output as a terminating error. A Python subprocess driver with separate
captured logs resolved this orchestration failure; it was not a dependency or
runtime failure. Test PATH changes were isolated from the persistent user PATH.

## Complete platform release build

[Release run 37136579094](https://github.com/snowman0919/clef-use/actions/runs/37136579094)
passed all 15 native combinations and final assembly. The downloaded 0.1.0 site
contains 15 unique platform/architecture/Python targets; every archive SHA-256
matches metadata. Total tree size is 379,606,200 bytes. macOS Intel cryptography
requires a local wheel build with its pinned maturin build backend; initial
missing-backend failure was retained and the corrected native jobs passed.
[Platform job evidence](release-010-platforms.json) records the exact revision.

0.1.1 retains immutable 0.1.0 checkpoints and delivers subsequent corrections
through a versioned update. The release builder excludes cached older project
wheels, preserving exactly one version of clef-use in each bundle. Local 0.1.1
install/update/rollback passed.
[0.1.1 release run 37137294737](https://github.com/snowman0919/clef-use/actions/runs/37137294737)
also passed all 15 native combinations and final assembly.
[Latest platform jobs](release-011-platforms.json) pin revision 7c734f1.

## Public host readback

[Public endpoints](public-hosting.json): install.sh and install.ps1 are HTTP 200;
latest/manifest.json and latest/SHA256SUMS are HTTP 404. Earlier Python urllib
requests received Cloudflare 1010/403; the release client now supplies the project
User-Agent and reaches the same missing-metadata 404 as curl/PowerShell. The
served bootstraps predate this correction and must be refreshed from the final
site tree. Upload version artifacts first, then checksums/manifest and bootstraps.

The public POSIX one-line installer was executed in an isolated temporary install
root. Bootstrap download succeeded, but its embedded old Python client returned
HTTP 403 and exit 1 on secondary metadata. No real installation or input was
changed. Refreshing both bootstraps is required alongside the missing latest tree.


## Installed final package and transfer bundle

Historical 0.1.1 installed update: the exact assembled archive was
served through the canonical loopback installer. The existing user installation
updated from 0.1.0 to 0.1.1; repeating returned CURRENT; installed fixture self-test
completed two actions with no outer planner intervention. The config file bytes
were unchanged. This updates the runtime without duplicating the external ML cache.

[Complete tree](release-tree.json) records all 30 verified archives for 0.1.0 and
0.1.1, 15 targets each. `release-site/` is the exact upload layout;
`dist/clef-use-release-site-0.1.1.tar.gz` and its adjacent SHA-256 file package it
for transfer. These generated bundles are intentionally excluded from Git.

Unowned concurrent GPU/quantization source edits are preserved in the workspace
and excluded from these commits and acceptance claims. This report refers to
committed implementation 7c734f1 and its exact packaged artifacts. Integration
of those separate edits requires its own review and execution evidence.

Historical installed 0.1.1 doctor confirmed dependencies, pinned cache
availability, PyTorch MPS detection and five real stdio MCP tools. With capture
disabled it correctly reports ready=false; input and model semantics were not run
by doctor. Readback used the installed package, not the dirty source tree.


## Completion audit: ordinary keyboard cleanup

[Input cleanup regression](input-cleanup-audit.json): the installed 0.1.1 adapter
failed two real execution-path unit probes when a simulated native key-down
raised during ordinary press/ASCII typing: neither key was released. This is a
concrete missing cleanup invariant, not a GUI acceptance claim. PyAutoGUI 0.9.54
source confirms these convenience methods perform internal key-down/up without
project-owned tracking.

The adapter now routes ordinary presses and ASCII characters through tracked
key-down/finally-release. It also tracks implicit Shift and Windows layout
modifiers. Cleanup attempts every owned key/button even if one release fails;
failed inputs remain tracked for retry, while failsafe state is restored.
Cancellation after the first held key stops the next press and releases ownership.

The frozen committed source plus only these owned patches passed 42 tests in
2.37 seconds, lint and formatting. Concurrent GPU/MLX/quantization source edits
were excluded, including overlapping edits to the CLEF section of backends.py.
Tests substitute only native event calls and inject no GUI input. Release 0.1.2
will carry the correction; 0.1.1 archives remain immutable.

## Completion audit, 0.1.3

Installed 0.1.2 reproduced three contract defects: exhausted budgets lacked a
terminal log row; failed inference lost its elapsed time; observe returned stale
objects after a changed fixture scene. The corrections retain failure latency,
record explicit terminal reasons, refresh idle observations and return matching
PNG/object epochs. While busy, observe labels its cache and never races parsing.
A frozen committed base plus only owned patches passed 48 tests in 5.12 seconds
and lint/format in a clean /tmp environment. Concurrent acceleration, MLX and
model residency changes are excluded from this result.

Native Windows PowerShell installation in a Korean/space parent path initially
failed with UnicodeEncodeError. UTF-8 atomic writes and a relative CMD launcher
fixed first install, CURRENT, update and all three failed-update preservation
cases. check_installation.py now exercises this path on every native CI target.
See completion-audit.json; release-specific results follow after packaging.

Hermes official native MCP discovery and registered handler at upstream commit
3c9847f5e86e81c23335a54daa532de28eeffeb3 initialized the installed 0.1.2 server
and completed two fixture actions/four decisions without an outer LLM. The five
canonical tools remain unchanged; four extra resource/prompt utilities are added
by Hermes itself. Existing Hermes launcher still lacks its runtime, so a full
agent conversation is NOT_RUN. hermes-mcp.json records this boundary. All setup
command/config examples across four locales match (localized-commands.json).

At that checkpoint the operator deferred native GUI tasks. This historical
GUI deferral is superseded for Windows by the authorization and real execution
below. Public latest metadata was HTTP 404; the overall goal stays active.

0.1.3 CI run 37143721190 passed all six native jobs. Windows SSH at
000885b passed all 48 tests in 4.71 seconds and Unicode installer checks;
see windows-ssh.json. Aggregate historical model latencies are in
model-latency-summary.json: warm parser mean 1.236s, CLEF mean 6.784s per
decision, wall 33.037s. These are generated pixels and simulated actuation,
with no claim of native GUI speed or comparative performance.

## Final packaged 0.1.3 readback

Release run 37143721968 passed all 15 native jobs and assembly. All 60 archives
in retained 0.1.0/1/2/3 trees match SHA-256. Exact assembled 0.1.3 updated the
Mac user installation; repeats returned CURRENT, fixture self-test completed
two actions/four decisions and config bytes were preserved. Disabled-capture
doctor correctly reports ready=false, pinned cache/MPS and five MCP tools.
See release-013-platforms.json, release-tree.json, installed-update.json and
installed-doctor.json. The transfer archive and deploy order are in RELEASE.md.
At the 0.1.3 checkpoint public HTTPS installation and native GUI were open gates.
The following Windows GUI evidence supersedes the latter for the measured scope.


## Windows native input and real model GUI, 0.1.4

The operator explicitly authorized actual Windows GUI testing and requested the
trycua/cua input reference. WINDOWS_INPUT.md pins that source and describes the
independent checked Win32 implementation and its boundaries. The five MCP tools
and semantic action whitelist are unchanged. Mixed/licensed cua source is not
vendored or installed.

Windows 11/Python 3.12.10 on Pocket4: an InteractiveToken/least-privilege on-demand
task ran session 1; SSH stayed session 0. No security-policy change, elevation,
unlock or autostart was used. Installed non-editable 0.1.4 wheel passed 57 tests
in 4.57s. Windows API fakes in boundary regressions prove zero/partial event
failure, Unicode surrogate pairing, cancellation/focus checks and release retries;
actual GUI checks independently establish effects on a disposable native window.
The initial pytest invocation omitted asyncio_mode=auto outside the repo and
reported two async collection failures; correcting the configuration passed the
same suite. It was not a product/input failure.

[Native GUI](windows-native-gui.json): actual entry readback `Windows 한글 테스트 😀`,
clipboard preserved, Ctrl+A/Backspace cleared text, click+double-click produced
three callbacks, wheel delivered -360, cancellation/control text sent no payload,
changed foreground was refused, no held native inputs remained after release.
2560x1440 screenshot and physical-coordinate mapping were observed. The final
non-editable wheel rerun passed. [Session zero](windows-session-zero.json) was
explicitly refused without input. Doctor only checks desktop availability.

[Initial real GUI/model run](windows-model-gui-initial.json) completed two native
clicks/four decisions in 99.334815s with zero outer interventions. OmniParser CPU
and CLEF-Flash MPS ran on macOS against actual cropped Windows pixels; Windows
executed canonical native input. Independent application callback readback was
Continue, Confirm, Task complete, and completion needed two fresh observations.
This is an actual disposable Windows GUI vertical slice, not Windows-local ML,
calculator coverage, every application, a performance comparison, a production
remote backend or unattended/secure-desktop support. The final packaged adapter
rerun also completed two actions/four decisions in 213.569719s, recorded in
windows-model-gui.json. These are separate cold loads under uncontrolled host load;
there is no measured speed improvement. Public screenshots contain only the
test-owned window. Test endpoints and ephemeral tokens are removed after use.

## Visual readiness iteration, 0.1.5

Owned frozen source passes 83 tests plus lint/format. Windows installed-wheel
checks passed 80 tests/6.86s and native GUI Unicode/shortcut/click/wheel/cancel/
foreground/cleanup readbacks. The latest diagnostic scripts check clipboard
sequence without reading or writing clipboard. The independent Windows app
reported Continue -> Confirm -> Task complete after two correct native actions
and relevant change/stability waits over 500ms delayed rendering. CLEF failed
during final verification: windows-visual-initial.json is ERROR, not COMPLETED.
Warm performance ablation was stopped because the cold task was unaccepted.

Controlled public-safe completion-image probes separate request context from
MPS execution. Keeping new mode/effect questions after existing questions and
omitting null actionability metadata produced goal 0.949 / condition 0.9638,
mode COMPLETED 0.903 with the full structured action history retained. Earlier
ambiguous context produced goal about 0.02; thresholds were not reduced. Exact
processor CPU/MPS image token counts matched 532 in eight repetitions. Vision
metadata indices/positions matched CPU in 24 repeats; maximum interpolation
weight difference was 6.4969063e-6. These checks do not prove model correctness.
Repeated real forwards still reproduced index errors; allocator clearing,
synchronization and retention are being compared with actual outputs/memory.
See VISUAL_READINESS.md and machine-readable diagnostic files.

The cache policy pilot returned CLEAR 2/8 errors, SYNC_CLEAR 3/8, KEEP 4/8
(clef-cache-ablation.json), so the production policy is unchanged. Allocator
state carries between rotated trials; this does not establish an independent
policy speed improvement or root cause. A subsequent Windows task ablation
retains every failure and marks actual worker cold restarts explicitly.


Latest final frozen 0.1.5 source passed 83 tests locally (21.45s), lint/format,
and wheel build. Final rebuilt noneditable wheel on Windows passed the same
83 tests in 7.42s with PYTHONPATH removed. The later repeated real model task
measurement was interrupted after four failed tasks: three ModelWorkerError
and one TimeoutError; all restarted at least one worker, no actual warm samples.
Only one accepted native action occurred, with zero observed wrong input,
early advance or false completion. A concurrent MPS diagnostic confounded host
load and was stopped; these latency values cannot establish an improvement.
windows-visual-measurement.json retains every completed task. The fifth task
was interrupted and excluded. No-effect model task was NOT_RUN. Diagnostics
now persist interrupted reports and stop after three consecutive backend errors;
warm percentiles include only actual resident-worker trials.
The fallback-environment probe was interrupted before producing results;
PYTORCH_ENABLE_MPS_FALLBACK is not established as the cause. Production model
worker and allocator policy are unchanged. Windows GUI agent exited and its
on-demand scheduled task/token were removed. New readiness-only native GUI
checks are separate from model/task acceptance. Existing unowned MLX/quantization
and residency changes remain excluded. Public HTTPS still serves 0.1.3; publishing
0.1.5 requires the assembled release-site delivery. Overall goal remains active.


Installed-wheel Windows native readiness smoke passed five delayed transitions
with unrelated blinking outside the target ROI: actual rendering occurred
563-578ms after input, and STABLE was returned only afterward, at 781-797ms.
The no-effect case returned NO_CHANGE at 1046ms against a 1s sampling deadline,
with one native callback and no repeat input. Six native actions and 57 actual
screenshot polls used zero model calls. windows-visual-wait.json records the
readbacks. This uses known owned-widget geometry and tests readiness only;
it is separate from CLEF task acceptance and supplies no speedup baseline.
Two harness schema mistakes were corrected before any native action in the
accepted run. Both disposable windows closed, inputs released, pointer/foreground
restoration requested; owned scheduled tasks, SSH forward and ephemeral token files removed.


Exact assembled Windows 3.12 archive installed via PowerShell in an isolated
owned root, version readback 0.1.5; repeated bootstrap/update CURRENT and fixture
self-test sample COMPLETED. User PATH equality was checked on the corrected
readback. windows-015-assembled-install.json discloses the initial result-parser
mistake and the boundary: installation/control flow, not GUI/model proof. Release
workflow 37159016423 passed 15 builds plus assembly; source CI 37159015133 passed
six jobs. New 15 and prior 60 archive hashes verified. Source checkpoint bd217b0.
Public HTTPS latest is still 0.1.3; 0.1.5 upload is prepared, not deployed.


## Controlled native Windows visual trials, 0.1.5

[Controlled report](windows-visual-controlled.json) used the installed Windows
native adapter, real owned Tk pixels/input, Mac OmniParser CPU and CLEF-Flash MPS,
500ms delayed rendering, one resident worker pair and rotating variant order.
There were no outer model interventions, backend errors or worker restarts.
Cold visual/no-cache task: COMPLETED, 86.1762s, 2 actions/4 decisions.

| Variant | Warm success | Empirical p50 / p95 | Parser / CLEF calls per task | Early advance |
| --- | --- | --- | --- | --- |
| 300ms fixed delay, diagnostic ablation | 0/5, BLOCKED | Successful latency unavailable | 2 / 2 before stopping | 5 |
| Visual wait without cache | 5/5 | 42.434 / 43.846s | 4 / 4 | 0 |
| Visual wait with exact cache | 5/5 | 42.694 / 47.114s | 3 / 4 | 0 |

Wrong input and false completion were zero in every variant. Fixed-delay failures
were safely blocked before repeat input; their shorter failure time is not a
speedup. The overall all-variant gate is FAILED because the weakened fixed-delay
ablation fails, while production visual variants completed 10/10 tasks. The real
no-effect task returned NO_PROGRESS after one correct native input/one CLEF call,
with no retry: 15.6474s total, 5.2643s screen sampling against a 5s deadline.
Screen sampling can finish after the deadline because a capture is in flight.

Warm mean parser call latency was 774.8ms without cache and 786.2ms with cache;
CLEF call latency was 8.871s and 9.266s respectively. Exact cache eliminated one
parser call per successful task, but this sample demonstrates no end-to-end speed
improvement. Host load was not controlled; n=5 empirical percentiles are not a
statistical guarantee. Earlier MPS failure evidence remains intact and its cause
is unresolved. Windows-local inference, arbitrary apps and macOS input are not
established by these results. Raw step metrics stay on the authorized SSD.

The later reporting tests passed 2/2 on the actual Windows installed interpreter
in 0.16s. Pure-source regression suite passed 85/85 in 7.19s; lint/format passed.
Hermes official CLI/handler evidence is [here](hermes-process-mcp.json): isolated
Python3.14 client and Python3.11 runtime, five canonical tools, 2 fixture actions/
4 decisions, exact upstream source tree checked. It does not prove an LLM agent
conversation. Original user settings and missing-interpreter wrapper are preserved.

2026-10-04 installation-to-removal acceptance: public HTTPS `irm .../install.ps1 |
iex` installed0.1.3 in a reserved native Windows root, then version/self-test,
idempotent update/reinstall, real resident service startup, CLI run/status/observe/
abort and idle shutdown executed. Fresh-install run returned ERROR before input
because model preparation was not part of the bootstrap. Managed root/launcher,
service endpoint/process were removed; existing user PATH/launcher remained equal.

The assembled native0.1.6 command additionally connected five actual stdio MCP
tools, exercised configured CLI refusal of SSH Session0 (`BLOCKED`,
`ACCESS_UNAVAILABLE`,0actions), then ran the installed package in interactive
Session1 with native Windows ROCm/NF4 CLEF and CPU Omni. Owned GUI independently
read `Continue -> Confirm -> Task complete`:2correctinputs/4jointdecisions,
127.9586342s task wall excluding preinitialization; diagnostic command187.2827891s.
Installed backends/model_worker/runtime/service SHA matched clean canonical source.
This uses the experimental loader/bridge, not released default CLI GPU integration.

Earlier0.1.5 attempts found real `0x80070005` limited-token launch denial: Python
private directories created by OpenSSH had Administrators ownership/OWNER RIGHTS
and lacked the account SID.0.1.6 grants only that same user inheritable access to
its installation root/new stage. The unchanged installed interpreter then started
from a least-privilege interactive task; no global policy change/elevation request.
Malformed identity is rejected before ACL mutation. All failed trials and cleanup
are retained. Clean canonical88tests/6.02s; native changed-boundary7tests/0.34s;
lint/format passed. No actor draft was included.

Normal idle shutdown and removal completed. Independent final CIM/task/socket
readback found no owned model/GUI processes, tasks,37945/54174listeners, endpoint,
installed root or launcher. PATH/previous launcher and model cache retained.
Evidence: [windows-install-lifecycle.json](windows-install-lifecycle.json); raw
SSD `validation/windows-lifecycle-20261004/raw/`. Public latest remains0.1.3;
new0.1.6 public delivery, full platform release matrix and canonical local-GPU
provisioning remain separate gates. One separate launch probe unnecessarily used
a process-only ExecutionPolicy flag; no machine/user policy was mutated and all
lifecycle/installer commands used EncodedCommand without that flag.

0.1.6 source checkpoint84d4aa3 published. CI37185328541 completed success in all
six jobs, actual logs each88passed. Release37185328391 passed all15 native
platform/Python build+installer jobs and assembly; downloaded bundle has15unique
expected targets and everyZIP SHA verified. Existing75archive hashes retained.

Native `scripts/check_installation.py` on ssh win additionally passed managed
`clef-use.cmd` launches in Unicode/space paths,0.1.6 install/CURRENT, synthetic
0.1.7 update and preservation on checksum/missing-download/failed-smoke cases.
Synthetic0.1.7 existed only inside temporary test tree, removed automatically.
No production0.1.7 release. Durable report `installer-command-016-report.json`.

Delivery `dist/clef-use-release-site-0.1.6.tar.gz`379782678bytes,
SHAd6d26b72dc45ae21f6b54f2ee50b22735511ee95c4a8296927279c381efaf2ec,
contains new release/latest/bootstrap only; preserve remote older releases.
Public metadata fresh read remains0.1.3/15targets; new FTP upload is not observed.
Source/CI/release delivery is ready, canonical local-GPU model preparation and
prerequisite doctor correction remain open full-goal work.


2026-10-04 doctor/cache prerequisite correction (source0.1.7): previously cache,
capture and MCP could admit missing ML environments or unavailable requested GPU.
Doctor now imports both isolated environment dependency sets and required lazy
Transformers classes, reuses canonical choose_device and executes a tiny device
sum. Source check validates exact OmniParser HEAD and tracked util changes; cache
inventory includes joint-head config/processor/tokenizer and pinned Florence
processor/caption code. No weights/readers/input loaded by the diagnostic.

Clean canonical tests95passed/6.58s; native Windows focused regressions7/.79s;
lint/format and wheel build passed, packaged probe bytes equal source. Actual
Mac MPS+CPU Omni and Windows ROCm+CPU Omni environment/device checks OBSERVED.
Both real CLI diagnostics intentionally --no-capture: readyfalse, Windows
SSH Session0 unavailable, five MCP tools observed. These are prerequisite checks,
not model-load/memory/quality proof. Evidence doctor-readiness.json; raw SSD
validation/doctor-readiness-20261004. First exploratory probe mistakenly checked
unused ultralytics; pinned icon_detect_v3 uses util.yolov9, corrected after direct
upstream inspection; final actual Omni checks pass without optional package.

Existing actor doctor/models edits merged only in working tree; canonical source
blobs staged separately, no actor acceleration/MLX/quantization change published.
Earlier synthetic0.1.7 update check is unrelated to this new source0.1.7 release.
Windows install/model-GUI proof remains prior0.1.6. No new GUI input this turn;
canonical Windows GPU/NF4 provisioning and public newest upload still open.

Doctor source0.1.7 published at a009b8b878f5380f78250646607b45759183241b.
CI37190038155 completed success for all six Mac/Windows/Linux xPython3.11/3.13
jobs; actual logs each95passed. All six build/install-update checks also passed.
Compact logs retained SSD validation/doctor-readiness-20261004/ci-37190038155-tests.txt.
No standalone15-target0.1.7 release assembly/public upload claimed. Next work
remains canonical Windows GPU/NF4 provisioning/worker integration, with new model
GUI proof through normal CLI/MCP and source-pinned environment checks. Existing
actor24 paths remain intact and unpublished; current owned change is this
evidence/documentation refresh. Goal ACTIVE; no live model/GUI/service handles.
