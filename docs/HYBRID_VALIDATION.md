# Hybrid validation evidence

This records execution on 2026-10-07. Frozen-head native diagnostics now pass
all six original Blender tasks and all six tasks on a previously untouched v12
snapshot. Those diagnostics omit CLEF and OmniParser. The requested full-model
resident sixty-trial comparison stopped at sixteen completed rows on its
host-memory guard. The subsequent exclusive comparison was stopped after one
completed row to correct foreground-boundary defects found in source review.
The post-fix sixty-trial result remains **not yet established**.

## Latest full-model comparison

**OBSERVED:** the frozen-head, CPU bfloat16/SDPA resident comparison completed
sixteen of sixty planned trials before a host-memory guard abort. All three
real model workers started, and thirty-two actual CLEF replies were archived.
The preserved structured baseline confirmed zero native task goals in eight
trials; hybrid confirmed seven in eight. Neither variant returned runtime
`COMPLETED`. Hybrid statuses were seven `NEEDS_REPLAN` and one `BLOCKED`.
The latter stopped a repeated viewport click whose small selection change
was not accepted as a verified content change. Native goal success and model
completion are separate outcomes.

The splash trial dismissed the modal but left `Layout` active. CLEF proposed
completion with goal score 0.8164 and condition score 0.8648, below the unchanged
0.9 completion gate. The runtime correctly rejected that proposal and did not
manufacture another click. Splitting the compound success condition into
observable splash-absence and active-Modeling predicates was tested as a
contract clarification and rejected. Four actual saved-image CLEF calls all
proposed `COMPLETED`; incomplete and successful frames had goal scores below
0.9. The clarified incomplete frame falsely scored active Modeling at 0.908.
No changed conditions or native retry were adopted. Exact requests and cleanup
are in `/tmp/clef-splash-condition-diagnosis-162/review-summary.json`.

**OBSERVED input policy, cause INFERRED:** the canonical CLEF worker restricts
full screenshots to `max_pixels=512*512`. A separate fixed experiment compares
512 squared and 1024 squared pixel budgets on the same original compound
contracts and full images. Four actual calls rejected that hypothesis: both
incomplete-frame budgets proposed completion, and successful-frame goal and
condition scores remained below 0.9. Actual processed dimensions were 608 x 416
and 1216 x 832, with 3,872-5,210 untruncated input tokens. No higher-resolution
policy was adopted. The current original-task retry uses the intended external
System-2 planner handoff after fresh observation, with the same completion gate.
Results are in `/tmp/clef-splash-image-budget-diagnosis-163/review-summary.json`.

**OBSERVED, original-task retry:** actual OmniParser, CLEF and
SigLIP2 first executed the unchanged compound contract in a fresh private v13
Blender fixture. One native click dismissed the splash; native readback and
the parent-reviewed after screenshot showed `Layout` still active. CLEF again
proposed completion, but goal 0.8309 and condition 0.8706 failed the 0.9 gate,
yielding `NEEDS_REPLAN/COMPLETION_UNVERIFIED`. All model workers were closed and
reaped before planner review. The parent retained the original global goal and
authorized one remaining subgoal, `Switch to Modeling workspace`, without
resetting the fixture or changing the original visual query, head or thresholds.
The second contract delivered one canonical click and changed native
`Layout -> Modeling`. Independent parent review of the final screenshot
confirmed Modeling active and splash absent. The original global task was
achieved with two contracts, one planner handoff and two completed native clicks.
Stage two still returned `NEEDS_REPLAN`: goal 0.8840 and condition 0.8634 did
not meet 0.9. This is native goal success, not runtime `COMPLETED`. All four
OmniParser calls, four CLEF calls and two visual requests were real. Owned
workers, scopes, display and endpoint were cleaned; watched source, head and
manifest hashes were unchanged. Evidence is in
`/tmp/clef-v13-system2-task-164/review-summary.json`. This bounded diagnostic
is separate from the fixed-contract sixty-trial comparison.

**MEASURED:** completed baseline runtime ranged from 131.541 to 353.873 seconds,
and hybrid from 147.605 to 380.050 seconds. These partial, uneven case counts
mix cold and resident inference and do not establish a speed comparison.
The guard recorded `MemAvailable=1,167,085,568` bytes at 12:20:38 UTC; owned
termination began 158.501 seconds later. The cause of that delay is not
established, and prompt guard response was not demonstrated. Owned supervisor
peak was 17,946,451,968 bytes, with zero owned OOM events or swap usage.
All owned processes, scopes, display and endpoint were subsequently removed,
and every watched source hash matched.

Forty-four planned trials remain `NOT_RUN`, including an interrupted viewport
trial with a delivered click and a native Face-selection journal but no final
trial row. Its initialized `ERROR` placeholder is not an observed model error,
and it is excluded from completed denominators. Partial artifacts are retained
in `/tmp/clef-hybrid-frozen-overview-bf16-sdpa-resident-benchmark/` with the
separate `...-partial-evidence-summary.json`. The next exclusive comparison
completed one baseline trial, then was intentionally stopped for source fixes
under `/tmp/clef-hybrid-frozen-overview-bf16-sdpa-exclusive-benchmark/`, with
the same exclusive-worker policy for both variants, all real models and reload
latency included. Its baseline returned `LOW_CONFIDENCE`, no input, native
goal false, runtime 355.500 seconds. Fifty-nine trials remain `NOT_RUN`.
Owned cleanup and original source hashes were verified before edits. This was
not a resource abort. Neither partial comparison nor the System-2 diagnostic
will be merged into the fresh post-fix comparison.

**OBSERVED, foreground correction:** actual two-window X11 reproduction found
that changing input focus A to B left both old capture identities/bounds unknown.
Pixels and frame references were identical and `same_context` falsely passed.
Capture now resolves the native focus to its top-level window and bounds, and
checks context again after capture. Identical A/B pixels now produce different
references; same-window repeat passes, resize changes bounds, and PointerRoot
reports unknown identity. A deterministic model-free canonical runtime focus
switch returned `NEEDS_REPLAN`, zero steps and zero actual Tk native click events.
This is execution-boundary proof, not three-model grounding evaluation.
Redraw retries now require established identity and bounds. Six permanent
VISUAL/CANVAS regressions reject missing or partial metadata before input.
Windows double-click now retains its original target: the modeled API previously
delivered presses to windows `[100,101]`; it now refuses the second press and
releases the first button. All 27 Windows input tests passed; real Windows
hardware was not available. Actual X11 evidence is retained under
`/tmp/clef-linux-focus-{before-166-v2,after-166}/`.

## Executed paths

- **OBSERVED:** the canonical CLI structured self-test returned `COMPLETED`
  after two actions. This is a deterministic fixture, not a desktop ML result.
- **OBSERVED:** pinned, frozen SigLIP2 inference produced original-screenshot
  points through overlapping native tiles and a fine ROI. An initial zero-shot
  workspace query localized the wrong viewport point and was rejected.
- **OBSERVED:** a separately trained rank-16 head, real visual worker, router,
  native input and fresh-frame waiter opened Blender Material Properties in
  three of five trials. Two trials refused input because their screenshot
  reference changed during inference. Blender `OBJECT -> MATERIAL` readback
  and saved before/after screenshots establish the three successful clicks.
  CLEF was omitted in this component diagnostic; it is not full-loop completion.
- **OBSERVED:** real CLEF subsequently loaded through the existing CPU NF4
  backend and assessed one of those saved actual visual candidates. It returned
  `ACT`, action confidence `1.0`, mode confidence `0.8618`, safety probability
  `0.0152`. No desktop input occurred during that feasibility check.
- **OBSERVED:** the corrected isolated Blender fixture passed twelve resets
  across six cases. Screenshots confirm a visible splash and the mutable
  Principled Thin Wall checkbox. State readback alone had missed a stale panel;
  Properties now requests redraw. Native GUI search prepares the splash because
  invoking it from the fixture timer did not display the modal.
- **OBSERVED:** deterministic regressions reproduce and fix disappearing-target
  completion, empty-candidate completion assessment blocking a second action,
  drag becoming a native click, wait-region loss, collapsed drag endpoints, and
  sparse-region routing on a dense screen. Raster canvas tests exercise an actual
  painted drag segment and button release, without claiming Blender grounding.

## Measurements and retained failures

Environment: Linux x86-64, Ryzen 7 9700X, RTX 3080 10 GiB, four CPU inference
threads. CLEF uses the pinned `clef-flash` revision; visual inference uses pinned
`google/siglip2-base-patch16-512`. ML environments contain Torch 2.11 and
Transformers 5.10.2 for CLEF/visual, and Transformers 4.46.3 for OmniParser.
The CUDA worker belonging to another session was preserved.

**MEASURED:** an early paired benchmark ran six cases, five alternating trials
per variant, at 1280 x 900. Raw candidate counts were 204-242. Both variants
recorded zero task successes out of thirty. Baseline CLEF failed with
`OUT_OF_MEMORY`; hybrid returned CLEF errors or `NEEDS_REPLAN` on low grounding
confidence. No input was delivered. These are retained failures, not proof of
hybrid accuracy or speed. Later inspection invalidated the splash precondition
and corrected contradictory drag direction wording in that early run.

| Early failed-run metric | Baseline | Hybrid |
| --- | ---: | ---: |
| Task successes | 0/30 | 0/30 |
| Planner escalation, `NEEDS_REPLAN` only | 0/30 | 25/30 |
| End-to-end median | 6.719 s | 10.290 s |
| End-to-end p95, nearest rank | 94.501 s | 21.918 s |

The original report counted every unsuccessful status as an escalation. The
table above is recomputed from its retained rows: thirty baseline `ERROR`s and
twenty-five hybrid `NEEDS_REPLAN`s plus five `ERROR`s. An inference failure is
not a planner escalation. The runner now keeps these counts separate.

**MEASURED:** isolated real CPU CLEF loading took 61.787 s and its real decision
took 34.778 s. A full-runtime CPU pilot then failed its 120 s cold OmniParser
request timeout before any CLEF decision. The original task was retried with
the established 300 s timeout and four-step budget. Concurrent host memory fell
to about 4.7 GiB available with almost no free swap, so only the owned pilot was
stopped before CLEF loading. Its guarded scope recorded no OOM event. The
10 GB headroom guard was a conservative execution choice, **not a measured
minimum CLEF memory requirement**. A successful full CPU benchmark is NOT_RUN.

**OBSERVED:** a later canonical 60-trial CPU comparison was launched under an
18 GiB supervisor cap and a separate 3 GiB Blender cap, both without swap.
It reached simultaneous real OmniParser and CLEF workers, then its guard stopped
only owned processes when host `MemAvailable` fell to 1.894 GiB. The owned
supervisor peaked at 10,674,565,120 bytes; neither scope recorded OOM. No trial
row was persisted, so all sixty remain NOT_RUN (an in-flight trial had started).
This resource abort is not an action failure or a measured minimum requirement.
An explicit CPU bfloat16 setting has been added with float32 retained by default.
Tiny real Torch forwards passed finite-output and storage checks.
**OBSERVED:** a subsequent canonical CPU CLEF bfloat16 load and decision succeeded;
the worker reported `compute_dtype=bfloat16` and 248 NF4 modules. All raw numeric
answers were finite, with `ACT` on the supplied saved visual candidate.
**MEASURED:** load 75.501 s, decision 36.306 s, owned scope peak 8.831 GiB,
minimum host available memory 4.761 GiB. No resource guard or OOM event occurred;
owned processes exited and the scope was empty. A concurrent visual-head audit
ran, and the earlier float32 request was not retained exactly, so these numbers
do not establish a dtype speedup or decision parity. No GUI input occurred.
The full paired benchmark remains pending.

**OBSERVED:** the Gaussian bfloat16 paired retry also stopped during the first
baseline CLEF stage when host available memory reached 1.803 GiB. The parser
was still resident; owned supervisor peak was 11,797,491,712 bytes. It recorded
no OOM event, no persisted CLEF readiness or decision, and zero completed trials
(all sixty NOT_RUN). The model-free label fixture had already exited about
seventy seconds before this abort. The guard cleaned only owned processes.
Parser-only scope residency immediately before CLEF startup was 2,955,350,016
bytes. A subsequent benchmark option keeps only the currently requested model
resident, equally for both variants; consecutive requests to that model remain
warm. Its complete-model resource fit is not yet observed. Stage changes incur
cold reloads, so those results cannot establish normal resident-worker latency.

**OBSERVED:** the subsequent exclusive-worker 60-trial attempt stopped at
1.785 GiB host available memory, with an owned supervisor peak of
17,267,126,272 bytes. OmniParser had already exited; CLEF was the sole model
worker. No OOM event occurred. The atomic journal retained the first baseline
Properties trial with no input attempts, zero completed rows and sixty NOT_RUN
trials. Only owned processes were stopped and both scopes became empty.
These two interrupted attempts did not persist startup responses early enough
to distinguish CLEF loading from its first inference. Neither establishes the
phase or cause of its memory peak. The runner now saves actual startup responses
before inference and archives exact CLEF requests, images and replies with
trial attribution. Retained readiness after closing a worker is historical
startup evidence, not evidence that a later trial invoked that model.

**OBSERVED:** a separate Properties pilot archived the exact first baseline
request (100 objects, 48 candidates, 26,107 state bytes). Its CPU bfloat16 CLEF
startup response was saved before inference. About 18.45 seconds later the
resource floor interrupted only that owned model worker; runtime persisted
`ERROR` without input and started the already planned hybrid trial. Supervisor
peak was 16,367,333,376 bytes, with no OOM event. The supervisor then received
SIGTERM and stopped the pilot during hybrid parsing. Its original sender could not be
established from the available journals. One trial completed, nine remain
NOT_RUN; this is not a completed pair or benchmark.

**OBSERVED:** the CPU worker had explicitly selected eager attention. The
installed Qwen provider materializes quadratic score matrices and a float32
softmax. A bounded native-provider probe on bfloat16 grouped-query attention
at lengths 128 and 256 dispatched CPU flash through SDPA, with maximum absolute
error 0.009391 against its float32 eager reference (predeclared tolerance 0.02).
Actual tiny Qwen text-model regressions reproduced a 4,194,304-byte eager
operator allocation at length 512. After selecting CPU SDPA, float32 and
bfloat16 retained the reference outputs and causal prefix invariance while
remaining below the 1,048,576-byte per-operator bound. These are tiny-model
numerical/allocation checks, not full CLEF memory or latency measurements.

**OBSERVED:** exact archived baseline replay subsequently completed through the
canonical CPU bfloat16/NF4 worker, reporting loaded text attention `sdpa` and
248 quantized modules. Original PNG bytes, 100 objects, 48 candidates and
26,107 state bytes were restored. All numeric answers were finite; CLEF chose
allowed candidate `a36` (Shading icon), action confidence 0.2319, ACT probability
0.4092 and replan probability 0.4187. This is the original Properties goal's
static pre-action request, not successful native input.
**MEASURED:** startup 57.033 s, completed request 131.383 s, 8,192 input tokens,
owned scope peak 15.930 GiB and minimum host available memory 9.520 GiB. No
guard trip or OOM occurred, and the owned worker/supervisor exited with an
empty scope. Background pressure differs from the interrupted eager pilot;
this single replay does not establish reduced full-model peak memory or a
speedup. It establishes that the exact previously interrupted request can
complete on the tested SDPA path. The full paired comparison remains pending.

**MEASURED:** six paired real-image feature-cache trials retained identical
points and confidence within `1e-6`. Cold median inference was 6.611 s; warm
median was 0.500 s. The cold maximum was 13.694 s and warm maximum 1.209 s.
This measures repeated grounding on the same image, not end-to-end GUI latency.

Initial training used different v10 screenshots at 1600 x 1000; held-out screenshots
shifted an editor boundary 200 pixels. Final v13 benchmark images were excluded
from training and validation. Three initial seeds each produced three points
inside held-out annotations. An extended head produced six of seven intended
default points inside annotations, but accepted none at the default confidence
gate. Bbox containment is weaker than independently verified object selection.

**OBSERVED:** replacing its trained temperature with the pretrained global
SigLIP scale left all 34 paired points unchanged, but accepted an incorrect
three-pixel divider and two negative controls. Blank-image Thin Wall confidence
became `0.805236`; an absent banana query became `0.816663`. That readout change
was rejected. Confidence sharpness does not establish semantic target presence.

The v13 scene is a reused development/regression scene: its failures informed
subsequent changes. Excluding its images from training does not make a later
result on that scene a blind evaluation.

## Acceptance status

The first V2 dense head was trained with frozen SigLIP2 encoders on independent
v10 screenshots, including full 1280 x 900 Blender captures. Its post-load audit
ran 105 actual grounding passes. **OBSERVED:** all 69 absent-target passes were
rejected at the unchanged 0.55 gate. Six positive passes were accepted, but three
points fell outside their annotated boxes. Default full-frame points hit four
of seven boxes. Fine offset precision and serving confidence remained unresolved.

**OBSERVED:** the original v13 six-case component retry sent zero inputs.
Properties icon and Thin Wall targets were accepted at confidence 0.7673 and
0.7229, then rejected by the exact screenshot-reference check. Saved pixel
comparisons showed viewport redraw and a small material-list redraw. Outliner,
viewport, divider and Modeling-tab targets remained below threshold. CLEF and
OmniParser were omitted in this diagnostic; these results are not full-runtime
successes. A correct predicted point alone did not pass action verification.

The runtime now retries generated stale visual candidates by parsing and
grounding the fresh frame, with an independent bounded retry counter and the
existing step budget. It preserves exact pointer binding and rejects supplied
planner coordinates or foreground changes. Deterministic tests execute stale
recapture, budget exhaustion, counter reset and foreground-change rejection.
The current head trains supplied regions and half-patch crop translations.
Scoped negative annotations apply only within their region. Its 156-pass
post-load point audit rejected all 117 absent-target passes at the default gate;
their maximum confidence was 0.251026. The thirteen default positive contexts
accepted five correct boxes at 0.55, or nine boxes at 0.35 with eight hits.
These correlated contexts are development evidence, not independent calibration.
The head SHA-256 is
`f084635e4aca4a1eca5cadbd62ff0b2421af35a891752b55cf6339eb7dd5d7d0`.

**OBSERVED:** the third real v13 component retry completed all six cases and
established two task successes: Material Properties and Outliner Face selection.
Each used fresh grounding after a changed screenshot reference. Viewport and
divider abstained. Thin Wall produced an accepted point, but readiness blocked
input because a small material thumbnail permanently changed. The splash click
dismissed the popup without switching workspace, so that composite task failed.
The isolated Blender process peaked at 2,222,219,264 bytes under a 3 GiB cap with
no OOM event. This cap is an execution choice, not a measured minimum.

The readiness correction now waits for stability of the current region and then
regrounds any changed frame. It never substitutes a new reference on an old
point. Tests exercise a permanent region change during readiness.

**OBSERVED:** the divider head's strongest fragments lay on the same horizontal
boundary. An explicit line decoder combines these fragments while subtracting
competing parallel boundaries. Its 33-pass actual-model audit rejected all 27
absent-target controls (maximum confidence 0.012117); all three v13 refinement
points hit the divider with confidence 0.327579, 0.377695 and 0.291971. Point
query scoring is unchanged. A private 0.35 configuration is being evaluated;
the shipped default remains 0.55.

The viewport nose query subsequently selected the separate `Nose contour` mesh
in a real canonical runtime retry, although its point confidence was 0.587399.
This is a task failure: anatomical location accuracy cannot certify Face-object
selection. Diagnostic decisions omit CLEF and OmniParser and use independent
state readback; their runtime completion is not a full-model success claim.
**OBSERVED:** the fifth six-case diagnostic runtime retry achieved five task
states: Properties, Outliner, divider, Thin Wall and splash-to-Modeling. The
workspace goal required two actual native clicks and two fresh confirmations.
Face selection still chose `Nose contour`; this failure remains in the report.
No CLEF or OmniParser inference occurred in that diagnostic.

A model-free follow-up refused its manual label click: after Modeling-to-Layout
reset, readback said Layout but the viewport had not regained the original zoom.
The fixture had prepared the old workspace screen before its deferred switch.
Reset now separates workspace switching, viewport preparation and Properties
redraw into successive event-loop turns. Native regression evidence is
recorded below for this second fixture correction.

The next private head was trained on the same eighty v10-only rows and splits, changing
seven positive boxes and two absent-query strings to clean image-left cheek
skin. The objective remains selecting Face. No v13 or v12 image enters training.
Native object identity of that annotation must be checked independently.
**MEASURED:** its separate post-load audit executed 189 grounding passes.
All 117 point negatives were rejected at 0.35 (maximum 0.257657); all 27
horizontal-line negatives were rejected (maximum zero). Ten positive point
passes and one positive line pass were accepted at 0.35, all inside their
annotations. Held-out cheek queries still had low confidence or localized the
other cheek. Training alone does not establish the requested Face selection.
The head SHA-256 is
`9a59a601fa10a77de9206efc45ca147aed65c0a2f29f3ba31ae22fa6bfbcd04f`.
**OBSERVED:** the sixth actual v13 diagnostic completed Properties and Thin
Wall (2/6). Outliner, viewport, drag and splash abstained without input. The
viewport points lay near the cheek but their confidence remained below the
fixed gate; Face was not selected. The divider start passed, but the grounded
Face-row endpoint failed its gate, so no drag occurred. This head regressed
other tasks relative to the previous diagnostic and is not an established fix.
The untouched v12 snapshot and full-model paired benchmark remain pending.

**OBSERVED:** a Gaussian localization variant trained on the same eighty v10
rows, frozen encoders and seed, without v13/v12 training images. Its 189-pass
post-load audit rejected all 144 absent-target point/line controls at the shipped
0.55 gate (maximum confidence 0.436689). The experimental 0.35 gate wrongly
accepted three absent Thin Wall targets and is prohibited for this checkpoint.
Eleven positive passes were accepted at 0.55; ten hit their annotation, while
one scoped Thin Wall point missed. Held-out cheek localization still failed;
training does not establish Face-object selection. Head SHA-256:
`c34940b3f4256298e35a4df95956d9e495ff6768bde9ff6bb57d11c85c35ec12`.
Training peaked at 8,273,960,960 bytes, with no OOM or swap event. These correlated
control contexts establish this observed rejection result, not general calibration.

**OBSERVED:** the seventh original v13 runtime retry at the unchanged 0.55 gate
completed Properties, Outliner Face and Thin Wall (3/6). These used three actual
native clicks, each confirmed by independent Blender state and runtime completion.
Their accepted confidences were 0.903122, 0.570109 and 0.751964. Viewport, drag
and splash-to-Modeling abstained with zero input; Face was not selected.
CLEF and OmniParser were omitted, so this remains a component diagnostic.
The owned Blender scope peaked at 2,216,771,584 bytes and supervisor at
1,455,013,888 bytes; both cleaned up with no OOM event. The full paired run uses
the actual CLEF, OmniParser and visual workers separately from this diagnostic.

**OBSERVED:** a separate model-free label check selected actual `Face` with
both a manually reviewed image-left cheek click and chin click after independent
fixture resets. Native input used exact screenshot references; each first stale
attempt was refused, then a fresh capture and fresh annotation succeeded.
Before/after screenshots showed the Face outline and Outliner selection, and
Blender readback reported `Face`. This proves those two private fixture labels,
not model grounding or completion. No CLEF/Omni/ViT inference occurred.
Its owned fixture ran 06:41:44-06:43:21 UTC while the paired benchmark started;
the additional Blender peak was 971,542,528 bytes. That host overlap must be
considered when interpreting cold benchmark timing. All owned scopes cleaned up.

**OBSERVED:** saved-image hypotheses did not fix the same failed Face task.
Three chin query variants produced nine rejected grounding passes; their points
missed the reviewed chin annotation. Sixty absent-target controls were also
rejected. A separate global overview proposal, retaining the same head, fine
refinement and 0.55 gate, produced three wrong viewport points and rejected all
of them. Its fifteen absent-target controls were rejected; the unchanged tiled
control also rejected three passes. Neither query changes nor the overview
strategy was adopted. These are model diagnostics on saved images, without
CLEF, OmniParser or native actions.

**OBSERVED:** native Blender ray casting validated both manually confirmed Face
points against the current, aligned viewport. The exact window-region offset
and image-to-window Y mapping were recorded. Thirty-nine retained Gaussian
prediction records hit hair objects thirty-three times and no object six times;
none hit Face. These records include repeated coarse points and are not
thirty-nine independent accuracy trials. A 16-pixel ray grid found 398 visible
Face hits among 3,185 tested centers. Its sparse mask marks only tested centers;
untested pixels remain unknown. The diagnostic delivered no input, changed no
scene state, used no model, and cleaned its owned scopes. This establishes a
location error in this failed task, rather than correct Face points being
blocked only by confidence. The v13 mask is diagnostic evidence, not training
data.

**OBSERVED:** a separate native v10 audit reconstructed the seven existing
cheek-annotation contexts. Four orthographic contexts returned visible Face at
all tested points (nine distinct interior points each; the reported center is
duplicated). Three Camera contexts visually matched the saved projection but
returned no ray hit, so their native labels remain UNKNOWN rather than wrong.
The latter ray provider still needs camera-specific validation. A subsequent
independent native check deselected Face, reviewed fresh aligned captures and
clicked each Camera annotation center. All three actual clicks selected Face,
confirmed by screenshots and Blender RNA. Each initial stale reference was
refused before input; a reviewed fresh annotation then succeeded. This validates
centers only, not entire boxes or the Camera ray provider. The private helper's
top-level `native_input_sent=false` was stale; actual per-row delivery and the
review summary record three clicks plus one fixture-preparation divider drag.
The raw report is preserved. These checks overlapped head training and are not
benchmark timings. All owned scopes/display/port were cleaned. No labels were
changed, and v13/v12 images were not added to training.

**MEASURED:** the retained 80-row training manifest generated 71 coarse and
499 fine contexts. The old loop updated once per context; each positive cheek
row had two coarse and fifteen fine contexts. Eleven of twelve saved held-out
cheek coarse ROIs missed their annotation. Aggregate context hit rates did not
report this stage separately. Training now gives coarse and fine stage means
equal weight per row, updates once per row and reports stage-specific hits.
Actual dense-head regression predictions remain invariant when an entire fine
augmentation bank is duplicated twelve times. This objective also changes negative-update share from
24.6% of context updates to 63.6% of row updates; any result must not be
attributed solely to coarse weighting. `optimizer_steps` counts updates;
checkpoint training counters count context exposures.

**OBSERVED:** the stage-balanced seed-zero head trained for 100 epochs and
5,500 optimizer updates on that same manifest. Coarse training hits were 24/36,
coarse validation hits 5/13, and fine validation hits 103/125. Its exact loaded
189-pass audit rejected all 144 absent-query passes at `.55` (maximum `.1121`),
but accepted only four of 45 positive passes, all correct Material icon points.
All twelve held-out cheek passes missed the annotation and were rejected.
Their coarse ROIs intersected it in only two passes and fully covered none;
refinement cannot recover a target excluded by the coarse crop. This checkpoint
is not adopted. Its SHA-256 is
`258716735b139241cb8091b44e095477c51f39ff71807ccb4a9ac3820450ead7`.

**INFERRED:** fixed manifest order is another training bias: each epoch used
13 positive, 13 negative, seven positive, then 22 negative rows, and the head
was evaluated immediately after that final absent-only block. The absence loss
pushes shared scores downward. This mechanism does not establish the cause of
wrong-object localization. Training now uses a seeded epoch shuffle; the
isolated actual-feature comparison retains the same seed, 100 epochs, 5,500
updates, objective, labels, serving decoder and `.55` gate. The observed result
below remains insufficient for an original-task retry.

**OBSERVED:** the exact order-only comparison completed with equal baseline
metrics and 5,500 updates. Coarse train hits increased 24/36 to 31/36,
coarse validation hits 5/13 to 8/13, and fine validation hits 103/125 to 109/125.
The loaded 189-pass audit rejected all 144 absent passes at `.55` (maximum
`.1899`) and accepted seven of 45 positives, all bbox hits. Cheek coarse ROI
overlap increased 2/12 to 9/12, with four full covers, but final cheek hits were
only 2/12 and none were accepted. Its maximum combined cheek confidence was
`.0290`; the order correction did not fix Face selection. Head SHA-256:
`4b13ac52158ac0a0705c12e0b00fe1358168e5af06881f6a13bb8f164d7bcccd`.

**OBSERVED training, native accuracy NOT_RUN:** train matching whole-region coarse inputs for
the original cheek query, retaining native magnified fine crops and default
tiled small controls. The new 80-row manifest preserves every image, label,
query, split and region; only `coarse_strategy` is added. Overview coverage is
five positive/one negative training rows and two positive/one negative
validation rows. Such limited coverage does not bound general false acceptance.
Serving V3 checks declared strategy coverage and refuses untrained strategies.
**OBSERVED:** translated non-square pixel tests preserve original coordinates
and fine crop size. A partial letterbox-edge regression reproduced confidence
zero when single-overview patches were merged by tile-fusion anchor bins;
retaining those distinct patches produced confidence one third on the same
pixel fixture. Fine half-patch augmentation now uses the actual fine-context
pitch. These tests establish geometry, not Foundation accuracy.
The matching head produced a 100-epoch, 5,500-update training report and V3
checkpoint SHA-256
`c3c2109fd106377bef3edb86ee7ae0fd20a65f7e449a1033acd95660690dc087`.
Coarse validation hit 10/13 contexts, fine validation 112/123. The loaded audit
observed all twelve Face coarse points inside their annotations, with nine
coarse confidence gates passing `.55`; all twelve fine gates failed. Final
points hit eight annotations and none passed `.55`, maximum `.29193`. Matching
overview supervision improved proposals but has not fixed accepted Face input.
The complete 321-pass control audit finished with exit zero. At `.55`, four of
45 positive passes were accepted, all annotation hits, and zero of 276 negative
passes were accepted. Overview negatives had maximum confidence `.20705`
(144 passes), tiled negatives `.34380` (132). These are correlated configurations
from 41 distinct absent image/query/region keys, not 276 independent samples.
The owned audit scope peaked at 890,740,736 bytes, with no swap/OOM and minimum
available memory 16,998,260,736 bytes; both owned PIDs exited and the scope was
inactive. No overview checkpoint has passed native Blender acceptance yet.
Posthoc `.35` accepted fifteen positives with one bbox miss and no negatives;
`.25` accepted nineteen with two bbox misses and one negative. The latter
incorrectly grounded an absent Save As confirmation on the Thin Wall screenshot.
That global lower gate is not adopted. Face still had no acceptance at `.35`.
The original v13 six-case native retry uses the unchanged `.55` gate.

**OBSERVED limitation:** training supervisor session 81172 exited with SIGTERM
(143). The sender/cause is not established. Its final resource row was
09:40:52 UTC, while the trainer wrote the valid report and checkpoint at
09:43:51. The 179-second interval has no global-memory-floor monitoring evidence;
final peak, final OOM events and trainer exit zero are not established. The
systemd scope's 14 GiB/no-swap limits remained configured, but that does not
replace the missing observations. Original guard artifacts remain untouched,
with the anomaly recorded separately. The saved checkpoint is assessed under
a fresh guarded scope; its supervisor now reaps its owned child on interruption.

**OBSERVED:** an actual canonical diagnostic runtime drag selected a model-derived
divider and endpoint, changing Outliner height from 155 to 88 with one native
gesture. Its oracle verified two fresh readbacks; CLEF and OmniParser were
omitted. The following Material reset revealed asynchronous editor geometry:
`area_move` returned before `out.height` updated. Reset now flushes the redraw
before checking restoration; a later real reset restored height 155 successfully.
**OBSERVED:** the subsequent model-free native Modeling-to-Layout regression
restored the original viewport zoom. Its manual cheek label click was refused
because the whole-frame hash changed; no Face-label input was delivered.

**MEASURED:** canonical fixture rounds recorded wall latencies 169.569 and
167.685 ms, including 162.951 and 162.176 ms of visual waiting. The previous
stage sums were only 14.165 and 12.378 ms; they omitted waits and were not
end-to-end step latency. The logger now measures elapsed wall time directly.
These numbers verify logging semantics, not desktop ML performance.

| Requested condition | Current evidence |
| --- | --- |
| Preserve STRUCTURED | OBSERVED CLI fixture and regression suite |
| Foundation ViT and coarse-to-fine x,y | OBSERVED real pinned model inference |
| Router and explosion fallback | OBSERVED runtime regressions and real dense traces |
| Separate model logic and ActionBackend | OBSERVED real native visual clicks |
| CANVAS click/drag and real viewport selection | OBSERVED native six-case diagnostics and partial full-model viewport/drag trials |
| Improve original Blender failure and six-case workflow | OBSERVED original and blind native 6/6; partial full-model native goals baseline 0/8 versus hybrid 7/8, with no runtime completion |
| Comparable successful latency/success benchmark | NOT MET; resident sixteen-trial partial comparison stopped on host-memory guard; fresh sixty-trial comparison pending |
| Regression tests and documentation | OBSERVED; commands and artifacts below |

The native backend is implemented. A CUA Driver adapter, C-RADIO comparison and
DINO implementation are not included in this slice. Interfaces permit another
backbone or input backend without placing OS input inside model logic.
The six-case acceptance exercises a viewport selection click and a divider
drag. An AUTO visual drag routes to CANVAS because it requires a continuous
gesture. This does not establish model-driven dragging inside a 3D viewport.

## Latest original-task retry and diagnosis

**OBSERVED:** a resident-model Properties pair subsequently completed with real
OmniParser, CPU bfloat16/NF4/SDPA CLEF and the V3 SigLIP head. Raw perception
contained 242 candidates. Baseline passed 48 choices to CLEF, refused input
at low confidence and retained `OBJECT`. Hybrid passed one grounded VISUAL
choice, delivered its native click and independently read `MATERIAL`.
Its terminal runtime status was nevertheless `LOW_CONFIDENCE`, not `COMPLETED`;
the post-action completion assessment lacked the required visible evidence.
Four actual CLEF replies and all three worker startup responses were archived.
**MEASURED:** owned supervisor peak was 17,744,674,816 bytes, Blender peak
2,193,223,680 bytes and minimum host available memory 6,878,593,024 bytes.
No OOM or swap event occurred; owned processes and scopes were cleaned.
This establishes resident resource fit for this pair. Cold baseline and warm
hybrid timings are not an isolated speed comparison; the other 58 trials of
the pilot journal remain `NOT_RUN`. A final sixty-trial comparison under one
fixed implementation and confidence policy remains pending.

**OBSERVED:** the pilot exposed an unverified `COMPLETED` assessment being
discarded in favor of grounding another action. A deterministic raster-state
regression reproduced repeated inputs undoing an enabled setting. Preserving
the completion assessment now returns `NEEDS_REPLAN`, retains the visible
setting and delivers only the original input. The focused hybrid-runtime
suite returned `30 passed`; the real native task has not yet been retried
with this correction.

**OBSERVED:** the loaded V3 overview head `c3c2109f...` at the unchanged 0.55
gate completed three of six original v13 native component tasks: Material
Properties, Thin Wall and splash dismissal followed by Modeling. Outliner,
Face viewport selection and divider drag refused input. Four native clicks
were delivered; independent Blender state readback verified the three task
results. This diagnostic omitted CLEF and OmniParser and therefore does not
establish full-loop success or populated-perception routing.

**MEASURED:** twelve saved-image stage traces reproduce the remaining refusals.
Original native coarse confidence was 0.504672 for Face, 0.511869 for Outliner
and 0.461170 for the drag endpoint, all below 0.55. The divider start passed
coarse at 0.702657 but failed fine at every refinement. Eighteen separate Face
fine-crop traces also failed the gate even when the annotated point was inside
the crop. One correct, high-presence fine prediction had a single active
component with only 0.257966 of the full-map posterior; diffuse background
held the remaining mass. These observations establish that crop displacement
alone does not explain the confidence failures.

**PROPOSED, NOT ADOPTED:** an earlier absolute-mass alternative was evaluated against saved maps.
Expanding support to binary score >= 0.5 and requiring peak score >= 0.9 at
both stages hypothetically admits six of twelve correlated refinements, only
Outliner and the drag endpoint. Face and the divider start still reject.
This calculation does not execute the changed decoder or native actions,
has no additional negative-control result, and has not been adopted.

**MEASURED:** the subsequent conditional primary/competitor ratio was executed
on the unchanged head, queries, 321 coordinate/crop configurations and 0.55
action gate. It admitted 30/45 positive configurations, including eight
annotation-box misses, and no absent targets among 276 configurations (132
tiled and 144 overview). These negatives include repeated refinements and
41 distinct image/query/region keys; they are not 276 independent examples.
None of the fine maps had every binary score >= 0.9, so preserving the
uniform-fine alternative changes none of these results. The canonical decoder
then reproduced every score, probability and coordinate from 642 saved stage
maps exactly, with maximum error 0.0. Independent region reconstruction and
the twelve original native contexts also matched exactly. This verifies the
implemented calculation, not native success or general false-positive safety.

**OBSERVED:** the first original six-case native retry with that correction
passed five cases. The viewport click `[439, 559]` selected `Face` through
`VIEW_3D`; the Outliner click selected `Face` through `OUTLINER`. Divider drag
changed Outliner height from 155 to 74, Thin Wall became true and Material
Properties opened. Splash dismissal succeeded, but a same-window tooltip
changed foreground pixels before the second workspace click, which was
refused. No stale input was delivered. The retry omitted CLEF and OmniParser.
The subsequent runtime correction lets eligible generated pointers observe
stable new pixels in the same window and fully reground/redecide within the
existing two-retry budget. It preserves immediate rejection of changed window
identity, geometry and planner coordinates. Painted-state regressions observed
one correct fresh input after a large redraw, and zero inputs after persistent
redraws exhausted three decision rounds. The focused runtime suite passed
32 tests. The original six-case retry then completed all six tasks, retaining
the correct-editor Face transitions and Outliner height change. Splash used
two completed clicks plus one no-input stale retry before `Layout -> Modeling`.
Seven native actions completed, with no partial deliveries; owned scopes,
processes, display and endpoint were cleaned. This remains a
`NO_CLEF_NO_OMNI` diagnostic.

**OBSERVED:** the subsequent frozen blind v12 pass also completed all six
tasks, with seven completed native actions and one no-input stale retry.
The viewport target was independently generated at `[424, 567]`, changed
`None -> Face` through `VIEW_3D` and passed the editor-bound outcome predicate.
Before the first v12 open, the helper persisted the six fixed cases, queries,
config, source hashes, head and manifest. Original and private-copy source
hashes stayed `df093c03...`; policy and code matched the successful v13 run.
No query, threshold, coordinate or weight was tuned from this holdout.
Cleanup verified empty scopes, absent owned PIDs and closed endpoints.
The blind interval included manual screenshot review and brief concurrent
pure-Python validation/build work, so it is not comparison performance.
The subsequent sixty-trial comparison ran fresh rows with actual CLEF,
OmniParser and SigLIP resident under the fixed implementation and policy.
Its partial results and resource abort are recorded at the top of this page.

**OBSERVED:** benchmark state readback alone confused the two Face tasks:
the old predicate credited a viewport task for selecting Face through Outliner.
The corrected predicate binds the native selection transition to a completed
click in the required editor. Per-action state snapshots and the boundary
before the next input handle queued events; missing evidence stays unverified.
Readback errors preserve the already persisted native result. All 32 focused
benchmark tests passed, including both wrong-editor directions and an earlier
correct-editor click followed by a wrong-editor selection. This predicate was
then exercised in the partial real Outliner and viewport trials.

## Local evidence and reproduction

Private screenshots, VRM copies and learned head weights remain outside git:

The current Gaussian checkpoint, its exact eighty-row manifest, twenty referenced
images and completed training/control reports are also copied byte-for-byte to
`~/.cache/clef-use/hybrid-grounding/2026-10-07/gaussian-c34940b3/` (private directory,
24 files). Its copied head retains the SHA-256 recorded above. This preserves
reproducibility beyond `/tmp`; it does not certify the unresolved tasks.

- `/tmp/clef-hybrid-benchmark-20261007-v8/report.json`: early raw 60-run failures.
- `/tmp/clef-hybrid-grounding-smoke/report.json`: five real visual/native trials.
- `/tmp/clef-hybrid-setup-v10/report.json`: corrected fixture readiness and images.
- `/tmp/clef-cpu-nf4-feasibility/report.json`: real CPU CLEF answer.
- `/tmp/clef-hybrid-cpu-properties-pilot/report.json`: original parser timeout.
- `/tmp/clef-hybrid-cpu-properties-pilot-v2/report.json`: resource stop and samples.
- `/tmp/clef-hybrid-dense-scoped-cpu-benchmark-guard.json`: actual full-runtime resource abort and sixty NOT_RUN trials.
- `/tmp/clef-v2-head-data/`: split manifests, head provenance and held-out audits.
- `/tmp/clef-v2-head-data/assessment-dense-seed0.json`: first dense head's 105-pass audit.
- `/tmp/clef-hybrid-dense-component-v13/report.json`: six-case dense component retry.
- `/tmp/clef-hybrid-dense-component-v13/stale-image-analysis.json`: saved pixel differences.
- `/tmp/clef-v2-head-data/assessment-dense-scoped-seed0.json`: current 156-pass point audit.
- `/tmp/clef-v2-head-data/assessment-line-geometry.json`: explicit line audit.
- `/tmp/clef-hybrid-dense-scoped-component-v13-v3/report.json`: six real component cases.
- `/tmp/clef-hybrid-calibrated-component-v13-v4/`: canonical runtime diagnostic retry.
- `/tmp/clef-hybrid-calibrated-component-v13-v5/report.json`: five task-state successes, one Face failure.
- `/tmp/clef-hybrid-calibrated-component-v13-v6/report.json`: two task-state successes; four safe abstentions with the new head.
- `/tmp/clef-hybrid-workspace-reset-label-v13/`: retained model-free stale-frame refusal.
- `/tmp/clef-v2-head-data/text-context-smoke.json`: real worker query-limit refusal and unchanged short-query point.
- `/tmp/clef-v2-head-data/assessment-dense-cheek-seed0.json`: new head's 189-pass point/line audit.
- `/tmp/clef-v2-head-data/assessment-dense-cheek-gaussian-seed0.json`: Gaussian head's 189-pass audit; 0.35 rejected as unsafe for this checkpoint.
- `/tmp/clef-hybrid-gaussian-default-component-v13-v7/report.json`: three actual task-state successes at 0.55, three safe abstentions.
- `/tmp/clef-cpu-bf16-feasibility-v2/report.json`: actual CPU bfloat16 worker-ready and canonical decision evidence.
- `/tmp/clef-hybrid-dense-cheek-gaussian-bf16-cpu-benchmark-guard.json`: retained co-resident bfloat16 resource abort, sixty NOT_RUN trials.
- `/tmp/clef-hybrid-dense-cheek-gaussian-bf16-exclusive-cpu-benchmark-guard.json`: exclusive-worker resource abort and durable in-flight evidence.
- `/tmp/clef-hybrid-dense-cheek-gaussian-bf16-exclusive-pilot/report.json`: startup-confirmed baseline inference interruption and next-trial continuation.
- `/tmp/clef-cpu-attention-dispatch-probe.json`: actual installed-provider CPU kernels and numerical differences at two small lengths.
- `/tmp/clef-cpu-bf16-sdpa-baseline-replay/report.json`: exact full baseline request, actual SDPA startup, finite reply and token usage; no GUI input.
- `/tmp/clef-v2-head-data/diagnostic-gaussian-chin-v7-v2/report.json`: rejected saved-image query alternatives and absent controls.
- `/tmp/clef-v2-head-data/diagnostic-gaussian-overview-v7/report.json`: rejected overview proposal and unchanged tiled controls.
- `/tmp/clef-v13-manual-face-label-v7/report.json`: model-free cheek/chin Face identity, stale refusals and fresh annotations.
- `/tmp/clef-v13-raycast-dataquality/summary.json`: native Face label validation and actual hair/no-hit identities for rejected predictions.
- `/tmp/clef-v2-head-data/native-v10-cheek-label-audit-summary.json`: four validated orthographic annotation contexts and three unresolved Camera raycasts.
- `/tmp/clef-v10-camera-center-gt-155/review-summary.json`: actual native Face selections at all three Camera centers and explicit correction of the raw top-level input flag.
- `/tmp/clef-v2-head-data/train-dense-cheek-stage-balanced-seed0.json`: actual balanced training, 5,500 updates, separate coarse/fine results.
- `/tmp/clef-v2-head-data/assessment-dense-cheek-stage-balanced-summary.json`: loaded 189-pass audit, failed cheek crops and retained negative controls.
- `/tmp/clef-hybrid-workspace-reset-label-v13-v2/report.json`: actual native workspace reset and zoom restoration.
- `/tmp/clef-v13-overview-component-157/review-summary.json`: original six-case V3 native retry, three successes and three refusals; no CLEF or OmniParser.
- `/tmp/clef-overview-fine-context-diagnostic/hypothesis-results.json`: eighteen loaded-head fine-context traces and rejected component-only alternative.
- `/tmp/clef-v13-stage-support-diagnostic/`: twelve actual coarse/fine traces and explicitly unadopted pure posthoc calculations.
- `/tmp/clef-hybrid-dense-newhead-bf16-sdpa-resident-pilot-evidence-summary.json`: actual resident-model pair, distinct native and runtime outcomes, resources, source hashes and cleanup.
- `/tmp/clef-v2-head-data/assessment-dense-cheek-conditional-summary.json`: actual unchanged-head 321-pass conditional-confidence evaluation.
- `/tmp/clef-v2-head-data/canonical-conditional-raw-parity.json`: exact 642-stage/321-final canonical decoder replay.
- `/tmp/clef-v13-conditional-component-158/review-summary.json`: five verified native successes and the retained splash/workspace stale-frame refusal.
- `/tmp/clef-v13-conditional-component-159/review-summary.json`: all six original native successes, including the fresh-frame splash retry and complete cleanup.
- `/tmp/clef-v12-blind-component-161/review-summary.json`: immutable before-open blind protocol, all six native successes, unchanged hashes and cleanup.
- `/tmp/clef-hybrid-frozen-overview-bf16-sdpa-resident-benchmark/report.json`: sixteen completed full-model trials and the interrupted native viewport journal.
- `/tmp/clef-hybrid-frozen-overview-bf16-sdpa-resident-benchmark-partial-evidence-summary.json`: exact host-memory floor, delayed termination, partial outcomes, source hashes and cleanup.

Run repository code with `PYTHONPATH=src`; this workspace's `.venv` otherwise
imports an installed wheel. **OBSERVED:** the current dev suite returned
`425 passed, 10 skipped in 21.01s`; the focused benchmark suite returned
`32 passed` and hybrid-runtime suite `32 passed`. Grounding, head-training and model-loading tests returned
`76 passed in 6.32s` in the ML interpreter; plugin autoload was disabled, and
pytest reported an unused `asyncio_mode` setting and a profiler-cycle warning.
The current CLI structured self-test returned `COMPLETED` with
two actions, explicitly proving only deterministic control flow. Ruff was executed;
Torch-only tests additionally ran in the existing ML interpreter using the
dev environment's pure-Python pytest packages. Package build produced a wheel
and sdist in `/tmp/clef-hybrid-v2-build-frozen`. See
[setup and benchmark commands](HYBRID_EXECUTION.md).
