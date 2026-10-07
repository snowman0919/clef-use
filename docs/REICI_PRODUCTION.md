# Reici production acceptance and evidence

## Goal and authority

The user-designated `/home/monad/develop/prompt.md` (1,090 lines, read in full)
defines this task: improve and commit clef-use while producing a recognizable,
rigged, expressive VRM 1.0 avatar through meaningful clef-mcp and blender-mcp
participation. Technical milestones alone are not completion.

Starting state: canonical main at c86d499, clean; installed runtime 0.1.21.
Preserve unrelated work, original reference images and the existing Blender
process. Local coherent commits were authorized initially. The later explicit
user correction authorizes source push and deployment through the existing
GitHub Actions pipeline; use that pipeline rather than publishing a local build.

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

The active owned scene is `reici_model_v10_clef_sculpt.blend`, modeling-only
with zero armatures and visual likeness still rejected. V10 adds two actual
GUI lower-cheek Grab strokes to the preserved V9 checkpoint; deployed execution
and independent saved-coordinate verification are detailed below. Earlier
polygon remodeling remains historical preparation, not CLEF-led mesh input.
After the user's renewed request for actual polygon refinement, V6 displaced
751 of the 1,408 base facial
vertices (maximum 0.009253851 m), reconstructed unequal upper-lid strips and
radially clipped iris topology, and rebuilt directional hair, flat cloth bow
loops and long open cargo hems. This is actual mesh editing, not texture-only
retouching. V6's render then exposed crumpled fringe: two locks each had five
upward spline rows. An actual failing Blender check was corrected in V7 with
monotone polygon control grids; all nine main locks now have zero upward rows.
Coupled eye/lid/iris footprint edits and fresh facial-surface projection retain
the round native texture and depth gate. No visual acceptance follows.

V8 then made the evaluated face topology directly editable (21,506 vertices)
and moved 11,521 actual facial vertices, maximum local displacement
0.020590544 m, to shorten the lower face and sculpt subtle nose/mouth planes.
FaceTint survived the conversion. Actual garment vertices changed too: 11,420
in the rounded coat shell, 2,834 in each sleeve, plus the crown border and soft
canvas bag. Canonical Front inspection prevented an unjustified blanket crop
of the long oversized coat. V9 replaced protruding pink ear ellipsoids with
closed helix/concha shells (386 vertices each) and inset surfaces (513 each),
reprojected thicker upper-lid strips, and rebuilt physically clipped iris meshes
(2,049 vertices each). The pupil texture is still a traced native derivative,
not a new native generation or a substitute for geometry.

Current actual images: `model_v10_clef_sculpt_{front,three_quarter}.png` and
`model_v10_clef_sculpt_relaxed_{front,side}.png` in the task artifacts directory;
all four PNGs are verified. Corresponding V9 views are preserved as baseline.
The relaxed views temporarily transform arm/sleeve/hand groups and restore
them (V10 measured maximum matrix residual 0.0); they are not rig validation.
Direct comparison still rejects overall likeness: the fringe has repetitive
wedge tips, face/eye rendering is still doll-like, garment construction needs
closer source matching, and layered hair lacks the original airy flow. The
V8 independent visual review in `evidence/reici-v8-likeness-review.md` is
complete and rejects likeness: coupled eye/lid/iris, lower-face/head/neck,
nonrepetitive hair flow, coat volume distribution and cargo folds/hem are its
five priorities. These remain remodeling targets, not reasons to advance
rig/expression/physics.

Pre-GUI V9 structural evidence: eye width 0.058500001 m, height 0.036609173 m,
opening aspect 0.6257978; iris surface error about 3.72e-9 m; outer/inner upper-lid
strip ratio about 9.2872; maximum visible iris UV V 0.7636. Cargo hem-shoe gap is
0.015486255 m with 64 open base-hem edges per leg. The previous V5 had 0.113 m
hem gap, closed hems and essentially equal corner strip widths. Crown pole was
already closed in V5; a render's dark seam was not proof of a physical hole.
Outward normals, finite coordinates, finger layout and head-neck join passed
on those historical checkpoints; only explicitly measured V10 checks below
are claimed for the current saved model.
Exact evidence: `polygon-face-v6-proof.json`, `polygon-v7-proof.json`,
`polygon-refinement-reici_model_v{5_canonical_eye_fix,7_polygon}-{red,green}.json`,
`fringe-flow-reici_model_v{6_polygon,7_polygon}-{red,green}.json`, and
`blender-polygon-v7-independent-readback.json`. The brace forms denote the
corresponding old-red/new-green files, not every Cartesian combination.

The historical V5 checkpoint and all of its images are retained. The latest
canonical Close Up governs the face and muted olive/sage round-pupil texture,
with verified native Codex provenance. V6's derived illustrated annulus preserves
that generated central pupil; it is not a new native generation. It remains
packed in the current eye meshes. Cargo trousers restore the canonical outfit.

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

The completed actual-weight CPU comparison used five real toolbar crops from
one frozen owned screenshot, float32/eval/inference_mode, seed 1046 and four
threads. After one warmup per variant it alternated five measured runs each.
Caption-only processor/generate/decode batch medians were 12.423328 s for
`[5,3,768,768]` and 0.388341 s for `[5,3,64,64]`; parent recomputation confirms
counts, order, shapes, dispersion and stable within-variant text. Exact matches
were 0/5: the 64 input hallucinated unrelated video/menu/count/drawing meanings.
The baseline captions were also weak or inaccurate. No quality-preserving resize
optimization is accepted, and shared-host contention, changed generated-token
lengths and manually selected crops prevent any full-parser production-speedup
claim. Production resize remains unchanged. Raw evidence and the Korean report
are in `evidence/caption-resolution-ab/{results.jsonl,validation.json,report.md}`.

Independent canonical image review in `evidence/reici-v5-canonical-likeness-review.md`
rejects current likeness and prioritizes coupled lid/iris/white geometry,
nonrepetitive swept fringe, compact lower-face transition, longer open cargo
hems with reduced sock exposure, then layered rear hair/ribbon and pose-matched
jacket inspection. The review does not verify saved Blender internals. The main
agent inspected the original Close Up and current actual 3/4 render directly;
modeling-only and no visual acceptance remain in force.

Release-v2 parent readback exercised c62a83e-export Linux/Python-3.11 artifacts,
20 activation boundary tests, actual installed 0.1.22 fixture version and immutable
same-version checksum rejection with target preservation. These artifacts predate
the two follow-up source corrections and must be rebuilt before final release.
They do not establish native Windows/macOS or all distribution-target acceptance.
See `docs/evidence/REICI_INSTALL.md` for historical source identity and limits.

## Deployed planned pointer feature (2026-10-06)

The user's corrected production route is clef-use primary for actual
geometry-editing GUI gestures; Blender MCP is auxiliary for inspection,
necessary scene/tool preparation, saved state, and independent verification.
A viewport-only click or scripted mesh construction is not a substitute.

OBSERVED source commit `9460cbb` adds bounded observation-bound mouse clicks
and continuous strokes, not pressure-sensitive tablet support. Candidate and
adapter gates enforce exact frame/reference, foreground geometry, quantized
containment and conservatively padded sensitive-surface exclusion. Native
Windows input rechecks identity, geometry and start containment after the
single initial move and before pressing; finally cleanup remains active.
Independent review initially rejected two concrete security defects; both
were reproduced, corrected and independently re-reviewed without findings.
Windows behavior tests use injected fixtures, not a physical desktop.

The initial pushed CI failed on Windows because translated UTF-8 installation
documents were read using cp1252. Commit `00d5903` specifies UTF-8 without
weakening the command-equivalence assertion. Local full suite: `287 passed,
4 skipped`; Ruff check/format and diff checks pass. Actual CI run
`37423126984` for exact `00d590383842fc3ddea7a6271d816a2232656cde`
succeeds on all six OS/Python checks, including Windows 3.11 and 3.13.

OBSERVED registered `release.yml` run `37423169550` at that exact source:
all 15 platform/Python builds, assemble and production deploy succeed.
Canonical public latest manifest reads back version `0.1.22` and 15 artifacts;
the canonical installer updates the owned prefix to `0.1.22`. Installed
`version`, `self-test`, and real stdio MCP pointer schema checks pass.
Self-test explicitly proves fixture control flow, not ML or real GUI quality.
Exact workflow and published metadata are retained as
`evidence/github-actions-0.1.22-{run,published-manifest}.json`.

After confirming idle ownership, the old private `0.1.21` service was stopped.
The new service reports `0.1.22` and its Python executable is inside the
canonical installed version prefix. All five changed runtime module SHA-256
hashes equal the published source; proof:
`evidence/deployed-0.1.22-source-integrity.json`. Production `mcp_call.py`
launches that installed MCP executable and removes PYTHONPATH, never the
repository CLI. Auxiliary Sculpt Mode/Grab/X-symmetry setup retained all
21,506 Face vertices exactly; the original V9 file is preserved.

First real deployed lower-cheek stroke session
`b1d11d4c26da487caf857a95bdf767e7` returned `BLOCKED`, zero actions,
one CLEF decision, `no scoped actionable candidate in current observations`.
The initial inspected screenshot and fresh observed frame differ only in
`image_sha256` within the reference fields. The image changed after setup;
independent vertex readback proves geometry unchanged and fresh parser objects
show no sensitive surfaces. Exact frame refusal is functioning, not a
successful stroke and not evidence to relax the gate. MCP wall time was
188.5667 s, parser 139.7017 s, decision 47.5467 s. Actual MCP
`computer_observe(include_image=True)` then supplies a newly inspected frame;
the same scoped path passes the unchanged safety policy on that exact frame.
Its real retry retains confidence threshold `0.55`; session
`19cef4ac63cb476c8e4e0ca78ba3fac5` delivers one Grab stroke and two
CLEF decisions. Result is `NEEDS_REPLAN`: proposed completion lacks required
visible condition evidence. Independent vertex readback measures 389 left
Face vertices moved inward, maximum 0.00235311687 m; no right vertices moved.
Actual Blender mesh symmetry was OFF although the legacy Sculpt setting was
true. This invalidates the original X-mirrored assumption, not the input proof.

Using the inspected new MCP frame and read-only projection of the symmetry
axis at screen x=526, opposing session `0eaf0381f7ce487ba12affe552fcb6db`
delivers exactly one right-cheek stroke and two decisions, again
`NEEDS_REPLAN`, without a completion override. Independent readback confirms
389 newly changed right vertices, zero additionally changed left vertices;
778 total changed, 389 each side, all inward, finite, maximum 0.00235330313 m.
Both actual edits are deployed GUI gestures, not API coordinate edits.
Checkpoint `artifacts/reici_model_v10_clef_sculpt.blend` preserves original V9
and explicitly marks likeness unaccepted. Auxiliary preparation was corrected
to the actual Object.use_mesh_mirror_x/Mesh.use_mirror_x flag; activation and
save read back true without altering vertex coordinates. Autonomous completion,
bilateral mirror behavior of a future single gesture, and likeness remain
separate unaccepted criteria. A separate background Blender process reloads the
saved V10 and confirms all 21,506 coordinates equal the independently captured
post-gesture coordinates, mesh symmetry true, zero armatures and rejected
likeness marker; evidence `clef-v10-saved-independent-verification.json`.
Four actual checkpoint-labelled renders are verified; the relaxed inspection
matrices restore with residual 0.0 and do not prove rig deformation. Current
parent visual inspection still rejects likeness. Independent V10 image review
`evidence/reici-v10-likeness-review.md` returns REJECT: the small cheek edit
does not visibly resolve the lower-face mismatch. The user explicitly confirms
V10 still does not resemble the original. Retain V10 only as deployed-input
proof and a rejected modeling checkpoint, not an artistic improvement. Next
modeling work must address pose-matched lower-face/chin/neck, coupled eye
aperture/lid/iris, and nonrepetitive hair flow before garment refinements or rig.

The prior V9 Wireframe inspection returned `LOW_CONFIDENCE`, probability
`0.4813`, zero actions and one decision. Its wrapper exit zero was not success;
readback confirms the viewport remained SOLID.

## Likeness rejection follow-up (2026-10-06)

The user explicitly rejects V10. Independent V10 visual review also returns
REJECT and cannot distinguish a meaningful cheek improvement from V9.
Actual deployed GUI lower-jaw trial `7fc4b6dc0acc47a6a4d3c3c84364308e`
produces V11 with bilateral surface dents. Keeping its path/radius/strength
and changing only brush falloff from SPHERE to PROJECTED after exact V10
restoration yields trial `1fd577527500420793ecd7c1056ce954`, V12 with
bilateral contour notches. Both actual front and 3/4 renders are inspected
and rejected. Finite coordinates, bilateral participation and zero triangle
orientation reversals did NOT predict acceptable anatomy or likeness.
Both trials end NEEDS_REPLAN; neither is an improvement or successful
completion. They remain diagnostic checkpoints only.

After the failed V12, the owned live scene is restored from preserved V10;
independent readback proves all 21,506 Face coordinates equal its stored
post-gesture baseline. Original V9/V10 files remain intact. Stop local jaw
Grab iterations; establish canonical landmarks and a broad edit selection /
controlled GUI transform before claiming further face remodeling progress.
The existing runtime key allowlist does not support general Blender modeling
shortcuts; investigate the actual visible gizmo route or implement a reviewed,
deployed capability if genuinely needed, never bypass with scripted mesh edits.

## Completion status

IN_PROGRESS. Pipeline deployment and canonical owned runtime installation are
verified above; character likeness, current avatar, physics, autonomous GUI
completion and final E2E remain incomplete. Native Windows/macOS desktop input
was not exercised by installer matrix checks or injected input fixtures.
