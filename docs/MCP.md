# Canonical MCP contract

Five tools are exported: `computer_run`, `computer_continue`, `computer_observe`,
`computer_status`, `computer_abort`. Runtime execution is inside one service;
MCP calls do not expose per-click primitives.

`computer_run(goal, success_conditions=[], constraints=[], max_steps=30,
confidence_threshold=0.55, text_inputs=[], pointer_inputs=[])` returns structured session status.
`text_inputs` contains exact `value` and optional `target_label`; text inferred
from a goal is limited to quoted strings and numeric expressions. No arbitrary
model-generated strings or coordinates are accepted. A planner may explicitly
submit inspected pixel paths using the bounded `pointer_inputs` contract below.

## Inspected canvas paths

`computer_observe(include_image=true)` supplies `frame_reference` alongside the
image. Copy that reference unchanged into each pointer input. It binds the exact
pixels, image dimensions/mode, monitor origin, logical coordinate size and
available foreground-window identity/geometry. Normalized coordinates refer to
the entire observed image, including when its PNG is downscaled for transport.

Each pointer input contains:

- `operation`: `click` for exactly one point, or `stroke` for 2-128 points.
- `label`: the planner's nonempty description of the inspected target/path.
- `reference`: the observation's `frame_reference`.
- `surface`: a normalized `{x1,y1,x2,y2}` rectangle containing every point.
- `points`: normalized `{x,y}` points, all within that surface.
- `duration`: 0.05-5 seconds for a stroke (default 0.5).

Up to eight paths may be offered in one run. With nonempty `pointer_inputs`,
only these paths become candidates; unrelated detected controls are not offered.
CLEF still selects the action and evaluates its effect/completion. There is no
per-click MCP tool, forced execution or confidence-threshold bypass. Paths are
recorded in action/model history as planner-supplied pixels, not parser-detected
controls. Click/stroke delivery uses the left mouse button; tablet pressure,
right-button gestures and arbitrary keyboard shortcuts are not supported.

The candidate builder and input adapter refuse stale references, sensitive
surface overlaps and points outside captured foreground bounds when available.
Delivered quantized coordinates must also remain inside the supplied surface;
sensitive-overlap checks conservatively pad it by one input-coordinate pixel to
cover rounding, pixel coverage and every interpolated stroke segment.
Immediately before input the runtime requires an exact matching fresh frame,
not merely the usual screenshot-change tolerance. A stroke releases owned input
on completion, cancellation or error, and rechecks native Windows foreground
identity/geometry during movement. These checks are not an OS sandbox; use an
isolated, nonsensitive desktop. Linux/macOS do not gain a native foreground-
identity guarantee from this feature.

After pixels change, an old path reference expires. Observe again and submit a
new run with newly inspected paths; `computer_continue` does not replace paths.
Visible change alone is readiness evidence, not successful modeling or drawing.

## Session results

Every run returns `session_id`, `status`, action `steps`, decision `rounds`,
`last_action`, `confidence`, `reason`, and `summary`. The states are COMPLETED,
NEEDS_REPLAN, LOW_CONFIDENCE, SAFETY_BLOCK, NO_PROGRESS, STEP_BUDGET_EXHAUSTED,
ERROR, ABORTED, plus RUNNING while status is polled.

Continue accepts `session_id` and `instruction`, only for replanning, low
confidence and no progress, within the remaining original budget. Use a new run
for an exhausted or aborted session. Observe refreshes the screen and object map while the runtime is idle. While
execution owns the desktop, it returns the latest cached observation with
`observation_fresh=false`. Objects, image hash and optional PNG share one
`observation_id`. Observation never consumes the action/decision budget. `include_image=true` returns MCP PNG
content at up to 1280 pixels; there is no permanent screenshot file or cloud
upload. Status/abort accept an optional session ID (latest session by default).
Cancellation of a running MCP request also aborts its session.

Use a long harness tool timeout (3600 seconds) for cold model loads and bounded
multi-step sessions. No timeout authorizes extra steps. Setup examples are in
[HARNESS_SETUP.md](en/HARNESS_SETUP.md).

## Startup update request

Since 0.1.10, each stdio MCP launch checks the canonical HTTPS release manifest.
A newer release must pass the installer's manifest/origin validation and provide
an artifact for the running OS, architecture and Python version. The server adds
an update request to `InitializeResult.instructions`, naming the installed/new
versions and asking the agent to run `clef-use update` when authorized, then
reconnect before GUI work. Clients receive it in the standard initialization
response; client behavior determines whether it is presented to the model.
The five GUI tools retain their existing contracts.

The startup wait is capped at three seconds. An offline host, timeout, malformed
manifest, incompatible artifact or older/equal release leaves normal MCP startup
available. This check requests an update; it does not install it in the server
process. Remote metadata contributes only a validated version, never executable
instructions. Tests include a real stdio initialization readback of the request.
