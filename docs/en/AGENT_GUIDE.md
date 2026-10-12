# Agent setup, use and recovery

The runtime wheel includes three portable, instruction-only guides: `clef-use`,
`clef-use-blender`, and `clef-use-diagnostics`. Core and diagnostics are selected
by default; select Blender explicitly. Preview the exact paths before applying.
Only selected targets change. A first unattended installation does not enroll
harnesses without `--integrate codex|hermes|omp|all`. Model preparation is separate.

Load the Blender guide for read-only menu/state assessment as well as editing.
Linked `references/` files belong to their owning skill. In Hermes, read the
baseline with `skill_view(name="clef-use", file_path="references/API_BASELINE.md")`.

OMP resolves `PI_CONFIG_DIR` as a name relative to HOME (default `.omp`). Use
`PI_CODING_AGENT_DIR` for an absolute default agent directory. An explicit empty
or `default` `OMP_PROFILE` selects the default even when `PI_PROFILE` is set.

If the registered executable points to an immutable older installation, `refresh`
preserves that path and refuses incompatible new guides. `--command-path` also
preserves an existing registration. Review managed removal with `--dry-run`, remove
only unchanged managed entries, then enroll with the current executable's
`--command-path`. User edits and disabled-entry conflicts remain preserved.

<!-- clef-use:commands -->
```sh
clef-use capabilities --json
clef-use capabilities --detail --json
clef-use capabilities --operation-id numeric_transform --json
clef-use integrate codex --dry-run
clef-use integrate codex --scope user --skills core --skills blender --skills diagnostics
clef-use integrate hermes --scope user
clef-use integrate omp --scope user
clef-use integrations status --json
clef-use integrations verify codex --live --read-only
clef-use integrations remove codex --dry-run
clef-use integrations refresh --managed-only
```

Discover current schemas before submitting a bounded goal. Supply exact literals;
do not mix text with shortcuts or assume a keymap. `ASSESS` sends no input. Cached
observations cannot authorize pointers or prove final completion. Registered local
operations are finite typed procedures, separate from Agent Skill prose. They need
verified editor, selection, mode, IME and keymap facts from a trusted local provider.
With trusted facts, guards compare keymap content as well as its version label.
Viewport editor geometry is rechecked before and during gestures; a change stops
execution and releases owned input.
Numeric transforms require full XYZ translation, rotation and scale readback.
The transform context is rechecked before input, the initial values before entry,
and the verified preview before commit. A partial vector cannot verify unchanged
axes. Property edits compare all observed fields and object identities afterward;
this does not establish preservation of fields that were never observed.
Numeric literals preserve the requested float; application readback must still
meet the requested tolerance.
Changing operations and owned cancellation require a complete stable
`selection_identities` map. Blender supplies process-scoped public `session_uid`
IDs; a rename preserves the ID, while replacing an object under the same name
blocks further input. Missing IDs remain unknown. The observer also exposes
location and scale properties for X/Y/Z. Discover operation registry v4 before use.
Missing facts block input. The default screenshot provider cannot assert Blender's
hidden state. API-assisted fixture results do not prove pixels-only operation.
Capture-derived coordinates and foreground facts retain capture time; slow capture
or processing cannot renew them. Current provider facts keep their own timestamps.
Windows literal input validates UTF-16 before sending and rechecks the current
guard at every native unit. Cancellation/deadline is rechecked after state sampling.
On X11, confirmed cancellation before the paste attempt releases owned modifiers
and restores supported prior clipboard formats after native acknowledgement.
Concurrent copies are preserved. If paste delivery is possible, offered text is
retained for the queued paste; unacknowledged recovery remains unresolved.
Blender view-effect readback uses the effective view matrix and perspective mode
from one complete, unambiguous viewport. Region/layout/projection-only changes do
not prove orbit/pan; missing pose and ambiguous quad views remain unknown.
An operation report's `SUCCEEDED` verifies its typed effect. The session stays
`NEEDS_REPLAN` until a separate fresh `ASSESS` verifies the actual task goal.
The default provider remains `NONE`: screenshots and available native window
identity do not establish Blender's hidden state. An optional read-only Blender
observer is available on Linux X11. `clef-use blender-observer-script` prints its
installed path. Use that exact path with your approved Blender executable and a
new, nonexistent directory under a private parent; the script creates the private
directory and socket. It does not attach automatically to an existing Blender.

```sh
clef-use blender-observer-script
blender --python "/absolute/installed/blender_observer.py" -- --clef-state-dir "/absolute/private/new-observer"
```

Set this top-level option in the runtime's `config.toml` (normally
`~/.config/clef-use/config.toml`, or the file selected by `CLEF_USE_CONFIG`):

```toml
blender_state_socket = '/absolute/private/new-observer/state.sock'
```

The listener starts from the first Blender UI timer. Association requires Unix
`SO_PEERCRED`, the XRes kernel process identity, a unique RNA window/client with
matching dimensions, and native foreground focus. The observer reads window,
selection, object mode, raw transforms/units, viewport and positive modal-operator
records; it does not change scenes or invoke operators. Popup, text focus, IME,
effective keymap and global busy/idle state remain unknown. An empty operator list
does not prove absence. All six operations still return `BLOCKED` when their
required verified facts are missing, including with this partial observer.

`keymap_inventory` preserves relevant merged user bindings, duplicate/inactive
entries, tri-state modifiers (`-1` means any) and a content digest. It is raw
inventory, not the effective `keymap` or `keymap_version`. `editor_layout` maps
area/region rectangles to screen pixels and capture coordinates; hidden, clipped
or off-capture rectangles have no normalized box. It does not establish focused
editor, popup ownership or a verified gesture surface. Inventory limits refuse
the snapshot rather than dropping bindings.
Linux input coordinates use the captured monitor's size, including on a larger
multi-monitor X11 root; inconsistent capture/input extents refuse Blender state.

A fresh observe response can expose `compiled_state`, `state_provider_status`
and `state_pixel_association`. State has its own observation ID, is sampled near
capture before parsing, and can expire while parsing. `FOREGROUND_WINDOW_ONLY`
association is not pixel-synchronous scene evidence. Discovery describes schemas
and default availability, not live `READY`. The existing `API_ASSISTED` fixture
verification does not verify this new production path; full production operation
support remains open. Never replace unknown dispatch context with assumptions.

Continuing a typed operation session requires an explicit `operation` request
(`clef-use continue ... --operation '<JSON>'`); planner guidance alone cannot repeat
the preceding effect. To verify the complete original goal, create a new
`computer_run` contract with `execution_mode="ASSESS"` and no `operation`, or use
`clef-use run "Verify the complete original goal" --mode ASSESS`.
Use `integrations verify ... --trigger natural|explicit|negative|native` to keep
model triggering distinct from native catalog/guide/MCP adapter verification.

Integration stages are separate: `INSTALLED`, `DISCOVERED`, `LOADED`, `INVOKED`,
`TASK_VERIFIED`. A copied file, tool list, or guide-name echo proves no later stage.
Live trigger verification uses a fresh harness session with read-only tools;
provider authentication failure leaves loading and invocation `NOT_RUN`.
Task verification separately requires authorized input in an isolated target,
fresh external state checks and input/process cleanup. A private API-assisted
task pass does not establish production availability or whole-goal completion.

`MODIFIED` or `CONFLICT` preserves your edits and leaves a comparison under the
integration state directory. Explicit disabled entries remain disabled. Reload
cached clients after a compatible update; inspect capability versions first.
Local requests bind the executable version, runtime protocol and API fingerprint.
An older client cannot stop or control a newer service; reload the current
executable and MCP session after a mismatch. A newer client may replace an idle
older service, but active input or modal recovery blocks replacement. Finish or
abort an active older session through its retained matching executable first.
An immutable old client may display a generic refusal instead of the server's
reload guidance. Same-version protocol/schema mismatches require explicitly
stopping the idle service before reloading; they are never silently restarted.
Uninstall removes unchanged managed entries only. Hermes project scope is unsupported;
use its selected user profile. Inspect source/shadow status before moving guides.

Cancel only your own session; verify owned input release. Exact Unicode clipboard
insertion and IME composition are distinct; active or unknown IME blocks shortcuts.
X11 left/middle/right buttons and wheel directions follow the current OS pointer
mapping. Disabled logical buttons refuse input. Normal release, independent abort
and guardian recovery release the physical button acknowledged at press.
X11 literals require the explicit clipboard method, including ASCII; keyboard
events can enter an idle IME instead of inserting the requested characters.
Clipboard transfer is not widget readback. Unsupported prior clipboard formats
refuse before input. If cancelled before consumption, the owned literal remains
available for a queued paste until transfer or another copy; previous data is not
restored early. Windows operations use native Unicode insertion.
Watchdog recovery is limited by native permissions and acknowledgement windows.
Decision diagnostics retain the exact UTF-8 text-budget bytes (image excluded),
object/question counts and SDK-reported input tokens. `SDK_USAGE` means an integer
from 1 through 8192; missing usage is `UNAVAILABLE`, invalid reported values are
`INVALID`, both with a null count. These counters do not measure correct-target
coverage, calibrated confidence or model latency.
Decision candidates retain their operation and observed target ID so equally
labelled controls can be distinguished by position. This preserves the mapping;
it does not certify correct selection or relax confidence guards.
Literal-text candidates retain every matching observed input, including equally
labelled fields. If those alternatives exceed the configured action budget,
structured execution requests replanning before a model call or input; narrow
the target scope rather than assuming that the first field is correct.
Missing targets or more than 40 distinct executable targets are refused instead
of silently removing their observed geometry from the decision context.
Reaction coverage stays null/`NOT_MEASURED` without prospective eligibility and
policy evidence for every opportunity; fast successful inputs alone cannot pass
the release gate. Native event timestamps are distinct from backend ACKs.
No measured 100ms profile or release-gate success is currently advertised.
See [execution evidence](../EXECUTION_STATUS.md) and [acceptance](../../ACCEPTANCE.yaml).
