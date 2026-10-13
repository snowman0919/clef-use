# Reactive runtime execution status

## Source 0.1.43 caller Torch budget correction, 2026-10-14

**OBSERVED / offscreen native control and source candidate:** the exact preserved
original Windows editor parser request reproduces an inference timeout after
readiness. Installed .42 initializes in 10.8 seconds, completes OCR 22/detection 139/
fusion 81, returns the first caption generation, then exceeds its unchanged
180-second receive limit during generation 2. This separates this replay's
initialization from its inference failure; it does not retrospectively observe
the original InteractiveToken worker's internal phases or environment.

Paddle import changes absent OMP_NUM_THREADS to 1; native post-import Torch reports
one thread. A separate real import intervention observes caller Torch 12 becoming 1
and restores 12. Source .43 captures the resolved caller Torch budget before upstream
imports and conditionally restores it before detector/Florence loading and task
inference. It adds no thread setting or hardcoded CPU count. Paddle's environment
change itself remains;
the preserved contract is the caller's Torch budget in the isolated model worker.

The private source candidate completes the same request with 81 objects and 59
captions over four generations: 84.95 seconds from inference receive to reply,
95.47 seconds including initialization/cleanup. These are single instrumented
diagnostics with file I/O/copy/hash overhead, not production performance evidence.
OCR output, source image and first 16 caption tokens match the retained control.
Detection/fusion preserve count, order and all nonnumeric values, but are not byte
identical: maximum numeric differences are 0.000244140625 for detection output and
1.1920928955078125e-7 for normalized fused geometry. The control's later captions
are censored, so complete numerical/task-quality equivalence remains NOT_RUN.

**OBSERVED / real prepared-parser regression:** fresh child processes use actual
Torch, pinned upstream models and constructor readback. Original code fails the
native/default and explicit 4 budgets (1 != 12, 1 != 4); explicit 1 passes. The candidate
passes all three without skips. An initial driver omitted canonical cache/offline
environment and all six constructors failed before thread assertions; that attempt
is retained as NOT_RUN for the invariant, with inner errors unavailable. Corrected
tests set canonical cache/offline variables only in each child. Local .43 regression
passes 1612 tests, skips 49 and reports 41 warnings in 110.70 seconds; the three new
prepared-parser cases skip locally without its explicit configuration/dependencies
and pass in actual Windows as above. Generated contract checks pass all 198 published
CLI examples and 12 tool examples. Immutable .43 CI/installation remains NOT_RUN at
this source checkpoint.

No desktop capture or OS input runs in these diagnostics. Actual installed editor
task, current Codex GUI task, complete pinned accuracy suite, 1000 opportunities,
100ms p95/coverage/goodput, Blender hidden contexts and public release remain open.
See the [partial native parser receipt](validation/2026-10-14/windows-omni-thread-budget-0143.json).

## Actual installed Windows and source 0.1.42 verification recovery

**OBSERVED / immutable CI and installation:** `d8b5218` completes run
`38427788423`, all fifteen build/install jobs and assembly. Every archive matches
all 68 Git product payload files. Actual Windows .41 -> .42 returns INSTALLED;
repeat returns CURRENT, managed Codex refresh and unrelated configuration/previous
version preservation pass. Session 0 doctor has no interactive desktop. Public
deployment is skipped by the existing feature-branch guard. These results are
[installation evidence](validation/2026-10-14/windows-installed-ci-0142.json),
separate from prior .40 native inputs and failed whole tasks. Previous .41
immutable CI/installation evidence remains retained separately.

**OBSERVED / OMP evidence correction:** replaying the retained actual .40 batch
through the corrected consumer identifies two failed native `write` attempts in
the explicit case and one successful `write` in the unrelated-request case.
The earlier `--tools` list restricted the initial catalog, but native SDK lazy
registration reintroduced the writer. Those sessions did not enforce read-only
filesystem scope. Explicit/natural/unrelated cases now all classify FAIL; a
deadline cannot erase an observed forbidden attempt or earlier status error.

Source .42 uses native `--config` approval overlays without editing persistent
settings. Existing non-probe grants become deny, explicit reader deny/prompt is
preserved, and `read:null` leaves native argument-sensitive tiers in control.
Native `Settings.loadReadOnly` avoids migration/storage writes; legacy-only
settings require migration outside this read-only preflight. Full guide bodies,
source hashes, runtime/schema/guide contracts, complete call inventories and
actual selected-project cwd are verified. Unknown tool attempts and errors cannot
pass after later success. Native helper nonzero exit prevents model startup;
managed verification is serialized with installation/removal/update.

Two initial .42 preflights fail before model execution: native stdout truncates
at 8192 bytes, then an awaited stdout write duplicates its prefix at that boundary.
Both batches remain NOT_RUN with no model requests. The helper now writes complete
native results to a seeded private 0600 file, rejects symlinks and bounds its read.
No stdout reconstruction/fallback is used. Final native preflight and two
concurrent public native-only CLI verifications PASS with managed bytes preserved.

The fresh actual .42 model batch remains FAIL: explicit reads the full core guide
and invokes capabilities but repeats two absent-runtime status errors and reaches
the 90-second budget; natural invokes capabilities without reading the required
guide; unrelated invokes capabilities despite the actual no-runtime request and
also reaches its budget. All three exact user prompts are observed in native
messages. No writer attempt or unexpected project file is observed; global
configuration is unchanged and the temporary policy is removed. Native source
supports catalog inclusion, but the exact provider system request was not captured:
catalog delivery is INFERRED. Unsafe native HTTP/header recording is not enabled.
This does not close GUIDE-03, GUI E2E, model accuracy or reaction-performance gates.
The native writer-wrapper component separately returns the actual user-policy
block before creating its owned receiver file; native local reads remain allowed
and SSH reads retain exec/prompt classification. This uses real native Settings,
SessionManager and tool classes with unused runtime/model-registry context, not a
complete SDK/model session. Actual model writer-pressure makes no completed write
call before its budget and is NOT_RUN for model-driven denial. An initial component
matcher used the wrong denial word and is retained separately. The existing owned
Hermes profile refreshes to .42 and native catalog/load/invoke/two-tool scope PASS
with its configuration unchanged; this refresh runs no model. See the
[native harness receipt](validation/2026-10-14/omp-native-verification-0142.json).

**OBSERVED / separate passive OMP request diagnostic:** one additional natural
case uses a hook-only native trusted extension. All nine actual request bodies
contain exactly one leading system/developer skills catalog with all three guides,
and their user content matches the exact requested prompt hash. Only whitelisted
names, counts, booleans and digests are recorded; HTTP headers and body text are not
retained. These are native pre-provider JSON payload hashes, not final HTTP byte
hashes, and do not retroactively observe the original unmodified batch's requests.
The diagnostic reads Blender/diagnostics guides and invokes capabilities, but
remains FAIL after status/tool errors, a forbidden writer attempt and its deadline.
The actual model's native writer is blocked by tools.approval.write:deny, with no
project-file change. This supplies actual model-driven denial evidence separately
from the earlier NOT_RUN pressure case. It proves neither a whole-process sandbox
nor successful model trigger behavior. See the [request diagnostic receipt](validation/2026-10-14/omp-request-catalog-0142.json).

**OBSERVED / installed Windows Codex cache challenge:** the actual .42 default
runtime captures/parses a real owned Task complete screen in an input-free ASSESS
session. The independent receiver then resets to Continue. Native Codex reads the
full core guide, discovers current schemas/capabilities, reads the unchanged cached
frame, obtains a new frame and correctly reports current completion false. Cached
full frame reference/id/hash match the seed; fresh HWND/bounds match the owner,
and its actual runtime-process capture timestamp is after the verified reset.
The owned receiver remains incomplete without a click/effect. All final cleanup
checks pass, including original foreground, input release and global configuration.

Two proof-driver failures remain retained: the first wrongly demanded one OCR
object instead of the actual Task/complete word pair and never starts Codex; its
foreground restoration fails with native API details unavailable. The second
observes core-guide/cached/capability success but its extra capability-before-cache
prerequisite declines the authorized fresh request. Its full challenge remains
NOT_RUN. Corrections change only the private premise/controller; product candidates,
confidence thresholds and dispatch guards are unchanged. The final single case
proves the completion-evidence branch, not authorized-input cache misuse, other
harnesses, original Continue/Confirm success, OS-wide critical-error coverage or
latency. See the [actual cache challenge receipt](validation/2026-10-14/windows-codex-cache-0142.json).

**OBSERVED / installed independent Windows editor task:** the original contract
is unchanged: enter exact 123 in Text input, click Save once, max_steps5, threshold
0.9, AUTO, original conditions/constraints/text attachment. Actual installed
RuntimeClient/service/default factory runs against an independent native RichEdit
receiver. Its first parser request returns no reply and the runtime ends ERROR,
TimeoutError in runtime backend, zero actions/decisions. The field remains empty,
status Not saved, Save count0, saved bytes absent and false completion false.
No candidate roster or typing/focus/IME guard was reached; startup versus inference
timeout subdivision is unproven. This is neither a native harness task nor a pinned
Linux/Windows paired accuracy comparison.

Read-only process classification identifies brave.exe as the other foreground
owner in all five non-receiver transitions. It is neither this runtime/receiver
nor a process recorded by the owned passive hook. The initiating actor remains
unproven; parallel desktop use has been asked about while repository work continues.
Before cleanup that process owns foreground. The fixture preserves that owner
and does not attempt restoration; the initiating cause is not yet proven. Runtime
endpoint, owned process/resources, input release and global configuration cleanup
pass; original foreground restoration fails. No automatic refocus/retry is used.
See the [actual editor failure receipt](validation/2026-10-14/windows-editor-task-0142.json).

## Current unfinished acceptance checks, 2026-10-14

The goal remains active. Original statuses are 34 PASS / 3 FAIL / 7 NOT_RUN;
component passes below do not close whole-task requirements. Authentication is
not the current cause of the executed Codex, Hermes or OMP model results.

| Acceptance ID | Current evidence and exact remaining condition |
| --- | --- |
| GUIDE-03 | Current Hermes explicit, natural Blender and unrelated-request cases pass with native two-tool read-only scope. Latest OMP .42 explicit has absent-runtime status errors/budget exhaustion, natural omits the guide, and unrelated calls capabilities/budget exhaustion. Earlier .40 write attempts are retained; no writer attempt occurs in the original .42 batch, while the separate passive diagnostic blocks an actual attempted write. Older route-specific HTTP 401 is historical. |
| GUIDE-04 | Installed .42 Windows Codex cached-to-fresh completion challenge PASS with independent incomplete receiver and cleanup. Authorized-input cache misuse and Hermes/OMP challenges remain NOT_RUN; one case does not establish general reliability. |
| INPUT-05 / E2E-01 | Installed collector/provider/compiler connects eleven Blender facts, but eight dispatch facts remain UNKNOWN and all six operation families are BLOCKED with zero input. Public RNA and native UIA do not prove Blender popup/input owner/effective keymap/IME/idle. Real menu/transform/property/viewport success and the full input-context matrix remain unverified. File-menu 0/5 is retained separately from operation admission. |
| E2E-02 | Installed browser parser exceeds its unchanged 180-second inference timeout; captioning of 38 regions is unfinished after OCR/detection. Actual Codex delivers Continue once but refuses Confirm at ACT confidence 0.6958 below 0.9, despite the correct candidate and geometry. Actual installed .42 independent native editor with the original contract FAILS at its first parser backend timeout, zero decisions/actions; other-process foreground ownership precedes cleanup and restoration is refused. The other foreground owner is brave.exe; its initiating actor and parallel desktop ownership are awaiting clarification. |
| PERF-01 / PERF-02 / PERF-03 | The same complete real-task suite against pinned baseline, at least 1000 predeclared opportunities, state-change-to-correct-OS-input p95 <=100ms, prospective eligibility coverage >=0.80, goodput and critical-error review remain NOT_RUN. Existing Tk/component timings do not meet this scope. |
| E2E-03 | Reici matched-view evidence and independent review are pending the separate session; this does not stop repository work. |
| RELEASE-01 | All fifteen immutable .42 CI artifacts and actual Windows .41 -> .42 update pass. Public deployment is skipped by the existing feature-branch guard; public URL/hash/fresh-install/update proof remains NOT_RUN. Do not bypass release gates. |

## Actual Hermes verification correction, source 0.1.41

**OBSERVED:** native stream output truncates large tool responses to 5000 characters
plus an ellipsis, and concurrent same-name calls omit result IDs. The verifier now
recovers the complete read-only native session, binds exact session/call/argument
inventories and uniquely matches response bytes. Confined spillover is bounded;
shared prefixes, altered/truncated responses and failed calls cannot pass. The
retained diagnostics pressure session now proves all three full guide loads and
two successful capability responses without rerunning the model. It did not prove
server-enforced read-only scope: native Hermes filters the parent's environment.

The correction sets the selected unchanged managed MCP entry's read-only flag
through native in-memory registration. It preserves disk configuration, native
CLI entrypoint/generated prompt, authentication and selected model. Native live
discovery must prove the actual capability/status two-tool schema before model
execution. New actual explicit, natural Blender and unrelated-request model
sessions each PASS with this scope; no effectful tool attempt is observed. These
are one sample per case, not a measured trigger reliability or Windows installed
release claim. A separate explicit diagnostics pressure run reads all three guides
and invokes capabilities, but its status lookup returns `runtime service is not
running`; the overall result remains FAIL. Native generated resource/prompt
adapters are read-only protocol calls, not product invocation proof. Failed
protocol calls still fail verification. See the
[actual harness receipt](validation/2026-10-13/hermes-canonical-verification-0141.json).
The native `skills` toolset also exposes `skill_manage`; native CLI/config cannot
select only its two reading tools. This overlay enforces the MCP scope, not a
whole-process write sandbox. Any native skill-management attempt in stream or
canonical history fails verification. None is observed in the recorded sessions.
Review additionally reproduced pending-tail and canonical-only omitted-effectful
false passes; the final scorer rejects both and preserves their regression cases.

## Actual installed Windows 0.1.40 on 2026-10-13

**OBSERVED / immutable CI and installation:** commit `7e744c5` produced 15
successful build/installation jobs and the assembled release-site artifact in
run `38391697986`. All 15 archives match all 68 tracked/force-included product
payload files, including the three guides, schemas and license notices. The
actual Windows installation updated from 0.1.39 to 0.1.40, matches those 68
payload hashes and refreshes the previously managed Codex command. Repeat update
returns CURRENT. Unrelated configuration, unrelated Codex bytes and prior version
files remain preserved. Feature-branch public deployment is SKIPPED. The SSH
Session 0 doctor correctly reports no interactive desktop; the following native
checks execute separately in the signed-in desktop session.

**OBSERVED / installed keyboard and independent recovery:** the compiled generic
route inserts the exact six-UTF16-unit fixture literal. Four active-IME refusal
routes preserve the positive two-byte preedit and existing editor text with zero
forwarded send calls. Native Ctrl+A selection, Backspace empty readback and a
single acknowledged Enter callback moving focus to the second owned RichEdit
pass. IMM/layout restoration, keys, worker/guardian, windows, foreground and
scheduled-task cleanup pass. Left/right/middle buttons, three bounded gestures,
blocked-injector cancellation and terminated-worker guardian recovery also pass.
A separate installed CLI abort releases held Shift/middle input while the
injector remains blocked and its lease is unexpired. Suspending every worker
thread leaves its heartbeat unchanged; the independent guardian releases input
at the six-second deadline before resume, EOF or parent release. After resume,
the worker observes cancellation and refuses further input.

**OBSERVED / default Blender state connection:** the actual runtime factory wraps
the live collector's BlenderStateProvider in WindowsStateProvider. Eleven bound
application facts reach the State Compiler. Unsupported custom Blender UI yields
zero native UIA facts; eight dispatch facts remain UNKNOWN. All six registered
operation families remain BLOCKED with input_count=0, and wrong-foreground
sampling is refused. This proves the installed connection and guards, not
successful menu/transform/property/viewport input. Owned Blender/UIA worker,
pointer, foreground and task cleanup pass. Native installed GDI lifetime and
observer transport regressions pass 12 tests with zero skips or failures.

**OBSERVED / browser component and actual Codex task:** an owned real Chrome
profile using `--force-renderer-accessibility` accepts the exact fixture literal
through UIA/compiler/generic native input, independently verified by a nonce-bound
DOM beacon. This input component is separate from model-task completion. In the
actual native Codex GUI task, guide load, schema discovery and invocation pass.
Continue is delivered once, but Confirm is refused: action confidence is 0.928
and the separate ACT-mode confidence is 0.6958, below the unchanged 0.9 gate.
Independent readback remains stage 1 with Confirm visible and no Task complete.
Both actual packets retain the correct target among three nonuniform candidates;
their geometry matches independent widget bounds. This failure is mode judgement,
not candidate omission/flattening or authentication. All owned cleanup and global
configuration preservation pass. Initial browser provenance/accessor fixture
failures are retained separately; neither started model execution or task input.

The [installed 0.1.40 receipt](validation/2026-10-13/windows-installed-ci-0140.json)
contains whitelisted facts and private artifact digests. Literal wall times and
forwarded method counts do not establish state-change-to-correct-input p95,
prospective fast-path eligibility coverage or pinned whole-task accuracy.
Original acceptance statuses and numeric release gates remain unchanged.

**OBSERVED / actual browser model task FAIL:** a separate installed default
Omni/CLEF factory executes the original E2E-02 semantic contract, entering exact
123 in Text input and clicking Save once, at threshold 0.9/max_steps 5. Native
focus, identity, writability and idle-IME facts are VALID before the task.
The first parser call times out: runtime ERROR, zero decisions/actions/forwarded
send calls, parser 194078.960ms and whole-task wall 194.131s. Independent DOM Save
readback is absent; false completion is false. Model workers, owned browser,
loopback server, inputs and previous foreground are cleaned up. This is an actual
failed task, separate from successful browser input delivery. The original
attempt did not archive startup-versus-inference failure state or worker stderr;
the exact preserved image request is retained for a separate read-only diagnostic
replay. Different OS/rendering prevents treating it as a paired Linux baseline.

**OBSERVED / parser diagnostic separation:** the identical preserved request's
canonical read-only replay becomes ready in 10.536s, then its inference receive
exceeds the unchanged 180s backend timeout. A separate direct native stage probe
records OCR 14 regions in 34.077s, detection 87 in 3.829s and fusion 52 objects;
captioning starts with 38 regions and does not finish before timeout. Neither
diagnostic sends desktop input. A single CPU batch-one feasibility attempt keeps
the same model/dtype/processor/generation parameters and request bytes, completes
19 of 38 generations and also times out. It is rejected without a production
change. Exact baseline boxes were not saved, so full-roster/output equivalence,
five alternating warm comparisons and an improvement claim remain NOT_RUN.
Foreground-only cropping is also rejected before implementation: native menus
can extend outside their owner window, losing structured candidates and public
observation coverage. No candidate, timeout or confidence gate is weakened.

## Recovery execution resumed on 2026-10-13

The user resumes the existing goal, authorizes Windows E2E and normal deployment,
and keeps separate Blender host builds/model production outside this repository
scope. Reici verification waits for the other session and does not stop clef-use
development. The named `clef-use-unblock-recovery-goal.md` was not found by filename
or matching content in the available local attachments; the user's explicit
recovery instructions are applied. Reading that unavailable file is NOT_RUN.

**OBSERVED / source Windows observation connection:** the four original dirty
files were preserved with bytes/hashes in a private snapshot before editing.
An owned factory Blender 5.2 on the actual Windows interactive desktop ran the
standalone public-RNA collector. Native peer PID/user, private NTFS metadata and
physical foreground/client geometry bind its facts through BlenderStateProvider
and SessionRuntime's actual capture/State Compiler path. Selection/datablock
identity, object mode/properties, scene units, editor layout, configured tool,
raw keymap inventory and view revision arrive as partial application evidence.
All eight inspected unobserved guards stay UNKNOWN. Six registered operation
families return BLOCKED with input_count=0; wrong-foreground sampling returns
UNAVAILABLE. Pointer and exact previous foreground restoration, owned Blender
exit and scheduled-task removal pass. This is source-component execution, not an
installed-current operation success or full E2E pass.

The original Windows metadata probe failed ownership validation because the SSH
admin token's default file owner was Administrators. Explicit exclusive native
file creation with the current-user security descriptor fixes ownership without
loosening ACL checks. Eight native transport tests pass, including a real distinct
Python peer, foreign ACL refusal, metadata redirect/coercion refusal, preservation
and UI-thread-only sampling. Failed/short native writes initially left a new
incomplete endpoint in two fault-injection subcases. Both now remove only the new
owned file; existing endpoint bytes remain preserved. The first PID test incorrectly compared the native peer
against a venv launcher PID; its retained failure is corrected by comparing the
actual receiver PID. Linux scoped checks pass 185; Windows-only cases skip.

Two initial Blender smokes retain `UI thread did not sample within 400ms`.
The first also used unsupported `--no-splash`, interpreted as a file to open.
Removing that flag alone did not resolve the timeout. Disabling the disposable
instance's startup splash through public preferences before UI startup produces
the successful connection. No production preference was saved; timeout and
input guards are unchanged. Full source regression passed 1418 tests with 42
skips and 41 warnings in 66.02 seconds. Active Ruff/format checks cover 151 files;
generated contracts pass. See [Windows observation evidence](validation/2026-10-13/windows-blender-observation.json).

**OBSERVED / installed Windows CLI abort:** the actual immutable 0.1.36 executor
holds native Shift/middle input while its injector is independently blocked.
A separate installed CLI sends abort through the authenticated loopback HTTP
service and real SessionManager/SessionRuntime.abort. Session ABORTED, cancellation,
native held [4,16,160] -> [], receiver key/button release, still-blocked injector
and an unexpired lease are observed before any explicit cleanup release.
After unblocking, the cancelled injector receives InputInterrupted and sends no
new input. Own guardian/HTTP service/endpoint/window/task exit and exact pointer/
foreground restoration pass. The session is explicitly registered for this
component; SessionRuntime.execute, full GestureInput and Blender admission are
NOT_RUN. First fixture lease60 violated the unchanged max30 guard; a second
fixture misclassified the expected InputInterrupted after a successful abort.
Both FAIL attempts remain retained. See [service abort evidence](validation/2026-10-13/windows-service-abort.json).

**OBSERVED / installed Windows suspended-worker deadline:** installed 0.1.37
holds native Shift/middle input in an owned non-text receiver with its IMC
disabled and absence read back. The worker reports its actual PID separately
from the venv launcher; documented DebugActiveProcess/WaitForDebugEvent bind the
owned process and leave its attach breakpoint pending, suspending all worker
threads. Its heartbeat stays unchanged while the distinct guardian family
remains alive. At the six-second lease deadline, native held [4,16,160] -> []
and receiver button/key releases are observed before worker EOF, debugger resume
or any parent release. After the intentional breakpoint is continued and the
debugger detached, the real worker watchdog cancels and further input raises
InputInterrupted. Worker/guardian exit, no held input, exact pointer/foreground
restoration, owned window closure and scheduled-task removal pass.

This is partial additional evidence for original INPUT-04, not full
SessionRuntime.execute, service-driven operation admission, full GestureInput,
Blender semantics or model/harness completion. It adds no latency/p95, goodput or
coverage claim and changes no acceptance status or numeric gate. Private paths,
process/window identifiers and raw traces are omitted from the
[suspension receipt](validation/2026-10-13/windows-suspended-input.json); original
private artifact hashes and the executed script digest are retained there and
the public receipt is digest-indexed in the validation summary.

**OBSERVED / diagnostic separation:** existing FINAL12 menu packets preserve the
actual before-image pixels and independent ground truth. File/Edit/absent scores
separate, but File goal probability 0.7639-0.7694 and condition 0.8112-0.8157 fail
the unchanged 0.9 completion gate. The ASSESS action roster is intentionally
empty; these runs do not demonstrate action-candidate flattening. The 40-object
context contains Open Recent, Save Copy and External Data. Five repeats per case
cover only three unique screens, not general calibration or coverage.

The preserved Windows 0.1.36 service steps were collected without rerunning its
model task. Both actual clicks have NONUNIFORM distributions and retain all three
proposed targets. This is proposal retention, not correct-target coverage. The
last goal/condition probabilities remain 0.8952/0.9504 with independent stage 2
and Task complete. Original object/packet contents were not archived in that
attempt, so candidate coverage cannot be reconstructed. No confidence threshold,
acceptance status or whole-task performance gate is promoted by this diagnosis.

## Actual installed Windows Codex GUI on 2026-10-13

**OBSERVED / harness invocation PASS, task FAIL:** actual native Codex app-server
uses installed0.1.37, discovers all three managed guides and the six real MCP
schemas, reads the complete core guide, then calls capabilities, one bounded
computer_run and its own fresh computer_observe. The configured model and
resolved on-request/readOnly policy are preserved. Only exact preauthorized
owned-GUI run/observe requests receive one-off native approval; unknown requests
remain refused. No global configuration or installed byte changes.

The receiver observes one actual Continueclick and then visibleConfirm. The
second action choice is.9378 with a NONUNIFORM three-candidate vector, but its
ACT-mode probability.6967 fails the unchanged.9 guard. FinalTaskcomplete is
absent, so task verification is FAIL. Both correct semantic targets occur in
the actual rosters. The first-step image is bit-identical to a later independent
native calibration; its top candidate center lies inside the measured physical
Continuebutton[88,385,823,595]. This binds one retained opportunity, not overall
coverage. Confirm spatial coverage and full reaction metrics are not established.

All five native attempts are retained, including startup capability-isolation
failures, missing controller handling of native approval, a screen-change refusal
and failed cleanup in one attempt. Final invocation has complete cleanup and no
current authentication error. The earlier installed0.1.36 final-completion
confidence failure remains separately recorded. Native0.1.38 GUI rerun follows
immutable installation. See [actual Codex GUI evidence](validation/2026-10-13/windows-codex-gui-0137.json).

## Windows capture DPI correction on 2026-10-13

**OBSERVED / real failure before correction:** installed0.1.37 DesktopCapture
changed an already-open owned Tk window from2560x1600 to1463x914 and moved its
button from[88,385,823,595] to[50,220,470,340]. Its image still had2560x1600 pixels.
MSS calls a process-wide DPI setter after the window exists; restoring the
thread DPI context cannot reverse that mutation. The native regression fails
before delivering input and restores the owned window, foreground and pointer.

**OBSERVED / source correction:** Windows now captures the existing primary
monitor with native GDI inside the scoped physical coordinate context, without
process DPI setters. The same native regression preserves geometry and passes
Unicode/selection/click/scroll, cancellation, wrong-foreground refusal and exact
cleanup. Four actual Windows GDI resource/error regressions pass without skips
in InteractiveSession1. Earlier Session0 preflight access-denied errors and a
throwaway source-loader syntax failure are retained, not hidden. Both tested
cleanup revisions pass native resource counts; no leak reproduction is claimed.
The full active Linux suite reports1418PASS/46SKIP/41warnings, including four
Windows-only skips; native Windows results are recorded separately.

**MEASURED / capture component only:** ten alternating batches,100captures per
variant after five warmups, in separate processes against the same unchanged
owned2560x1600 GUI produce identical RGB pixels in all200captures. Capture p95
is53.2624ms for immutable installed0.1.37 and42.4806ms for the source correction.
Hashing and IPC are outside the timer. Power/thermal state was not recorded.
This is not state-change-to-correct-input latency, model accuracy, goodput or
eligibility coverage. Original PERF-01/02/03 remain NOT_RUN. Immutable0.1.38
build/install and the native Codex GUI run are recorded below. See the
[capture DPI receipt](validation/2026-10-13/windows-capture-dpi.json) and
[decision](decisions/0010-preserve-windows-capture-dpi.md).

## Installed Windows 0.1.37 CI and observer verification on 2026-10-13

**OBSERVED / CI archives and installed component:** CI source commit `3cb3dc59` produced 15/15 passing platform/Python archives, each containing the exact 65-file source/guide payload. Assembly succeeded and deploy was skipped. The existing Windows installation updated from 0.1.36 to 0.1.37; repeat returned CURRENT, with unrelated configuration and prior runtime files preserved. The installed public-RNA collector fed partial state through the provider and compiler; six operation families remained BLOCKED with `input_count=0`. Installed native observer transport tests reported 8 tests and OK. This is bounded installation/component evidence, not public deployment or whole-task E2E. Original requirement statuses and numeric gates are unchanged. See the [installed Windows CI receipt](validation/2026-10-13/windows-installed-ci-0137.json), digest-indexed in the validation summary.

## Installed Windows 0.1.38 CI, native input, and Codex GUI on 2026-10-13

**OBSERVED / CI and installed update:** CI commit `cdcf3840` produced 15/15 passing platform/Python archives with the exact 66-file payload; assembly succeeded and deploy was skipped. The existing installation updated from 0.1.37 to 0.1.38, repeat returned CURRENT, managed Codex command refresh passed, and unrelated configuration/prior runtime files were preserved. Installed native capture/input regression and 8 transport tests passed.

**OBSERVED / actual installed Codex GUI:** native discovery and guide/schema loading passed. The model clicked Continue once; independent readback observed Confirm in the actual physical target box `[88, 385, 823, 595]`. Both retained opportunities included the correct target, and its center was inside the target box. The runtime stopped after one action because ACT mode confidence was 0.7016 against the unchanged 0.9 gate; action selection confidence was 0.9372. The task remains FAIL, with no repeated input. Cleanup passed. This does not establish overall target coverage, fast eligibility, performance, or public deployment. Browser/editor E2E-02 and abort smoke remain NOT_RUN. Installed Blender evidence has two retained foreground-cleanup failures followed by a close-first cleanup PASS; all six operation guards remain BLOCKED with zero input, so this does not demonstrate operation success. The [installed Windows CI and Codex GUI receipt](validation/2026-10-13/windows-installed-ci-0138.json) is digest-indexed in the validation summary; original 44 requirement statuses and numeric gates are unchanged.

## Installed Windows 0.1.39 CI, Codex GUI failure, and IME bypass on 2026-10-13

**OBSERVED / CI and installed update:** immutable commit `dd253df8` produced 15/15 passing platform/Python archives. Each archive contains the exact 68-file Git payload; all 15 CI installation checks and assembly passed. Deployment was skipped. The existing Windows installation updated from 0.1.38 to 0.1.39, repeat returned CURRENT, and all 68 installed payload files matched. Managed Codex command refresh and preservation of unrelated configuration and prior runtime files passed. The self-test establishes control flow, not model quality or desktop speed.

**OBSERVED / native Codex invocation PASS, task FAIL:** native discovery, real schema discovery, and the complete core-guide load passed. The configured runtime returned NEEDS_REPLAN after one round with zero actions because the screen changed during the decision. Owned-fixture raster hashes were identical, but native foreground identity and bounds changed. The own-session fresh-observe parameters matched the approval rule; the current foreground did not match the preauthorized owned window, so the subsequent native request required interaction. This is not an authentication failure. Who changed foreground is NOT_PROVEN. Cleanup removed the endpoint and subscription, exited the app server and owned GUI, restored the pointer, released input, and preserved configuration bytes; foreground restoration failed and remains recorded as FAIL.

**OBSERVED / installed active-IME guard PASS, legacy bypass UNSAFE:** the bound RichEdit UIA provider and State Compiler observed valid active composition with positive native preedit bytes. Canonical InputIR literal insertion refused while preserving exact preedit and editor text. Separately, direct legacy typing reported success, committed the active composition, and appended its literal payload. This is an observed installed 0.1.39 safety failure, not an IME separation pass for every input route. Owned IMC/layout restoration, worker/guardian exit, input release, and window/foreground cleanup passed. The inherited initial-literal UTF16 count is not a measured total input count.

The installed 0.1.39 failure remains retained while the source 0.1.40 correction is verified separately below. The [sanitized installed 0.1.39 receipt](validation/2026-10-13/windows-installed-ci-0139.json) is digest-indexed in the validation summary. Original 44 requirement statuses and numeric gates remain unchanged; no whole-workload accuracy, performance, all-platform GUI, or public-release claim is made.

## Source-built Windows compiled keyboard correction, 0.1.40, 2026-10-13

**OBSERVED / guarded generic route:** the source correction routes generic Windows keyboard input through the canonical InputIR executor with compiled state and a live guard. Literal insertion requires bound focused-control identity and physical geometry, explicit writable/non-password/enabled evidence, and known idle IME. Direct legacy Windows keyboard dispatch refuses. Owned input releases remain independent of target state. This is native source-wheel component evidence, not installed 0.1.40 or a model/harness task.

**OBSERVED / retained writability failure and correction:** the first complete source wheel left editability UNKNOWN because inherited TextEdit DocumentRange returned `0x80040201`; no input was sent. A separate cold/warm read-only diagnostic obtained registered TextPattern `10014`, its DocumentRange, and strict Boolean IsReadOnly false. The corrected canonical observer uses that explicit TextPattern for writability and retains TextEdit for composition. Unsupported, mixed, failed, or contradictory proof remains UNKNOWN; no Value-pattern fallback or guard relaxation was adopted.

**OBSERVED / retained prefix failure and fixture diagnosis:** the corrected source wheel first inserted only four UTF16 units, then refused at the unchanged three-second input deadline after eight native sends. All four active-IME refusal routes passed in that attempt. A read-only A/B/B/A diagnostic compared manual `ui.update` polling with canonical Tk mainloop on the same wheel: all four observations stayed valid, used 34 native COM calls each, and sent no input. Summed native QPC durations were 260.7523, 3.8924, 4.9454, and 245.8045 ms; complete compiled-state durations were 390.5544, 38.0232, 60.3020, and 282.2283 ms. These four observations diagnose fixture pumping, not product speedup or a reaction-performance gate. The earlier quantized monotonic profile is retained for call-path inspection and excluded from comparative timing conclusions.

**OBSERVED / earlier canonical mainloop component PASS:** the same corrected wheel completed exact literal readback in 0.789056 seconds, with six UTF16 units and twelve forwarded send-method calls. The default input deadline and all numeric gates remained unchanged. Observed-context InputIR, direct legacy dispatch, generic runtime typing, and context-omitted InputIR each refused during positive two-byte composition, with zero forwarded calls and byte-exact preedit/editor preservation. Owned IMC and thread layout restoration, UIA worker/guardian exit, foreground restoration, window closure, and native input release passed. Its promoted-script rerun passed with 22 valid UIA samples; both precede the final submit-accounting candidate.

**OBSERVED / final source candidate and promoted script PASS:** the final complete source wheel, digest beginning `c4ad3bc5`, ran the promoted native script whose digest begins `1a748703`. Exact literal readback took 0.8401943 seconds for six UTF16 units and twelve forwarded send-method calls. All 38 UIA samples were valid. Four active-IME routes refused with zero forwarded calls while preserving the two-byte preedit and exact editor text. Native Ctrl+A returned EM_GETSEL `[0,7]`; EM_GETSELTEXT matched the exact six-unit literal, with RichEdit's terminal paragraph included in the range. Backspace emptied the native editor. Enter produced one non-repeated owned WM_KEYDOWN callback, acknowledged delivery, moved native focus to the second owned RichEdit, and released the key. This verifies input delivery and a focus transition, not goal completion. IMC/thread-layout readback, subclass removal, worker/guardian exit, native input release, window closure, foreground restoration, and runner cleanup passed.

Two earlier final-candidate fixture failures remain retained: the selection validator expected an end index of six instead of the native seven; another attempt captured before the new control finished painting and correctly refused Enter with zero forwarded calls and zero callbacks. The final fixture verifies selected literal text and settles both controls before capture. The strict pre-input guard remains unchanged. After acknowledged Enter, cleanup/accounting checks the same top-level native window, PID/TID, and physical bounds while allowing the owned control focus transition. An acknowledged but unverified delivery consumes input budget, records DELIVERED_UNVERIFIED, and returns NEEDS_REPLAN; it does not become an undelivered failure or goal completion.

**OBSERVED / owned browser component PASS:** the preceding source wheel completed exact Unicode DOM readback in an owned Chrome app window with a unique disposable profile and nonce-bound local HTML beacon. Literal execution took 1.0593251 seconds with twelve forwarded send-method calls; all 19 UIA samples were valid and owned browser/server/input/foreground cleanup passed. The fixture explicitly used `--force-renderer-accessibility`; this does not establish default Chrome accessibility behavior or a model/harness task. All send counts here instrument unchanged forwarding through WindowsInput._send, not OS receiver events, global input monitoring, or OS input latency. The [sanitized compiled-keyboard receipt](validation/2026-10-13/windows-compiled-keyboard.json) retains the failures and binds each source component separately.

**OBSERVED / source checks:** final source regression passed 1531 tests, skipped 46, and reported 41 warnings in 70.24 seconds. The earlier 1523-test run remains recorded separately with its 129-file Ruff check and generated-contract validation of 198 CLI examples and 12 tool examples. These source and component checks do not establish installed 0.1.40, model-task accuracy, successful Blender operations, 100ms reaction performance, or public deployment. The receipt is digest-indexed with partial original requirement links; original statuses and release gates remain unchanged.

**OBSERVED / final source pointer and recovery components:** the migrated native
fixture verifies left/right/middle down/up, three bounded modifier/button
gestures, independent cancellation while the injector remains blocked and
guardian recovery after its owned worker is terminated. Native held input
changes from `[4,16,160]` to `[]` without a parent release. A retained crash
subcase first failed because Windows refused replacement of a proof file while
the parent read it. Immutable per-nonce request/reply files correct that fixture
race without changing its 500ms proof deadline or native guards. The corrected
run and capture/pointer/legacy-keyboard-refusal smoke pass with exact cleanup.
The Tk smoke now verifies keyboard refusal only; canonical Unicode/selection/
deletion/submit delivery is covered by the separate native RichEdit fixture.
These remain source components, not installed .40 or Blender/model E2E.

## Source-built Windows state and input verification, 0.1.39, 2026-10-13

**OBSERVED / source-built runtime and focused TextEdit:** a complete 0.1.39 wheel was built, but this does not establish installation or release. The source UIA provider-to-State-Compiler path produced cold and warm PARTIAL samples with valid `text_focus=true` and `ime_composing=false` for the bound focused TextEdit. Exact literal readback passed in an owned editable fixture whose explicit creation contract supplies editability; this is not a generic editability observer. Six other application facts remain UNKNOWN and `menu_assess` remains BLOCKED with `input_count=0`. The initial fixture failed because its UI-owning thread blocked COM pumping; moving the fixture caller to a background thread while the UI pumped COM resolved that setup failure without changing the 500ms query timeout. The UIA worker exited cleanly.

**OBSERVED / native failsafe and watchdog geometry:** installed 0.1.38 failsafe probing changed the existing window bounds from `[210,210,1638,1066]` to `[120,120,936,609]` before input; input count was zero. The same-path source correction preserved the original bounds, which is source-only evidence, not an installed pass. A separate watchdog measurement found default-thread bounds `[120,120,936,609]` versus physical bounds `[210,210,1638,1066]`. The 0.1.39 source now reads intrinsic physical bounds on any thread; the failing unit passes. Console hypotheses were rejected without changing product console flags. These checks make no 100ms performance claim.

**OBSERVED / source CLI abort and installed .38 regressions:** the actual 0.1.39 source-wheel CLI/HTTP abort cancelled a blocked injector before the deadline, observed no held inputs or reacquisition, and passed cleanup; the cancelled injector refused later input. Two earlier failed attempts remain digest-bound in the receipt. Installed 0.1.38 GDI resource tests passed 4/4 with zero skips and no source overlay. Four earlier suspended-worker attempts remain FAIL; the final installed .38 run passes after correcting validator point geometry only, with original console flags retained. The initial Chrome UIA probe was UNAVAILABLE with keyboard focus unverified and IME UNKNOWN. After acknowledged document-focus setup, a separate read-only native UIA query returned VALID for focused TextEdit and IME false with the same process, ancestor and foreground bounds; cleanup passed. Neither probe is browser/model task E2E.

**OBSERVED / source-candidate GUI and suspension:** the 0.1.39 candidate GUI component passed Unicode, selection, click, scroll, cancellation, control-character and wrong-foreground checks; both capture and input preserved owned-window geometry, and cleanup passed. The suspension test stopped every worker thread while the separate guardian stayed alive and released owned input at its deadline. The resumed worker observed cancellation and refused later input; cleanup passed. These are source-candidate component results, not installed .39 runs.

**OBSERVED / source checks:** the 0.1.39 regression suite passed 1440 tests, skipped 46, and reported 41 warnings in 82.09 seconds; Ruff and generated-contract checks passed. The [state/input/DPI receipt](validation/2026-10-13/windows-state-input-dpi.json) records source, installed and unavailable evidence separately. Installed .39 discovery, GUI and suspended-worker runs remain NOT_RUN. The original 44 requirement statuses and numeric gates are unchanged.

## Native pointer scope correction on 2026-10-13

The 0.1.39 candidate above was subsequently checked for native pointer scope.
**OBSERVED:** a paired test with two disposable owned windows found that a click
bound to A reached B and returned success. The corrected candidate checks the
physical native recipient before button-down/wheel injection; the same test
then delivered zero events to B. Recovery releases stay independent. Both
attempts and their distinct wheel hashes are retained in the
[pointer recipient receipt](validation/2026-10-13/windows-pointer-recipient.json).
The corrected source wheel also passed the native GUI/input component, and
the subsequent regression suite reported 1446 passed, 46 skipped, 41 warnings
in67.17seconds. This paired case does not establish whole-workload critical
zero, installed .39 E2E, or the original performance gates.

## Windows SSH E2E scope resumed on 2026-10-12

The user explicitly requested SSH Windows E2E and permitted updating the existing
installation. Earlier software-only/other-session boundaries below are historical.
Separate Blender host observer/build development and model production remain
excluded. Full results, earlier failures and private artifact digests are in
[the Windows receipt](validation/2026-10-11/windows-ssh-current-e2e.json).

**OBSERVED / current immutable installation:** the canonical installer activated
CI version 0.1.36 from source b9af0e9 and bound all 64 packaged source/guide files
across Git, CI wheel and installed runtime. Managed Codex refresh selected the
new physical executable; repeat installation returned CURRENT/UNCHANGED.
Unrelated configuration bytes, previous runtime files and model cache were
preserved. Only manifest download URLs were projected to the owned loopback;
archive bytes, hashes, other metadata and every installer guard stayed intact.
The first controller's unprojected production URL was refused with
`artifact origin differs from configured release host`; that failure is retained.
The older 0.1.35 local candidate has a different archive checksum from its CI
artifact. A distinct 0.1.36 release preserves same-version checksum immutability.

**OBSERVED / CI:** [run 38255521947](https://github.com/snowman0919/clef-use/actions/runs/38255521947)
completed all 15 platform/Python build and actual installation-check jobs plus
assembly. All 15 downloaded archive digests and each archive's 64 packaged
source/guide files match. Superseded/cancelled runs, including the duplicate
accepted after an ambiguous HTTP 502 dispatch, remain recorded. Tag publication
and production deployment were skipped by the existing feature-branch policy;
this is an immutable CI artifact installation, not a public release.

**OBSERVED / actual MCP and harness:** native installed read-only stdio MCP
advertises the exact live two-tool schema, accurate effects and all three matching
guide-resource hashes. Actual Codex 0.151.0 fresh model sessions pass explicit
(60.389 seconds) and natural (126.817 seconds) discovery/load/invoke. Natural
triggering reads all three complete guides; negative triggering (24.168 seconds)
reads none and attempts no calls. Compatibility is MATCH. Approval policies were
not changed. These read-only checks leave TASK_VERIFIED=NOT_RUN; they do not prove
a Codex-driven GUI operation. Hermes/OMP Windows sessions are NOT_RUN because
their executables are absent. These are individual wall times, not latency gates.

**OBSERVED / actual installed CLI/model GUI:** 0.1.36 runtime status is
NEEDS_REPLAN, controller status FAIL, with 2 actions and
3 decisions in 266.374 seconds. Independent Tk readback recorded
stage 2 and visible result `Task complete`. Endpoint removal,
input release, pointer restoration, exact original foreground restoration,
owned-window closure and scheduled-task removal are recorded individually in the
receipt. No action bridge was used. Current goal probability 0.8952 is below the
unchanged 0.9 requirement, although the visible-condition probability is 0.9504;
the exact blocker is COMPLETION_UNVERIFIED. The current whole task is FAIL, and
was not repeated to obtain PASS. Earlier 0.1.30 COMPLETED (332.868 seconds),
0.1.32 NEEDS_REPLAN (259.747 seconds) and 0.1.35 COMPLETED (286.265 seconds) remain
retained. The earlier 0.1.32 NEEDS_REPLAN run made both correct clicks but goal probability
0.8992 did not satisfy 0.9; that guard is unchanged. These individual bounded runs
are not paired accuracy or a speedup estimate.

**OBSERVED / native fixture and cleanup:** original 0.1.34/0.1.35 fixed-sleep
smokes failed after Ctrl+A/Backspace. The live receiver UI loop now verifies full
selection [0,17] before Backspace, exact Unicode/empty text and independent
click/wheel effects. Current 0.1.36 native input and cleanup passed in
8.915 seconds, including clipboard preservation, cancellation,
control-character/stale-focus refusal and empty held-input readback. The first
0.1.36 smoke passed inputs but failed strict foreground restoration after target
WM_NULL. A focus-only probe observed that consuming the owned UI queue resolved
a mismatch; a later one-pump smoke still failed. Both failures are retained.
Final shared cleanup sends one activation request, consumes the owned UI queue
within a bounded completion observation, checks the exact original HWND and
refuses intervening ownership. The final native PASS restored immediately;
that single run does not establish delayed-completion reliability. The model
fixture now applies the same ownership/foreground check before destroying its
window and records independent cleanup errors. A controller runpy import-path
failure is also retained separately; it sent no input. No activation or input is
replayed within these fixtures. The one-second fixture observation bounds and
raw Windows timing ticks do not establish the 100ms reaction release gate.

**OBSERVED / installed Windows typed input and independent recovery:** the new
[single native fixture](../scripts/windows_typed_input_smoke.py) uses installed
0.1.36 DesktopAction.execute_input without a model, action bridge or mocked OS.
Actual receiver events confirm left/right/middle down/up, Shift+left and
Shift+middle bounded drags, and a middle drag without Shift. Final assertions
check held-button/Shift state during motion, coordinates within the declared
surface and the actual endpoint. The initial run (11.567 seconds) is retained;
the final stricter fixture passed in 8.867 seconds. These are functional wall
times, not a speed comparison. Receiver IMC is disabled only on the disposable
non-text canvas and its absence is read back; no general IME observation is claimed.

The same installed executor holds Shift and middle. After cancellation, both
native holds disappear while the worker remains blocked, before any direct
release call. A separate owned worker process then holds both; its guardian is
confirmed live before abrupt worker termination. Both holds disappear and that
guardian exits before the parent calls release. Held-input lists, exact original
pointer/foreground restoration, own guardian/window closure and task removal all
pass. Local and remote final fixture hashes match. This observes executor
watchdog/guardian recovery, not service CLI abort with an admitted Blender gesture
or full-process suspension/deadline recovery in that 0.1.36 slice. The separate
0.1.37 suspension component above supplies bounded native deadline evidence;
admitted Blender gesture execution remains NOT_RUN.
No installed product byte changed. Four-language input guidance and INPUT-03/04
partial Windows notes are updated without changing original criteria or gates.

**OBSERVED / defects and regression:** native Codex overrides preserve other
MCP transports; managed refresh rebinds only unchanged approved entries; complete
shell-escaped guide paths prove load while copied-body suffixes do not. Pure MCP
effects are accurate and failed runs retain private stderr. Earlier 0.1.31
INCOMPATIBLE update, 0.1.32 denied tool call and 0.1.34 CLI exit 1 remain recorded.
The old verifier discarded stderr for the last error, so its cause is
NOT_CAPTURED; no current authentication failure is asserted.
Product b9af0e9: 1418 tests passed, 34 skipped, 41 warnings in 67.20 seconds.
Generated contracts and active src/tests/scripts Ruff/format checks pass
(148 files including the final typed-input validation fixture). A broad read-only formatting
check also found 20 pre-existing unformatted frozen old/ files; none was changed.
Final validation scripts were executed natively; all 64 installed product files
remain exact b9af0e9. Canonical pinned ROCm/NF4 and CPU OmniParser preparation
passed in 809.585 seconds; no model was trained. Doctor exit 2 identifies SSH
Session 0; actual GUI checks use limited InteractiveToken tasks on Session 1/Default.

**NOT_RUN / remaining acceptance:** general Windows Blender popup/input-owner/
IME/effective-keymap/global-idle observation, full same-work paired accuracy,
goodput/coverage and state-change-to-correct-OS-input p95<=100ms are not established
by this bounded task. Six Blender operation guards retain UNKNOWN where evidence
is unavailable. Original 44 conditions and numeric release gates remain unchanged;
no whole-goal completion or public release is claimed.

**OBSERVED / positive-only Blender busy evidence:** the actual public-RNA
collector omitted the owning manager's read-only running-job interface lock.
In a private factory Blender component, native lock false/23 true/false samples
all compiled `loading` as UNKNOWN before the correction. The collector now
retains the strict optional Boolean; the provider compiles only exact true to
`loading=true` after existing native identity, window and freshness checks.
False or unavailable remains UNKNOWN and cannot establish global idle.

The same actual collector/socket/provider/compiler path now preserves all 25
native lock samples: 23 true samples produce VALID APP_TELEMETRY busy evidence
with matching acquisition time/version, and both false samples remain UNKNOWN.
A positive render modal remained after the lock cleared, demonstrating why false
cannot authorize input. Seven other unobserved guards remain UNKNOWN; all six
operation families stay BLOCKED with zero input. The bounded render setup used an
owned factory instance, saved no render/model artifact and left production display
untouched. Owned processes and sockets were removed. An earlier controller
assertion failure remains recorded; its exact failing subexpression was not
recorded, so the suspected modal assertion is an inference, not a product result.

The actual read-only stdio MCP advertises the positive-only busy semantics and
matches its listed tool schemas. Twenty-four permanent collector/compiler cases
produce 11 FAIL / 13 PASS on immutable prior source and pass currently; scoped
checks pass 191. Final integrated source passed **1398 tests / 34 skipped /
41 warnings** in 63.49 seconds. Four changed Python files passed Ruff/format;
generated contracts and four-language guides are updated. See
[positive busy evidence](validation/2026-10-11/blender-positive-busy.json).

**MEASURED / pre-change read-only source baseline:** five warm batches of 100
samples on an owned authenticated 800x600 factory Blender 5.2/software-GL instance
measured capture to provider/socket/collector to State Compiler. Across 500 samples,
total median was 13.025ms, nearest-rank p95 23.573ms and maximum 43.296ms; capture
p95 was 9.049ms, provider 15.418ms, compiler 0.051ms and native collector 3.181ms.
Raw timings, all five batches, separate profiles and the first startup readiness
failure are retained. The later batch was slower; thermal state and competing
workload were not controlled. No optimization or speedup is claimed. This is the
prior source's read-only component baseline, not the actual state-change to correct
OS-input latency or whole-task accuracy/goodput/coverage. See
[baseline evidence](validation/2026-10-11/blender-provider-performance-baseline.json).

General production popup/text/IME/effective-keymap/focused-editor/global-idle
observation remains incomplete. Whole E2E and model tasks belong to other sessions;
new installed-current, release and whole-task performance checks are NOT_RUN in
this slice. No acceptance status or release gate changed.

**OBSERVED / harness invocation classification:** the canonical read-only stdio
MCP server returned `isError=true` for an unknown operation, yet the Codex source
verifier counted the response as INVOKED=PASS and overall PASS. Controlled failed
and incomplete call traces also passed negative-trigger verification.

Five native/model response boundaries now share explicit error classification.
Successful responses alone prove invocation; explicit protocol/transport errors
produce INVOKED=FAIL when no successful invocation exists. Missing or incomplete
results remain NOT_RUN. Three model adapters independently retain call attempts,
so negative checks reject unsuccessful attempts too. Guide provenance, loading,
exit-status rules and runtime guards remain unchanged.

The real MCP response replay now fails correctly, successful response controls
still pass, and failed/incomplete negative attempts fail. These are actual MCP
responses consumed through controlled executable catalogs/traces and canonical
source parsers, not real harness discovery or model sessions. Seventy-five new
permanent cases produce 50 FAIL / 25 PASS on immutable prior source; current
scoped checks pass 196. Integrated source passed **1374 tests / 34 skipped /
41 warnings** in 63.77 seconds. Ruff/format and generated contracts passed;
four-language guides describe the result distinctions.

Real harness/model sessions, installed-current, whole E2E, full-task performance
and release remain NOT_RUN in this slice under the user's scope. Production
Blender popup/text/IME/effective keymap/busy/focused-editor observation remains
incomplete; UNKNOWN required facts still block guarded operations. No acceptance
or release gate changed. See
[invocation classification evidence](validation/2026-10-11/harness-invocation-classification.json).

**OBSERVED / integration ownership through discovery:** actual integration
reproduced user data loss: a guide or MCP entry edited during the compatible
executable's capability probe was overwritten by stale planned content, and the
operation returned INSTALLED. The transaction had adopted the later edit as its
before baseline after ownership validation.

Both integrate and remove now retain approved metadata/config bytes and targeted
guide inventories through discovery. Snapshot drift, including added/deleted files,
stops with CONFLICT before journaling; preview and otherwise unchanged plans also
revalidate. Journal baselines use approved bytes. Existing post-journal activation
exceptions and recovery conflicts remain unchanged; concurrent external editors
do not participate in an atomic multi-file transaction.

The same actual executable fixture now returns CONFLICT, preserves both edits
and creates no journal. Thirty-six permanent cases fail on immutable prior source
and pass currently, including benign config comments/model-field edits, metadata,
new/removed targets, remove and direct transaction-entry boundaries. Scoped
integration checks passed 121. Final integrated source passed **1299 tests /
34 skipped / 41 warnings** in 64.43 seconds. Two Python files passed Ruff/format;
generated contracts passed and four-language guides are updated.

These are isolated software components with an executable capability fixture,
not installed-product/harness E2E. New installed-current, native, model, full-task
performance and release checks remain NOT_RUN. No acceptance status or release
gate changed. See
[integration ownership evidence](validation/2026-10-11/integration-validation-ownership.json).

**OBSERVED / modifier gesture context:** the actual typed input consumer
previously admitted modifier strokes with explicit active text, composing IME or
UNKNOWN context, while chords refused the same contexts. Modifier gestures now
use the same shortcut admission before any movement or press, independently of
an optional post-input transition guard. Existing exact text controls remain
key/chord-only. Unmodified pointer gestures, calls without context and owned-up
recovery retain their existing behavior.

Seven permanent unsafe-context cases fail against immutable prior source and
pass currently, with zero movement, key/button presses and strokes. Three control
cases retain actual stateful-device strokes and release. The separate canonical
consumer component confirms active/UNKNOWN direct gestures stop and idle gestures
run. Existing registered viewport guards already blocked active contexts before
the correction; no MCP/registered-operation bypass is claimed.

Final integrated source passed **1263 tests / 34 skipped / 41 warnings** in
58.56 seconds; scoped input/operation checks passed 88. Two Python files passed
Ruff/format and generated contracts passed. Four-language guides are updated.
This is deterministic source-component evidence, not native input or real IME
observation. Production context discovery remains incomplete. New installed-current,
harness, whole E2E/model, full-task performance and release checks remain NOT_RUN;
no acceptance status or release gate changed. See
[gesture context evidence](validation/2026-10-11/modifier-gesture-context.json).

**OBSERVED / candidate identity and primitive budgeting:** normalization now
preserves exact validated geometry and differing action, confidence or source
evidence. Equivalent numeric spellings and signed zero deduplicate; object IDs
remain observation-scoped. Canonical source consumers reproduced two real dispatch
points collapsing into one, passive-first evidence erasing an input capability,
and equivalent numeric observations consuming duplicate slots. Final source
preserves both points and evidence while deduplicating equivalent records.

Explicit structured primitives now filter eligible proposals before counting
or reserving literal-text slots. With four input targets and twelve supplied
literals, old explicit click/double-click/scroll rosters were empty; corrected
rosters retain all four targets (4/4/8 proposals). No-intent literal alternatives
and overflow refusal remain enforced. An existing hybrid test pinned the old
irrelevant-double-click budget loss; its replacement checks all twelve requested
click targets and zero input and fails on immutable prior source.

An owned authenticated native Canvas component observed adjacent one-pixel click
effects change from [1,0] to [1,1] through actual capture/normalization/candidate/
DesktopAction consumers. **The original AFTER run remains FAIL / AssertionError**:
its private oracle expected Y=50, while both actual in-bounds points had Y=49.
Offline semantic assessment of the retained effects is separate from that failed
run. Native AFTER used the earlier normalizer candidate; the final confidence
signed-zero correction has source/regression proof only, native-final NOT_RUN.
Targets came from controlled Canvas coordinates, not model inference. Owned
children/sockets and held input were cleared; production was preserved.

Final integrated regression passed **1253 tests / 34 skipped / 41 warnings** in
58.40 seconds; scoped checks passed 151. Five Python files passed Ruff/format and
generated contracts passed. Four-language guides are updated. Earlier RED results,
the initial integrated failure and native oracle failure remain recorded. No
threshold, capability, unknown-state guard, acceptance status or release gate was
weakened. Historical model-quality failures and incomplete production context
observation are not resolved by these corrections. Whole E2E/models belong to
other sessions; new installed-current, full-task performance and release checks
remain NOT_RUN here. See
[candidate evidence](validation/2026-10-11/candidate-identity-and-primitive-budget.json).

**OBSERVED / Windows input ownership:** controlled Win32 boundary execution
reproduced missed user intervention: owned extended cursor keys masked distinct
numeric-keypad holds, and left modifiers masked right modifiers. The canonical
checker now retains scan plus extended flag and modifier side, separates virtual
fallback ownership, and refuses missing held-key layout observation. Generic+left
modifier reports remain one acknowledged fallback hold; opposite-side holds block.
The first correction's fallback false refusal was independently reproduced and
fixed, with three permanent cases retained. The final 20 new identity regressions
produce 17 failures / 3 passes against immutable prior source and pass currently.

The actual InputExecutor acquired bounded Left/Ctrl holds against controlled
Win32 APIs. Prior source sent G in all four stable/intervention cases; current
source sends G only in the two stable cases and sends zero G events with a distinct
human hold. Owned records clear in every case. The actual guardian loop separately
reproduced stale key/Unicode releases after successful deadline recovery and later
EOF. Successful ACKs are now retired; existing EOF recovery retains only failed
pending entries. Four guardian regressions fail before and pass after correction,
preserving the subsequent owner's holds and recovering known refused entries.

These are source components on Linux with controlled native API boundaries,
**not native Windows input**. Same-virtual-key physical aliases remain outside
GetAsyncKeyState's distinction; a new parent ownership update is a separate
protocol event. Integrated regression passed **1240 tests / 34 skipped /
41 warnings** in 58.35 seconds; scoped input checks passed 90. Four Python files
passed Ruff/format and generated contracts passed. Four-language guides are
updated. Native Windows for this patch, new installed-current checks, whole E2E,
models, full-task performance and release remain NOT_RUN; no acceptance status
or release gate changed. See
[Windows ownership evidence](validation/2026-10-11/windows-input-ownership.json).

**OBSERVED / fixture numeric unit normalization:** the existing API-assisted
Blender state producer now returns supported numeric translation/readback in
METERS/CENTIMETERS using the actual scene scale and retains NONE as raw. Native
Euler values remain radians when declaring RADIANS and convert only for DEGREES.
Preview uses the same normalized values; exact properties and dimensionless scale
retain raw values. Unsupported distance-unit names cannot authorize translation;
their raw coordinates remain unchanged-channel evidence for rotation/scale.

The actual standalone STARTUP producer ran in authenticated private factory
Blender with fixed API-owned scene settings and token-authenticated local readback.
Before correction, four of seven settings disagreed with independent native RNA
expectations: METERS at scales 0.01/100, CENTIMETERS and RADIANS. The corrected
producer matched all seven; preview and raw property preservation passed each.
Both runs retained identical source hashes from start to end and cleaned up their
four owned children and private X sockets. No whole fixture task, native input,
OperationRunner, harness, model or production scene was executed.

Eight permanent behavioral regressions exercise the real embedded reader with
controlled data. Immutable prior-source execution reproduced four failures;
current source passes all eight. Final integrated source passed **1216 tests /
34 skipped / 41 warnings** in 62.83 seconds. Scoped Ruff/format, inner producer
compilation and generated contracts pass. The fixture normalization finding in
the earlier numeric-unit receipt is resolved; that historical evidence is retained.
Installed-current E2E, actual numeric modal input, full-task performance and release
remain NOT_RUN in this slice. See
[fixture unit evidence](validation/2026-10-11/fixture-numeric-units.json).

**OBSERVED / numeric translation scene conversion:** translation now validates
and anchors complete `scene_units`, including unit NONE, through runner refresh,
native input and final readback. Owned translation cancellation retains the same
conversion guard and checks it after closure; observed closure clears obsolete
ownership even if final verification fails. Rotation and scale remain independent
of scene length settings. Registry v6 advertises conditional translation and
translation-modal requirements through actual source CLI and stdio MCP discovery;
request schemas and default BLOCKED availability are unchanged.

Canonical pure execution reproduced success across a scale change from 1 to 100:
the same METERS/readback 2 accompanied raw movement 0.02 instead of 2. Current
source blocks before input while stable conversion still succeeds. This is an
explicit normalized-distance consumer model, not native Blender typing. Actual
factory Blender observations independently confirmed unchanged METERS/zero
baseline at scales 1 and 100. Public parser output plus division gives raw 2 and
0.02; it is parser-only evidence, not numeric UI input.

An authenticated owned Tk component loaded seven immutable baseline modules and
observed stale-context G/Escape delivery. The corrected native runtime guard
delivers stable G and refuses changed-context G/Escape with zero key events;
explicit fixture state is API_ASSISTED, not automatic Blender context discovery.
Native AFTER retains its earlier candidate operations hash: it exercises direct
runtime input, not the subsequent runner cancellation-final-readback correction.
That additional correction was reproduced by two source failures and verified
in the final regression suite. All six owned child processes exited, their X
sockets disappeared and input ownership was empty; production was not accessed.

Final integrated source passed **1208 tests / 34 skipped / 41 warnings** in 59.98
seconds; scoped checks passed 174. Five changed Python files passed Ruff/format,
and generated contracts passed. Four-language guides and ADR0008 are updated.
Native final runner cancellation, Blender numeric text/commit, installed-current
E2E, models, full-task performance and release remain NOT_RUN here. The existing
API-assisted operations fixture had a separately identified unit-normalization
defect (always-degree/raw-location values with current-unit declarations); it was
neither changed nor run in that guard slice; the later producer correction above
resolves it. No acceptance or release gate was promoted.
See [numeric unit evidence](validation/2026-10-11/numeric-scene-units.json).

**OBSERVED / configured Blender tool:** the canonical read-only collector and
provider now supply scoped `active_tool` evidence. Native `Context.mode` is used
only when context window, workspace and view layer match the owning window;
`Object.mode` is not translated. Exactly one configured VIEW_3D reference and
complete process-bound area IDs are required. Missing, malformed, ambiguous or
overflowing evidence stays UNKNOWN; focused editor and effective dispatch remain
UNKNOWN even when this configuration fact is VALID. No product context override,
tool creation, refresh or operator was added.

An owned authenticated factory Blender 5.2 component exercised the actual UI
collector, Unix socket/peer credentials, XRes foreground/client binding, capture,
provider and State Compiler. OBJECT and EDIT_MESH facts matched independent RNA
tool references and identities, including native Object.mode EDIT versus context
mode EDIT_MESH. Nine other guard facts remained UNKNOWN; each of the six operation
families returned BLOCKED in both modes with no input executor call. One private
focus setup and one fixed EDIT fixture setup were recorded separately. Source
hashes remained unchanged; both owned children exited and their sockets were
removed. Production process existence was checked without reading its scene.

The integrated source passed **1177 tests / 34 skipped / 41 warnings** in 58.59
seconds; scoped checks passed 167 tests. Actual source CLI and stdio MCP discovery
advertise the scoped fact with identical schemas, registry v5 and unchanged
default BLOCKED availability. Five changed Python files passed Ruff/format and
generated-contract checks passed. Other native modes, add-on tools, multiwindow,
installed-current/harness E2E, models, full-task performance and release remain
NOT_RUN in this slice. No acceptance status or release gate was promoted. See
[tool observation evidence](validation/2026-10-11/blender-active-tool.json) and
[scope decision](decisions/0007-scope-workspace-tool-observations.md).

Date: 2026-10-12. Baseline: `b3f0b23309a7c7ea6a943e0c14e0ae51034552cd`.
Initial evidence snapshot HEAD: `1c52c80877d94116071107c67454457bbd2da46c`.
Latest built, installed and CI-verified implementation: `4932557` on
`codex/reactive-agent-contracts`;
the bounded Blender fixture remains unchanged from `a7a46b5`.
The newer optional Blender observer source passed 907 regression tests and real
component verification; its installation and whole-task E2E are NOT_RUN here.
The subsequent literal-candidate correction passed **911 tests / 34 skipped**;
its component verification uses synthetic observations, without model or OS input.
The newer operation-context guards passed **915 tests / 34 skipped** and a native
owned Tk input-bridge component; this does not implement automatic Blender context discovery.
The newer raw Blender inventory/editor layout and Linux monitor mapping passed
**946 tests / 34 skipped**. An owned Blender 5.2 component observed 164 relevant
bindings (80 wildcard modifier values) and 4 areas / 18 regions. A real native
two-monitor click missed at `(640,300)` before the coordinate correction and hit
the same target at `(320,300)` afterward. Raw bindings and rectangles do not
establish effective dispatch, focused editor or operation readiness. See
[component evidence](validation/2026-10-11/blender-inventory-and-coordinates.json).
This changed source has no new installed/harness E2E or full performance result.
The subsequent numeric readback/dispatch correction requires complete transform
vectors, stable context and baseline before entry, and a stable verified preview
before commit. Scalar property edits verify all observed fields and identities.
Roundtrip float literals avoid the former 15-digit rounding. Owned cancellation
also rechecks transform context at the native boundary; the CLI advertises
operation registry v3. Regression counterexamples reproduced the old false
success, stale dispatch and precision failures before correction.
The integrated candidate, including the separately recorded X11 pointer patch,
passed **982 tests / 34 skipped / 41 warnings**. An owned API-assisted Tk rectangle
component observed `g` and `Enter`, rejected real baseline/group/preview changes
before input, and ended with no owned input. This verifies the input bridge and
readback helpers, not native numeric text parsing or a complete Blender operation.
The exact owned HOME process scan found no matches; 420 unreadable unrelated
process entries were outside that check. See
[numeric component evidence](validation/2026-10-11/transform-readback-and-dispatch.json).

**OBSERVED / X11 pointer mapping:** the exact prior source delivered Button3 for
a logical left click and a negative native wheel delta for an upward scroll under
an owned swapped pointer map. Typed and legacy paths now query the current map
and retain the acknowledged physical code for release. Nine authenticated private
Xvfb cases verified all three logical buttons, fresh remapping, both wheel axes,
modifier gestures, disabled-button refusal, preservation of unrelated held input,
independent abort and executor SIGKILL/guardian EOF recovery. Every case ended
with native pointer mask zero, its server reaped and its socket absent. The scoped
checks passed 49 tests; the integrated source result above includes all nine cases.
Mapping lookup and injection are separate requests; a simultaneous external remap
is outside the atomicity claim. Windows/Darwin native execution is NOT_RUN in this
slice. No production display or model was used. See
[pointer component evidence](validation/2026-10-11/x11-logical-pointer-mapping.json).

**OBSERVED / capture freshness and view effects:** capture-derived geometry,
window and foreground facts now preserve the capture start time through
compilation and later processing. Before correction, an actual owned native
capture aged 1.15 seconds was renewed as VALID by compilation. After correction,
all three facts remained STALE while independently current fixture evidence
retained its own VALID timestamp. Age/future boundaries and slow acquisition have
deterministic regression coverage. FrameReference and public API schemas did not
change. See [capture evidence](validation/2026-10-11/capture-fact-freshness.json).

The Blender provider previously hashed the entire VIEW_3D area, so a layout-only
region identity change could make a viewport operation report SUCCEEDED without
a view effect. It now requires a complete finite, unambiguous non-quad viewport
and fingerprints its effective view matrix and perspective mode. Layout,
projection, pointer IDs, quaternion sign and pending redundant pose values cannot
alone count as the effect. Missing or ambiguous pose remains UNKNOWN.
The actual factory Blender component kept the revision unchanged after a real
sidebar/region layout change with identical pose, and changed it after an actual
view-matrix change. Canonical observer/provider paths ran on an owned authenticated
display; fixture setup used explicit RNA setters, with zero keyboard/pointer input
or model calls. Owned children and sockets were removed; production Blender was
preserved. This is component proof, not a complete orbit/pan task or provider
readiness. The integrated source passed **1014 tests / 34 skipped / 41 warnings**;
seven changed Python files passed Ruff/format and contract generation passed.
See [view-effect evidence](validation/2026-10-11/blender-view-effect-revision.json).

**OBSERVED / selected-object continuity:** changing operations and owned modal
cancellation now require a complete, unique `selection_identities` map and retain
it through dispatch, every refresh/readback and the native input boundary. Same-name
replacement cannot continue input, acquire modal ownership or report success.
Read-only observation of a closed modal still releases obsolete ownership, but
does not attribute unchanged readback to a replacement object. Registry v4
advertises the new required fact; the public request schema digest is unchanged.

The Blender observer publishes process-scoped public `ID.session_uid` identities
and all six location/scale scalar properties. Missing or incoherent identity
remains UNKNOWN. In an authenticated private factory Blender component, the
immutable prior collector omitted IDs and four axis properties. The current
collector/provider retained the ID across a real rename and changed it for a
same-name copy with identical transforms; all six numeric properties matched.
Fixture setup used explicit public RNA setters, with zero keyboard/pointer input
or model calls. Native Tk components separately reproduced old `g`/`Escape`
delivery after same-name replacement, then refused both before OS input while
unchanged-identity input still worked. These exercise the input boundary with
API-assisted state, not a complete Blender operation.

Owned children/sockets were removed and production Blender was preserved. An
exact scan of both Tk fixture HOMEs found zero process matches; 417 unreadable
unrelated entries were outside that check. The integrated source passed
**1062 tests / 34 skipped / 41 warnings** in 54.13 seconds. Ten changed Python
files passed Ruff/format, and generated contract checks passed. Whole-task E2E,
models, installed-current harness E2E and full p95/goodput/coverage are NOT_RUN in
this slice. See [identity evidence](validation/2026-10-11/blender-selection-identity.json).

**OBSERVED / input authority and clipboard preservation:** cancellation and
deadline are checked again after potentially slow state/native queries. Actual
authenticated private X11 Tk components reproduced the old key delivery after
cancellation/deadline during sampling; the corrected path delivered no key and
left the native keyboard released. Windows Unicode now validates the entire
UTF-16 payload before input and rechecks context, geometry, unowned input and
deadline before each unit. The controlled Win32 API fixture previously sent
`abc` after the first unit invalidated the guard; it now sends only `a` and
refuses further input. Native Windows execution of this patch is NOT_RUN.

An actual native armed clipboard provider previously retained the new literal
after cancellation with zero paste attempts. Confirmed pre-trigger cancellation
now releases owned modifiers and restores supported prior contents with a
bounded independent cleanup deadline and native acknowledgement. Authenticated
X11 checks covered cancellation/deadline, distinct and identical concurrent
copies, a stopped provider without ACK, and ordinary armed EOF. Canonical caller
checks observed zero V events and restoration after pre-trigger cancel/arm error;
an actual V event followed by a controlled OS error retained the literal until
native consumption and reported unresolved ownership. No concurrent owner was
reacquired. Owned providers/guardian/server exited and sockets were removed;
the exact owned-HOME scan found zero matches, excluding 419 unreadable unrelated
entries. Production Blender was preserved.

The integrated source passed **1074 tests / 34 skipped / 41 warnings** in 55.63
seconds. Seven changed Python files passed Ruff/format; generated contracts
passed. Four-language guides document these boundaries. Whole-task E2E, models,
installed-current harness E2E and full accuracy/p95/goodput/coverage remain
NOT_RUN in this software slice; no acceptance or release gate was promoted.
See [input evidence](validation/2026-10-11/input-authority-and-clipboard.json).

**OBSERVED / property scene units:** location `PropertyEdit.value` retains the
raw `Object.location` coordinate contract. Fresh validated `scene_units` now
binds scene identity, system, default length unit and scale. Unit-enabled fields
receive explicit meters computed from the observed scale; NONE receives the raw
literal and scale fields remain dimensionless. Location input and final readback
anchor these settings. Missing/malformed settings and conversion overflow or
underflow refuse before input; changed units stop further input or success.
The read-only provider publishes this positive scene evidence without inventing
field focus, modal units or coordinate space. Source CLI and actual stdio MCP
advertise registry v5, conditional field requirements and raw-value semantics;
the request schema digest remains unchanged and default operations stay BLOCKED.

Canonical in-memory runtime components reproduced the old raw 0.02 commit for a
request of 2 in a centimeter field. Current complete evidence commits 2; missing
units sends no input, and a mid-text unit change stops before commit. Independent
actual factory Blender Location X input reproduced `2.0` -> raw
`0.019999999552965164` under METRIC/cm/scale1 and `2.0m` -> raw2. With actual
observed scale `0.009999999776482582`, a separate fixed single-edit driver admitted
only `0.019999999552965164m` and observed raw `[2,0,0]`, preserving the scene/object/
selection/mode/unit anchors. This proves the native field recipe, not native
guarded OperationRunner execution or automatic field discovery.

The earlier native unit matrix executed 12/13 declared cells. One external
dispatch bypassed that test controller's literal admission; its result is excluded
from controller proof and the replaced IMPERIAL/.01 nominal cell remains NOT_RUN.
The separate fixed actual-scale check does not relabel that matrix as passed.
Other observed rows include NONE/scale100 raw2 and explicit meters under METRIC/
IMPERIAL scale1/100. Setup and positive visual field admission remain separate.
Owned children and sockets were removed; HOME and authority scans found zero
matches, excluding 418 unreadable unrelated entries. Production Blender PID was
retained; no production scene/display was accessed.

Final integrated source passed **1120 tests / 34 skipped / 41 warnings** in 55.99
seconds. Nine changed Python files passed Ruff/format; generated contracts passed.
The maintained native fixture now forwards actual scene units and selected-object
identities; only its nested startup was statically compiled, with full fixture E2E
NOT_RUN under the user's scope. Four-language guides and the decision record are
updated. Native Windows/Darwin, installed-current harness E2E, whole-task/model
and full accuracy/p95/goodput/coverage remain NOT_RUN here. No acceptance or release
gate was promoted. See [unit evidence](validation/2026-10-11/property-scene-units.json).

**OBSERVED / viewport input baseline:** the runner and native input guard now
retain the initial view revision until the actual gesture button-down is
acknowledged. A pre-existing independent change cannot verify a no-effect gesture.
Only the acknowledged button switches to the existing phase guard that permits
expected drag changes; selection, keymap, editor geometry and other context checks
remain exact. No key/chord delivery receipt is fabricated for a gesture.

An owned authenticated X11/Tk Canvas component loaded four exact historical Git
modules and reproduced `SUCCEEDED` despite identical pre/post-gesture coordinates.
The frozen corrected source refused that pre-dispatch change with zero input,
performed a genuine Shift+middle drag with an independently read 64-by-48 change,
and stopped a view change during initial positioning before middle-button press.
The latter case moved the pointer to the starting point; it is not zero OS input.
All owned buttons/modifiers were released and children/sockets removed. Fixture
application/editor/keymap/idle facts are explicit API-assisted protocol assertions;
this does not prove automatic Blender context discovery. One oracle-concurrency
failure and two earlier startup-only dependency-binding runs remain retained;
the final baseline and current source bindings are pinned through execution.

The integrated candidate, including the separate legacy keyboard correction,
passed **1133 tests / 34 skipped / 41 warnings** in 57.77 seconds. Eight changed
Python files passed Ruff/format and contract generation passed. Source CLI still
advertises registry v5 and the unchanged request schema. Four-language guides
describe the baseline boundary. Simultaneous external changes after button ACK
are outside this causality claim. Whole E2E/models, installed-current harness E2E,
Windows/Darwin native and full accuracy/p95/goodput/coverage remain NOT_RUN here;
acceptance/release gates are unchanged. See
[viewport evidence](validation/2026-10-11/viewport-input-baseline.json).

**OBSERVED / legacy X11 keyboard bindings:** the canonical old legacy action
requested `a` but delivered `b` and returned `ok=True` after the native keymap
changed following PyAutoGUI import. Current legacy type/press/hotkey preflight
every chord member and implicit Shift against the original binding, recheck each
press, and release acknowledged physical codes. A stale binding refuses before
any chord event. The full native held-key bitmap excludes only acknowledged owned
physical keys, so unrelated external modifiers refuse input and remain held.

Eight authenticated private native regressions verified exact normal `a`, Enter,
Ctrl+A and uppercase input; changed mappings emitted no keys. Mapping mutation
immediately after an acknowledged press still released the original physical
code; external `a`, Shift and Ctrl stayed held on refusal until fixture-owned
cleanup. A separate native counterexample reproduced uppercase `A` and Ctrl+A
events for literal `a` before the unowned-modifier correction. The initial three
mapping cases and two later modifier cases failed before their corrections.
The corrected scoped suite passed 31 tests, including nine existing native pointer
cases. Two earlier fixture focus failures remain retained; they stopped before
product key input.
Owned server, socket, keymap and input cleanup passed.

The final integrated source, including the later unowned-modifier correction,
passed **1135 tests / 34 skipped / 41 warnings** in 58.26 seconds. The preceding
1133-test result remains the earlier candidate's record. Windows/Darwin native
execution, a new legacy crash guardian, concurrent external remap atomicity and
whole E2E/model/performance are
not established by these components. No acceptance/release gate was promoted.
See [legacy keyboard evidence](validation/2026-10-11/x11-legacy-key-binding.json).

**User scope update (2026-10-12):** this session owns clef-use improvements and
component/regression verification. Whole-task E2E and model production/evaluation
belong to other sessions. Earlier completed task failures remain historical
evidence; this session will not execute new E2E or model-quality runs.
Published evidence HEAD before the following measurements: `8e1eedf`.
Earlier installed local candidate: FINAL24, correcting complete-directory aliases and duplicate
declared names in active skill sources while preserving separate resources and
unreadable metadata. Actual fresh and repeat shell installation, three guides across
three harness profiles, 26 preserved HOME files and 61 exact source/wheel/installed
files are recorded in [final24-install.json](validation/2026-10-11/final24-install.json).
FINAL24 includes the FINAL23 native catalog/explicit lookup and Codex individual
file-disable corrections, and preserves valid Hermes YAML documents during actual
enrollment. Its source regression passed **874 tests / 34 skipped**. Native discovery
and native loading are recorded separately below.
FINAL21's planned native matrix was stopped before execution and retains
[14 NOT_RUN cases](validation/2026-10-11/install05-final21-native-not-started.json).
Native discovery is recorded
separately; installation does not prove guide loading or invocation. FINAL19 retains
its original [837-test installation record](validation/2026-10-11/final19-install.json). FINAL17 retains its original
[installation and 835-test record](validation/2026-10-11/final17-install.json).
FINAL16's installed numeric model request retains its original candidate identity
in [final16-install.json](validation/2026-10-11/final16-install.json).
FINAL15's runtime identity correction and **792 passed / 34 skipped** regression
retain their original [candidate record](validation/2026-10-11/final15-install.json).
Earlier FINAL12 native tasks retain their original candidate and guide hashes.
This is partial execution evidence, not specification completion or release approval.
Current acceptance evidence is **34 PASS / 3 FAIL / 7 NOT_RUN**; the newly executed
general GUI tasks failed rather than remaining unexecuted.
Machine-readable, sanitized evidence and artifact hashes: [summary.json](validation/2026-10-11/summary.json).
Most recent native input/profile measurement candidate: [final10.json](validation/2026-10-11/final10.json).
Latest input-candidate measurement: [reaction-final10.json](validation/2026-10-11/reaction-final10.json).
Per-scenario status and remaining scope: [ACCEPTANCE.yaml](../ACCEPTANCE.yaml).

## Remaining work and specific verification boundaries

**OBSERVED / operation context revalidation:** three counterexamples reproduced
before correction. A transform continued after observed keymap content changed
without a version-label change; a resized viewport received a stale gesture;
and the runtime input bridge did not refuse a changed keymap. Dispatch now
anchors actual keymap content, viewport dispatch anchors the checked geometry,
and the input guard compares keymap content and editor surface again before
and during native input. Four new regression cases passed; the focused state,
operation and runtime checks passed 63 tests. An authenticated, owned Xvfb/Tk
component observed one real key event and a normal middle-button gesture,
refused a same-version native binding change and actual editor resize before
input, and stopped an owned gesture after an actual resize during its button
press. Native middle-button state and owned sets were released afterward.
This is an API-assisted input-bridge fixture with explicit application facts,
not automatic Blender observation, operation readiness or whole-task E2E.
The first native attempt's default-left-button setup error is retained separately.
Full regression: **915 passed / 34 skipped / 41 warnings**; scoped Ruff,
formatting and contract generation passed. The independent process check found
no matching processes for the two exact owned HOME values; unreadable unrelated
process entries remain outside that check. No production display was accessed
or model invoked.
See [component evidence](validation/2026-10-11/operation-context-guards.json).

**OBSERVED / literal input alternatives:** the canonical builder previously
proposed only the first matching input per literal. Before correction, four new
regression cases failed: right-field alternatives were missing, an unmatched
label still reserved a candidate slot, and an incomplete text roster reached
the decision stage. Each matching observed input now retains its own ID and
literal. Reservation counts actual matching alternatives, and overflow requests
`NEEDS_REPLAN` before model or input execution with explicit before/after counts.
The actual builder/router/serializer/JSON component path preserved both equally
labelled fields' distinct pixel boxes for both literals. These are synthetic
observations, not native GUI or task-quality evidence. The focused source checks
passed 124 tests. The first full run also exposed a pre-existing stale packaged
Blender guide manifest from the preceding documentation change; regeneration
is committed separately as `1e42658`. After that correction the full suite passed
**911 tests / 34 skipped / 41 warnings**. Confidence, input guards and acceptance
gates are unchanged. New installation/E2E/model-quality checks are `NOT_RUN`
under the current session boundary. See
[component evidence](validation/2026-10-11/literal-candidate-alternatives.json).

### Historical boundary assessment before Windows recovery

The following table records the earlier scope and route state. Its authentication
and other-session ownership entries are historical; the current table at the top
supersedes them. Windows E2E is now authorized in this session.

The overall stop was not justified by the recorded failures. Unimplemented
production observation and failed model decisions are engineering work, not proof
of an unavailable environment. The following boundaries apply to individual checks.

| Check | Observed result or missing prerequisite | Next action and ownership |
| --- | --- | --- |
| Production operations | The optional Linux X11 public-RNA producer is bound through `blender_state_socket`. Actual UI-thread scene/viewport facts and positive running-job busy evidence are verified with native PID/peer/window binding. Popup, editing, IME, effective keymap, focused editor and global idle remain unobserved; all six operation guards remain in force. | Continue clef-use observation/input improvements without inventing absence facts. The partial producer does not close general operation support; whole-task verification belongs to the other session. |
| OMP native model loading/invocation | The recorded `aipi/dgx-moa-fast` primary and three auxiliary requests returned HTTP 401 before any tool call. Current provider health and the credential cause were not checked. Actual Codex native loading/invocation succeeded separately. | This blocks that OMP route only. Do not request Codex desktop authentication repair or stop independent implementation. Keep OMP loading/invocation NOT_RUN until its selected provider can execute. |
| Blender and general GUI accuracy | Earlier Blender assessment failed all five positives. The completed CI493 browser/editor check also failed 0/2: browser mode confidence 0.7027 and editor replan probability 0.9056. Native input/effects were zero. | Preserve this diagnosis for the E2E/model session. This session improves clef-use software and does not repeat model-quality or whole-task runs. |
| Reici matched-view verification | A real private production checkpoint was located through an existing active task ledger. The earlier missing-scene assumption is withdrawn. That task records a default-computer-use approval timeout before an alignment input, and part-local/final quality gates remain open. | Preserve the other actor's scene and input boundary. Establish the permitted isolated verification target without rerouting or bypassing its unapproved input. Existing scene discovery proves neither edits nor independent review. No asset purchase is required to continue software work. |
| Full reaction profile | Whole-workflow accuracy, prospective fast-path eligibility coverage and state-change-to-correct-input p95 are unmeasured. The bounded Tk profile is separate. | Owned by the E2E session. Do not count refusal, ACK, component observation or fixture success as this gate. |
| Public release | CI built and checked all 15 combinations; deploy was skipped because the feature branch is outside the existing main/version-tag guard. Current deployment variable, runner and public server health were not verified. | Finish the candidate and use the existing authorized promotion/release workflow. A branch guard is not a deployment outage; do not bypass it or request release approval for an incomplete candidate. |

**OBSERVED / candidate identity correction:** a direct canonical packet check with
two equally labelled controls could not resolve an action to its observed object:
the model-facing serializer omitted `operation` and `target`. The regression failed
with `KeyError: 'operation'`. Reusing `ActionCandidate.audit()` preserves both fields
and the existing pointer representation. The same real builder/serializer/JSON path
now resolves `a1` to the right control's pixel box `(70, 20, 80, 40)` while `a0`
remains bound to `(10, 20, 20, 40)`. A separate boundary reproduction found that
the router kept only 32 executable target objects despite allowing more actions.
All 33 or 40 targets are now retained within the unchanged 40-object budget;
41 distinct targets explicitly request replanning before any model or input call.
The canonical serializer also refuses a target absent from its observation.
The focused suite passed 124 tests and the full source suite passed
**880 tests / 34 skipped**; scoped Ruff and formatting passed.
The packet check itself executed no model or OS input. Subsequent immutable
CI493 Linux/Windows installation matched all 61 Git/wheel/installed files;
fresh installation returned `INSTALLED`, repeat returned `CURRENT`, preserving
selected HOME/config/guide bytes. CI run 38183395770 completed successfully.
The completed identical native tasks still failed both cases. Their prospective
packets had no dangling targets and included the correct next control geometry;
the editor still lacked an initial type/focus candidate. This is not full task
coverage or a demonstrated cause of the quality failures. No acceptance status
or confidence guard changed. See
[source correction evidence](validation/2026-10-11/candidate-target-context-fix.json).

**OBSERVED / optional Blender component:** the real factory UI producer sampled
selection, mode, properties and viewport on Blender's main thread through the
canonical provider. Three positive samples passed; an actual separate-process
decoration frame was resolved to its Blender client. A wrong kernel peer, actual
OS frame resize after capture and native query-stream loss returned UNAVAILABLE.
The visible Quick Setup popup did not turn an empty operator roster into absence:
popup/text/IME/keymap/loading facts remained UNKNOWN. The final component run used
no profiling, models, keyboard or pointer input; owned children exited. Initial
startup/transport failures are retained separately. Full regression:
**907 passed / 34 skipped**; subsequent guide/integration checks: **105 passed**.
The wheel contains the exact new collector/observer/provider and callers.
This proves partial observation and refusal behavior, not operation readiness,
installed E2E, task quality or p95. See [component evidence](validation/2026-10-11/blender-rna-observer-component.json),
[Linux CI493 install](validation/2026-10-11/ci493-linux-installed.json),
[Windows CI493 install](validation/2026-10-11/ci493-windows-installed.json),
[historical task failure](validation/2026-10-11/ci493-native-quality-failure.json),
and [completed CI493](validation/2026-10-11/release-ci4932557.json).

## Objective and invariants

Implement the attached KODEX specification while preserving active V2, the existing
five tools, confidence guards, pinned model boundaries, unrelated work and frozen
`old/`. Instruction-only Agent Skills do not authorize runtime input. Local operation
`SUCCEEDED` verifies its typed effect; session `NEEDS_REPLAN` still requires separate
fresh goal ASSESS. No API-assisted fixture or cache-only observation certifies a
production task or a 100 ms release gate.

## Provenance and versions

**OBSERVED:** user-provided attachment archive SHA-256
`bd3b71075324544b03e3ca3a45f9cd94d3ed55d754f78e8b2c35285008b82b33`.
Repository `KODEX.md` and `docs/BASELINE_AND_SOURCES.md` match the archive exactly.
`ACCEPTANCE.yaml` also matched before this evidence update; its requirement strings
and numerical release gates remain unchanged. No tracked `old/` diff was present.

**OBSERVED:** FINAL5 is a local, unpublished `0.1.30` installed candidate: API schema
`1`, guide contract `1`, operation registry `2`; schema SHA-256
`df0899e3691cd7ba6f4d6b30760766ba5d349e06ce4504ee4a2cba914937ea91`.
FINAL5 installed Blender and Windows component evidence includes the gesture timing
correction. Browser/editor and reaction measurements remain explicitly FINAL4; those
measurements are not results for the subsequently rebuilt FINAL5 wheel.

**NOT_RUN:** a general trusted production state provider. Installed capability
metadata reports provider `NONE`, configuration path `UNAVAILABLE`, and all six
operations `BLOCKED` without verified facts. The private Blender fixture provider
is not installed into normal runtime.

**OBSERVED / production-provider feasibility probe:** a separate owned Blender 5.2
factory process was sampled in ten UI phases, five samples each. Timer context
`region_popup`, `area`, `space_data` and `property` remained null even with an
actual F3 search caret or numeric-field caret. Empty `modal_operators` also occurred
with those editors open; native G exposed `TRANSFORM_OT_translate` in all five
samples and Escape cleared it. A read-only Properties draw callback identified
hovered `Object.location[0]`, but did not distinguish hover from editing ownership.
Those observations cannot justify null-to-false popup/text-focus guards. General
IME, loading, menu identity and native per-window binding remain unverified.
The sanitized private probe summary SHA-256 is
`e8d2c3eb249196150d6b05cf895865e78ee5455feba63fbb10b3b7c5bd12d3b4`;
only the owned Blender/Xvfb processes were terminated.

## Executed evidence

**OBSERVED / committed YAML-fix Windows installation:** the actual `bb971ef`
Windows 3.11 CI archive completed ten native commands with fresh `INSTALLED`,
repeat `CURRENT` and all 61 Git/wheel/installed files identical. At three stages,
the actual installed `read_config` parsed the enrolled flow document and verified
unchanged settings, user-note hash, original CRLF prefix and tail bytes. Three
guides across three profiles enrolled then remained `UNCHANGED`; repeat HOME,
configuration and guide bytes were identical. Independent readback found zero
owned processes. Global wrapper/configuration/PATH and bootstrap/prior-fixture
trees were preserved; full active production V2 runtime identity is not established
by that bootstrap snapshot. Native harness/model/service/GUI/input were not run.
See [immutable Windows proof](validation/2026-10-11/windows-cibb971ef-install.json).

**OBSERVED / isolated accessibility setup failure:** installed GI/AT-SPI imported,
but the owned Xvfb terminated with SIG11 before any bus, registry or factory
Blender started. Blender accessibility publication remains `NOT_RUN`; this is not
evidence of its absence. NVIDIA EGL library names in the stack are observations,
not a proven cause. The owned child and namespace exited, and independent
mount/socket checks found no survivors. See [setup failure](validation/2026-10-11/production-atspi-factory-setup-failure.json)
and [separate metadata review](validation/2026-10-11/production-atspi-installed-metadata.json).
The separate v2 startup correction stopped when its nested user namespace was
refused, before Xvfb executed. It supplies no comparison of EGL vendors or Blender
publication; the original crash and both cleanup results remain recorded. See
[v2 setup stop](validation/2026-10-11/production-atspi-factory-v2-setup-failure.json).
The v3 route observed the Xvfb socket, then failed to establish the private DBus
connection with a UID password-database lookup diagnostic. Its mapped namespace
identity differs from the first attempts. Registry and Blender remained unstarted;
this still supplies no app-publication result. See
[v3 setup stop](validation/2026-10-11/production-atspi-factory-v3-setup-failure.json).
The v4 route initialized the actual private AT-SPI bus, registry and desktop
observer, verified the owned registry PID and observed an empty baseline. Its
separate app launcher failed to create a mount namespace before the Blender ELF
executed. App publication remains inconclusive; observer initialization alone
does not provide application state. See
[v4 observer and app setup results](validation/2026-10-11/production-atspi-factory-v4-observer-pass-app-failure.json).
The v5 direct-ELF route verified the official executable and its OS window PID.
Five samples each observed one owned window and zero registered applications.
However, Blender treated the original `--noaudio` argument as a filename and
reported a read error. This is a bounded observation with a startup limitation,
not a clean factory baseline or proof of interface absence. See
[v5 limited observation](validation/2026-10-11/production-atspi-factory-v5-startup-error-observation.json).
The v6 direct-ELF run corrected that argument to `-noaudio`. The actual observer,
registry identity, executable inode and OS window PID checks passed. Five samples
from 0.318 to 2.321 seconds each observed one owned window and zero registered
applications. The complete app log had no unknown-argument or error lines; locale
and mounted-filesystem warnings remained. This is a short bounded observation,
not a settled-scene check or universal interface-absence proof. It establishes no
verified popup, edit, IME or keymap facts for the production State Compiler.
Owned children and namespace exited; independent mount/socket readback found zero
survivors. All five earlier attempts remain recorded. In the original v3/v4
receipts, `environment_route.outer_retained_capability` describes declared policy;
live capability sets were not measured. The original receipt bytes and hashes
remain preserved. See
[v6 bounded observation](validation/2026-10-11/production-atspi-factory-v6-bounded-observation.json).

**OBSERVED / committed YAML-fix release workflow:** run 38157978139 at `bb971ef`
completed all 15 build/installation-check/upload pairs and release-site assembly.
Production deployment and tag publication remained skipped by the existing guards;
no bypass, main/tag change or agent retry occurred. Native Windows flow-config
installation is a separate check. See
[exact-source workflow receipt](validation/2026-10-11/release-cibb971ef.json).

**OBSERVED / installed FINAL24 native Hermes boundaries:** identical block-YAML
seeds exposed five preservation-report mismatches in the actual FINAL22 installation
and none in FINAL24 across eight conditions. A separate original flow-YAML seed
actually enrolled, parsed with the native parser, retained trusted-project settings
and loaded the complete selected project guide. All 17 conditions verified native
config parsing, trust, full body and preexisting HOME bytes. Root independently
checked all 51 actual exit/output receipts; 24 capability children ran, no retries
or model/service/GUI/input calls occurred, and owned-process readback was zero.
The original fixture stop and serialization failure remain unchanged. See
[paired native proof](validation/2026-10-11/install05-hermes-boundary-v5-paired.json).

**OBSERVED / INSTALL-05 assessment:** the 14 native conditions cover the four named
behavior classes across three harnesses, plus configured Hermes sources. Together
with the separately executed Hermes boundary corrections, the exact named condition
is `PASS`. Complete-directory realpath aliases and Codex individual file inactivity
retain their tested scope; condition results are dry-run preservation reports,
not overwrites or a whole-profile/task claim. Native14 file preservation hashes
cover selected `SKILL.md` files; broader preservation is proven only where separate
installation or paired receipts measure it. See
[root policy and limits](validation/2026-10-11/install05-final24-root-policy.json).

**OBSERVED / source354 release workflow:** run 38156320672 completed all 15 OS and
Python build/installation-check/upload pairs and assembled the release site.
Production deployment and tag publication were skipped by the existing main/tag
guards. No bypass, new tag, main change or agent retry occurred. This is an
immutable candidate artifact result, not public download/fresh installation.
See [workflow receipt](validation/2026-10-11/release-ci3542636.json).

**OBSERVED / immutable Windows source354 installation:** seven native commands
completed with fresh `INSTALLED` and repeat `CURRENT`; all 61 Git/wheel/installed
files matched. Three guides across three selected harness profiles enrolled then
remained `UNCHANGED`. HOME, CRLF comments, disabled OMP settings, global wrapper,
configuration and PATH checks passed; independent owned-process readback was zero.
The runtime-tree snapshot covers the existing bootstrap tree and prior fixture,
not a verified identity of the full active production V2 runtime. This seeded
block-config proof does not clear the separately observed flow-YAML defect or
execute native harness/model/service/GUI/input. See
[actual Windows installation](validation/2026-10-11/windows-ci3542636-install.json).

**OBSERVED / separate Hermes boundary fixture stop:** the original paired attempt
stopped on its first BEFORE case after a manually copied unmanaged guide correctly
returned `CONFLICT`. Native missing-child cwd fallback and full-body loading worked.
The other 15 candidate-case checks remained `NOT_RUN`; the exact CLI exit was not
persisted and is explicitly distinguished from source-inferred exit 2. This was
a fixture ownership error, not a product cwd regression. A separately reviewed
fresh attempt uses actual canonical enrollment before constructing each condition.
See [original setup stop](validation/2026-10-11/install05-hermes-boundary-v3-setup-failure.json).

**OBSERVED / Hermes YAML serialization failure:** actual enrollment in the next
attempt returned `INSTALLED` but appended a block after a closed valid flow
mapping. Hermes rejected that document and fell back to defaults; successful
local guide loading therefore did not establish trusted-project configuration.
The evaluation CLI returned `ParserError`, exit 1, and the remaining 15 conditions
were not run. Three outer children were waited; independent owned-process count
was zero. The source correction keeps new entries inside flow mappings and before
document endings. Six deterministic regression cases failed before correction;
99 harness/integration cases passed after, including two empty explicit YAML
documents that initially raised `AttributeError`. Installed native correction evidence
remains separate. See
[actual serialization failure](validation/2026-10-11/install05-hermes-boundary-v4-serialization-failure.json).

**OBSERVED / FINAL23 native discovery:** all 14 conditions executed with 28 native
reports and 20 actual capability queries. Complete-directory aliases, duplicate
names, project overrides and the tested inactive sources agreed with the installed
preservation reports across Codex, Hermes and OMP. Codex's exact individual
`SKILL.md` disable now reports `PREVIEW`, matching the actual disabled project copy
and enabled managed copy. This does not claim whole-profile or directory-entry
disable semantics. Hermes create/external source conflicts preserve the selected
local body; `CONFLICT` does not certify which duplicate the native harness selects.
All 70 command receipts were waited and final owned-process/socket counts were
zero. No model, service, GUI or input ran. Three non-atomic live-observer
disagreements remain recorded. See
[FINAL23 native matrix](validation/2026-10-11/install05-final23-native-matrix.json).

**OBSERVED / FINAL23 source regression:** the integration suite passed 85 cases and
the frozen full suite passed 866 with 34 skipped. Corrections cover Hermes cwd
validation, directory and declared-name aliases, malformed frontmatter, catalog
pruning versus legacy flat lookup, and Codex individual file disables. Independent
review was static and is not execution evidence. No confidence threshold changed.
See [frozen regression](validation/2026-10-11/final23-regression.json).

**OBSERVED / FINAL22 native discovery:** all 14 cases executed with 28 native
reports and 19 runtime capability queries. Whole-directory aliases, duplicate
names, trusted project sources and configured Hermes roots agreed with preservation
reports. Codex's individual disabled project `SKILL.md` was actually disabled,
but enrollment still returned `CONFLICT`; this concrete mismatch remains retained.
The earlier directory-only disable attempt did not establish inactivity.
The separately executed FINAL23 results above address this mismatch. See
[actual 14-case batch](validation/2026-10-11/install05-final22-native-matrix.json)
and [root policy interpretation](validation/2026-10-11/install05-final22-policy-readback.json).

**MEASURED / locked component comparison:** both models completed the same 72
queries over 36 original native screenshots. The supported V3 alternative hit
0/54 PRESENT targets and correctly abstained on 18/18 absent or ambiguous queries.
UI-TARS hit 50/54 PRESENT targets (browser 18/18, editor 18/18, Blender 14/18),
but proposed a point on all 18 queries requiring abstention. Neither result
supports production adoption. Thresholds remain unchanged. These correlated
component opportunities do not certify actual task accuracy, a genuine historical
baseline, reaction p95, goodput or coverage. Only seed 17 was executed. The original
environment failures remain retained separately. See
[completed comparison](validation/2026-10-11/heldout-component-comparison-final2.json).

**OBSERVED / FINAL22 source regression:** the missing-child, padded absolute and
home-relative `TERMINAL_CWD` cases each failed before correction and passed after
matching native Hermes directory validation. Explicit project selection remains
authoritative. The integration suite passed 67 cases; the full suite passed
848 with 34 skipped. This does not prove an installed native harness result.
See [source regression](validation/2026-10-11/final22-regression.json).

**OBSERVED / FINAL20 complete discovery batch:** all 12 planned cases executed,
with 24 actual catalog reports and 18 capability queries. Distinct duplicate names
now produce installed `CONFLICT` across Codex, Hermes and OMP. Hermes trusted-project
precedence exposed a remaining source-report gap: its native catalog selects the
project guide and shadows the local guide while enrollment reports `PREVIEW`.
The source now considers configured create/external directories and only the
current nearest trusted Git project, preserving `project_discovery: false`.
Codex's directory-targeted disable entry did not disable either catalog copy;
its installed conflict is correct and the inactive condition is `NOT_ESTABLISHED`.
No native accuracy/task/input or whole-source/profile gating pass follows from
these reports. See [all12 native observations](validation/2026-10-11/install05-final20-native-matrix.json)
and [precise policy readback](validation/2026-10-11/install05-final20-policy-readback.json).

**OBSERVED / model namespace boundary and first initialization failure:** exact
FINAL19 code and a narrow existing dependency overlay imported in separate CPU/UI
namespaces with original private paths inaccessible. The original missing-pydantic
failure is retained. The first authorized model batch subsequently stopped during
Transformers lazy import because the empty filesystem had no UID record or
`USER`/`LOGNAME`. No model weight load or query was reached; all 144 model-specific
query opportunities remained `NOT_RUN`. This is an environment initialization
failure, not model accuracy evidence. A separately authorized correction supplies
synthetic account environment values without mounting the host account database.
See [import admission](validation/2026-10-11/heldout-model-dependency-admission.json)
and [original initialization stop](validation/2026-10-11/heldout-model-first-initialization-stop.json).


**OBSERVED / FINAL19 native discovery:** actual Codex discovery and installed
preview now agree for a project alias of the complete managed directory. The next
case exposed a second defect: `duplicate-clef/SKILL.md` declared `name: clef-use`,
and the real Codex catalog returned two enabled copies, but enrollment returned
`PREVIEW` with no conflict. The matrix stopped at this concrete mismatch after
four native responses and four capability queries. The remaining ten cases,
including Hermes and OMP, remain `NOT_RUN`; no model, service, GUI or input ran.
The source correction scans declared names within the selected and other active
sources, preserving different directories and unreadable metadata as conflicts.
Its new installation and native matrix require separate evidence. See
[original FINAL19 native result](validation/2026-10-11/install05-final19-native-matrix.json).


**OBSERVED / historical FINAL19 source correction:** native Codex discovery deduplicated a
project alias of the complete managed guide directory, while FINAL17 enrollment
incorrectly rejected the same alias. The source now recognizes that shared resource
root. A file-only `SKILL.md` alias and separate identical files still conflict,
preserving divergent relative references. Regression passed **837 tests / 34 skipped**.
FINAL19 actually installed and repeated as `INSTALLED`/`CURRENT`, with all three
guides across three profiles, 26 HOME files preserved and 61 exact packaged files.
Native matrix results are recorded separately when observed. See the
[original native false conflict](validation/2026-10-11/install05-native-alias-false-conflict.json).

**OBSERVED / completed held-out acquisition and annotation:** the next capture
carried 17 original images byte-for-byte and acquired the remaining 19, completing
all 36 native browser, Tk and Blender screens. All 72 queries retain their original
text and kinds. Root viewed all 36 originals and approved the native DOM/Tk geometry
and independent Blender boxes before any model predictions. Local exact encoded
and decoded overlaps with the 20 known training/validation images and excluded
development image are zero; all 36 held-out images are distinct. Fifteen dHash
flags were reviewed against nearest references. The private data lock retains
54 present, nine visible-absence and nine ambiguous queries. Blender-10 includes
an explicit component-label inference limitation. Disabled-control localization
never grants input permission, and visible absence includes full occlusion.
No public-pretraining exclusion, statistical independence, model quality, native
control effect, task success or latency pass is claimed. All 72 model queries remain
`NOT_RUN` at this acquisition stage. See
[complete capture](validation/2026-10-11/heldout-acquisition-v6-complete.json),
[local leakage review](validation/2026-10-11/heldout-all36-local-leakage-review.json),
[root annotation review](validation/2026-10-11/heldout-all36-root-annotation-review.json),
and [all12 Tk pixel review](validation/2026-10-11/heldout-tk12-root-pixel-review.json).
Earlier partial-capture and pending-review records below retain their historical states.

**INFERRED / production provider boundary:** primary Blender 5.2 source confirms
that public modal-operator enumeration omits internal UI handlers and that event
context is temporary. The actual local runtime accepts partial verified provider
facts, but a production collector and authenticated OS-to-RNA per-window binding
have not been implemented or verified. Unknown text focus, menu, IME and busy
state cannot be replaced with `false`. Accessibility collectors remain unverified.
See [source feasibility review](validation/2026-10-11/production-state-provider-source-feasibility.json).


**OBSERVED / native discovery setup failure:** the 12-case discovery matrix stopped
in its first installation setup, before any native harness or capability discovery
call. The driver used the lexical `runtime/current` Python path; the actual console
shebang uses its immutable versioned VENV path. The former exposed a symlink ancestor
to the bundled-source guard. This did not reproduce a failure of the canonical
launcher. Eleven remaining cases and first-case discovery remain `NOT_RUN`.
See [original setup failure](validation/2026-10-11/install05-native-first-setup-failure.json).
The unchanged installed console body subsequently ran once through its exact
shebang VENV: exit 0, `INSTALLED`, three exact guide hashes and one actual capability
subprocess. This confirms the corrected console route, without native harness
discovery or a separate shell-launcher execution. See
[console proof](validation/2026-10-11/install05-canonical-console-proof.json).

**OBSERVED / historical b3219c5 immutable Linux artifact:** CI run `38148208835` built
`b3219c5`. Its Linux 3.11 archive installed and repeated as `INSTALLED`/`CURRENT`;
all 46 Python modules and 15 resources matched source, wheel and installation,
including manifest ordering. Three guides for three profiles, 26 HOME files and
configuration comments survived repeat integration. The actual installed client
started an owned idle service, verified version/protocol/schema, observed the
expected no-session status refusal, and shut down its matching endpoint. Independent
process readback found no owned runtime remaining. Two earlier driver mistakes
that expected idle status success are retained. No model, GUI or task ran.
See
[immutable Linux installation](validation/2026-10-11/cib3219c5-linux-install.json).

**OBSERVED / historical b3219c5 immutable Windows artifact:** the same commit's successful
Windows 3.11 job artifact installed and repeated as `INSTALLED`/`CURRENT`. All
61 files matched Git, wheel and installation, with no manifest exception. Three
guides across three managed harness configurations enrolled and repeated as
`INSTALLED`/`UNCHANGED`. All 12 checks and six preservation checks passed; V2,
PATH, existing fixture bytes, comments and disabled settings were preserved.
Read-only post-run inspection found no process command line referencing the owned
root. This did not execute a harness, model, GUI, input or runtime service. See
[native Windows installation](validation/2026-10-11/windows-cib3219c5-install.json).

**OBSERVED / historical b3219c5 CI failure:** all 15 platform/Python build and installer-check
step pairs succeeded, but the macOS Intel/Python 3.12 job failed when
`actions/upload-artifact` timed out creating its artifact after five built-in
attempts. Fourteen jobs passed; assembly and deployment were skipped. No agent
rerun or deployment bypass occurred. This is not an overall CI or release pass.
See [original CI result](validation/2026-10-11/ci-b3219c5.json).

**OBSERVED / eligibility provenance correction:** the changed native scorer ran
against the retained 3,015 actual reaction rows and 50 editor rows. All 25 summaries
preserved the original accuracy, latency, goodput and error values. Those historical
rows contain no prospective eligibility/policy-decision provenance, so coverage
remains `NOT_MEASURED`, with no success-based backfill or release-gate pass.
Source regression passed **835 tests / 34 skipped**. An actual older FINAL15 Python
also ran the current benchmark's help/checkout selector without preloading its
incompatible scorer. This is scorer reanalysis,
not a new installed task or latency measurement. See
[retained-row evidence](validation/2026-10-11/reaction-final17-reanalysis.json).

**OBSERVED / held-out preparation failure:** initial isolated native capture stopped
on private loopback initialization `PermissionError: [Errno 1] Operation not permitted`,
before Firefox launched. Zero of 36 screens were captured; all 72 queries remain
`NOT_RUN`. Owned processes and X sockets were removed; existing Blender survived.
No model, accuracy-task input or quality claim resulted. See
[original failure](validation/2026-10-11/heldout-acquisition-stopped.json).
The corrected zero-capability private-loopback preflight passed, but the next
capture stopped before any screenshot: actual Firefox DOM was 1080x720 at (4,4),
while Xvfb was 1200x800. This is a native coordinate-binding failure, with all
72 queries still `NOT_RUN`, not model-quality evidence. See
[second failure](validation/2026-10-11/heldout-acquisition-v2-stopped.json) and
[native namespace preflight](validation/2026-10-11/heldout-namespace-v2-native.json).
The next driver failed because its private namespace could not import the Xlib
dependency visible to the host interpreter; no screenshot was attempted. A
subsequent exact namespace admission loaded the actual Xlib/Pillow/native XCB
dependencies through narrow read-only mounts. The next authorized run captured
all 12 Firefox images and DOM oracles, then stopped when the first Tk oracle
reported unmapped 1x1 controls. The remaining 24 scenes and all 72 model queries
remain `NOT_RUN`. Root inspected all 12 original browser images. All 12 encoded
and decoded image identities differ from the 20 local train/validation images and
the excluded development image. Five dHash flags were inspected against both
nearest source images, which are uniform gray; no copied local screen was observed.
This does not establish absence from public pretraining. Final annotations and
the full data lock remain pending, with no model or quality pass. See the
[dependency failure](validation/2026-10-11/heldout-acquisition-v3-stopped.json),
[actual dependency admission](validation/2026-10-11/heldout-v4-dependency-native.json),
[partial capture](validation/2026-10-11/heldout-acquisition-v4-partial.json), and
[pixel review](validation/2026-10-11/heldout-browser12-pixel-review.json), and
[local leakage review](validation/2026-10-11/heldout-browser12-leakage-review.json).
The subsequent run carried those 12 browser images and oracles byte-for-byte and
captured five native Tk scenes. It stopped on the next scene because an empty
toolbar legitimately measured one pixel high while the actual Notebook targets
were mapped at 1172x30. No scene was retried or relabeled. Seventeen screens are
available; 19 screens and all 72 model queries remain `NOT_RUN`. Root inspected
the five new Tk originals; their local leakage review and the full data lock remain
pending. Owned processes and all declared X sockets/locks were gone after cleanup;
production Blender remained alive. See
[v5 partial capture](validation/2026-10-11/heldout-acquisition-v5-partial.json) and
[Tk pixel review](validation/2026-10-11/heldout-tk5-pixel-review.json).

**OBSERVED / grounding-head provenance:** the configured historical head uses v2;
both pinned and current canonical loaders require v3. Refusal is inferred from
source/metadata, not an executed load. The existing supported v3 head is a separately
named alternative, without evidence that it is currently served. Earlier general
GUI tasks disabled visual grounding. Global configuration and active V2 remain
unchanged. See [metadata readback](validation/2026-10-11/grounder-head-provenance.json).

**OBSERVED / installed numeric diagnostics:** FINAL16's actual default CLEF worker
returned SDK usage of 1,565 input tokens and zero output tokens. Independently
re-serializing the actual request state/questions counted 3,198 UTF-8 bytes,
nine questions and zero objects; all matched the returned diagnostics. The one
request used retained development pixels with an empty roster and no candidate
actions. Its original result was `BLOCKED`; this proves numeric retention, not
task quality, full runtime execution, correct-target coverage or a latency gate.
Worker streams/process and outer sandbox cleanup were observed. Raw requests
and replies remain private. See [native result](validation/2026-10-11/decision-numeric-final16-native.json)
and [cleanup scope](validation/2026-10-11/decision-numeric-final16-cleanup.json).

**OBSERVED / actual general GUI tasks:** FINAL15's installed default factory ran
one native Firefox form and one independent Tk editor task through actual cached
OmniParser and CLEF workers. Neither completed: browser stopped on ACT-mode
confidence 0.7271 below the unchanged 0.9 guard; editor requested replanning at
probability 0.9041. Independent HTTP submission and saved-file/widget oracles
confirmed zero effects, with zero native inputs and no false completion. All six
owned cleanup checks passed. The action distributions were NONUNIFORM and no
candidate truncation occurred. Logs did not retain exact candidate descriptions,
geometry, decision requests or raw head values, so correct-target coverage is
unknown. No threshold, prompt, provider or model retry was used. See
[native task failures](validation/2026-10-11/general-gui-final15-native.json) and
[retained-trace diagnosis](validation/2026-10-11/general-gui-final15-diagnostic.json).

**OBSERVED / GUI-trained model preparation:** public UI-TARS-2B-SFT was downloaded
at revision `f366a1db3e7f29635f5b236d6a71dea367a0a700`; both actual F32
safetensors hashes match the pinned producer metadata. An offline standard
Qwen2VL BF16 CUDA development smoke loaded it and produced coordinate tokens,
without remote code or OS input. That image is excluded from future heldout
evaluation. One forward is neither a quality comparison nor a speed improvement.
The original producer's coordinate prompt and /1000 mapping are pinned; its
OpenAI-compatible frequency penalty has no identical Transformers parameter,
which remains an explicit decoding difference. No default model, confidence gate
or production operation was changed. See
[pinned acquisition](validation/2026-10-11/ui-tars2b-pinned-acquisition.json) and
[development smoke](validation/2026-10-11/ui-tars2b-development-smoke.json).

- **OBSERVED / source fixture:** FINAL6 source regression reports **772 passed, 34 skipped** and 41 warnings.
  Earlier FINAL5: 767 passed, 34 skipped; phase: 766 passed, 34 skipped. Unit/protocol/fixture coverage is distinct
  from native, installed and actual-harness verification. Exact log hashes are in JSON.
  The subsequent metric-label correction passes seven targeted regressions and
  executes the changed scorer against 3,000 retained warm native events; no input
  is replayed and no timestamp or denominator changes.
- **OBSERVED / installed candidate:** disposable Linux HOME with spaces/Korean
  characters installs selected MCP/guide entries for Codex, Hermes and OMP. Same-version
  reinstall reports `UNCHANGED`; unrelated configuration is preserved. Local lifecycle
  fixture covers update and old-version preservation on checksum/download/smoke failures.
  Its synthetic `0.1.31` version is not a published release.
- **OBSERVED / installed schema:**
  `/tmp/clef-use-installed-final4-20261011/runtime/current/bin/python scripts/generate_agent_contract.py --check`
  returns `PASS`: 3 common tool examples, 11 CLI examples, 3 portable guides and matching
  command blocks in the four localized AGENT_GUIDE documents. This is not exhaustive
  validation of all published prose or model behavior.
- **OBSERVED / FINAL5 installed native Blender:** **22/22 expected cases pass**, including
  one service-entry refusal while a previous session owns modal recovery. Real native
  input runs through `SessionManager.run/continue_session -> SessionRuntime.execute`.
  Cases include numeric translation/scale/rotation, preview/commit/cancel/readback,
  abort immediately after modal entry, same-session modal recovery, command search,
  exact property edit, viewport orbit/pan and menu/context guards. Access is explicitly
  **API_ASSISTED**, in disposable factory-startup Xvfb, with no production scene touched.
  All eight runtime module hashes match source. The fixture does not run the original
  canonical model ASSESS or a harness GUI task.
- **OBSERVED / source Linux native input:** disposable X11 widget evidence records
  key/chord/down/up, exact Unicode, buttons/modifier gesture, deadline/cancel/focus/user
  intervention, guardian failure, process crash and frozen-injector cleanup checks.
  This post-correction source result is separate from earlier FINAL4 measurements.
- **OBSERVED / installed Firefox and Code:** exact Unicode native insertion is
  independently checked by HTTP form submission and saved UTF-8 file bytes. Code uses
  a private observed editor/native window/no-XIM guard, `context=None` for Ctrl+S and
  zero input retries. These typed-input checks do not exercise SessionRuntime/harness
  general GUI task execution or prove a general application state provider.

## Windows result remains FAIL

**OBSERVED:** immutable FINAL5 wheel components in an owned Windows payload using
existing managed Python/dependencies pass native Unicode/chord, three-button,
corrected two-point Shift+MMB gesture, deadline/cancel, preexisting input, focus-loss,
crash and frozen-injector cases. All four loaded module hashes match wheel SHA-256
`6c41e000b528a4aa3aa850c64253cd8a94b57aa5a366057f14554d338c70c1cc`;
no held keys remain and the owned task was removed.

**FAIL / foreground restoration:** `SetForegroundWindow` admitted `True`, but the
immediate foreground readback was `None`. A later restoration-only probe found the
original window valid while foreground had independently changed, so it preserved
that foreground and did not replay native input. The raw report's old source-scope
label is explicitly stale; module hashes identify the actual FINAL5 components.
This failure is not hidden by passing input cases. Windows overall and release
are not PASS.

**OBSERVED / FINAL7 Windows installation:** the exact Windows CI artifact from
run `38127830854` installed the runtime, matched all five contract fields and
preserved the working wrapper after a checksum-refused update. Actual managed
integration failed: native text-mode writes converted guide LF bytes to CRLF and
existing CRLF configuration to CRCRLF, breaking hashes and transaction recovery.
An intermediate private install with only the canonical atomic-writer fix then
preserved exact mixed newlines/Unicode, installed all three profiles idempotently,
and preserved customized guides and disabled entries. Codex discovered all three
project guides; isolated user-root discovery failed because native Windows Codex
used the real known-folder home rather than overridden environment variables.
Both outcomes remain recorded in
[`windows-final7-integration.json`](validation/2026-10-11/windows-final7-integration.json).
This source-patched install is not an immutable rebuilt artifact. Its historical
scope remains separate from the corrected immutable verification below.

**OBSERVED / corrected immutable CI:** run `38132441002` at `26d9252` passed all
15 platform/Python builds and assembly. Existing branch policy skipped deployment.
The assembled site installed on a fresh isolated Linux HOME, preserved all 26
managed file bytes on repeated explicit three-guide integration, matched every
packaged Python module to frozen source and verified all 15 archive hashes.
See [ci26d9252-linux-install.json](validation/2026-10-11/ci26d9252-linux-install.json).
The exact corrected Windows ZIP also passed native PowerShell install, executable
launch, all five contract fields, three-guide enrollment across three profiles,
idempotence, exact mixed-newline/Unicode preservation, edited-guide conflict,
disabled-entry preservation and checksum-refused update with the old wrapper intact.
All 61 installed Python files matched its wheel. Global V2/config/PATH were preserved.
An actual native walk found zero reparse points across 6,625 owned entries and
seven ancestor components; the registered PE executable directly launched 0.1.30.
Native Windows Codex isolated user-source discovery still failed, while supported
project discovery found all three guides. Hermes/OMP executables were unavailable;
their native stages and all model/GUI stages remain **NOT_RUN**. Two earlier fixture
configuration errors and their actual safety refusals are preserved. See
[windows-ci26d9252-immutable.json](validation/2026-10-11/windows-ci26d9252-immutable.json).
The earlier Windows foreground failure remains open.

**OBSERVED / immutable installer refusal boundaries:** actual Linux `install.sh`
and native Windows `install.ps1` refused checksum mismatch, an offline origin,
parent traversal, absolute paths, backslash paths, symlink members and duplicate
ZIP entries before activation. Existing runtime selector, executable/version and
owned HOME bytes survived: 26 Linux files and 111 customized/disabled Windows files.
Both owned loopback servers stopped. Synthetic `0.1.31` metadata represented only
malformed test inputs, never a published or installed release. See
[Linux boundary evidence](validation/2026-10-11/linux-installer-boundary-ci26d9252.json)
and [Windows boundary evidence](validation/2026-10-11/windows-installer-boundary-ci26d9252.json).

## Actual harness stages

**OBSERVED / FINAL6 installed native adapters:** Codex discovers the exact three
enabled guides. Hermes and OMP discover, load actual guide bodies and invoke
read-only capabilities. OMP also passes with a custom relative config root and
an explicitly default canonical profile overriding a legacy profile. An absolute
`PI_CONFIG_DIR` now refuses before writing instead of registering an undiscoverable
location; use `PI_CODING_AGENT_DIR` for an absolute default agent directory.
These fresh native-library checks do not establish model triggering or GUI tasks.
All eight Blender/input core module hashes match FINAL5; native results remain
attributed to their actual installed candidates.

Hermes and OMP model-trigger observations below used the pre-FINAL4 `0.1.30`
guide bundle. The Blender reference changed afterward; these earlier model stages
do not certify a fresh FINAL4 guide reload. Codex's later model-trigger check used
the exact FINAL6 bundle and is recorded separately in
[`codex-final6-triggers.json`](validation/2026-10-11/codex-final6-triggers.json).

| Harness | INSTALLED | DISCOVERED | LOADED | INVOKED (read-only) | GUI TASK_VERIFIED |
| --- | --- | --- | --- | --- | --- |
| Codex | PASS | PASS (native catalog) | PASS (FINAL6 explicit/natural) | PASS (capabilities) | NOT_RUN |
| Hermes | PASS | PASS | PASS (explicit/natural) | PASS | NOT_RUN |
| OMP | PASS | PASS | PASS (SDK and achieved model stage) | PASS (achieved stage) | NOT_RUN |

**OBSERVED:** Hermes natural trigger loads the Blender guide and calls capabilities;
explicit invocation loads core/diagnostics; a negative non-GUI task loads/invokes
neither. A separate `codex-cli 0.160.1` process in the isolated installation fixture
stopped at provider HTTP 401 `invalid_api_key` using local API-key authentication;
no credential values are retained. This does not establish an authentication
failure in the active Codex desktop chat or that the chat uses the same transport.
An existing authenticated Codex daemon (`0.159.2`, ChatGPT authentication) then
completed fresh ephemeral `gpt-6.1-sol` turns without changing authentication or
global configuration. Native discovery resolved all three exact FINAL6 installed
guide paths. The explicit turn read the core body; the natural Blender turn read
all three bodies; both successfully called read-only capabilities. The negative
non-GUI turn read no guide and called no runtime tool. A status call correctly
refused because there was no active session. Earlier denied-approval rounds are
retained separately. These results establish the named read-only stages, not a
GUI task or identity between the daemon and this chat's transport.
OMP's model natural run achieved
load/invoke, then exited with `DeadlineExceeded`; overall model session is `NOT_RUN`.
The independent native SDK survivor check passes after removing Codex's shared owner.
None of these read-only stages certifies a GUI task.

## Bounded native reaction measurement

**MEASURED by the native runner; artifact inspected, not independently rerun here.**
FINAL4 runs three native input variants against an owned disposable Tk/Xvfb widget:
1,005 opportunities per variant, five rotating-order sessions, five cold and 1,000
warm opportunities. Separate processes timestamp native state-to-KeyPress receipt;
widget effects are independently verified after idle. Every failed opportunity and
miss remains in accuracy/coverage denominators; latency percentiles are labelled
correct-event latency. Hardware: Ryzen 7 9700X, 16 logical CPUs, Linux, Python 3.11.16.
Power/thermal state is uncontrolled and other workspace agents may compete for load.

| FINAL4 warm variant | Correct | p50 ms | p95 ms | p99 ms | Misses | Goodput100 | Goodput/s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pinned_b3 | 1000/1000 | 20.226 | 20.271 | 20.304 | 0 | 1.000 | 4.523 |
| current_legacy | 1000/1000 | 20.228 | 20.272 | 20.404 | 0 | 1.000 | 4.523 |
| typed | 1000/1000 | 40.273 | 80.457 | 80.526 | 10 | 0.990 | 14.474 |

Each variant reports zero critical errors in this bounded input workload. The separate
50-opportunity Tk Text single-key profile reports 50 correct, p95 **100.577 ms**,
goodput100 **0.78**, 11 misses and zero critical errors. Cold/all/session statistics,
source hashes, scope/exclusions and artifact hashes are retained in the JSON summary.
**MEASURED / FINAL5:** the same predeclared workload completes with 1,005 correct
opportunities per variant. Warm typed p50/p95/p99 are **40.268/80.447/80.509 ms**,
goodput100 **0.991**, 9 misses and useful throughput **14.665/s**. Warm pinned-b3
p95 is **20.268 ms**, goodput100 **1.000** and throughput **4.523/s**. Typed event
latency is slower than this native baseline despite higher throughput. The separate
50-opportunity Text single-key profile has p95 **100.558 ms**, goodput100 **0.82**, and 9 misses.
It does not pass the 100 ms p95 target. All reported critical counts are zero.
Exact Unicode clipboard insertion was a separate correctness preflight, not the
50 timed opportunities. Unicode insertion p95 was not measured by these profiles.

**Metric correction:** historical raw native reports called deadline success ratio
`fast_coverage`. Under KODEX that ratio is `goodput_100`; fast-path eligibility
was not recorded and its coverage is **NOT_MEASURED**. Curated evidence corrects
the labels without changing timestamps or attempts. The runner now keeps these
metrics separate and preserves unknown eligibility. No eligibility coverage gate
is certified by these narrow input measurements.

**MEASURED / FINAL10:** the frozen installed runtime completed five sessions and
1,005 opportunities per variant. Warm typed input was **1,000/1,000 correct**,
p50/p95/p99 **20.174/20.235/20.270 ms**, goodput100 **1.000**, with zero misses
or critical errors and useful throughput **24.785/s**. The pinned primitive's warm
p95 was **20.261 ms**, throughput **4.526/s**. The separate 50-opportunity native
Text single-key profile was **50/50 correct**, p95 **20.319 ms**, goodput100 **1.000**.
All five Unicode clipboard correctness preflights passed; they do not measure
Unicode latency. Runtime hashes remained unchanged. Native state notification,
correct KeyPress timestamp and independent widget readback bound this result;
parser/model inference and full operation-return latency are excluded.
Eligibility coverage remains **NOT_MEASURED**. See
[reaction-final10.json](validation/2026-10-11/reaction-final10.json).

**NOT_RUN:** the production/model/Blender/harness task performance gate. The pinned
baseline is only the `b3f0b233` DesktopAction implementation with current supporting
libraries, not the entire old runtime/model stack. No overall 100 ms result or
controlled comparative speedup is claimed. Earlier independent editor profiles
missed the stated threshold and remain recorded; all original numerical gates
remain unchanged.

## Remaining acceptance and milestones

**OBSERVED / FINAL10 installed input correction:** the frozen source suite passed
**780 tests**, with 34 skips and 41 warnings (44.60s). A fresh local archive install
matched eight changed source modules, enrolled all three guides in three isolated
profiles and preserved all 26 owned-home file bytes on repeat integration. Real
installed native widget/protocol checks pass, including prior Unicode/large-data
restoration, interrupted queued paste and requestor destruction. A private actual
Hangul engine confirms explicit clipboard literals commit exactly while native
Unicode-keyboard substitution and active-composition insertion are refused.
This is API-assisted owned-widget evidence, not shipped composition control or
general production state support. Fresh reaction measurements are recorded above;
harness GUI tasks remain a separate gate.

**OBSERVED / FINAL10 Blender operations:** the canonical installed fixture returned
**FAIL, 21/22 expected outcomes**. Its Edit setup screenshot contained no popup;
the runtime correctly reported `ABSENT`, while the fixture expected `WRONG_MENU`.
One private instrumented run, separating pointer movement from click with native
screenshot/OCR checkpoints, passed 22/22. The proposed Escape/popup race was
rejected by those checkpoints. The canonical failure's cause is not established;
the instrumented result does not correct or erase it. Both results and the initial
diagnostic import failure are retained in
[blender-operations-final10.json](validation/2026-10-11/blender-operations-final10.json).

**OBSERVED / original live menu task FAIL:** a predeclared 30-trial comparison
executed the full pinned `b3f0b233` 0.1.29 runtime and immutable FINAL6 installed
0.1.30 against actual Blender File-open, Edit-open and absent states, five repeats
per state/version. All 15 pairs had identical before-image pixels and independently
verified menu state. Both versions returned `LOW_CONFIDENCE` in all 15 trials;
File-open completion was **0/5 each**. Negative false completions and native OS
inputs were **0**. Original File-menu recognition remains unsolved; E2E-01 is
**FAIL**, distinct from the 22 passing API-assisted operation cases. Cold and
warm/caption-cache timings are separate; no speedup or state-change-to-input p95
is inferred from input-free ASSESS. Exact sources, unchanged thresholds, setup
failures and cleanup are retained in `blender-menu-paired-final6.json`.

**OBSERVED / same FINAL10 CLEF versus d1:** a second predeclared comparison executed
all 30 canonical ASSESS trials with identical installed code and contract, five
repeats per File-open/Edit-open/absent state and model. All 15 paired screenshots
matched; independent ground truth verified every before/after state. CLEF returned
15 `LOW_CONFIDENCE`; d1 returned ten `NEEDS_REPLAN` and five `LOW_CONFIDENCE`.
File completion was **0/5 each**, with zero false completions and zero native inputs.
This completes DEC-02's comparison, while original menu quality remains **FAIL**.
The actual d1 backend loaded its pinned local BF16 checkpoint without a budget
refusal; its exact encoded token count was not exported. Cold/model-warm/parser-cache
timings remain distinct, with no 100 ms or comparative speedup claim. Exact selected
OCR text/bboxes were not retained by canonical history, so no cause is inferred
from matching context IDs or the intentional ASSESS `none` singleton. See
[blender-menu-clef-d1-final10.json](validation/2026-10-11/blender-menu-clef-d1-final10.json).

**OBSERVED / native IME counterexample:** a private GTK/IBus Hangul fixture
observed real preedit and committed text through official owner-widget events.
Known active composition correctly blocked shortcut/literal requests. With an
idle enabled Hangul engine, the previous X11 ASCII keyboard substitute returned
success while creating preedit instead of the requested literal. Linux now
requires explicit clipboard delivery even for ASCII; Windows native Unicode is
separate. External read-only IBus peer observation did not establish generic
composition state. A shipped trusted observer and typed composition transaction
remain **NOT_RUN**; this fixture does not satisfy INPUT-02 by itself.

**OBSERVED / FINAL6 OMP native default:** OMP18.6.1 using its current
`aipi/dgx-moa-fast` route completed explicit and natural turns, read complete
installed guides through native `skill://` URIs and invoked read-only capabilities.
This establishes HARNESS-03 at its named read-only scope. The independent negative
Python question also completed, but unnecessarily read GUI guides and invoked
capabilities: GUIDE-03 is **FAIL**. Earlier deadline, workspace and socket failures
remain in the evidence. This route differs from the historical
`existing-local/qwen3.8-flash-next`; no same-route recovery or GUI completion is
claimed. The first negative raw trace was overwritten by a throwaway rerun;
its previously inspected derived result, hash and process log remain, and the
missing raw trace is explicitly recorded.

**OBSERVED / OMP probe fidelity correction:** the installed native SDK's fixed
`systemPrompt` option replaces generated blocks, including the normal skill
catalog. The controlled model probe used that option. Its actual body loads,
capability invocations and over-trigger failure remain recorded, but it does not
establish normal generated-prompt behavior. A separate zero-inference preflight
using the native generator plus permission-only appended scope found all three
catalog entries and native skill instructions. Fresh installed model verification
with that corrected native context stopped before primary inference. Three genuine
native description-compression invocations produced **0/3 cache entries**; the
three primary cases remain **NOT_RUN**, with zero primary invocations. HTTP
completion, status and underlying cause were not captured. No retry, seeded cache,
provider substitution or rescoring of the earlier negative failure is used. See
[omp-final10-native-generated.json](validation/2026-10-11/omp-final10-native-generated.json).

**OBSERVED / OMP profile and readiness correction:** the earlier isolated runner
omitted the actual configured `smol` role and selected a priority fallback. The
corrected official read-only settings reader preserves both configured roles.
Native bootstrap returned with all three original description previews. Its
three background description completions returned stop and three phase fetch
deliveries returned HTTP 200; two descriptions were accepted, one exceeded the
native compressed-description limits. Phase fetches are not guaranteed model-only
request counts. The declared driver required all three cache entries and stopped
before primary turns. Actual OMP does not impose that gate: it keeps the original
preview and catches the background warning. These primary cases remain
**NOT_RUN due to driver readiness policy**, not a native fatal bootstrap error.
No cache was seeded and all prior results remain. See
[configured-profile evidence](validation/2026-10-11/omp-native-profile-readonly.json).

**OBSERVED / FINAL10 Codex:** three fresh authenticated native-daemon model sessions
passed explicit full-body load/capability invocation, natural three-guide loading
and capability invocation, and the non-GUI negative with no guide/tool calls.
The native read-only facade's schema exactly matched the installed selection.
An attempted status query correctly refused because no session existed; no GUI
session was started. Ephemeral sessions were unsubscribed. This is distinct from
the current desktop chat's transport and requires no authentication repair. See
[codex-final10-readonly.json](validation/2026-10-11/codex-final10-readonly.json).

**OBSERVED / FINAL10 Hermes native generated prompt:** explicit core-body loading
and capabilities passed. The natural Blender case completed but loaded only core;
it also named a reference path as a separate skill, which the native reader refused.
The batch stopped without retry and the negative case remains **NOT_RUN**. Correct
native linked-file reads return exact packaged bytes; no missing-file or runtime
bug was established. FINAL11 clarifies owning-skill/reference arguments and includes
read-only Blender assessment in discovery. One fresh native batch passed all three
read-only cases: explicit core/reference/capabilities, natural Blender/core/capabilities,
and negative with zero tool requests. Eight actual primary API calls were made;
there was no retry, GUI/session creation or provider substitution. Earlier failures
remain recorded. This is not GUI task verification or a reliability estimate.

**OBSERVED / FINAL11 Codex:** fresh explicit, natural Blender and non-GUI negative
turns all passed through the existing authenticated native daemon. Actual full
guide and linked-file outputs matched the frozen installed bytes; capabilities
matched the selected installed schema. The negative turn requested no tools.
All ephemeral threads were unsubscribed. This is read-only verification, with
GUI `TASK_VERIFIED` still **NOT_RUN**. Both Codex and Hermes FINAL11 guide bytes
are unchanged in FINAL12; their earlier results remain attributed to FINAL11.

**OBSERVED / actual menu context boundary:** three fixed FINAL10 canonical ASSESS
captures retained the full parser result, exact serialized packet and raw answer.
The File popup's Open Recent, Save Copy and External Data evidence was present in
the parser but absent from all eight selected objects. Edit's distinguishing rows
were likewise omitted. Keeping the same ranking while using the existing 40-object
total budget retains all observed popup objects; cached native encoding measured
7850/8011/7883 tokens, below the unchanged 8192 limit. Edit has only 181 tokens of
headroom. The supplied full image remains unchanged, so information loss does not
alone establish the cause of low completion confidence. FINAL11 uses unreserved
target slots for evidence, adds a failing-then-passing long-dropdown regression,
and retains input sets and all guards. Its fixed 15-trial installed model run was
stopped after three actual forward errors in the CUDA allocator/NVML path; all
remaining 12 cases are **NOT_RUN**. The host reports kernel driver 595.84 versus
NVML library 595.99, and memory queries are unavailable. OOM is not established.
No menu quality improvement is claimed from this failing candidate.

**OBSERVED / FINAL12 model packet:** the corrected packet retains the same forty
ranked objects and every non-geometry fact. Explicit shared defaults preserve
known false/true versus unknown values. Only model-facing boxes use outward
integer image-pixel envelopes, with less than one pixel expansion per edge;
original native objects and input geometry are unchanged. Actual pinned encoding
of the three preflight packets is **4269 / 4292 / 4240 tokens**. The independent
visual gate confirmed the same File/Edit/absent states. These encoding and
installation checks alone do not establish live menu accuracy. The subsequent
fixed fifteen-trial installed run returned fifteen real model answers, with
**zero forward errors**, unchanged source and fifteen matching prior screenshots.
File completion remained **0/5** (`NEEDS_REPLAN`); all ten Edit/absent trials
returned `LOW_CONFIDENCE`, with zero false completions and zero native ASSESS
inputs. This does not prove correct wrong-menu/absent classification. Original
menu acceptance remains **FAIL**; no threshold, provider, model or retry changed.
See [actual FINAL12 menu evidence](validation/2026-10-11/blender-menu-context-pixel-final12.json).

**OBSERVED / installed compatibility recovery:** the actual FINAL12 CLI refused
a genuine pinned 0.1.29 executable and all three stale CI guide bindings before
harness execution. Refresh retained the approved immutable older launcher and
refused its incompatible guide contract. Explicit rebinding also preserved the
registration as a conflict. Native managed removal followed by explicit current
launcher enrollment restored matching contracts across all three harnesses,
preserving original user bytes. Four probe-assumption failures are retained;
no product guard was relaxed. This is isolated CLI evidence, not a complete
unsupported-operation or active-session update matrix. See
[compatibility evidence](validation/2026-10-11/installed-compatibility-final12.json).

**OBSERVED / FINAL11 local installation:** first installation and repeat returned
`INSTALLED`/`CURRENT`; all three guides in all three selected harnesses returned
`INSTALLED`/`UNCHANGED`. All 26 HOME file bytes and original CRLF comments were
preserved; 61 installed Python files exactly match the frozen source. Full source
regression: **781 passed, 34 skipped, 41 warnings, 45.03 s**; Ruff and generated
contract checks passed. Archive SHA-256 is
`2d063fbcec0536ef3a63302721c1845a512028bcd2a67d26f80bb9d9b37d9899`.

**OBSERVED / Linux fresh-install crashes:** the actual immutable CI installer was
terminated with `os._exit(87)` at eleven declared staging/activation boundaries.
Every fresh installation resumed, retained original user bytes and launched the
complete native 0.1.30 runtime. The final post-switch crash resumed as `CURRENT`;
earlier boundaries resumed as `INSTALLED`. No installer function was substituted.
The genuine pinned 0.1.29 to immutable CI 0.1.30 update also passed all eleven
declared crash/resume boundaries. Before pointer activation the old native 0.1.29
runtime remained usable; after activation the complete 0.1.30 runtime launched.
Every case retained the previous environment and original user bytes. Native
Windows subsequently passed eleven fresh and eleven genuine update process-exit
boundaries. Each crash returned 87; resume verified the real executable, current
contracts, old runtime and user bytes. Global V2, settings, PATH and existing
fixture bytes remained unchanged; owned server and children stopped. INSTALL-07
passes at this process-termination scope; machine power-loss durability was not
tested. The Windows installer is from immutable CI `26d9252`, not a claim about
FINAL12 model or GUI behavior. See
[Windows crash evidence](validation/2026-10-11/windows-installer-crash-phases-ci26d9252.json) and
[update crash evidence](validation/2026-10-11/linux-installer-update-crash-phases-ci26d9252.json).

**OBSERVED / actual Codex GUI task:** an authenticated native ephemeral Codex
session discovered the installed FINAL12 guides, read all three full bodies and
inspected the actual capability/schema contract. It submitted exactly one bounded
numeric transform through the installed MCP and private loopback service. The
operation returned `SUCCEEDED` after four inputs; the session remained
`NEEDS_REPLAN`, which the model reported without claiming whole-goal completion.
Independent fresh RNA and visual checks confirmed Cube X +2 m, unchanged Y/Z,
rotation, scale, selection, mode, space and unit, with no modal. Owned input,
endpoint, server, Blender and Xvfb cleanup all passed. This establishes
`TASK_VERIFIED` only at the controlled `API_ASSISTED_FIXTURE_ONLY` scope;
production availability, whole-goal ASSESS and workload latency remain open.
See [native Codex task evidence](validation/2026-10-11/codex-final12-native-gui.json).

**OBSERVED / actual Hermes GUI task:** the configured native model read complete
core and Blender guides and current capability/schema results, then submitted one
bounded transform through installed MCP. Fresh independent RNA and pixels verified
the same Cube X +2 m task, unchanged remaining state and complete cleanup. MCP
resources and prompts were disabled; the actual instruction results were present
in the native model conversation before invocation, establishing HARNESS-04 at
this controlled task scope. One request for an unavailable terminal tool was
refused without execution and counts as a model tool-selection error. Task success
does not imply an error-free trajectory or whole-goal ASSESS. See
[native Hermes task](validation/2026-10-11/hermes-final12-native-gui.json) and
[instruction delivery proof](validation/2026-10-11/hermes-final12-resources-disabled.json).

**OBSERVED / independent abort and cleanup:** an actual independent MCP abort
interrupted the first native transform input, leaving a positively identified
owned modal. Idle shutdown correctly refused. The fixture's normal deadline then
issued one same-session typed cancel; fresh RNA confirmed the original transforms,
selection, mode, space and units, with no modal or owned inputs. All 28 resource
and state checks passed. The earlier short setup expired with zero operation,
abort or model calls and remains recorded as NOT_RUN. See
[pending modal cleanup](validation/2026-10-11/blender-final12-pending-modal-cleanup.json).

**OBSERVED / original fixture regression:** the unchanged canonical 22-case
installed Blender run after adding serve mode remains **21/22 FAIL** overall.
`menu_edit` expected `WRONG_MENU`, but actual evidence was `ABSENT`; the runtime
honestly returned that read-only assessment with zero inputs. The cause of the
missing popup is not established. The other 21 cases passed. Neither the passing
harness transforms nor the instrumented private diagnostic replaces this failure.
See [original regression](validation/2026-10-11/blender-operations-final12-after-serve.json).

**OBSERVED / immutable f440de1 CI install:** all fifteen platform/Python builds
and assembly succeeded. Every downloaded archive hash matched the immutable
manifest. Actual isolated Linux installation/repeat returned `INSTALLED`/`CURRENT`;
all three guides in three harnesses were installed and retained, 61 packaged
Python files matched source and 26 HOME files retained their bytes. Deployment
was skipped by the existing branch policy. Native harness execution on this new
CI archive is separate from the differently hashed local FINAL12 task evidence.
See [immutable CI installation](validation/2026-10-11/cif440de1-linux-install.json).

**OBSERVED / OMP probe corrections:** consumer-native batches reached actual core
body reads and current capabilities but stopped at the predeclared eight primary
calls without a final answer. Earlier private probes incorrectly rejected native
read selectors and an advertised capability argument. Their use of the unsupported
`CLEF_USE_HOME` variable also limits prior status isolation claims. Those records
remain partial and are not attributed as product or native-model failures.
Official selector equivalence and native MCP schema/state-directory checks are
recorded separately; they alone do not establish model task success. The subsequent
schema-faithful batch stopped on its first native primary invocation with
`workspace_violation`, before any parsed tool call. The precise error origin and
rejected arguments were not observed; no retry or later case ran. See
[stopped native batch](validation/2026-10-11/omp-native-schemafaithful-stopped.json).

The bounded fixture source and four localized document updates passed the full
regression (**783 passed, 34 skipped, 41 warnings, 45.35 s**), scoped Ruff and
generated contract/example checks. This does not replace the actual GUI evidence
or turn skipped acceptance work into a pass.

## Runtime identity correction and remaining checks

**OBSERVED / fresh FINAL15 native harness tasks:** Codex and Hermes each loaded
the changed installed instructions, checked actual capabilities/schemas and
invoked one Cube X +2 m operation. Each produced four acknowledged native inputs,
typed `SUCCEEDED` and session `NEEDS_REPLAN`. Fresh independent RNA verified nine
effect/preservation conditions; root viewed both result screens and shut down the
owned fixtures. Complete installed guide bytes were present in actual tool output,
including the final LF. Hermes also delivered the three complete reference files
with MCP resources/prompts disabled. Its attempted unavailable `execute_code`
tool was refused without execution and is retained as one tool-selection error,
separate from the earlier FINAL12 terminal error. These are API-assisted operation
tasks, not whole-goal ASSESS, a shipped production provider or a latency result.
See [Codex FINAL15](validation/2026-10-11/codex-final15-native-gui.json),
[exact guide-byte audit](validation/2026-10-11/codex-final15-guide-bytes-audit.json)
and [Hermes FINAL15](validation/2026-10-11/hermes-final15-native-gui.json).

**OBSERVED / actual installed regression:** a genuine immutable baseline .29 client
request replaced an idle FINAL12 .30 service with .29. FINAL15 binds control
requests to the runtime version, protocol and actual schema digest. Replaying the
same old client preserved the .30 PID, start time and endpoint bytes. All 36 real
HTTP identity-mismatch control requests returned 409 and reload guidance; all four
invalid/unsupported run bodies returned 400 and current capability guidance. The
immutable old client still displays its original generic refusal; this is distinct
from the actionable server response and current client diagnostics. Matching
capability discovery and idle shutdown passed. No session or model ran in this
transport check. See [original defect](validation/2026-10-11/stale-client-downgrade-final12.json)
and [installed correction](validation/2026-10-11/runtime-binding-final15-native.json).
An actual active-session update subsequently passed in one disposable native Tk
scene using the unchanged default factory and genuine installed .29 archive.
The .29 session was RUNNING/busy before and after installing FINAL15; 48 interval
samples preserved its PID/start time, endpoint and session. The current client
refused with matching-old-executable/reload guidance. Matching .29 abort was
followed by separately observed `busy=False`; .30 then reloaded the exact protocol
and schema and honestly blocked a menu contract with provider `NONE`. All owned
resources exited. The immediately-before snapshot had zero workers; the active
gate, all interval samples and after snapshot had one. Sampling does not prove
unsampled continuous state, and the XRecord startup acknowledgement was not
observed. This is lifecycle evidence, not an OS-effect task or production-provider
result. See [actual active update](validation/2026-10-11/active-gui-update-final15-native.json).

Its first actual attempt had a status observer missing the desktop-scope header:
the service correctly returned 403, but the driver failed to stop at preflight.
One real local ASSESS ended LOW_CONFIDENCE at the unchanged 0.9 threshold; no
installer update, abort or reload ran. Native input was zero, pixels/input maps
were unchanged and owned cleanup passed. This observer defect is retained as
NOT_RUN for that attempt, not a product lifecycle or model-task failure. A second
attempt used only the service leader thread's children and missed actual workers
launched by the execution thread; no update ran. A real native thread/subprocess
preflight then verified the all-thread union against an independent PPID oracle.
Both original observer failures remain retained. See
[stopped observer attempt](validation/2026-10-11/active-gui-update-final15-observer-stopped.json).

**OBSERVED / historical immutable CI6cdf182 Linux:** the actual CI archive installed
as `INSTALLED`, then `CURRENT`. All 46 Python files and 15 packaged resources
matched that commit; three guides across three harnesses enrolled idempotently,
preserving user bytes, comments and disabled settings. Native read-only MCP
schemas and status were checked separately from the full product schema. A
genuine .29 client could not replace the idle .30 service; matching shutdown
removed the endpoint and reaped the service. See the [aggregate evidence and three
preserved driver errors](validation/2026-10-11/ci6cdf182-linux-install.json).
The first stopped record's original "12 tools" wording is an erroneous driver
assertion: the verified full catalog has six tools and the read-only facade two.
This covers CI source `6cdf182`, before the later guide-manifest ordering
correction. Native harness loading, model/GUI/input tasks, active-session update
on this archive and performance gates were not run. Deployment remained skipped
by branch policy.

**OBSERVED / exact-source CI Windows installation:** CI `38143663561` at `6cdf182`
passed 15 platform/Python builds and assembly; the existing branch policy skipped
deployment. Its actual Windows ZIP installed and repeated, matched all 61 installed
files to the immutable wheel, enrolled three guides across three selected profiles
and passed native Codex project discovery. All six preservation/cleanup checks
passed, including global V2 and prior customized bytes. Sixty wheel files match
Git exactly; the generated manifest has equal parsed values but platform-dependent
key ordering. That exception is explicit. No model, GUI, input or service task ran.
See [CI Windows installation](validation/2026-10-11/windows-ci6cdf182-install.json).

**OBSERVED / manifest ordering correction:** native Windows sorted `Path` objects
with its case-insensitive ordering, placing `references/` before `SKILL.md`.
The exact manifest generator in a separate private module reproduced the packaged
digest. Sorting by relative POSIX spelling instead produced the existing Git/Linux
digest, with all parsed values and guide files unchanged. The canonical correction
has the exact tested source hash; 66 scoped tests and the real generated-contract
check pass. This corrects reproducibility, not a previously failed schema contract.
A new immutable corrected archive has not yet been exercised. See
[native before/after](validation/2026-10-11/guide-manifest-native-ordering.json).

**OBSERVED / earlier native Windows installation:** immutable f440de1 installed and
repeated successfully, matched 61 package files (46 Python modules, 15 resources),
enrolled three guides for three profiles and passed native Codex project discovery.
Global V2, configuration, PATH and prior customized bytes survived. Earlier
foreground-restoration and isolated user-discovery failures remain retained;
load/invoke/model tasks and FINAL15 Windows transport are not established by this
archive. See [Windows f440de1](validation/2026-10-11/windows-cif440de1-install.json).

**OBSERVED / actual native IME:** the installed f440de1 input layer observed real
composition start, positive preedit bytes, committed result and composition end.
Literal insertion during active composition refused without changing the native
preedit/widget or input count. After commit, Ctrl+A selected the actual UTF16 text;
exact Unicode insertion matched 12 bytes without clipboard mutation. Independent
cancellation released a held Shift without the main worker calling release.
All six cases and IMC/layout/foreground/resource/global V2 preservation passed.
The original alphanumeric-mode attempt remains NOT_RUN. The corrected fixture
supplied truthfully native-observed context; automatic IMM/TSF discovery, canonical
service/model/harness tasks and latency are not proved. INPUT-02 now passes its
exact input-separation condition. See [native IME proof](validation/2026-10-11/windows-ime-native-mode-f440de1.json)
and [original stopped attempt](validation/2026-10-11/windows-ime-alphanumeric-stopped.json).

**OBSERVED / OMP task attempt:** actual managed-project enrollment and native
discovery passed. The subsequent configured OMP provider returned HTTP 401 before
any guide load or tool call, so its GUI task remains NOT_RUN. Independent native
scene/pixel readback and fixture cleanup passed. This failure is separate from the
working Codex desktop session and its authentication; no authentication changes
were requested or made for this attempt. See [stopped OMP task](validation/2026-10-11/omp-final12-native-gui-stopped.json).

**OBSERVED / menu diagnosis:** passive XRecord confirmed that the original Edit
click was delivered while no prior popup remained, but the popup did not open.
Application activation timing remains an inference. A separate offline structural
menu witness found a false positive on an ordinary document panel; semantic
promotion was rejected and all state facts remain UNKNOWN. No confidence threshold,
model, production provider or original failing workload was changed. See
[passive diagnosis](validation/2026-10-11/blender-final12-menu-setup-diagnostic.json)
and [counterexample](validation/2026-10-11/blender-pixel-menu-witness-counterexample.json).

PASS labels in ACCEPTANCE.yaml apply only to each exact condition at its recorded
scope. Partial results retain `NOT_RUN` and explicit evidence; they never inherit
native, harness, installed or public-release status from another evidence level.

| Milestone | Status | Remaining condition |
| --- | --- | --- |
| M0 baseline | IN_PROGRESS | Software/attachment and original live menu baseline pinned; remaining full workflow matrix remains. |
| M1 discovery/integration | IN_PROGRESS | Codex and Hermes actual native private fixture GUI tasks pass; corrected OMP native consumer turns remain partial; OMP and production GUI coverage remain. |
| M2 typed input | IN_PROGRESS | Linux and Windows native input/actual IME separation observed; historical Windows restoration failure and canonical automatic IME discovery remain. |
| M3 state/operations | IN_PROGRESS | FINAL10 canonical API-assisted fixture21/22 and private instrumented22/22; original model menu replay FAIL and shipped production provider remain open. |
| M4 reaction/quality | IN_PROGRESS | Bounded native profile measured; complete task workload/baseline/accuracy and release gates remain NOT_RUN. |
| M5 harness/install/release | IN_PROGRESS | FINAL24 local installation and native Hermes boundaries, native14 discovery and bb971ef CI/Windows flow-config installation pass at their recorded scope; OMP, production tasks and public release remain open. |

Reici matched-view production edits, independent visual review, Warudo/VRChat
verification and public artifact publication/download/hash/fresh public install
remain **NOT_RUN**. No screenshots, raw harness traces, authentication material,
restricted assets or production scenes are copied into repository evidence.
