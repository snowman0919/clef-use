# Portable guides and guarded local operations

Status: accepted implementation boundary, 2026-10-11.

Agent Skills are portable instructions with relative references. They cannot
register executable steps or supply trusted application facts. The runtime wheel
ships the guides with its API schema digest and per-file content hashes. Managed
enrollment preserves modifications and records the selected harness profile.

Runtime Operations are a finite typed union implemented locally. Each operation
requires fresh evidence with source, version, timestamp, validity and uncertainty.
Missing editor, keymap, selection, IME or field evidence blocks OS input. Readback
of the intended effect is required; input delivery alone is insufficient. Owned
modal state stays with the same session. An operation report's `SUCCEEDED` proves
its typed effect, not an arbitrary natural-language goal. The session returns
`NEEDS_REPLAN` for separate fresh goal assessment; a non-open menu is `BLOCKED`.

The screenshot-only default does not infer Blender's hidden state from labels.
The disposable Blender fixture explicitly supplies API-assisted invariants and
application readback. This establishes the scoped operation behavior, not a
general production application provider. A future native provider must preserve
this trust boundary and report unavailable facts instead of guessing them.

The shipped desktop factory does not connect a trusted application provider and
ships no public provider configuration path. All six registered operations are
therefore `BLOCKED` by unknown facts in the default installation. Capability
discovery distinguishes implemented schemas from default availability, lists the
actual common and family-specific guard facts, and never fabricates live readiness.
Only the controlled `API_ASSISTED` fixture has verified operation execution.
General production enablement remains an open requirement, not completed work.

A reusable opt-in bridge can safely expose read-only Blender snapshots through
authenticated loopback or stdio, with process/window binding, connection epoch,
timestamp and version. It must not include fixture scene setup or arbitrary code
execution. API-observable selection, transforms, properties, geometry, modal
operators and keymap items are insufficient by themselves: trustworthy widget
focus, exact focused property, IME composition, UI popup/menu identity and absence,
effective context-specific keymaps, and normalized numeric input/readback units
remain necessary. Missing facts stay unknown; a partial bridge must not authorize
the changing operations or be presented as production completion.

Typed continuation requires an explicit operation request. Guidance alone cannot
silently repeat an earlier effect. Complete-goal verification uses a new `ASSESS`
contract without an operation; same-session known-modal cancellation remains an
explicit, ownership-checked cleanup request.

OS acknowledgement produces a per-dispatch final-trigger receipt. Only after
that acknowledgement may a bounded search-open, transform-enter or modal-close
guard accept its specific expected transition. All other context facts remain
exact. Abort after entry reconciles verified modal ownership read-only; observed
closure releases it even if abort interrupts the normal return. Pending recovery
retains the desktop lease and prevents idle service replacement or another goal.

Typed input tracks only acknowledged ownership. Independent thread/process
watchdogs release that ownership on cancellation, deadline and worker failure.
OS permissions, secure desktops and the injection/acknowledgement crash window
remain explicit limits. Actual native verification is platform-specific.
