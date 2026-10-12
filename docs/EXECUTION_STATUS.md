# Reactive runtime execution status

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

The overall stop was not justified by the recorded failures. Unimplemented
production observation and failed model decisions are engineering work, not proof
of an unavailable environment. The following boundaries apply to individual checks.

| Check | Observed result or missing prerequisite | Next action and ownership |
| --- | --- | --- |
| Production operations | The optional Linux X11 public-RNA producer is now bound through `blender_state_socket`. Actual UI-thread selection, mode, properties and viewport observations were verified with native PID/peer/window binding. Popup, editing, IME, busy and effective keymap facts remain UNKNOWN; all six operation guards remain in force. | Continue clef-use observation/input improvements without inventing absence facts. The partial producer does not close general operation support; whole-task verification belongs to the other session. |
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
