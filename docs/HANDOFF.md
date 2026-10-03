# Engineering handoff

Updated 2026-10-04. Repo clef-use/main, public origin
https://github.com/snowman0919/clef-use. HEAD f130d6f (published 0.1.4), all six source CI jobs passed.
Owned visual-condition waiting changes are in progress. Overall goal remains active; numbered
requirements: IMPLEMENTATION.md; evidence: evidence/VALIDATION.md.

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
