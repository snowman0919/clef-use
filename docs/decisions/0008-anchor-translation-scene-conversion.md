# Anchor translation scene conversion

Status: accepted software contract, 2026-10-12.

Numeric transform amounts and readback use the verified matching operation unit.
The unit name alone cannot identify Blender's length conversion: at an initial
location of zero, changing scene scale from 1 to 100 preserves METERS and the
normalized baseline. Bare input 2 then moves raw location by 0.02 instead of 2;
normalized readback still reports 2. Success must not cross that changed context.

Every numeric translation requires complete validated `scene_units`, including
scene identity, system, default length unit and actual positive finite scale.
The runner anchors them before entry, through refresh and input, and at final
readback. The native input guard independently checks them, including cancellation
of a translation modal. Missing or changed conversion stops further input or
success. NONE also retains the scene binding; its numeric value remains raw.
Rotation and scale do not acquire a length-conversion requirement.

Registry v6 advertises conditional translation and translation-modal cancellation
requirements without changing request schemas. Property location edits retain
their existing raw-coordinate/explicit-meter contract. Numeric transforms retain
bare numeric input and their existing normalized readback contract; this change
does not guess effective units or reinterpret requests.

Alternatives: comparing only the unit label misses scale and scene changes.
Comparing final normalized values alone can validate input performed across the
changed context. Requiring scene length settings for rotation or scale adds no
protection against this conversion defect. Automatically cancelling after context
drift would send an unverified shortcut; retain unresolved ownership instead.

Costs: translation providers must supply complete fresh scene-unit evidence in
addition to independently verified numeric input/readback units. This does not
make the optional partial observer operation-ready. Verification levels and
remaining native/installation/task limits are recorded separately.
