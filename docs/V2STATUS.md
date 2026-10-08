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

- F1 FIXED 2026-10-08: verified effect crops + facts now reach the next CLEF decision
  via Observation.evidence (runtime -> router -> clef_request -> ClefWorker multi-image). Regression
  test_effect_evidence.py reproduced the stale-completion failure red, green after fix.
  target-region change is captured (`last_effect["result_frame"]`, region_changed)
  but never enters the next decision record, so CLEF scores conditions low ->
  `COMPLETED -> NEEDS_REPLAN "lacks required visible condition evidence"`
  (runtime.py:599). Candidate general fix: pass the changed effect ROI crop as a
  second image (joint_schema_model supports `images * N`) or fold the verified
  `region_changed` fact into `record.state`. Requires real-model repro first.
- F2 LOW_CONFIDENCE after a single canvas stroke where the visual effect lags the
  observation round (trial-v43) — same root cause family as F1.

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
