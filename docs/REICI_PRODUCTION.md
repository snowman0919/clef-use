# Reici production acceptance and evidence

## Goal and authority

The user-designated `/home/monad/develop/prompt.md` (1,090 lines, read in full)
defines this task: improve and commit clef-use while producing a recognizable,
rigged, expressive VRM 1.0 avatar through meaningful clef-mcp and blender-mcp
participation. Technical milestones alone are not completion.

Starting state: canonical main at c86d499, clean; installed runtime 0.1.21.
Preserve unrelated work, original reference images and the existing Blender
process. Local coherent commits are authorized. Remote publishing is not.

## Acceptance checks

- Actual CLEF + OmniParser execution of Blender UI goals; exact MCP call/results
  and per-stage latency logs retained. Reproduce/fix/retry general failures.
- Visually inspect body, face, hair, outfit, accessories and materials separately.
- Humanoid and finger rig: actual evaluated deformation under representative poses.
- Expressions: neutral, blink/bilateral blink, happy, angry, sad, surprised, A/I/U/E/O;
  visible tests, nonempty morph deltas and export bindings.
- Physics: hair/ribbon/loose details with collider-aware motion inspected, not just
  spring entries present.
- Actual VRM 1.0 export and import; inspect final character and retain source blend,
  renders, support assets and asset inventory.
- Clean local release tree and isolated HTTP installation/update exercise; checksum,
  interruption safety, idempotency, CLI/version/doctor/MCP startup verified.
- Regression tests and consistent en/ko/zh-CN/ja setup documentation.
- Final E2E rehearsal using corrected runtime and coherent Git commits.

## Sources and output ownership

Task-owned assets and large binary outputs: `/home/monad/develop/reici-production`.
Original reference cache files are copied, never edited. All three supplied
images are preserved; the newly supplied `img_e46b52e05c98.jpg` design sheet and
its unaltered Close Up crop are the primary authority. Generated support sheets
remain provisional, with v1 rejected for its mature facial impression.
Unseen views must be identified as derived, not falsely called canonical.

The existing Blender process and user preferences are not modified. A dedicated
GUI session on an isolated virtual X11 display is used for reproducible dogfood
without injecting input into other user applications. This is an actual Blender
GUI, not a headless Blender-only replacement; physical-desktop generalization
must not be inferred from it.

## Initial defect: first-call diagnostics

OBSERVED: native clef-mcp `computer_status()` and `computer_observe()` failed with
`runtime refused ...; inspect session status`. Service health was healthy, idle;
HTTP status returned 400/KeyError. SessionManager indexed an empty session map.
The client discarded the response and told a failing status caller to query
status again.

Correction: distinguish NO_ACTIVE_SESSION and SESSION_NOT_FOUND without creating
fake sessions or initializing models. Preserve public SessionResult semantics.
Only recognized, bounded error codes are translated to static actionable text;
untrusted HTTP response text is not echoed. Regression checks cover status,
observe, abort and explicit unknown IDs through the actual authenticated HTTP
client/server path. All four failed before the correction.

## Modeling quality gate

The active owned scene is `reici_model_v5_canonical_eye_fix.blend`, still
modeling-only with no armature. The latest canonical Close Up now governs the
rebuilt face and muted olive/sage round-pupil texture, which has a verified
native Codex call/source-copy checksum and is packed into both eye meshes.
The alternate skirt was replaced with loose charcoal cargo trousers and side
pockets/webbing. The exposed neck was shortened without reopening its join.

Actual render inspection caught two physical regressions: inward scalp winding,
and iris occlusion after a Z-only iris shift lost its surface-depth relationship.
Both have actual Blender RED/GREEN evidence. The corrected iris is reprojected
through evaluated facial geometry, with maximum Y-offset error about 3.72e-9 m;
eye opening aspect is 0.61456, crown mean radial normal dot is 0.13495, and
finger/finite-coordinate/neck checks still pass. These are structural guards,
not source-landmark equivalence or likeness acceptance. The doll-like eye/face
expression, mechanical bangs, open-looking crown/rear-hair boundaries, clothing
and sock/hem proportions remain visual defects.

Current scripts: `remodel_face_v5.py`, `refine_face_v5.py`,
`build_canonical_pants_v5.py`, `repair_iris_depth_v5.py`,
`validate_face_structure.py`, `validate_canonical_outfit.py`, and
`render_model_v5_view.py` in the task-owned production root. Current actual
renders start with `model_v5_canonical_eye_fix_`; exact MCP evidence includes
`blender-face-v5-refined.json`, `blender-canonical-pants-{red,green}.json`,
`blender-iris-depth-{red,green}.json`, and the three `blender-v5-eye-fix-` renders.
Earlier checkpoints and original artwork are preserved.

Historical V3/V4 steps remodeled the
pre-rig checkpoint after the user's quality-first correction. V3 whole-model
renders exposed a cap-like rear-hair boundary and four fingers stacked in camera
depth. V4 corrects finger orientation, lower-face proportions, eye/lid surfaces,
scalp-rooted clumps, socks and the offset backpack. A newly exposed head/neck gap
was detected by evaluated-geometry bounds and repaired before the next images.
Structural RED/GREEN assertions and separate Blender readback are retained;
these are not a visual quality acceptance. The cap-like rear-hair band, hair
surface character, reference likeness, sleeves and strap clearances remain open.

A seven-render Blender MCP call exceeded the installed transport's 180-second
socket deadline while Blender continued producing the requested images and
checkpoint. Do not replay that mutating script: independent readback confirmed
V4 and its structural assertions. Subsequent render batches use fewer views.
Exact evidence includes `blender-model-v4-structure.log`,
`blender-model-v4-verified.json`, `blender-model-v4-neck-red.json`, and
`blender-model-v4-join-repaired.json`; actual render filenames start with
`model_v4_joined_` in the task-owned artifacts directory.

The current face, hair, proportions, outfit and accessories are not visually
accepted. Earlier rig, expression and physics checkpoints remain separate;
their bone counts and tests do not validate the current remodeled scene.
Do not expand avatar features before accepting the overall modeling quality.

## Runtime corrections and independent review

- CUDA NF4: compose the pinned backbone/head with output embeddings offloaded
  before the head moves onto a low-memory GPU. CPU already-offloaded embeddings
  must not receive duplicate hooks. Loader tests isolate allocation ordering;
  they do not prove forward-logit parity or controlled peak-memory savings.
- Idle observation: retain five-second control calls, but give observe a deadline
  covering cold parser startup and a fresh parse. An authenticated HTTP test
  exercises an observation beyond the old control timeout.
- Caption cache: reuse only byte-identical crops in one model worker, with a
  bounded 256-entry LRU. Independent review found Python float64 coordinates
  disagreeing with the pinned Torch float32 caption path. At image width 10,
  `0.699999988079071 * 10` truncated the key crop at column 6 while Torch included
  column 6 and stopped at 7. A changed pixel was incorrectly given the old caption.
  The regression failed before correction and passes with float32 products and
  NumPy slice boundaries; caption input dtype is explicitly float32.
- Completion transitions: invalidate stale completion evidence and reobserve
  without reissuing input, bounded by the existing decision budget. Review found
  the last inference was recorded twice when that budget ran out. Clear the
  already-recorded row; the regression fails before the correction and requires
  recorded CLEF calls to equal actual decision rounds afterward.
- Coverage: a separate click -> delayed transition -> stale completion -> fresh
  completion test confirms one input and fresh-frame consumption. Against the
  pre-change `fa6a4d2` runtime it failed with NEEDS_REPLAN; the corrected runtime completes.

OBSERVED: reviewer regressions were `2 failed, 1 passed` before correction.
The integrated suite is `240 passed in 16.86s`; Ruff check/format and diff checks
passed. The real CPU parser environment (Torch 2.11.0+cpu, seed 1046) matched
4,000 coordinate calculations across four image sizes, including out-of-bounds
slices; changing the boundary pixel invalidated the cache and matched the
uncached crop digest. This validates pixel arithmetic, not ML caption quality.

Evidence under `/home/monad/develop/reici-production/evidence`:
`review-regressions-red.log`, `review-regressions-green.log`,
`action-transition-baseline-red.log`, `caption-crop-torch-parity.json`,
`review-full-regression.log`. No latency improvement percentage is claimed;
prior cold/warm and different-frame timings were not controlled A/B measurements.

OBSERVED original-scenario retry after an idle-only restart of the task-owned
runtime: actual clef-mcp returned session `e00df2bef51d4d129f3e50ac007417ec`,
NEEDS_REPLAN, one action and two decisions. The click had confidence 0.7038;
independent Blender readback confirmed Layout active, no armature, and the same
357-mesh name/count/topology signature. Exactly two CLEF-call log entries matched
the two rounds. The second decision proposed COMPLETED but goal probability
0.7057 and condition probability 0.7197 did not satisfy the required evidence.
This is a completion-confidence limitation, not GUI E2E success; thresholds were
not relaxed and API readback was not substituted for visual completion evidence.

MCP wall time was 401.3 seconds; the two parser observations took 211.8 and 152.6
seconds. Their inputs and cold/warm states differ, so these are observations,
not a cache speedup benchmark. Parser latency and autonomous completion remain
open acceptance criteria. Exact artifacts: `clef-layout-review-fixed.json`,
`blender-review-layout-start.json`, `blender-review-layout-verified.json`, and
session-filtered rows in the task-owned `clef-state/steps.jsonl`.

## Runtime follow-up from the production review

The actual Render -> View Render inspection goal returned session
`08bced846009412bbcdecce4c6ee2631`, NEEDS_REPLAN, zero delivered actions and one
decision, with `screen changed during decision`. The parser took 135.705 s and
the decision 4.721 s; the MCP call took 141.186 s. Refusing the stale input was
a safety outcome, not a successful GUI inspection. A visible workspace tooltip
and material-preview updates are possible transition sources, not a proven
root cause without both original captures. A new retry uses the same goal and
confidence policy after a task-owned static viewport, neutral-pointer move for
diagnosis, equal-pixel captures and an idle-only private-runtime restart.

Independent source/fixture audit exposed two separate defects, neither asserted
to cause that stale-frame failure:

- Empty OCR plus valid detector icons: the pinned overlap primitive returns bbox
  lists instead of dictionaries. The real request raised `TypeError: list
  indices must be integers or slices, not str` before captioning. Normalize that
  documented branch at the wrapper boundary, retaining the actual filtered icons.
  Four prepared CPU-environment request tests cover icon-only, empty, OCR-only
  and OCR-inside-icon screens with real PNG decode, Torch scaling, pinned overlap,
  crop caching and response assembly. OCR/detection/generation are fixtures; ML
  quality is not claimed. Before correction one case errors; after, all four pass.
- First positive completion on the final budget round: `_record` retained its
  mutable row for the terminal finally block, logging three CLEF calls after two
  actual decisions. Clear row ownership after recording. The real runtime fixture
  now logs exactly two calls, one input, and STEP_BUDGET_EXHAUSTED, never inventing
  the second positive completion proof. This regression failed before correction.

The full core environment reports `241 passed, 4 skipped in 16.88s`; its four
skips are the explicit prepared-parser integration tests, separately executed and
passed above. The scoped runtime/cache suite reports 29 passes. Retained evidence:
`completion-budget-v2-red.log`, `omni-empty-ocr-v2-{red,green}.log`,
`runtime-followup-v2-{green,full}.log`, `runtime-followup-v2-restarted.json`,
`blender-v5-ui-stability.json`, `clef-v5-render-view-{review,retry}.json`.
The retry artifact is produced only when its real call returns; in-progress is
not completion. The retry did return: session `f2bb3280235145599a40f289e6521c00`
delivered two real clicks and three decisions in 534.816 s, then stopped with
LOW_CONFIDENCE (`execution mode confidence below threshold`). The three logged
CLEF calls match the actual rounds. Independent Blender readback and a real
post-action screenshot show a Render Result image-editor window; saved/live
geometry signatures match, with 405 objects, 96,137 mesh vertices, 93,899 polygons
and zero armatures. This proves actual GUI inspection progress and geometry
preservation, not autonomous completion. The floating window is at y=-83 on the
owned display, so its header is outside the captured screen. Missing visible
viewer controls are a concrete representation limitation, not yet a proven
cause of the low semantic confidence. Evidence: `blender-v5-gui-review-readback.json`,
`blender-v5-render-view-after.png`, `geometry-v5-{saved_baseline,live_after_gui}.json`.
The signature does not prove unchanged material shader appearance.

A bounded actual-weight CPU 64-vs-768 caption comparison was dispatched on a
frozen owned screenshot; its result has not yet been integrated. No resize optimization, caption-quality
parity or speedup has been accepted from tensor-shape evidence alone.

Release-v2 parent readback exercised c62a83e-export Linux/Python-3.11 artifacts,
20 activation boundary tests, actual installed 0.1.22 fixture version and immutable
same-version checksum rejection with target preservation. These artifacts predate
the two follow-up source corrections and must be rebuilt before final release.
They do not establish native Windows/macOS or all distribution-target acceptance.
See `docs/evidence/REICI_INSTALL.md` for historical source identity and limits.

## Completion status

IN_PROGRESS. No character, physics, final E2E or installer completion claim is
made by this document. Evidence and incomplete acceptance criteria will be added
as the actual production workflow is exercised.
