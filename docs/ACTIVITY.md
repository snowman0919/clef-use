# Desktop activity display

Starting `clef-use run "goal"` or MCP `computer_run` with the desktop runtime
shows a small, nonactivating status panel and a separate agent cursor. The
runtime reports screen reading, control detection, decision, target checking,
action and result verification. The cursor marks the same target coordinates
used by the input backend; it never moves the physical pointer on its own.
Completion, intervention and abort status remain visible for three seconds.
The existing five MCP tools are unchanged; session results now include `activity`.

The panel displays the action name, target label and action/decision counts.
Typing payloads and raw goals are never sent to the display process. Sensitive
fields use `Hidden field` instead of their label. This is progress reporting,
not a display of private model reasoning.

The native windows pass through mouse input and do not take focus. macOS
excludes their window IDs from capture at nominal resolution; Windows uses
`WDA_EXCLUDEFROMCAPTURE` when available. Other capture paths hide the display,
wait for its acknowledgement, capture, and restore it. A failed display process
is removed before capture continues. Display failure does not stop the task.
The Linux hide path includes a 35 ms settling interval.

The implementation uses existing Pillow and macOS dependencies, stdlib Win32,
and system X11/Xext. There is no browser server, Qt, Electron or new Python
dependency. macOS and Windows native displays were exercised; Linux X11 was
exercised under Xvfb. Wayland has not been validated. Unsupported displays
report `activity.display = "unavailable"` while normal runtime work continues.
Set `activity_overlay = false` in the existing configuration and restart the
runtime to disable the display.

Native checks use disposable owned windows. Windows verifies a real click
through the marker, unchanged foreground and no pointer movement caused by the
display. Capture checks compare the stable marker region before/after display;
macOS also checks capture dimensions and that exclusion works without hiding.
These checks do not exercise model inference or arbitrary application workflows.
See [evidence](evidence/activity-overlay.json) and
[diagnostic](../scripts/activity_smoke.py).

The separate agent cursor follows the interaction pattern described by
[cua's agent cursor documentation](https://cua.ai/docs/cua-driver/reference/mcp-tools/agent-cursor).
Reference source: trycua/cua commit
`f83bd7a5c0bbf4213ab8539e9793f53e580297f0`,
`libs/cua-driver/rust/crates/cua-driver-core/src/agent_cursor.rs`.
This is an independent implementation; cua code and dependencies are not bundled.
