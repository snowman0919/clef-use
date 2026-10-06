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

## Deployed installation observations

OBSERVED: implementation commit `664338e25a11e8515588c9f863c9b5432799c33b`
passed all six [CI jobs](https://github.com/snowman0919/clef-use/actions/runs/37449160887).
All 15 native package/installer jobs, assembly and the dev deployment passed in
the [release workflow](https://github.com/snowman0919/clef-use/actions/runs/37449625691).
The deployment returned `DEPLOYED`, version `0.1.23`, targets `15`.
Public latest and immutable release manifests agree; the previous 0.1.22
immutable manifest remains unchanged. Root and immutable bootstraps match the
source bytes; the downloaded Linux x86_64 Python 3.11 archive matches its SHA-256.

OBSERVED: the public bootstrap installed 0.1.23 in an isolated task prefix and
returned `CURRENT` on a second invocation. All six changed installed modules
match the implementation source hashes. Stdio MCP uses that installed Python
without `PYTHONPATH`. The existing protected desktop and global installations
were not updated by this isolated installation.

OBSERVED: fresh pre-session observation returns `session_id: null`, a full frame
reference and `observation_fresh: true`. One supplied stroke bound to that frame
was delivered on the disposable Blender scene. Both X mirror flags read true;
106 left and 106 right vertices changed. Independent background reopening matches
all 24,386 saved coordinates. Runtime visual readiness was `STABLE`, then the
model proposed completion with goal 0.7372 and condition 0.8211. The unchanged
0.9 gate returned `NEEDS_REPLAN` with `COMPLETION_UNVERIFIED`, the original
condition, its probability and observation ID. Exactly one input was delivered.
This validates the missing-evidence diagnostic; autonomous Blender completion
remains unresolved.

OBSERVED: the installed package completed the native Continue/Confirm task with
two native callbacks and four model decisions in 13.683852 seconds. Two fresh
positive observations had goal 0.9588 and condition 0.9782. Independent UI readback
and a fresh screenshot show `Task complete`. This single run is an execution
check, not a whole-task performance comparison.

The idle installed test service was shut down normally; the owned native GUI,
Blender and Xvfb were stopped. Protected Blender and Xvfb processes remain.
[Deployed measurements and results](runtime-0.1.23-deployed.json) preserve
package provenance, installer outputs, actual model/input results and cleanup.
