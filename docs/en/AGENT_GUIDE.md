# Agent setup, use and recovery

Immutable .52 CI passes all fifteen native build/install jobs and assembly;
all fifteen archives match the pinned Git payload68 and contracts. Installer
logs prove first/update/CURRENT and checksum/download/smoke failure preservation.
The synthetic fixture ends at .53; the actual candidate is .52. Public deploy
is skipped by the feature guard. Windows .52 installation and LIMITED CLI/MCP
are NOT_RUN: SSH port22 and native Tailscale ping time out; the local backend
is online but the win peer reports offline. The outage cause is unproven.
Historical shared .49/owned .51 results are not revalidated here. Another
Windows operator remains confirmed, so input coordination is also required.
See the [.52 CI/transport receipt](../validation/2026-10-14/ci-and-windows-transport-0152.json).

In .52, `computer_capabilities.operation_id` advertises exact registered family
IDs. Omit it first, then select `operations[].family`; application names such as
`blender` remain unsupported. Real packaged normal/read-only MCP probes pass.
Native Hermes's three canonical cases pass; OMP positive cases still fail guide
order/deadline/denied-write checks and its negative passes. Credential-related
OMP database row changes remain unproven as to cause/material, and are not
restored. See [.52 evidence](../validation/2026-10-14/operation-schema-0152.json);
Windows .52 and GUI/performance proof remain NOT_RUN at this checkpoint.
Read-only OMP verification temporarily disables automatic-learning writers and
their native guidance, which can otherwise be force-added outside `--tools`.
Persistent settings stay intact. Actual SDK component checks pass; corrected
model cases retain explicit status/write/deadline and natural guide-order failures.

Immutable .51 CI passes fifteen native installer/archive checks. An owned
Windows .51 installation passes install/CURRENT WITHOUT integration-preview,
preserving shared .49 and existing profiles; zero foreign profiles refresh.
LIMITED-token CLI/MCP and edited/foreign-launcher refusal checks pass. Task
absence is observed, but its exit code was not recovered after controller SSH
timeouts. Native Codex .51, shared update and GUI/performance remain NOT_RUN
while another session operates Windows. See the
[.51 receipt](../validation/2026-10-14/windows-isolated-ci-0151.json).

Immutable .50 CI passes fifteen platform installation/archive checks. An owned
Windows candidate passes CLI installation, CURRENT, payload and LIMITED-token
MCP checks with `--integration-preview`, preserving shared .49 and active harness
registrations while another session operates Windows. Standard update, native
Codex .50 and GUI E2E remain NOT_RUN. See
[the candidate receipt](../validation/2026-10-14/windows-isolated-ci-0150.json).

OMP can carry a read-only MCP call through `write xd://<tool>`. Verification
requires matching native target/arguments/server/result and exact consumer
payload before credit; the method name alone cannot prove a file write or a
safe reader. Early invocation, actual denied writes and mismatches still fail.
See [source .50 evidence](../validation/2026-10-14/omp-device-evidence-0150.json);
native component, retained-trace replay and fresh model checks are separate.

Immutable .49 CI passes fifteen platform installer checks and archive/source
verification. Actual Windows .48 -> .49 update, repeat CURRENT, LIMITED-token
payload/MCP checks and original native Codex explicit/natural/negative cases pass.
These windowless checks do not verify GUI tasks or 100ms input latency. Earlier
Hermes/OMP failures remain recorded, and public deployment stays guarded. See
[the installed receipt](../validation/2026-10-14/windows-installed-ci-0149.json).

The runtime wheel includes three portable, instruction-only guides: `clef-use`,
`clef-use-blender`, and `clef-use-diagnostics`. Core and diagnostics are selected
by default; select Blender explicitly. Preview the exact paths before applying.
Only selected targets change. A first unattended installation does not enroll
harnesses without `--integrate codex|hermes|omp|all`. Model preparation is separate.

Read-only verification filters Hermes `skill_manage` from the native definition
factory, including MCP refresh and deferred catalogs, and denies its registry
execution. Native Skill readers and their original schemas remain available.
Reader usage metadata can still change; preserved guide/configuration bytes do
not imply all native generated state is unchanged. OMP verification waits for
live MCP discovery through its temporary startup policy; saved settings and the
declared model deadline remain unchanged.

Actual .48 owned Linux cache tests are recorded separately from installed Windows
checks. Hermes rejects cached completion evidence and verifies fresh Continue under
an explicit private read-only permission overlay. OMP's current-session-default
cache subcheck succeeds, but its early status-before-guide invocation keeps the
native case FAIL. Explicit-ID validation still fails after real status/cache reads.
Native OMP can advertise cached tools during its startup window; a temporary
`mcp.startupTimeoutMs: 0` waits for live discovery. Saved settings remain unchanged.
These read cases do not establish GUI input accuracy or 100ms latency. See
[the receipt](../validation/2026-10-14/linux-native-cache-0148.json).

Harness JSON streams are decoded as UTF-8 independently of the Windows locale.
A failed runtime call keeps verification FAIL even if a later capability call
succeeds. Discovery alone does not prove model guide loading or invocation.
File reads and advertised guide resources must match the full managed body.
Capability results must match runtime/schema/guide hashes and the read-only
two-tool facade. Loading the required guide after invocation fails the sequence.
An early runtime attempt stays FAIL after later guide loading, success or a
nonzero process exit. Native Skill catalog discovery remains distinct from runtime invocation.
Operation-detail replies must exactly match an operation in a previously verified
live catalog. A status reply alone does not verify the current capability catalog.

Codex can report command startup failures only in its private stderr trace, with
no JSON command event. A native runner pipe connection timeout remains FAIL as
`NATIVE_EXECUTOR_STARTUP_TIMEOUT`, even after later success or an error exit.
The report publishes only the phase, timeout, guide-attempt flag and evidence
digest. An attempted guide read does not prove its body loaded; this error does
not diagnose authentication or establish why the native runner failed.

MCP connection instructions apply only to authorized GUI work or explicit
clef-use capability/schema requests. Ordinary code questions and requests that
forbid runtime access do not select these tools. A read-only connection describes
its advertised capability/status tools and schema/guide resources. Capability
discovery does not need a running GUI service; status requires an existing
service/session and cannot discover Blender's hidden state.
In OMP, linked skill files use the native owning-skill reader, for example
`read(path="skill://clef-use/references/API_BASELINE.md")`. Preserve this URI instead
of converting it to `file://`. Discover resource readers before using MCP resources;
do not guess server aliases or resource addresses.

OmniParser preserves the caller's Torch thread budget across upstream imports,
including an explicit single-thread setting. No new thread setting is required.
This initialization fix does not establish whole-task completion or 100ms input
latency; verify those independently with the installed runtime.

Load the Blender guide for read-only menu/state assessment as well as editing.
Linked `references/` files belong to their owning skill. In Hermes, read the
baseline with `skill_view(name="clef-use", file_path="references/API_BASELINE.md")`.
Read-only GUI capability/schema questions also use these guides. Discover the
skill catalog, load core and the applicable Blender guide, then invoke runtime
tools; a no-input capability call still counts as an invocation.

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
The view baseline must also stay exact until the native gesture button is
acknowledged. An earlier independent view change cannot count as gesture success;
after acknowledgement, expected drag changes are allowed under the other guards.
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
location and scale properties for X/Y/Z. Discover operation registry v6 before use.
Numeric translation requires complete fresh `scene_units` and retains the same
scene conversion through input, readback and owned-modal cancellation. A stable
unit name alone cannot detect changed scene scale. Amounts/readback keep their
verified operation unit; NONE stays raw. Missing or changed conversion blocks
further input/success. Rotation and scale do not require scene length settings.
Angular readback must match DEGREES/RADIANS; exact-property coordinates remain raw.
Location `property_edit.value` means the raw Blender-unit coordinate. Fresh
`scene_units` evidence determines explicit meter input and stays anchored through
entry and readback; missing or changed settings stop input/success. Scale values
are dimensionless. Default display units never reinterpret the requested raw
coordinate. Actual readback must still meet the original tolerance.
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
Legacy X11 keyboard actions also validate current bindings before pressing keys,
including implicit Shift. A changed cached binding refuses input. Releases use
the acknowledged physical code, and an externally held key remains untouched.
Blender view-effect readback uses the effective view matrix and perspective mode
from one complete, unambiguous viewport. Region/layout/projection-only changes do
not prove orbit/pan; missing pose and ambiguous quad views remain unknown.
An operation report's `SUCCEEDED` verifies its typed effect. The session stays
`NEEDS_REPLAN` until a separate fresh `ASSESS` verifies the actual task goal.
The default provider remains `NONE`: screenshots and available native window
identity do not establish Blender's hidden state. An optional read-only Blender
observer is available on Linux X11 and Windows. `clef-use blender-observer-script` prints its
installed path. Use that exact path with your approved Blender executable and a
new, nonexistent directory under a private parent; the script creates the private
directory and endpoint. It does not attach automatically to an existing Blender.

```sh
clef-use blender-observer-script
blender --python "/absolute/installed/blender_observer.py" -- --clef-state-dir "/absolute/private/new-observer"
```

Set this top-level option in the runtime's `config.toml` (normally
`~/.config/clef-use/config.toml`, or the file selected by `CLEF_USE_CONFIG`):

```toml
blender_state_socket = '/absolute/private/new-observer/state.sock'
```

The listener starts from the first Blender UI timer. Linux association requires
Unix `SO_PEERCRED` and the XRes kernel process identity. Windows uses an explicit
`127.0.0.1` listener: `state.sock` is private NTFS port metadata, not a Unix socket.
The native TCP peer PID and process token user must match the foreground process.
Both platforms require a unique RNA window/client with matching physical pixel
dimensions and unchanged native foreground focus. A blocked UI timer leaves the
provider unavailable; it does not establish idle. The observer reads window,
selection, object mode, raw transforms/units, viewport and positive modal-operator
records; it does not change scenes or invoke operators. Popup, text focus, IME,
effective keymap and global idle state remain unknown. An empty operator list
does not prove absence. All six operations still return `BLOCKED` when their
required verified facts are missing, including with this partial observer.

The observer retains the owning manager's public `interface_locked` Boolean when
available. Only `true` establishes the positive busy fact `loading=true` after
native identity, window and freshness checks. `false` or unavailable leaves
`loading` UNKNOWN: an unlocked manager can still have a modal or other input owner.
This fact cannot authorize input or establish idle.

`active_tool` identifies a configured VIEW_3D workspace tool for the independently
bound native context mode, with workspace and observed area IDs. Missing or
ambiguous evidence stays UNKNOWN. Focused editor and effective dispatch remain
UNKNOWN; this fact alone cannot authorize input. The collector reads initialized
references without creating or refreshing tools and refuses more than 128.

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
`INVOKED` requires a successful tool response; a completed transport event with
an MCP error does not pass. Negative triggers reject tool-call attempts even when
the call fails, so a rejected request cannot conceal unwanted triggering.
Explicit errors make `INVOKED=FAIL`; missing or incomplete results remain `NOT_RUN`.
Task verification separately requires authorized input in an isolated target,
fresh external state checks and input/process cleanup. A private API-assisted
task pass does not establish production availability or whole-goal completion.

`MODIFIED` or `CONFLICT` preserves your edits. Pre-existing guide conflicts leave
a comparison under the integration state directory. Changes during capability
discovery stop activation before journaling, including new or removed guide files;
preview and unchanged plans also recheck ownership. Explicit disabled entries
remain disabled. Reload
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
With an explicit input context, modifier gestures also require known idle IME and
no text focus before moving or pressing. Ordinary pointer gestures remain separate.
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
Windows held-key checks preserve extended scan codes and modifier sides; they
refuse a distinct human hold before further input. Same-virtual-key physical
aliases (such as both Enter keys) cannot be distinguished by this query.
The Windows guardian removes successful key/Unicode release acknowledgements;
later parent EOF does not release those inputs again after a new owner acquires them.

Installed Windows 0.1.36 validation observes left/right/middle clicks and bounded
Shift-held left/middle drags in a disposable non-text canvas. Cancellation releases
Shift and middle-button holds while the worker remains blocked; a separate guardian
also releases them after the owned worker process terminates. This fixture disables
IME only on its own receiver. It does not establish automatic IME discovery,
Blender orbit/pan semantics or harness-driven GUI completion.

A separate installed 0.1.36 component verifies actual CLI/HTTP service abort:
Shift/middle input is released while its injector remains blocked, and the
cancelled injector refuses further input after unblocking. It uses an explicitly
registered session and owned non-text receiver. Full gesture/Blender operation
admission remains unverified.

A separate installed Windows 0.1.37 component suspends all worker threads through
documented debug APIs. With the attach breakpoint pending and heartbeat unchanged,
the separate guardian releases Shift/middle input at the six-second lease deadline,
before worker EOF or parent release. After resume, the real watchdog cancels and
further input is refused. Worker/guardian exit and exact pointer/foreground cleanup
pass. This is partial input-recovery evidence, not full runtime/service operation
admission, Blender semantics, model completion or a latency/performance result.

Decision diagnostics retain the exact UTF-8 text-budget bytes (image excluded),
object/question counts and SDK-reported input tokens. `SDK_USAGE` means an integer
from 1 through 8192; missing usage is `UNAVAILABLE`, invalid reported values are
`INVALID`, both with a null count. These counters do not measure correct-target
coverage, calibrated confidence or model latency.
Decision candidates retain their operation and observed target ID so equally
labelled controls can be distinguished by position. This preserves the mapping;
it does not certify correct selection or relax confidence guards.
Parser objects keep exact geometry and conflicting action/confidence/source
evidence separate; only equivalent normalized records deduplicate. An explicit
visual primitive filters structured proposals before budgeting, so unrelated
literal alternatives cannot evict a requested click or scroll.
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

Windows capture uses native GDI in a scoped per-thread physical coordinate context. It does not change process-wide DPI awareness. Capture must preserve an already-open window and its controls; a frame that changes their physical geometry fails validation. This capture correction does not certify Blender popup, focus, IME or keymap state, nor the 100ms reaction gate.

Actual native Windows Codex verification separates discovery/load/invoke from GUI task success. A completed tool response with LOW_CONFIDENCE is a failed task, even when a prior click was correct. Retain allowed candidate rosters, independently measured physical target geometry and actual widget outcomes; do not lower confidence guards to turn invocation success into task success.

Hermes live verification retains the native event stream and reads only its exact
session through the installed harness's read-only session-export API. Complete
guide bodies and runtime responses must match the stream's original bytes,
session/call identities and managed contract. Native spillover is confined to the
selected profile and call. A truncated preview, error, ambiguous call or unavailable
export cannot prove invocation; unavailable complete evidence is NOT_RUN. Failed
calls remain recorded even when a later capability call succeeds. Native catalog
loading and model-trigger verification have separate stages.
Hermes filters parent environment variables before spawning MCP servers. Verification
sets the selected managed server's read-only flag in native in-memory registration,
preserving on-disk configuration, authentication, model selection and the native CLI
prompt. The live two-tool capability/status schema must match before model work
starts. Parallel responses require a unique full-response or bounded-preview match;
shared prefixes remain ambiguous. Any effectful tool attempt fails verification.
This enforces the MCP scope, not a whole-process write sandbox: the native
`skills` toolset also exposes `skill_manage`. Such an attempt fails the verifier;
the reported session evidence must distinguish observed calls from permissions.

OMP's initial tool list can be expanded by native lazy registration. Verification
uses a temporary native approval overlay to deny the writer and existing non-probe
grants, preserve reader deny/prompt and retain argument-sensitive read tiers.
Complete native SDK results use a bounded private file; full guide bodies and
runtime/schema contracts must agree. Any failed or unexpected tool attempt remains
a failure, including before a deadline or later successful capability call.
Verification shares the managed integration lock, and native helper failure stops
model startup. On-disk user settings are preserved and the overlay is removed.
Latest [actual Windows .41 installation](../validation/2026-10-13/windows-installed-ci-0141.json)
passes CI15/15/update/repeat; previous whole-task failures and numeric gates remain separate.

The current Windows state provider combines native UI Automation evidence with
the optional Blender provider. Its standard-library base-Python worker proves
its actual PID at readiness and uses a 500 ms query timeout. Each result binds
native foreground observations before and after the query to the same focused
UIA element, process identity, ancestor chain and bounds. For a supported
TextEdit, `GetActiveComposition` returning `S_OK` with a null composition
means `False`; unsupported interfaces, errors and stale or mismatched evidence
remain `UNKNOWN`. Focused-control identity additionally binds its opaque UIA
runtime ID and physical bounds. Writability requires explicit enabled and
non-password properties plus a strict Boolean IsReadOnly attribute from the
separately registered TextPattern document range. TextEdit composition support
alone does not establish this. No text content is read. These facts do not
establish popup ownership, keymap state, global idle or Blender operation
admission. Installed 0.1.39 verifies active composition refusal through InputIR
but reproduces an unsafe legacy type bypass. The immutable installed 0.1.40
correction separately passes exact Unicode, four active-composition refusals,
selection/deletion, Enter focus transition and independent abort/recovery checks.
Its actual Codex GUI task still fails the unchanged mode-confidence gate, and
the browser model task times out in parsing. Input delivery, task success and
the 100ms performance gate remain separate. See the
[installed receipt](../validation/2026-10-13/windows-installed-ci-0140.json).

Windows model keyboard actions use the State Compiler and typed InputIR. A literal
target must already match the writable focused control; typing never clicks a
field implicitly. Unknown IME, identity or writability refuses input. A fresh
guard checks focus and composition before each native unit. Keyboard/modifier
input requires observed context and a live guard, except explicit Escape and
owned recovery releases. Missing context is never an idle-IME assumption.
After an acknowledged one-shot Enter, focus may move; the post-input check binds
the original native window/process/thread and authorizes only release/accounting.
Delivered but unverified input consumes its action budget and returns NEEDS_REPLAN;
delivery alone never proves goal completion.

Windows native input checks its failsafe before dispatch and no longer imports
PyAutoGUI. An installed 0.1.38 probe changed owned-window geometry from
`[210,210,1638,1066]` to `[120,120,936,609]` before sending input; input count
was zero. A source correction on the same path preserved geometry. That is
source-only evidence, not an installed 0.1.38 pass. No 100 ms performance
claim follows.

Window bounds are physical on watchdog threads too. Owned Windows validation
maps widget points to physical bounds and checks native receiver ownership
before input; a successful capture does not establish input geometry.
Button-down and wheel events also require the native pointer recipient's root
window to match the bound foreground window. A matching foreground alone does
not authorize input to another window. Owned recovery releases remain available.
