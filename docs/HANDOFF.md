# Engineering handoff

Updated 2026-10-04. Repo clef-use/main, public origin
https://github.com/snowman0919/clef-use. Prior published evidence checkpoint 84c55c7, runtime 0.1.5
source bd217b0. Source CI/release passed; current owned diagnostic changes passed
85 tests/7.19s and lint/format. Overall goal active; requirement audit in
IMPLEMENTATION.md, current evidence in evidence/VALIDATION.md. Entries below
are chronological history; the continuation block at the end is authoritative
for live handles and next actions. Preserve unowned MLX/residency changes.

Canonical runtime owns capture -> pinned OmniParser -> semantic candidates ->
joint CLEF choice/noul/score -> deterministic input -> fresh verification. CLI
and five MCP tools share one resident core. No shell primitive/per-harness core.

Authorization: external SSD /Volumes/SSD/AI/clef-use, public repo/push, Windows
ssh win. Latest user explicitly authorized actual Windows GUI and asked to
reference trycua/cua. The old GUI deferral is superseded for Windows only; Mac
foreground/input remains deferred. Preserve user settings, apps, changes/secrets.
Production deployment route is still unanswered; public latest was HTTP 404.

0.1.4 Windows DesktopCapture/DesktopAction use stdlib ctypes Win32 input, checked
SendInput counts, physical DPI coordinates, captured foreground identity,
interactive/default desktop guard, clipboard-free UTF-16 text and tracked cleanup.
Session 0/secure desktop/changed focus are refused. Doctor probes desktop without
input. cua source pin, independent design and reproduction: WINDOWS_INPUT.md.

Owned frozen source passed 57 tests, lint/format and wheel build. Task-owned
Windows Python3.12 installed non-editable 0.1.4 wheel and passed 57 tests/4.57s;
actual native Tk GUI passed Unicode/emoji, clipboard, shortcut, click/double-click,
wheel, cancellation/control refusal, changed focus and no-held-input readbacks.
Real Windows GUI + Mac Omni CPU/CLEF MPS diagnostic loop completed 2 native
clicks/4 decisions, no outer interventions, 99.334815s; actual app readback
Continue -> Confirm -> Task complete. Final installed-wheel rerun also completed 2 actions/4 decisions in
213.569719s; both cold loads vary with uncontrolled host load. No Windows-local ML/GPU, arbitrary app/calculator or Mac-input proof.
Windows tests use an on-demand least-privilege InteractiveToken task, no security
policy changes/elevation/autostart. Close only disposable own windows; cleanup
SSH forward, own finished task and ephemeral tokens before ending the test.
These resources were removed after final GUI completion.

Windows workspace: %LOCALAPPDATA%/clef-use-validation-20261004. source/.venv holds
our 0.1.4 installed wheel; clean Git source remains previous 000885b until own
push/pull. windows-native-src is a temporary frozen-source diagnostic copy; final
native reruns import installed wheel. Mac pure tree /tmp/clef-use-windows-audit,
clean tool env /tmp/clef-use-audit-env. Original project .venv remains unmodified.

Earlier 0.1.3 CI 37143721190, release 37143721968 and doc CI 37144979945 passed;
0.1.3 site had all 15 platforms/Python targets and retained 60 hashes. Installed
Mac exact assembled 0.1.3 and config byte-preserved. 0.1.4 artifacts/CI to be
recorded after source push; do not replace existing version hashes. Existing
transfer dist/clef-use-release-site-0.1.3.tar.gz is now historical; latest delivery
must include the 0.1.4 release and latest metadata, preserving older versions.

Unowned edits are preserved and excluded from source/CI/release:
README.md; docs/INSTALL.md; docs/{ja,ko,zh-CN}/README.md; backends.py worker/CLEF
sections; cli/client/config/model_worker/models/provision; doctor acceleration
sections; service model holds/unload; tests/test_protocol.py extra model-hold;
acceleration.py, mlx_support.py, quantization.py, quantization_prepare.py;
extra acceleration/model-residency tests and MLX/quantization/residency evidence.
Stage only owned backends/doctor blobs from the frozen HEAD+owned tree. Do not run
dirty-source tests or publish unrelated edits. No subagents were delegated.

Next bounded actions: checkpoint reviewed Windows patches; validate CI/native
release+installation. Then implement the newly received user-requested visual
condition waiting, action-effect/stale ROI checks, explicit non-action decisions,
structured effect history and exact-image perception cache. Preserve strong
completion checks and bounded cancellation; measure effects before speed claims.
Refresh public metadata when an authorized route is available. Public install cannot be claimed until latest metadata/artifacts
and isolated public one-line installs work. Keep Windows-local ML and broader GUI
coverage explicitly separate. Full Hermes launcher still missing; Codex readback,
OMP native MCP and official Hermes discovery/handler passed at earlier checkpoint.

Visual iteration: screenshot-only bounded waiter replaces fixed settle delays,
tracks target/nearby ROI and foreground bounds; ACT/WAIT/BLOCKED/NEEDS_REPLAN/
COMPLETED remains one joint CLEF request. Unknown actionability stays unknown;
exact raster/geometry/model cache reuses perception only. Explicit text/goal
checks remain separate from readiness. Canonical owned snapshot:
/tmp/clef-use-visual-audit, refreshed by /tmp/clef-use-freeze-visual.py.
Do not test or publish the combined dirty tree. Next: pure regression checks,
installed Windows wheel/native smoke, controlled real-model GUI wait/cache
ablations, source checkpoint and release checks. No speed claim yet.

2026-10-04 visual iteration: own frozen final tree
/tmp/clef-use-visual-audit-final passes 82 tests, lint and format; installed Windows
0.1.5 wheel passed 80 tests/6.86s and native GUI. Clipboard sequence is checked
without reading/writing clipboard. pythonw task could not acquire foreground;
ordinary console Python task acquired the owned window without bypassing focus
policy. Public HTTPS 0.1.3 manifest now has 15 targets and isolated Mac/Windows
installs/self-tests passed; prior 404 blocker is resolved for 0.1.3 only.
Mode criteria initially stopped with low confidence; actual Omni detected the
correct Continue target. Clarified goal/evidence criteria + explicit allowed
candidates yielded ACT .8461 without changing thresholds. Subsequent actual
Windows run made two correct native clicks, waited for 500ms delayed rendering,
and app readback Task complete, but final CLEF forward failed in Qwen3.5 image
placeholder validation. This is ERROR, not completion or performance proof.
Warm ablation was stopped at failed cold acceptance. All failed results retained.
Standalone processor CPU/MPS count probe found 532 expected image tokens with
identical input IDs over eight repetitions. /tmp/clef-use-forward-probe.py now
runs six actual repeated public-safe completion forwards, preserving exact
exception/numerical evidence in /tmp/clef-use-forward-diagnostic.json. No blindly
removed cache clearing or new framework. Next: inspect forward evidence, fix only
proven cause, rerun controlled GUI benchmark, then source/CI/release.

Latest request-context correction is in the final frozen source: omit null
actionability metadata from CLEF state, append new mode/effect questions after
existing questions. Full structured history retained. Completion-image ablation
then returned goal .949/condition .9638/mode .903, no threshold reduction. Final
frozen checks now 83 tests. /tmp/clef-use-cache-ablation.py compares CLEAR,
SYNC_CLEAR (before forward + before clearing), KEEP on the same resident model
and completion request, rotating order, eight repetitions each; outputs and
MPS/RSS measurements /tmp/clef-use-cache-ablation.json. Early KEEP reproduced an
index failure; wait for all measurements before selecting a policy. No production
model_worker change yet. The diagnostic GUI task is finished, tokens and SSH
forward remain task-owned for the next bounded run; remove at final cleanup.

Cache policy pilot completed: CLEAR 2/8 errors, SYNC_CLEAR 3/8, KEEP 4/8;
no reliable fix established and production policy remains unchanged. Runs rotated
within one resident process, so allocator carryover prevents a standalone policy
speed claim. Actual model condition/goal requests are now calibrated with full
history and omitted null metadata, questions appended. Current 15-run Windows
measurement controller uses /tmp/clef-use-visual-audit-final and writes
/tmp/clef-use-visual-measurement.json. Every failure is retained; actual cold
worker restarts are marked explicitly. This is a reliability measurement even
if backend errors prevent a speed conclusion. GUI owned task has 45min cap.


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


Source checkpoint bd217b06868f49b963b37b21b0d9535ccea24baa is published on
origin/main; CI 37159015133 passed all six jobs. Release workflow 37159016423
passed all 15 builds and assembly; all new 15 and prior 60 archive hashes verified.
release-site/ retains earlier versions plus 0.1.5, latest now local 0.1.5.
Upload archive dist/clef-use-release-site-0.1.5.tar.gz is 379774706 bytes,
SHA256 f6145b1dcfc0553d971fb0f21daa95c249b538e3e1ae6972968b0b4f374cb66a.
A second durable copy is on /Volumes/SSD/AI/clef-use/releases/0.1.5/.
Fresh public HTTPS metadata is 0.1.3/15 targets. Do not claim 0.1.5 deployment.
Windows clean source fast-forwarded to this exact commit and installed wheel
passed 83 tests in 7.48s, import confirmed site-packages outside source. Native
readiness/input checks already accepted; do not repeat them without a new change.
Next bounded work: record assembled native installer readback; operator deployment
of prepared site; isolated, nonconcurrent CLEF MPS diagnosis if a new concrete
hypothesis justifies it. Preserve actor-owned dirty files and configs. No source
model-worker policy change or general speedup is accepted. Goal remains active.


Assembled native Windows package install was observed INSTALLED/version 0.1.5;
repeat bootstrap and update returned CURRENT. Self-test sample COMPLETED and
persistent user PATH equality passed on the corrected readback script. The first
diagnostic incorrectly indexed top-level self-test status; this was a report
parser error after successful installer execution, not a product error. The
loopback installer server stopped; no background GUI task/token/forward remains.
Evidence: windows-015-assembled-install.json. Public latest remains 0.1.3.


2026-10-04 continuation: prior turn classified progress (published tested source,
15-target release and actual native GUI evidence). Current root 84c55c7/main,
actor-owned 24 dirty/untracked paths still excluded. Official Transformers
placeholder+scatter mini test at actual [1,1781,4096]/532 image tokens passed
24 runs exact against CPU; not full-model proof. Canonical environment flags,
same retained public-safe completion request and one resident Flash MPS process
returned identical complete .949/condition .9638/mode .903 in four forwards
(two baseline, two diagnostic CPU-copy hooks). This does not fix intermittent
MPS failures or isolate their cause. Detailed reproduction scripts/raw records
are on SSD diagnostics/20261004-boundary; compact evidence in repository.
Actual 0.1.5 Window GUI rerun with 500ms rendering delay COMPLETED, two correct
native clicks/four decisions in 69.9906427s; parser 3, CLEF 4, exact cache hit 1,
20 screen polls, 2204.859ms wait/58.880ms pixel verification, zero outer clicks.
Single cold run under host load, not speed comparison. Agent closed; token/task/
forward still owned and pending reuse or cleanup. Do not overwrite earlier failures.
Hermes user wrapper is present but its target venv/bin/python is absent. Preserve
it and global configs. Exact official 3c9847f5 source/lock/CLI file hashes verified.
Isolated Python3.14.2, uv0.12.23 and source on SSD harness-validation/. uv0.9.24
could not parse newer lock settings; noneditable upstream build is deliberately
unsupported. Changed only audit setup to official editable installation. Ongoing
sync handle 58881; GUI client 76812 terminal COMPLETED; private forward 52040 live.
Next: official isolated Hermes CLI MCP connection, controlled actual-model warm
wait/cache comparison after installation stops, clean owned resources, update
acceptance audit. Public latest 0.1.3; new 0.1.5 publishing route unavailable.


2026-10-04 durable continuation: previous turn classified progress (actual 0.1.5
Windows GUI acceptance plus MPS boundary measurements). At resumed inspection,
old exec handles/processes were absent and /tmp outputs gone; SSD was disconnected.
User reconnected SSD, confirmed actual paths now present. Old Windows own task
was Ready, no bootstrap process; exact action ownership checked and task/gui-token
removed. Old SSH forward absent. No repeat was started from observation timeout.
New benchmark checkpoints atomically replace/fsync private reports, record the
active trial before reset/input, reserve unique durable default output, reject
existing output, separate successful-warm percentiles from all warm attempts.
Acceptance requires cold success, full balanced actual-warm samples, zero wrong/
early/false actions and a bounded negative trial with exactly one attempted input.
Two regression tests cover false acceptance and failed checkpoint replacement.

Isolated official Hermes full CLI mcp test and separate native registry handler
both exited 0 against canonical 0.1.5 fixture, two actions/four decisions.
Four upstream files (pyproject, uv.lock, main, mcp_config) byte-matched official
3c9847f5 raw source. Reproducer is scripts/check_hermes_client.py optional
--hermes-cli/--hermes-python mode. Report evidence/hermes-process-mcp.json;
raw compact report on SSD harness-validation/hermes-process-report.json.
No model/GUI proof from that fixture; original user broken wrapper unchanged.

Controlled measurement finished terminal handle75801 (exit1 from deliberate fixed
ablation failures, not backend failure). See evidence/windows-visual-controlled.json.
Cold visual task COMPLETED86.1762s; actual-warm visual variants10/10 COMPLETED,
zero wrong/early/false inputs and no backend errors/restarts. Per variantn5:
no-cachep50/p95=42.4343/43.8465s; cache42.6941/47.1135s. Parsercalls4->3,
CLEF4unchanged; no demonstrated wall-time speedup. Fixed-delay5/5BLOCKED,
earlyadvance5, no repeated/wrong input; shorter failure times are not speedup.
No-effectNO_PROGRESS after1correctinput/1CLEF,15.6474s total/5.2643s screen wait.
Raw full metrics on SSD validation/20261004-controlled-recovery/controlled.json;
compact public report includes actual callback readback/source hashes and limits.
Report acceptance intentionally gates all variants; FAILED is explained separately
from10/10 production visual successes. Historical MPS errors remain unresolved.

Current test snapshot /tmp/clef-use-continuation-audit has published84c55c7 core,
owned diagnostic scripts copied before measurement (later root changes only
canonical default report directory and Hermes source provenance). It passed85
regressions/7.19s and lint/format. Reporting regression tests passed2/2 on native
Windows installed0.1.5 interpreter in0.16s. Official Hermes CLI+handler rerun
verified actual client source paths belong to exact upstream source tree and passed.

Cleanup observed: owned GUI process absent, exact task action reidentified then
clef-use-controlled-validation-20261004 deleted; both gui-token files removed;
own SSH PID18125 command reidentified and terminated. Agent finally releases
input, closes own window, restores cursor and requests prior foreground. Foreground
restoration itself is not independently asserted. No other app/process touched.
Fresh canonical public manifest: curl and Windows Invoke-RestMethod HTTP200,
version0.1.3/15targets. Pythonurllib403 is client-specific admission. New0.1.5
public upload still unobserved, immutable release-site/hash unchanged.

Next bounded action: review/stage/publish only owned diagnostic/docs/evidence;
monitor resultingCI. Then audit full36-sectiongoal against canonical implementation
and evidence, preserving Mac input deferral, Windows-local inference NOT_RUN,
optional largerCLEF/CUDA untested and new0.1.5 operator upload blocker. Do not
claim arbitrary-app/model stability or mark goal complete from this narrow smoke.
All actor-owned MLX/quantization/residency changes remain excluded. No subagents.
