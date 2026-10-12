# Anchor scene units for raw location property edits

Status: accepted software contract, 2026-10-12.

`PropertyEdit.value` is compared with raw Blender `Object.location` readback.
Bare numeric field input uses the scene's display unit, so a requested raw value
of 2 can commit 0.02 in a centimeter field before readback reports failure.

Location edits require fresh trusted `scene_units` evidence containing scene
identity, system, default length unit and scale. Unit-enabled fields receive an
explicit meter literal computed from the raw coordinate and scene scale; NONE
receives the raw coordinate. Scale fields remain dimensionless. The operation
anchors scene units through refresh, native input and final readback. Missing,
malformed or changed units cannot authorize further input or success.

The bound read-only Blender provider publishes this positive scene evidence
without asserting field focus, modal input units, coordinate space or operation
readiness. Registry v5 advertises conditional requirements and value semantics;
requests retain the existing field/value schema.

Alternatives: interpreting the requested value in the visible display unit would
change the existing raw readback contract. Requiring the modal `unit` fact would
conflate a transform operator's context with a property's scene conversion.
Checking only after commit leaves the unintended application mutation in place.
Blocking all property edits would unnecessarily reject dimensionless scale.

Costs: location providers must supply complete scene-unit evidence; conversions
can incur application rounding and must still satisfy the unchanged tolerance.
Overflow or nonzero-to-zero conversion is refused before input. This decision
needs revision if a supported field has different RNA units or custom parsing;
such fields are outside the six registered object location/scale fields.

Verification is recorded separately in `docs/EXECUTION_STATUS.md`; component
results do not establish general production field discovery or whole-task E2E.
