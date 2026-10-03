# Visual readiness and bounded execution

`SessionRuntime` owns waiting. `DesktopAction` refuses a `wait` primitive. A
post-action delay is replaced by `VisualWaiter`: fresh captures must show a
relevant change, then consecutive stable samples, within a monotonic deadline.
The default deadline is 5 seconds, sampling interval 50ms, and two stable
comparisons. Sampling sleeps throttle capture work; elapsed time cannot establish
readiness. Cancellation interrupts sampling. Capture errors and foreground or
geometry changes cannot produce a successful wait.

Candidates carry an `expected_effect` and a target/nearby ROI. Four pixels with
channel changes over 20 are detectable; full-screen averaging cannot hide a small
control movement. Content effects additionally compare normalized edge structure
to reduce uniform hover-color readiness. These are documented pixel heuristics,
not a semantic assertion, event subscription, general animation classifier or
occlusion detector. No caret/background region is unconditionally masked. Before
input, the target's reference appearance must recur and stabilize; a moving
control or modal requires replanning. The Windows adapter independently checks
foreground HWND and physical window bounds before injection.

`STABLE`, `ALREADY_TRUE`, `NO_CHANGE`, `UNSTABLE`, `CONDITION_UNMET`, `CANCELLED`
and `CONTEXT_CHANGED` preserve different evidence. Already-true predicates are
explicit. A stable wrong condition is not accepted. Visible text matching uses
independent OCR inside the supplied field region; ambiguous/unobservable text
blocks further input. This does not establish a stored field value or reliable
multilingual OCR. Final completion still needs strong goal and condition answers
on two fresh frames; readiness alone cannot complete a task.

## Decision and ownership

One joint CLEF call returns fixed-choice ACT/WAIT/BLOCKED/NEEDS_REPLAN/COMPLETED,
action choice, noul effect/goal/conditions/safety and score progress. WAIT requires
an observed loading region or a prior action region and injects no input. BLOCKED
records evidence and a resume condition; explicit planner guidance can resume it
without resetting the decision budget. A missing target can therefore become
available later. Unknown enabled/editable/focused/occluded properties remain
unknown. The joint model request omits null metadata instead of presenting it as
false or positive evidence; its established goal/condition questions precede new
mode/effect questions. Explicit negative metadata removes candidates. Generic Enter/Backspace/
SelectAll require established input focus; text is scoped and exact.

History records attempted operation, target, expectation, observed readiness,
verification and failure. Repeating the same input in the same relevant state is
blocked regardless of the model's claimed effect probability. A genuinely changed
page may use the same Next control again. Accepted actions and attempted actions
remain distinct in the action budget. Cancellation and every exit release owned
inputs and the exclusive desktop lease.

The latest stable frame feeds the next perception step. The one-entry cache
requires an exact full raster plus image mode/size, origin/scale, foreground/bounds
and pinned parser identity/configuration. It caches normalized objects, never
coordinates from a similar image, decisions, completion probabilities or wait
results. Idle observe uses the same cache under the desktop lease; busy observe
cannot capture or run an independent parser. Additional resident-model hold/
unload changes in the working tree are excluded from this release. Their locking
was inspected: idle observe reserves `busy`, and unload rejects busy/cancelling
operations and overlapping holds. They have not been integrated or accepted here.

## Measurement

`scripts/windows_visual_benchmark.py` compares three variants on the same actual
Windows Tk GUI, task, model revisions and shared resident workers: a 300ms fixed
post-action delay, visual waiting without perception caching, and visual waiting
with exact caching. The fixed variant is a diagnostic ablation of the new runtime;
it retains current safety checks and joint questions and is not the old product
version. The GUI delays actual label rendering by 500ms. Cold loading is reported
separately; warm variant order rotates across repetitions. A no-effect button is
also checked for bounded stopping without repeated input.

Report empirical p50/p95 and sample size, task success, actual callback/readback,
wrong input, early advance, false completion, actions, CLEF/parser calls, wait
frames/time and pixel verification CPU time. `wait_ms` includes capture, checking
and throttling; `verification_ms` overlaps it and must not be added again. SSH
capture/input transport is included. No inference runs inside wait polls. Known model failures are retained; worker restarts are marked as actual cold
runs rather than being described as warm. Small-sample measurements do
not establish arbitrary-app accuracy or a general speed improvement.

## Primary references and follow-up decisions

- [Playwright actionability](https://playwright.dev/docs/actionability): separate
  visible/stable/enabled/editable checks and assertions. Pixel detection cannot
  supply its DOM guarantees.
- [SikuliX regions](https://sikulix-2014.readthedocs.io/en/latest/region.html):
  bounded region/change waits rather than unconditional action delays.
- [OSWorld-Human](https://arxiv.org/abs/2506.16042): measure task success and
  efficiency together; inference overhead and redundant work matter separately.
- [UFO multi-action](https://github.com/microsoft/UFO/blob/main/documents/docs/ufo2/core_features/multi_action.md):
  a possible later verified microbatch experiment. Current CLEF emits one allowed
  action per joint request; no speculative batch output is assumed.
- [Agent S2](https://arxiv.org/abs/2504.00906): later grounding improvements need
  a controlled failure/accuracy baseline first.

Read-only native UIA/AX metadata, improved ROI grounding and model-memory tuning
remain follow-ups requiring measurements. No additional execution framework or
unverified cache-clearing removal is introduced.

The retained public-safe MPS allocator pilot request is
`docs/evidence/clef-cache-request.json` (pixels of the owned Windows test app).
Run `scripts/clef_mps_diagnostic.py` in the pinned CLEF environment with
`--model-path <pinned Flash snapshot> --request-file docs/evidence/clef-cache-request.json
--output <local report.json>`. This diagnostic emits probabilities, numerical
measurements and sanitized errors; it injects no input. Do not use private screen
content for a public evidence capture. The pilot measured 2/8 CLEAR, 3/8
SYNC_CLEAR and 4/8 KEEP errors; no production allocator-policy change is justified.


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
