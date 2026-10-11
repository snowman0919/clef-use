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
Missing facts block input. The default screenshot provider cannot assert Blender's
hidden state. API-assisted fixture results do not prove pixels-only operation.
An operation report's `SUCCEEDED` verifies its typed effect. The session stays
`NEEDS_REPLAN` until a separate fresh `ASSESS` verifies the actual task goal.
The default installation supplies screenshots and possible native window identity,
but no trusted Blender application provider or public provider configuration path.
All six registered operations therefore return `BLOCKED` on missing verified facts.
Discovery exposes implemented schemas and this default availability separately;
it does not report a live `READY` state. Only the controlled `API_ASSISTED` Blender
fixture has verified these procedures. A general production provider remains an
open requirement; do not replace unknown focus, IME or popup state with assumptions.

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
Reaction coverage stays null/`NOT_MEASURED` without prospective eligibility and
policy evidence for every opportunity; fast successful inputs alone cannot pass
the release gate. Native event timestamps are distinct from backend ACKs.
No measured 100ms profile or release-gate success is currently advertised.
See [execution evidence](../EXECUTION_STATUS.md) and [acceptance](../../ACCEPTANCE.yaml).
