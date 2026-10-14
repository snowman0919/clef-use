# Guard Windows model keyboard input through compiled focus

Status: accepted implementation boundary, 2026-10-13.

Installed 0.1.39 correctly refuses literal InputIR during actual native RichEdit
composition, preserving exact preedit bytes and text. The same owned fixture's
legacy DesktopAction type path instead ends composition and inserts Z while
returning success. Context omission also bypasses the InputIR IME check.

Route native model type/press/hotkey actions through the existing State Compiler
and InputIR. Direct legacy Windows keyboard dispatch refuses input. Non-recovery
native keyboard and modifier gestures require observed context and a live guard.
Literal input additionally requires known text focus. Owned releases and explicit
Escape remain independent of text-state admission.

Persist focused UIA runtime identity, physical control bounds and native
window/process/thread identity. Generic literal targets must already lie in the
known writable focused control. Remove implicit focus clicks from typing: those
clicks can themselves commit an active composition before text admission.
Reobserve the bound focus, writability and idle composition before native units.
Opaque runtime IDs may be reused; they are not permanent application identities.

Writability requires strict enabled/non-password Boolean properties and the
IsReadOnly Boolean attribute of a supported, separately registered TextPattern's
document range. Never read Value, Name or text content. A native RichEdit probe
returned INVALIDOPERATION for the TextEdit inherited document-range path while
the separately registered TextPattern returned explicit supported writable
evidence. Use that public interface directly, without an assumed writable or
ValuePattern fallback. Unsupported, mixed, failed or stale evidence stays unknown.

The additional native observation has a real latency cost; this decision claims
no 100 ms profile or fast coverage. A guard refusal and partial delivered text
cannot become task completion. Blender popup, modal, effective keymap and global
idle facts remain unproved by focused text evidence. Existing registered Blender
operations retain their stricter application-state guards.

One-shot Enter submission has an explicit acknowledgment boundary. The strict
original focus/IME/writability guard admits key-down. After successful native
acknowledgment, the existing InputIR phase latch permits a changed focused field
while checking the original top-level native window, process, thread and bounds.
That check authorizes no further key-down and makes no claim about new IME state.
Owned key-up remains independent. Ordinary goal verification still follows a
successful action. A post-input refusal retains delivery metadata, consumes one
action from the budget and returns NEEDS_REPLAN with DELIVERED_UNVERIFIED instead
of describing an acknowledged submission as never sent.

Verification separates installed bypass reproduction, source regression, native
source execution and immutable installed execution in docs/EXECUTION_STATUS.md.
