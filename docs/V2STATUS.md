# clef-use V2 status (working doc, 2026-10-08)

Canonical spec: `~/develop/celf-use` (V2 + Reici dogfood goal). OLD tree frozen
under `old/` at tag `freeze-2026-10-08` (commit a2e677f).

## 2026-10-10: correct evidence scope and context-distance units

- Independent numerics review PASS for one-input head arithmetic only. Correct
  earlier "bitwise repeat" wording: rtol=0/atol=0 asserts exact numerical equality,
  not signed-zero byte identity. Original evidence/helper bytes stay preserved;
  their baseline_bitwise_repeat_verified field is a historical misnamed flag.
  Lexical shard/index/tokenizer digests were not recorded. Declared private/head
  hashes and pre-capture tolerance timing were outside that static verification.
- OFFLINE menu-coverage audit joins seven of eight logged context IDs to an older
 100-object structured snapshot with the same recorded native frame reference.
  Observation IDs differ; one context item is UNKNOWN, not inferred from pixels
  or raw tensors. Known hints include File/Edit/Render/Window and vertically
  aligned New/Qpen_/Open Recent. Raw OCR spelling/null confidence are unchanged.
  These support a dropdown-consistent layout hypothesis, not native popup state,
  actual goal success, complete context coverage or a causal recognition diagnosis.
- REPRODUCED separately: unit-square bbox distances ignore raster aspect ratio.
  In retained metadata New is nearer File in native pixels than Edit, yet the old
  policy ranks Edit first. Landscape/portrait bounded-context regressions both
  drop a10px-near hint for an18px-far hint before the correction.
- FIXED locally: measure rectangle gaps with native image width/height before
  squaring. Only unique-anchor hint ranking changes;32targets/8hints, actual raw
  objects/IDs, candidate set, question/option wording, weights and all safety/
  completion gates remain. Serialized hint text intentionally changes with
  selection. No menu dictionary or missing-object invention.
- VERIFIED: independent source review PASS, no blocking concerns. Recommended
  nonzero-origin/swapped-logical-aspect cases preserve frame/evidence/raw-object
  identity and reject an in-memory logical-dimensions substitution mutant.
  Targeted32passed; full local551passed/34skipped, existing41 Pillow warnings;
  active Ruff/format/diff pass. Production router bytes unchanged after review;
  post-review edits only focused tests and precise question/option wording.
  Actual original-task ASSESS sessionbc8da2b676034c71ae8d7c7e20aba75b on accepted
  router: one genuine CUDA/NF4 decision, zero candidates/GUI inputs. Same logged
  native frame hash e64a4a77... and126 objects; eight context IDs now select raw
  label Reyert instead of Window and reorder nearer dropdown hints. LOW_CONFIDENCE
  persists:
  modeACT0.4444/goal0.1578/condition0.1647. These one-case scores do not establish
  accuracy improvement, calibration, causality or completion. No capture re-arm,
  model/default/gate/cap change or denied full-GPU/prompt A/B.
  No OOM/kill, but unchanged8GiB cap reached with15992 max events and308215808
  swap bytes. Context-distance correction and actual task success remain separate.

## 2026-10-10: diagnose real head arithmetic without changing defaults

- Independent static re-review PASS after initial privacy/bounding/fidelity
  rejection and red->green regressions. The six code/test hashes and pinned SDK
  were independently rechecked before first use. ADR0003 defines host-only,
  default-off, one-attempt private numeric capture, not SDK replay or authority.
- ACTUAL: same original File contract in ASSESS; one genuine CUDA/NF4 decision,
  zero inputs. ModeACT0.4503, goal0.0944, condition0.0775; LOW_CONFIDENCE.
  Raw hidden/logit hashes,0600 files/0700 root, actual worker and native frame
  identity match the original logged decision. No OOM/kill; the8GiB service hit
  its memory limit and used swap, so this is not ample-headroom evidence.
- MEASURED: one saved real input on cached trained head/selected genuine rows,
  CPU2GiB/swap0/two threads. Production-rounded FP16 parameters/rows were widened
  unchanged to FP32. Two deterministic repeats give numerically identical FP16
  baselines under rtol=0/atol=0; this does not distinguish signed-zero bits.
  Real captured question/option token spans match independently preserved
  canonical definitions. No vocabulary table or backbone materialization.
- GPU/CPU probability bridge max delta0.00024178624153137207, below predeclared
 0.02 tolerance. FP32 arithmetic max probability change0.00019890069961547852,
  identical across repeats; lexical sign-flip changes logits1.994140625, finite.
  Goal0.09442688524723053->0.09441555291414261, condition
 0.07748274505138397->0.07756032049655914. Widening head arithmetic does not
  explain the low completion scores in this one input. It cannot restore source
  values already rounded or backbone/activation information already lost.
- VERIFIED: local547passed/34skipped; bounded real-Torch16passed; active Ruff,
  format/diff pass. Actual CPU peak charge1162428416bytes, RSS1375031296bytes;
  no CPU swap or OOM. Shared charge/RSS and post-exit unit footer differ; use
  in-process sampled resource fields, not the footer to claim containment.
- Task-only capture environment/drop-in removed and owned idle service reloaded;
  source weights/default model/NF4/gates/config/caps unchanged. Private inputs
  stay outside the repo and release artifacts. Capture is not UI success:
  File recognition, Reici production, full-GPU/prompt probes, accuracy/default
  promotion and new release remain NOT_DONE/NOT_RUN as applicable.

## 2026-10-10: remove weak completion through pixel-change evidence

- Parent verified the completed inference-integrity audit against the pinned
  encoder, option IDs/noul polarity, head forward path and local runtime. No
  deterministic inference-adapter scoring defect was demonstrated. BF16 source
  head/rows become FP16 in the NF4 deployment; causal accuracy loss is unproven.
- MEASURED separately: actual cached trained head and genuine selected checkpoint
  rows, seeded synthetic CPU hidden states23/730. Lazy transport and independent
  eager rows give bitwise-equal finite logits; sign-flipped rows change logits.
  This excludes neither CUDA/NF4 backbone error nor model-domain recognition.
  Initial zero-row FP16 participation control produced nonfinite normalization;
  rejected as degenerate, not evidence about actual task activations.
- REPRODUCED: the 0.75 single-pass branch accepted goal0.84/condition0.76 after
  one delivered fixture input and genuinely measured ROI change. The regression
  fails before with COMPLETED, passes after with NEEDS_REPLAN/COMPLETION_UNVERIFIED;
  its prior input is retained and never repeated. Pixel change is effect evidence,
  not independent proof that the final goal and all conditions are satisfied.
- FIXED: remove that fallback. Every completion now requires goal and all
  conditions>=0.9 on two fresh stable positive observations. AUTO/ASSESS prior-
  effect cases verify weaker goal/condition refusal, exact0.9 acceptance only
  after two rounds, and single-positive budget exhaustion without input.
- CORRECTION to earlier status/ADR wording: the 0.9 constant and normal two-fresh
  path remained, but an older calibrated-effect exception also remained. Earlier
  statements implying every completion path already enforced those gates were
  too broad. This change removes that contradiction rather than calling pixel
  evidence a calibration corpus.
- VERIFIED: full local543passed/18skipped, active Ruff/format/diff checks pass.
  Existing41 Pillow deprecation warnings remain. ML full suite and actual File
  inference not repeated: adapter/weights/precision are unchanged, and the prior
  ACT/LOW_CONFIDENCE result did not enter this completion branch. No success,
  speedup, FP32 benefit, default promotion, avatar import or new release claim.
- OPEN: real Blender completion recognition still unproved. Independent audit
  complete; actual backbone activations are absent. Precision candidates need
  causal evidence before adoption, not a threshold change or convenient PASS.

## 2026-10-10: retain bounded evidence and assess without input

- Parent verified the completed independent audit against primary code and saved
  artifacts. The old first-eight hint policy preserved some text, not none, but
  omitted dropdown entries. Singleton action none confidence1.0 is not completion
  probability. The historical grounding failure lacked completion scores.
- FIXED: unique genuine anchor plus observed rectangle distance prioritizes at
  most eight raw context hints. No File dictionary, synthetic menu, action trust
  upgrade or label/ID/bbox/null-confidence rewrite. Packet retains source and
  observation/frame provenance. Existing32targets+8hints remain; object/32KiB
  text overflow fails closed. The pinned encoder preflights with a larger bound
  and refuses >8192tokens before unchanged8192-token inference, never silently
  clipping completion evidence. This repeats CPU encoding, not a speedup claim.
- ADDED: opt-in ASSESS in the existing MCP/CLI goal contract; no sixth tool or
  low-level click API. It constructs no candidates, performs no spatial input
  grounding and cannot deliver input. Existing safety/mode/completion gates,
  including two fresh stable positive observations, remain unchanged. Raw model
  completion/condition scores are now retained even before grounding failure.
- FIXED: observe thumbnails carry their own pixel identity and native parent hash;
  a1280x720preview is not the1920x1080model input. Old saved mismatches remain
  disclosed, not relabeled. No native foreground metadata is invented.
- ACTUAL: real stdio sessioncca0c740d2dd4a73bbd52580855a1544, original File goal/
  conditions/constraints/max_steps3, delivery policy only changed AUTO->ASSESS.
  Already-open starting state; actual CLEF-FlashNF4/default and task8GiB limit.
  One decision/zero new inputs; modeACT0.4498, goal0.0943, condition0.0772,
  safety0.0185, replan0.6109. ResultLOW_CONFIDENCE, notCOMPLETED. OOM/kill deltas
 0/0. Menu context really reached the model; this correction did not establish
  actual completion recognition. No unchanged retry or previous-click repeat.
- VERIFIED: full local533passed/18skipped; isolated ML565passed/4skipped. Existing
  Pillow/profiler warnings remain. Actual setup reload owned PID2013293, idle;
  no model installs, training, asset import, default switch or new release.
- RISK M1: meta projection replacement is only valid for the pinned immutable
  untied CLEF joint-head consumer. Full HF forward/generate or later output
  embedding mutation is unsupported; static audit found no current pinned-path
  defect. Owner reclamation is not ample-memory or numeric whole-model proof.
- OPEN: File dropdown stays visibly open and empty scene unchanged, but runtime
  success still unverified. Overall avatar/rig/physics/Gemini gates incomplete.

## 2026-10-10: assess visible dense goals without redundant targeting

- FIXED: the completion-only CLEF assessment precedes non-structured target
  grounding even on a first frame with no previous effect. An already-visible
  goal does not require a new input point. This is a zero-proposal assessment,
  not permission to act on OCR text or bypass grounding for new input.
- VERIFIED: red->green dense first-frame tests require zero input, two fresh
  observations for strong completion, refusal of weaker completion with no
  independent effect witness, and safety veto even when the goal is visible.
  Existing completion probabilities, calibrated prior-effect requirement,
  safety/replan thresholds and action confidence remain unchanged.
- EXERCISED: same actual File request, now starting with its physically open
  dropdown, reached actual CLEF assessment with zero proposals; CLEF chose ACT,
  then the unchanged dense confidence gate (0.0) returned NEEDS_REPLAN/no input.
  The new assessment path is exercised; it did NOT fix this model's goal
  recognition or establish runtime completion. Captured genuine OCR File/New/
  Open Recent/Save/Import facts have no action proposals. The bounded empty
  context may discard useful read-only text: INFERRED, independent audit pending.
- VERIFIED integrated final source: local 518 passed / 18 skipped; isolated ML
  full suite 550 passed / 4 skipped, with dependency-dependent parametrization.
  Ruff, scoped formatting and diff checks pass. No ordinary Actions, new model
  training, default-model promotion, checkpoint relabel or Blender import.
- OPEN: runtime completion/grounding remains blocked; physical File menu stays
  open, empty V01 scene untouched. Private evidence and weights remain outside
  distribution. Goal is not complete; public release remains 0.1.25.

## 2026-10-10: honest isolated-environment readiness

- OBSERVED: running the full suite with existing ML/app packages exposed an
  ambient-path leak: an intentionally empty ML environment imported the
  caller's Torch and appeared ready. Explicit PYTHONPATH poison was imported;
  a foreign PYTHONHOME could prevent the interpreter from starting at all.
- FIXED: readiness uses Python isolated mode and explicitly admits only the
  probe's trusted sibling helper directory. No ML-environment install or lock
  change. Real empty-environment/poison regressions fail before and pass after;
  inherited app paths remain test harness context, never readiness evidence.

## 2026-10-10: scoped NF4 placement and unused host-table ownership

- OBSERVED: installed Accelerate hook initialization recursively places the
  root CUDA map before the CPU exception's offload hook is installed. A tiny
  real-hook regression reproduced the forbidden lm_head CUDA transfer on both
  a guarded CPU boundary and real CUDA. Pinned input/output tables are equally
  sized; the old full-model traceback did not name its tensor, so attributing
  that specific historical allocation remains an inference.
- FIXED: CUDA placement names the model subtree, not the root. The canonical
  lexical-row helper retains genuine checkpoint slices/casts, while the public
  output-embedding setter replaces the never-executed hooked projection with
  matching meta shape/dtype/bias metadata. This releases the hook's full CPU
  owner; garbage collection handles its forward-wrapper cycles. No checkpoint
  weight rewrite, zero-valued inference signal, CPU model fallback, quantizer
  exclusion change, threshold change or service-limit increase. Removed the
  redundant low-free-VRAM second row-hook installation and obsolete mock tests
  that pinned the broken root map/repeated offload rather than behavior.
- VERIFIED: the host-owner regression failed before correction even when the
  parameter was meta; fixed dispatch and row tests pass with weak-reference
  reclamation and exact numerical lexical-gather/reduction equivalence. Test
  fixtures use real hooks and tiny tensors, not real model/task success labels.
- EXERCISED: original real stdio File request constructed CLEF NF4 and delivered
  one model-selected click. Independent native capture shows the dropdown open
  and scene still empty, but subsequent parser work hit the unchanged 8GiB
  cgroup limit: ERROR/worker disconnected, oom_kill increased by one. A second
  structured observation also failed; raw native capture avoided another model
  retry. Physical input is not runtime COMPLETED; never blindly repeat/toggle.
- EXERCISED after the complete correction: real owned service loaded CLEF,
  parser and dense workers together and ran the same request without another
  OOM/kill (event deltas zero). Cgroup current still reached 8GiB with reclaim
  events and about 520MB swap, so this is not a memory-headroom claim. The task
  remains NEEDS_REPLAN because dense confidence is zero and completion was not
  recognized. Closed-menu click and already-open retries are different initial
  states; no controlled latency/memory improvement percentage is claimed.
- VERIFIED: scoped dispatch and row suite 8 passed, including real CPU/CUDA
  numerical and hook regressions. Ruff/diff checks pass. Integrated full-suite
  counts are recorded with the subsequent readiness/goal-assessment corrections;
  do not assign combined-working-tree counts to this isolated loader change.
  No environment install/lock changes, training, avatar import or new release.

## 2026-10-10: existing V3 recovery and bounded semantic routing

- OBSERVED: the independent read-only audit found an existing overview+tiled V3
  checkpoint outside the previously inspected hybrid cache. Parent verified its
  full SHA256, original manifest bytes, all 20 image hashes and 80 annotated rows;
  copied 26 exact files into a private durable bundle without changing metadata.
  Canonical `load_grounding_head` ran in the real isolated ML environment:
  finite payload, non-initial weights and both trained strategies accepted.
  No new training, legacy relabeling, threshold weakening or weight publication.
- The task-only config differs from the global config solely in `visual_head`.
  The owned display service reads that config via a runtime-only override; MCP
  callers must pass the same config. Global settings and CLEF-Flash/NF4 remain.
  Format/readiness compatibility is not evidence of UI grounding accuracy.
- EXERCISED: actual stdio MCP retried the original File-menu goal/conditions/
  constraints. V3 loading no longer fails, but visual confidence remained zero;
  a concise referential-query replan also safely returned NEEDS_REPLAN with zero
  input. Earlier zero *exact* File labels did not prove absence: the actual
  observation contains the OCR-backed interactive label `File ` with whitespace.
- FIXED: AUTO now bounds explicitly named OCR/native display-text proposals
  before applying whole-screen candidate density. Raw labels and IDs remain
  unchanged; this is not an OCR-to-native trust upgrade or automatic click.
  CLEF still chooses/vetoes with unchanged confidence/safety policy, and explicit
  geometry/operations/regions remain binding. If canonical action-budget limits
  omit any ambiguous matched target, replan without input rather than silently
  selecting from an incomplete subset. No Blender-specific label or coordinate.
- EXERCISED: real stdio MCP on the same owned empty Blender, same goal and
  constraints plus explicit query `File`: 120 raw candidates -> STRUCTURED ->
  one CLEF proposal. The downstream CLEF NF4 load failed OUT_OF_MEMORY before
  input, not a dense-context overflow. RTX 3080 10GB; actual exception attempted
  1.89GiB with 1.83GiB free. Pinned input/output embedding headers each contain
  BF16 [248320,4096], 2034237440 bytes. Input-table placement is a hypothesis,
  not a proven tensor attribution or a completed memory fix.
- VERIFIED: local 518 passed / 16 skipped / 41 existing Pillow warnings; Ruff
  and diff checks pass. Red->green regressions cover both bounded OCR selection
  and incomplete action-budget refusal; safety, region, geometry, ambiguity and
  untrusted-caption exclusions remain covered. Ordinary Actions stay disabled.
- OPEN: independent read-only memory-placement/API audit is pending. File menu
  remains closed, original workflow NOT COMPLETED, V01 not imported; rig/physics/
  matched renders remain NOT_RUN. Private weights/evidence stay outside releases.
  Cold and warm attempts have different load states: no controlled speedup claim.

## 2026-10-10: qualified source and real dense-head setup failure

- OBSERVED: official VRoid sample A/B primary usage flags and complete creator
  terms were parent-verified. Existing private original binaries were located;
  historical authorized mirror receipts and pinned remote byte hashes match.
  This is not a new Hub download, a login bypass or a CC0 claim. Asset-specific
  restrictions remain separate from the software license and release.
- EXERCISED: canonical reviewer -> AGY Gemini, three immutable references and
  two official multi-view source images. All five actual view_file calls, model
  identity and image hashes verified. Source suitability PASS, rank V01 then
  V02. V01 is qualified for technical inspection, not final avatar/rig approval.
- EXERCISED: a fresh task-owned empty Blender 5.2 window on isolated display
  :122 -> the actual CLI AUTO 'Open the File menu' contract. It failed before
  input: 122 candidates routed VISUAL; the configured legacy v2 cheek head was
  correctly refused by the audited v3 provenance gate. No compatible v3 head
  was found under the existing hybrid-grounding cache. No avatar was imported.
- FIXED: the public setup diagnostic, not grounding accuracy or GUI completion.
  A typed GroundingHeadProvenanceError crosses the real worker boundary; runtime
  presents a static visual_head/v3 remediation without exposing arbitrary worker
  text. A red->green consumer regression preserves zero input and secret redaction.
- RETRIED: same goal/constraints through the real stdio MCP server on the owned
  runtime. Status ERROR, zero actions/decisions, now with the precise safe setup
  explanation. Legacy weights were not relabeled, thresholds/defaults were not
  weakened, and Blender/Python did not bypass the failed GUI operation.
- MEASURED: local 503 passed / 16 skipped / 40 existing Pillow warnings; Ruff
  and diff checks pass. MCP retry 68.578 s includes cold reload; it is not a
  controlled speedup comparison with the earlier warm CLI failure.
- OPEN: prepare genuinely auditable compatible UI grounding weights, then retry
  the original File/import workflow and inspect actual source topology/rig and
  matched renders. A scoped read-only audit is pending. No hosted validation,
  new release or avatar distribution has occurred in this phase.

## 2026-10-10: source suitability separated from production acceptance

- OBSERVED: `rank` mixed a source-compatibility question with the final-character
  recognition rule. Source previews are now ranked as reusable infrastructure,
  with repeated labels treated as additional views of one asset. Production
  gates retain the strict identity rule; this does not lower final quality.
- Host-owned `review_scope` separates `source_suitability` from
  `production_stage`. A base PASS cannot carry a final-stage label, and a stage
  review cannot be relabeled by reviewer output. Two red->green regressions
  exercise these consumer-visible output boundaries.
- EXERCISED: actual CLI parser/rank handler -> sandboxed AGY Gemini, three
  immutable canonical references plus seven original BOOTH images. All ten
  view_file calls are DONE, model identity and before/after SHA256s verified;
  raw process/events are retained in private evidence. Runtime 86.229 s.
- RESULT: independent source review returned FAIL, ranking B01 before B07.
  Neither is selected. Framing evidence is better, but marketing still images
  do not establish reusable topology, deformation or physics. Do not retry to
  manufacture a PASS, recommend purchase from this result or call it final
  avatar acceptance.
- Primary asset-specific Japanese licenses were read in full (9 and 10 pages).
  Modification/format conversion are permitted for legitimate users; original
  model redistribution is not planned. The software embedding clause addresses
  embedding AND distribution, not private screenshot-based testing alone.
  Commission/corporate/commercial conditions remain separate. No asset binary
  was acquired or imported; private evidence is excluded from software releases.
- MEASURED: local 498 passed / 16 skipped / 40 existing Pillow warnings; active
  Ruff and diff checks pass. No Actions dispatch or release rebuild is needed
  for this source-review helper-only change. Live Blender editing remains NOT_RUN
  in this phase because an acceptable, legitimately acquired base is not ready.

## 2026-10-10: independent CV review path repaired

- OBSERVED: the shared AGY reviewer previously ignored native structured_output
  and could accept a PASS from a failed process/envelope. Red regressions reproduce
  both failures; it now parses actual event/result streams, retains typed output,
  and fails closed on unsuccessful transport.
- Reviews use the explicitly observed Gemini model in plan+sandbox mode, not
  auto-approved write permissions. Every requested image needs a DONE view_file
  record; before/after SHA256s bind the verdict to the actual immutable files.
  Model identity and hashes are retained; temporary schema files are removed.
- Real shared-adapter execution inspected 11 original shortlist inputs and six
  follow-up inputs. A raw PASS falsely claimed full-leg visibility in a cropped
  source preview. A separate Gemini original-pixel audit returned FAIL. Selection
  remains on HOLD; image-open traces prove inspection, not semantic correctness.
- No asset purchase/import, Blender scene mutation, model-default promotion or
  final visual-quality approval occurred. Private references/previews/reviews stay
  outside software source/release artifacts. See the private production ledger
  and TASK_STATE.md for remaining matched-view, acquisition, rights and rig gates.
- MEASURED: local full suite 496 passed / 16 skipped, with 40 existing Pillow
  deprecation warnings. Active-tree Ruff and diff checks pass. GitHub Actions
  was not dispatched; standalone CI/fixture workflows stay disabled.

## Ported and green (432 passed, 10 skipped)

- Contracts: `schema.py` (Contract.execution_mode AUTO/STRUCTURED/VISUAL/CANVAS/ASSESS,
  visual_intent), `interfaces.py` (Capture/Perception/Decision/ActionBackend/Verifier
  Protocols), `config.py`.
- Structured path: `candidates.py`, `objects.py`, `mcp_server.py`, `cli.py`.
- Input: `backends.py`, `windows_input.py`, `activity*` — deterministic ActionBackend.
- V2 visual: `router.py` (ExecutionRouter: bounded count before truncation, native
  exact-target precedence, VISUAL/CANVAS routing, CLEF veto preserved),
  `grounding.py` (SigLIP2 `google/siglip2-base-patch16-512`, tiled + overview
  coarse-to-fine, DenseGroundingHead w/ training-provenance audit gate).
- Runtime: visual fallback wired in `runtime.py` (grounding_ms timing, stale-input
  retry, visual wait states).

## Known gaps (from docs/HYBRID_VALIDATION.md §552 + this review)

1. C-RADIO alternate backbone: referenced in docs, not implemented as a swappable
   VisionBackbone. Needs a benchmark adapter, not a second runtime path.
2. Trained DenseGroundingHead requires provenance-audited weights; untrained
   installs fall back to dot-product head (weaker on tiny icons).
3. CUA Driver optional backend: unimplemented.
4. OmniParser still the only dense-UI proposal source for STRUCTURED; AX/DOM
   adapter coverage is per-platform.
5. Release/install path unchanged so far — must re-run installer build +
   check_installation against the V2 tree before tagging.

## Dogfood rule

Any Blender friction found in production goes into
`~/develop/clef-use-reici-goal/reici-production/clef_use_observations.md`, then
reproduce -> fix in V2 src -> regression test -> retry the SAME operation.

## Dogfood fix queue (from production observations, pending real repro)

- F1 FIXED 2026-10-08: verified effect facts + a measured 8x8 `roi_change_cells`
  vector now reach the next CLEF decision via `Observation.evidence`
  (runtime -> router -> clef_request -> ClefWorker). The pinned release
  checkpoint's vision tower accepts exactly ONE image per record (a second raster
  fails inside its linear projection on real CUDA weights), so evidence travels
  as text + change vector, never a crop. Regression `test_effect_evidence.py`
  reproduced the stale-completion failure red, green after fix; the completion
  gate was calibrated (model proposal + independent pixel witness, floor 0.75)
  against the real heads' ~0.84 ceiling (trial12 COMPLETED on live Blender).
- F2 LOW_CONFIDENCE after a single canvas stroke where the visual effect lags the
  observation round (trial-v43) — same root cause family as F1.

## F4 (fixed 2026-10-08): NF4 loader OOMs mid-materialize on a 10GB card

The fp16 lm_head (~2.9GB, never executed by the joint head) plus the visual tower
overflowed 9.6GB and `torch.OutOfMemoryError` fired inside
`core_model_loading.materialize_tensors`, surfacing as a bare
`ModelWorkerError in runtime backend` with zero decisions. Fix: the CUDA NF4
loader places lm_head on CPU unconditionally (`device_map` +
`llm_int8_enable_fp32_cpu_offload`, row-gather hook preserves semantics), and
effect-evidence never adds raster images. Worker errors now carry the exception
string so CLI users see `out of memory` instead of an opaque type name.

## F3 (fixed 2026-10-08): dense-screen decision overflow crash

Real Blender @1920x1080: 123 parser objects + 48 candidates -> the legacy
`pointer_inputs/grounder None` whole-roster passthrough serialized ~24.5KB of
state (~6.1k tokens) on top of questions/media and the real CUDA worker died
with OUT_OF_MEMORY inside forward. Fix: structured sessions ALWAYS use the
bounded `decision_observation` (targets capped to the 32-candidate choice set,
hints capped to 8); regression in test_decision_context.py + suite green.
Trial sequence: trial2/7/8 crashed or DisplayConnection (stale service env);
trial9 running against a systemd-run service bound to :122.

## Ops lessons (dogfood environment)

- CLI-launched service inherits the launching shell's DISPLAY; a service started
  while Xvfb was dead keeps the poisoned env forever (status shows stale sessions,
  not its own env failure). Restart the service, don't re-run the CLI.
- Hermes background wrappers die on gateway restart; use `systemd-run --user`
  for Xvfb/Blender/service on this box.
- Never `pkill -f <pattern>` in a tracked terminal: pattern matches the
  wrapper's own command line and self-kills (SIGTERM). Target pids explicitly.

### 2026-10-09: work continuity under host memory pressure

Primary evidence: `docs/evidence/HOST_MEMORY_2026-10-09.json`.

- OBSERVED: recent whole-gateway kills were systemd-oomd pressure kills, not
  exclusively kernel OOM. Its log identifies the gateway cgroup and the 50% /
  20-second monitored-ancestor pressure condition. `OOMPolicy=kill` had set
  `memory.oom.group=1`; it does not mean "kill only the offending worker".
- Corrected the task host's gateway drop-in to `OOMPolicy=continue` and bounded
  control-plane `ManagedOOMPreference=omit`. Verified equal cgroup owner uids,
  actual omit xattr, `memory.oom.group=0`, unchanged gateway PID/restart counter
  after live daemon-reload. The inference service is separate, capped at 8GiB
  memory / 1GiB swap, not exempted from oomd, with bounded service restarts.
- A real model retry still hit global OOM while another VM trial grew tmpfs.
  The model child died, but the repaired gateway and service survived. Thus
  isolation alone was not evidence that the task had enough RAM.
- With user permission, switched the current VM boot/backup helper scratch
  paths to disk; preserved the original disk-capacity checks and truthful
  non-tmpfs metadata. Existing live VM images were not moved/deleted. A disk
  qcow2 overlay smoke passed; a full VM reboot was NOT_RUN and new VM admission
  is currently blocked by disk space. No fallback to shared host RAM.
- Preserved the unused 091 root partition with single-thread LZMA2 level 9,
  16MiB dictionary. Full extraction matched the pre-archive SHA256 and exact
  byte count before releasing its 2,511,585,280 tmpfs bytes. The other
  `snapshot.raw` disappeared during concurrent work and was NOT archived;
  the preservation manifest explicitly records the incomplete full-disk copy.
- The pinned meta lm_head path now keeps a lazy safetensors slice and casts
  only selected lexical rows. The eager BF16 -> FP16 full-table copy fails the
  new allocation regression; selected row means are bitwise equivalent on
  real CPU/CUDA for FP16/BF16/FP32 (six cases). No confidence gate was changed.
  Independent code review found no blocking security/logic defects. Following
  its coverage finding, profiling includes initialization plus first gather;
  a deferred full-table dtype-copy mutation fails both FP16/FP32 CPU budgets.
  The corrected six precision/device cases and 441-test base suite pass.
- MEASURED: original Hair001 contract returned five real CUDA decisions over
  240.07 seconds, with 480 memory samples and 40 subsequent health checks.
  New OOM count = 0, main PIDs and restart counters unchanged, minimum host
  MemAvailable = 10.746GiB. One CPU parser and one CUDA CLEF worker remained
  resident. Service memory includes reclaimable checkpoint file cache and
  reached its 8GiB cap; this is not a claim of aggregate memory reduction.
- OPEN: all five decisions remained LOW_CONFIDENCE (zero inputs). This proves
  work continuity, not Hair001 selection or Reici visual quality. SSD space
  and the separate bounded-candidate/model-confidence defect remain explicit.

### 2026-10-10: desktop-owned runtime endpoints

- Linux X11/Wayland desktop identity scopes the default endpoint directory;
  local X11 screen-zero aliases share identity. Explicit state-dir overrides
  remain supported but do not waive ownership checks.
- Service health reports its captured desktop scope. Clients reject foreign or
  legacy-unknown ownership before version-based shutdown, startup or dispatch.
  Non-health service requests additionally require a matching desktop header.
- Protocol regressions cannot initialize GUI/model backends or spawn runtimes.
  Real :0 MCP observe against the :122 endpoint was refused, with the bounded
  service PID/cgroup unchanged. The correct :122 observe returned a fresh frame.
- The frame was blank and no Blender process was present; successful observation
  is NOT evidence of Hair001 selection, completed GUI work or model quality.
- MEASURED: full suite 452 passed / 16 skipped; changed-file Ruff and diff checks
  pass. The prior default decision model and confidence/safety gates are unchanged.
- Current user direction is the model-independent Decision Backend with d1-3B
  as a candidate. Default promotion requires paired task-success/safety evidence,
  including authentic Blender trajectories and Windows/macOS GUI coverage.

### 2026-10-10: model-independent Decision Backend (IN_PROGRESS)

Current user scope: add `LiquidAI/d1-3B` as the new default-model candidate, keep
CLEF-Flash as the compatibility/performance baseline and available fallback,
and preserve OmniParser, SigLIP2 grounding, CANVAS, MCP/CLI and ActionBackend.
Do not promote the candidate using a model-card benchmark or replay-only result.

- Primary HF metadata and complete SDK/license files were retrieved at immutable
  d1 revision `051bcc464b01b9f92942b364d9586b0ef5912432`. The SDK uses the public
  `AutoModel` / `system_one(state, questions, images)` API and requires its own
  pinned Transformers 5.14.1 environment. License: LFM Open License v1.0, not
  Apache-2.0; preparation/catalog notices link the pinned license and identify
  commercial conditions separately from the application license.
- `DecisionBackend` and `decision_request` replace the model-specific active
  backend names. Registry-selected worker kinds/interpreters isolate d1 from
  the unchanged CLEF loader. Invalid/missing/foreign/nonfinite typed answers
  fail closed; native choice confidence and noul probabilities are not rescaled.
- SDK audit caught two real compatibility constraints before model execution:
  CLEF requires an adapter-supplied model tag and rounds answers to four decimal
  places. Regression tests preserve that tag and bounded serialization error
  without normalizing/clipping scores. d1 keeps its native full-precision fields.
- d1 currently allows original weights only (`quantization=none`). It executes
  its tied lm_head; do not apply CLEF's unused-head NF4/CPU-row offload to d1.
- MEASURED: 476 passed / 16 skipped; changed-file Ruff and diff checks pass.
  These include adapter/loader spies, not a real d1 weight/inference benchmark.
- MEASURED: the hashed d1 environment lock contains 38 pinned packages. Real
  candidate preparation loaded the immutable 6,247,065,504-byte weight artifact
  on CUDA/BF16 and initialized the unchanged CPU OmniParser. Readback confirms
  the active model remains CLEF-Flash/NF4 and the pinned LICENSE SHA256 matches.
- Added a real-model replay runner with input/image hashes, raw typed answers,
  cold/warm timing, actual worker RSS/GPU allocator peaks and independent-only
  labels. Archived Blender v15/v27 failure frames have no invented quality
  labels; NEEDS_REPLAN is not ground truth. Replay never executes OS input.
- First real inference found a malformed corpus missing public-SDK question
  instructions; the reader now rejects it before model load. An early paired
  GPU attempt also failed while another PID held 6.86GiB; that failure is
  retained as ERROR, not accuracy/performance data. The next bounded replay
  returned six valid real d1 choice/score/noul responses from Windows + actual
  Blender failure frames. CLEF-Flash still OOMed during GPU loading, so that
  run is not a paired speed/quality comparison.
- MEASURED: matched CPU/BF16 + Torch 2.11.0 / Transformers 5.14.1 paired replay
  completed (3 authentic cases x 3 repetitions per model, exact input hashes,
  separate worker PIDs). CLEF-Flash warm median 29.391s / peak RSS 10.045GiB;
  d1 4.336s / 6.874GiB. One labelled Windows final fixture supplied 9 repeated
  known-field judgments: CLEF 9/9, d1 6/9 (ordinal progress underestimated).
  Blender image timing is real but quality labels remain unknown. This small
  replay is not task-success proof; explicit accuracy-regression blocker added.
- Native macOS collector/workflow was reviewed and committed as `15874a8`,
  pushed with exact remote SHA readback. Actual macos-15 fixture run
  `37968411148` passed real Swift/AppKit execution. Downloaded three macOS
  15.7.9 ARM64 owned-view PNGs; all hashes, native widget readbacks, dimensions
  and nonuniform pixels verified. Toolkit callbacks are not live OS input.
  Fresh Windows collection also passed on build 26200.9457 / AMD64 / Session 1:
  three 640x360 owned-client screenshots, Win32/Tcl readbacks and hashes verified.
  Foreground, pointer and owned-window cleanup read back unchanged/restored.
  `Button.invoke()` transitions are fixture construction, not model-led OS input.
- OBSERVED: real pinned CUDA/BF16 d1 now traverses canonical `DecisionBackend`
  on the authentic macOS Confirm frame and returns a validated ACT/a0 decision.
  This found/fixed missing progress `instructions`; using the exact CLEF fallback
  text preserves its prompt meaning. No OS input or task completion is asserted.
- MEASURED: complete active suite 491 passed / 16 skipped; CI-scoped Ruff lint,
  formatting and diff checks pass. Frozen `old/` is untouched. The whole-tree
  formatting check exposed only frozen legacy style differences, not a V2 error.
- MEASURED: expanded authentic nine-case CPU/BF16 comparison completed: 54 real
  responses with paired hashes, different worker PIDs and the same SDK/device.
  CLEF 63/63 versus d1 54/63 known-field judgments (21 unique fields x 3 repeats),
  zero false-completion choices in both. Warm medians 19.858s versus 1.614s;
  peak RSS 10.627GiB versus 6.656GiB. d1 progress regresses on three GUI frames.
  No Blender accuracy labels or live E2E safety claim. See DECISION_MODELS.md.
- Feature commit `a3c1b0e` is pushed; CI `37972241262` passed all six jobs,
  including native packaging/install/update failure-preservation checks.
- OBSERVED: release `v0.1.25` / source `1af8808` published. Exact-source CI
  `37974286598` passed all six jobs; existing release `37974290815` passed all
  15 native build/installer jobs, assembly and dev deployment. Public latest
  is 0.1.25; every archive SHA256/runtime wheel, both bootstraps, checksum list
  and immutable manifest were read back. Prior 0.1.24 manifest is unchanged.
- OBSERVED: actual public Linux and Windows isolated 0.1.24 -> 0.1.25 updates
  returned INSTALLED then CURRENT. Config and cache-sentinel bytes were preserved;
  installed candidate catalog still reports active CLEF-Flash. No model setup,
  desktop input or user PATH changes. Windows bootstrap bytes were HTTPS-fetched
  on monad and SCP-staged after its Invoke-WebRequest stalled; installer bundle
  fetching and update still used the public canonical distribution.
- Scoped idle display :122 service was restored and its 0.1.25 / not-busy RPC
  read back. See RELEASE.md and private goal-workspace verification JSON files.
- Remaining promotion evidence only: live paired Blender/Windows/macOS success
  and safety, labelled Blender quality, and a successful paired GPU baseline.
  None is asserted by fixture replay or successful software deployment.
  Default remains `Cloudflare/clef-flash`; d1 status remains `candidate`.
