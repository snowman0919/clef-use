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
for an exhausted or aborted session. Observe reads the latest session observation,
visible objects, recent actions and goal. `include_image=true` returns MCP PNG
content at up to 1280 pixels; there is no permanent screenshot file or cloud
upload. Status/abort accept an optional session ID (latest session by default).
Cancellation of a running MCP request also aborts its session.

Use a long harness tool timeout (3600 seconds) for cold model loads and bounded
multi-step sessions. No timeout authorizes extra steps. Setup examples are in
[HARNESS_SETUP.md](en/HARNESS_SETUP.md).
