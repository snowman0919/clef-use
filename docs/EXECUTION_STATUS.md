# Reactive runtime execution status

Date: 2026-10-11. Baseline: `b3f0b23309a7c7ea6a943e0c14e0ae51034552cd`.
Initial evidence snapshot HEAD: `1c52c80877d94116071107c67454457bbd2da46c`.
Latest implementation HEAD: `2371eb1` on `codex/reactive-agent-contracts`
(six local implementation commits).
This is partial execution evidence, not specification completion or release approval.
Machine-readable, sanitized evidence and artifact hashes: [summary.json](validation/2026-10-11/summary.json).
Latest installed harness/profile correction: [final6.json](validation/2026-10-11/final6.json).
Final input-candidate measurement: [reaction-final5.json](validation/2026-10-11/reaction-final5.json).
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
This failure is not hidden by passing input cases. Managed final-version Windows
installation/lifecycle, harness task E2E and active IME composition remain **NOT_RUN**;
Windows overall and release are not PASS.

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

These are pre-FINAL4 `0.1.30` guide-bundle observations. The FINAL4 Blender reference
changed afterward; prior stages do not certify a fresh FINAL4 guide reload.

| Harness | INSTALLED | DISCOVERED | LOADED | INVOKED (read-only) | GUI TASK_VERIFIED |
| --- | --- | --- | --- | --- | --- |
| Codex | PASS | PASS (native catalog) | NOT_RUN | NOT_RUN | NOT_RUN |
| Hermes | PASS | PASS | PASS (explicit/natural) | PASS | NOT_RUN |
| OMP | PASS | PASS | PASS (SDK and achieved model stage) | PASS (achieved stage) | NOT_RUN |

**OBSERVED:** Hermes natural trigger loads the Blender guide and calls capabilities;
explicit invocation loads core/diagnostics; a negative non-GUI task loads/invokes
neither. A separate `codex-cli 0.160.1` process in the isolated installation fixture
stopped at provider HTTP 401 `invalid_api_key` using local API-key authentication;
no credential values are retained. This does not establish an authentication
failure in the active Codex desktop chat or that the chat uses the same transport.
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
50-opportunity Unicode Tk editor profile reports 50 correct, p95 **100.577 ms**,
goodput100 **0.78**, 11 misses and zero critical errors. Cold/all/session statistics,
source hashes, scope/exclusions and artifact hashes are retained in the JSON summary.
**MEASURED / FINAL5:** the same predeclared workload completes with 1,005 correct
opportunities per variant. Warm typed p50/p95/p99 are **40.268/80.447/80.509 ms**,
goodput100 **0.991**, 9 misses and useful throughput **14.665/s**. Warm pinned-b3
p95 is **20.268 ms**, goodput100 **1.000** and throughput **4.523/s**. Typed event
latency is slower than this native baseline despite higher throughput. The separate
50-opportunity editor profile has p95 **100.558 ms**, goodput100 **0.82**, and 9 misses.
It does not pass the 100 ms p95 target. All reported critical counts are zero.

**Metric correction:** historical raw native reports called deadline success ratio
`fast_coverage`. Under KODEX that ratio is `goodput_100`; fast-path eligibility
was not recorded and its coverage is **NOT_MEASURED**. Curated evidence corrects
the labels without changing timestamps or attempts. The runner now keeps these
metrics separate and preserves unknown eligibility. No eligibility coverage gate
is certified by these narrow input measurements.

**NOT_RUN:** the production/model/Blender/harness task performance gate. The pinned
baseline is only the `b3f0b233` DesktopAction implementation with current supporting
libraries, not the entire old runtime/model stack. No overall 100 ms result or
controlled comparative speedup is claimed. The independent editor profile misses
the stated thresholds; all original numerical gates remain unchanged.

## Remaining acceptance and milestones

PASS labels in ACCEPTANCE.yaml apply only to each exact condition at its recorded
scope. Partial results retain `NOT_RUN` and explicit evidence; they never inherit
native, harness, installed or public-release status from another evidence level.

| Milestone | Status | Remaining condition |
| --- | --- | --- |
| M0 baseline | IN_PROGRESS | Software/attachment provenance pinned; complete original live task/model baseline remains. |
| M1 discovery/integration | IN_PROGRESS | Portable bundle/install and read-only harness stages observed; Codex auth, final-bundle reload and cross-harness trigger coverage remain. |
| M2 typed input | IN_PROGRESS | Linux checks and Windows component input cases observed; Windows overall FAIL/restoration and active IME composition remain. |
| M3 state/operations | IN_PROGRESS | Installed API-assisted Blender fixture passes; shipped production provider and canonical original task replay remain. |
| M4 reaction/quality | IN_PROGRESS | Bounded native profile measured; complete task workload/baseline/accuracy and release gates remain NOT_RUN. |
| M5 harness/install/release | IN_PROGRESS | Local candidate/lifecycle checks observed; harness GUI tasks, full Windows matrix and public release verification remain NOT_RUN. |

Reici matched-view production edits, independent visual review, Warudo/VRChat
verification and public artifact publication/download/hash/fresh public install
remain **NOT_RUN**. No screenshots, raw harness traces, authentication material,
restricted assets or production scenes are copied into repository evidence.
