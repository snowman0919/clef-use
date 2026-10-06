# Runtime verification 0.1.23

2026-10-06 KST, canonical `/home/monad/develop/clef-use`, starting main
`c7ac423`. Existing Hermes changes in `docs/REICI_PRODUCTION.md` are preserved
and excluded from this commit. Evidence is restricted to the current dogfooding
period; earlier OOM statistics are not used as an improvement baseline.

## Corrections

- A completion choice and goal/condition probabilities answer different questions.
  Preserve the 0.9 gate and two fresh positive observations. Rejected completion
  now returns `COMPLETION_UNVERIFIED` with the goal, each condition, probability,
  count agreement, observation ID and required visible evidence for the planner.
- Parser input is only image pixels. Foreground/geometry-only changes previously
  invalidated perception unnecessarily. Reuse exact pixels with the same pinned
  parser; every new candidate and input still checks its complete fresh frame.
- Observe immediately after desktop preparation and before the first run. This
  creates no fake execution session or input/decision budget. Concurrent
  observations reserve desktop access and clearly mark cached/empty results.
- Existing parser timing mixed startup and all recognition stages. Record load,
  OCR, detection, fusion, caption/cache, encode/decode and normalization separately.
  Warm cache hits retain no previous load or inference timings.

## Source observations

OBSERVED: 292 regressions passed, four prepared-parser checks passed separately;
Ruff lint/format and whitespace checks passed. The full suite's four skips are
those prepared-parser checks. Completion/initial-observation regressions failed
before the correction and passed afterward. Stale geometry/foreground and
sensitive-path refusal remain exercised.

MEASURED: frozen 1280x900 Blender screenshot, pinned CPU parser, Torch
2.11.0+cpu, eight threads, Florence float32/default768 resize. Five alternating
metadata-only frame changes in one resident real worker: baseline median
2.344068 seconds (2.279933..2.388605), corrected cache median 0.001785 seconds
(0.001752..0.001954). All 161 ordered objects, labels, boxes and action sets
match. This improvement applies to identical pixels with changed metadata.
Cold caption computation remains expensive: 83 unique captions consume about
119 seconds in the instrumented pipeline. Single cold samples and shared host
load do not establish a cold-start or whole-task speedup.

OBSERVED: actual stdio MCP, canonical CUDA/NF4 CLEF and CPU OmniParser on the
owned `:110` Xvfb desktop completed a native Continue/Confirm task: two native
callbacks, four model decisions, `COMPLETED`, 17.804083 seconds. The UI's delayed
500ms transitions and final visible `Task complete` were read independently.

OBSERVED: a separate Blender 5.2.2 LTS scene preserves its original coordinates
through preparation and reads both Object and Mesh X mirror true. One actual
GUI Grab stroke changed 106 vertices on each side (212 total). Independent
background reopening verifies all 24,386 saved coordinates against live readback.
Application readback is independent input-result evidence, not CLEF completion.

The first stroke ended `CONDITION_UNMET` at visual readiness. A planner-guided
assessment used the remaining budget and delivered no further input. CLEF chose
completion but goal 0.3471 / condition 0.4876 failed the unchanged gate. The
returned diagnostic names the original condition and missing visual evidence.
Autonomous Blender completion remains unresolved; pixel/edge heuristics and a
single current image do not establish subtle comparative shape changes.

## Boundaries and provenance

CPU resize, thread settings, model revisions and thresholds are unchanged.
No new dependencies or GGUF/model-serving deployment. Native Windows/macOS
input is NOT_RUN. The protected user Blender and earlier Xvfb are untouched;
the separate idle Reici runtime was stopped only after explicit user approval.

[Source measurements and results](runtime-0.1.23-source.json) retain numeric
stages, hardware/profile, source hashes, contracts and status/readback distinctions.
Raw task-owned evidence is in `/tmp/clef-validation-20261006`; screenshots and
private production assets are not committed. Installer tests use a synthetic
0.1.24 update fixture that is never a published product version.
