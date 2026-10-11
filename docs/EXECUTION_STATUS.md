# Reactive runtime execution status

Date: 2026-10-11. Baseline: `b3f0b23309a7c7ea6a943e0c14e0ae51034552cd`.
Initial evidence snapshot HEAD: `1c52c80877d94116071107c67454457bbd2da46c`.
Latest committed implementation: `f4ec498` on `codex/reactive-agent-contracts`;
the bounded Blender fixture remains unchanged from `a7a46b5`.
Published evidence HEAD before the following measurements: `8e1eedf`.
Latest local candidate: FINAL15, including the runtime identity correction;
installed module hashes and its **792 passed / 34 skipped** source regression are
recorded in [final15-install.json](validation/2026-10-11/final15-install.json).
Earlier FINAL12 native tasks retain their original candidate and guide hashes.
This is partial execution evidence, not specification completion or release approval.
Current acceptance evidence is **33 PASS / 3 FAIL / 8 NOT_RUN**; the newly executed
general GUI tasks failed rather than remaining unexecuted.
Machine-readable, sanitized evidence and artifact hashes: [summary.json](validation/2026-10-11/summary.json).
Latest installed input/profile candidate: [final10.json](validation/2026-10-11/final10.json).
Latest input-candidate measurement: [reaction-final10.json](validation/2026-10-11/reaction-final10.json).
Per-scenario status and remaining scope: [ACCEPTANCE.yaml](../ACCEPTANCE.yaml).

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
| M5 harness/install/release | IN_PROGRESS | Immutable6cdf182 CI/Linux/Windows install, Windows22process-exit cases, FINAL15 Codex/Hermes private fixture tasks and active GUI update pass at their recorded scope; OMP, production tasks and public release verification remain open. |

Reici matched-view production edits, independent visual review, Warudo/VRChat
verification and public artifact publication/download/hash/fresh public install
remain **NOT_RUN**. No screenshots, raw harness traces, authentication material,
restricted assets or production scenes are copied into repository evidence.
