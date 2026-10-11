# Blender operation recipes

These are semantic procedures to use through supported runtime contracts.
They are not executable tool names or a new keyboard API.

The default installation ships no trusted Blender state provider or provider
configuration path. All six registered families currently return `BLOCKED` on
missing facts there. The verified execution scope is the controlled API-assisted
fixture; do not present it as general Blender support. Inspect each operation's
`default_runtime_availability` before planning an invocation.

A successful operation verifies its typed effect and returns session
`NEEDS_REPLAN`. Verify the entire goal with a new input-free `ASSESS` contract.
Typed continuation requires an explicit operation to prevent repeating a prior
effect merely because guidance was supplied.

## Inspect an open menu

Use fresh input-free assessment. Include controls with menu absent, another menu
open, and duplicated labels elsewhere. A low-confidence result is not permission
to click until the requested state becomes true.

## Numeric transform

Before: known selection, correct editor/mode, no text focus, known keymap,
known scene units and local/world space, no conflicting modal operation.

Flow: start the intended transform; observe its modal state; constrain the
requested axis/space; enter the user's exact value; inspect preview; confirm;
verify the final change. On error, cancel only that known active operation.

The familiar G/X/number/Enter sequence is only an example for an applicable
keymap and context. Do not use it as a universal macro. A reference image does
not provide an exact scene-unit displacement without an explicit interpretation.

## Edit a property

Resolve one field in the right object/editor, focus it, replace with an approved
literal, commit only as requested, then read back the value. Treat IME composition
and keyboard layout as state. Test similar fields and wrong-object negatives.

## Orbit or pan

Resolve the configured middle-button/modifier gesture, keep it inside the target
viewport, and bound duration/path. On focus change or user intervention, release
owned input and stop. Reacquire subsequent mesh targets from the new view.

## Cancel a modal operation

Require evidence that the current operation is the one started by this session.
Cancel using the actual keymap. Confirm no unintended change was committed and
that no agent-owned input remains pressed.
Use the reported modal ID in an explicit same-session `modal_cancel` continuation.
Pending owned-modal recovery keeps the desktop leased and prevents automatic
service replacement or a competing goal. Complete that cleanup before updating
an active client; never discard the record to bypass a blocked recovery.

## Artistic review checkpoint

Save a scene checkpoint, render the same camera before/after, identify one major
mismatch, make a small change, and compare again. Technical success, avatar
likeness, rigging, expressions, physics, and target-application loading are
separate evidence categories.
