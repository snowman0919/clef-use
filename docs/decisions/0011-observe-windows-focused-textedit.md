# Observe focused Windows TextEdit composition conservatively

Status: accepted implementation boundary, 2026-10-13.

The Windows state provider combines native UI Automation evidence with the
optional Blender provider. Its worker runs under base Python with the standard
library, proves its actual process ID at readiness, and limits each query to
500 ms. A result is accepted only when native foreground observations before
and after the query bind to the same focused UIA element, process identity,
ancestor chain, and bounds. This ties the text fact to one current foreground
control instead of treating an arbitrary UIA element as active input context.

For a supported TextEdit, the native `GetActiveComposition` query returns
`S_OK` with a null composition when no composition is active; that result maps
to `False`. An unsupported interface or query error does not mean composition
is absent. Stale evidence, mismatched foreground or element identity, and
unsupported or failed queries map to `UNKNOWN`.

The original 0.1.39 boundary does not observe writability. The subsequent
[compiled keyboard contract](0012-guard-model-keyboard-through-compiled-focus.md)
adds explicit focused-control identity and separate TextPattern read-only
evidence. Neither boundary establishes popup ownership, effective keymap,
global idle or Blender operation admission. Installed 0.1.39 active-composition
refusal and its legacy bypass are recorded separately; they do not establish
whole-task end-to-end success.

Foreground identity alone is insufficient for pointer input: a different native
window can receive a click while the bound foreground check still passes.
Before button-down or wheel injection, Windows input checks the physical cursor
recipient's native root against the bound window. A mismatch sends no event.
Recovery releases remain independent of this admission check. A two-window
owned fixture reproduced the incorrect delivery before this guard and zero
receiver events after it; this does not establish general task accuracy.
