---
name: clef-use-blender
description: Use clef-use for Blender GUI editing, selection, transforms, viewport gestures, materials, or rig inspection. Check editor, mode, keymap, and effects. Not a primitive avatar generator or a substitute for asset-quality review.
metadata:
  guide-contract: "1"
  authored-against: "0.1.29"
---

# Blender with clef-use

Use the core `clef-use` guide when available and inspect current server schemas.
This document describes safe workflows; operation names below are semantic
intent, not invented MCP tools or proof that the installed release supports them.

## Establish the scene and context

Preserve the user's open scene. Use a named checkpoint before material edits.
Confirm the actual Blender version/keymap and the intended scene, selection,
editor, mode, active tool, text focus, and modal operation. Missing information
is unknown, not a default value. Do not execute shortcuts into an unknown editor.

Use fresh screenshots and available native state. A read-only Blender inspector
can assist when permitted, but label it app-telemetry-assisted. An evaluation
oracle may verify the result without leaking its answer into the visual policy.

## Choose the operation

Prefer a supported registered operation or a bounded high-level GUI goal over
listing every button. For dense controls consider a supported command-search,
region refinement, or semantic target path. Verify keymap bindings; do not assume
F3, G, modifier combinations, or Ctrl/Command substitution always apply.

Read [operation recipes](references/OPERATIONS.md) for preconditions and effects.
A missing keyboard/chord/MMB capability is a product limitation: do not disguise
console scripting as a working GUI operation.

## Execute bounded edits

Separate exact text/numeric input from key shortcuts, modal confirmation, and
modifier-held pointer gestures. Bind input to the current window/editor/state.
Release only agent-owned keys/buttons and stop on user intervention or context
change. Cancel a known active operation rather than repeatedly pressing Escape.

After viewport orbit, zoom, or layout change, reacquire the editing target. A
previous cheek/hair coordinate does not remain valid through a camera change.
Do not run a long blind brush path; use short bounded segments and verify effects.

## Validate results

For a transform, verify the actual selected object/mesh effect and coordinate
space, not merely that keys were delivered. For a property, verify the field
value. For a modal cancel, verify the intended operation ended without committing
an unintended edit. Compare against a restored baseline in regression tests.

For artistic edits, compare matched front/three-quarter/side views to actual
references. Keep technical export success separate from identity and visual
quality. A connected independent visual reviewer must inspect actual images,
not the producer's summary. Missing review is pending, not a pass.

## Dogfood rather than bypass

When clef-use fails, preserve the exact observation and request privately,
classify the failure, repair the general runtime when authorized, then retry
that same operation. Passing a mock test alone does not close the original issue.
Blender MCP/Python may support inspection, repetitive utilities, or validation;
do not replace the main clef-use editing workload with a giant generation script.

Record whether each result was pixel-only, accessibility-assisted,
app-telemetry-assisted, or API-assisted. Keep restricted bases, textures,
reference images, and raw scene captures out of public code releases.
