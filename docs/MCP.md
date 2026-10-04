# Canonical MCP contract

Five tools are exported: `computer_run`, `computer_continue`, `computer_observe`,
`computer_status`, `computer_abort`. Runtime execution is inside one service;
MCP calls do not expose per-click primitives.

`computer_run(goal, success_conditions=[], constraints=[], max_steps=30,
confidence_threshold=0.55, text_inputs=[])` returns structured session status.
`text_inputs` contains exact `value` and optional `target_label`; text inferred
from a goal is limited to quoted strings and numeric expressions. No arbitrary
model-generated strings or coordinates are accepted.

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
