# clef-use V2 status (working doc, 2026-10-08)

Canonical spec: `~/develop/celf-use` (V2 + Reici dogfood goal). OLD tree frozen
under `old/` at tag `freeze-2026-10-08` (commit a2e677f).

## Ported and green (432 passed, 10 skipped)

- Contracts: `schema.py` (Contract.execution_mode AUTO/STRUCTURED/VISUAL/CANVAS,
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
- OPEN: expanded cross-platform paired measurements, coherent feature commit
  and release/update verification. See DECISION_MODELS.md for the shared API and license notices.
  Default remains `Cloudflare/clef-flash`; d1 status remains `candidate`.
