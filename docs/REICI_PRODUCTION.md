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
Original reference cache files are copied, never edited. Two reference images
were recovered; the third reference mentioned in the prompt has not been found.
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

The active owned scene is `reici_model_v3_fringe.blend`, restored from the pre-rig
modeling checkpoint and remodeled after the user's quality-first correction.
Its current face, hair, proportions, outfit and accessories are not visually
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

## Completion status

IN_PROGRESS. No character, physics, final E2E or installer completion claim is
made by this document. Evidence and incomplete acceptance criteria will be added
as the actual production workflow is exercised.
