# 0002. Assess visible goals without authorizing another input

Status: accepted
Date: 2026-10-10
Scope: Contract.execution_mode, ExecutionRouter, SessionRuntime, MCP and CLI

## Context

The original Blender File task delivered a model-selected click, then its parser
failed under the task's host budget. Saved native pixels show an open dropdown;
a fresh separate session still returned NEEDS_REPLAN. Its completion-only
assessment used zero candidates, but order-dependent first-eight OCR hints
omitted the dropdown entries. Action confidence 1.0 meant a singleton `none`
choice, not completion evidence. The completion scores were missing from that
failed grounding row. Running an input-capable contract again could toggle the
already-open menu; natural-language "do not click" is not an input boundary.

Invariant: contextual evidence never grants action permission, and checking an
already-visible goal must not require or silently deliver another input.

## Decision

Keep the five high-level tools. Add ASSESS to the existing execution contract
and CLI mode enum. This path creates no executable proposals, does not invoke
spatial grounding, and returns through the existing completion/safety gates.
COMPLETED still requires two fresh stable positive observations; all weaker
assessments escalate without input. No previous-effect witness is fabricated
or copied between sessions.

Use a unique genuine query anchor and observed rectangle distances to choose
at most eight context hints, preserving the original records. Missing or
ambiguous anchors retain the existing bounded uncertain context; there is no
File-specific label list or synthetic popup. Preserve source, nullable confidence,
observation/frame identity and explicit evidence-only semantics in the packet.
Keep 32 target objects plus eight hints, refuse oversized packets, and preflight
with the pinned CLEF encoder at a larger bound before its unchanged 8192-token
inference bound. More than 8192 tokens is refusal, not truncation permission.
Log actual completion, condition and safety scores even when grounding fails.

Give an observe thumbnail its own pixel hash/dimensions and native parent hash.
A preview, later HUD-bearing capture and original decision frame are distinct
artifacts; no matching hash or native ownership is inferred from appearance.

## Alternatives considered

- Repeat AUTO input or reset the menu manually: rejected; unknown prior runtime
  outcome does not erase the delivered click, and repetition can undo its effect.
- Add an assessment RPC or sixth GUI tool: rejected; an existing goal contract
  and executor already provide budget, locks, cancellation and completion gates.
- Keep every parser object or hand-pick File labels: rejected; restores overflow
  or makes the correction scene-specific.
- Relax completion/grounding thresholds: rejected; this breaks evidence gates.
- Treat OCR as a native menu or inject completed=true: rejected; creates facts
  or authority not supplied by the observation.

## Costs and consequences

A new opt-in mode expands the public contract; AUTO behavior and default remain
unchanged. Context proximity is a heuristic, not popup detection or a calibrated
completion guarantee. Token preflight repeats CPU encoding/preprocessing before
inference; no latency improvement is claimed. Byte/object limits can refuse a
legitimate oversized request. Existing pinned row offload is only valid for the
immutable, untied CLEF joint-head consumer: full HF generation or later output-
embedding mutation is unsupported and not made safe by these context changes.

## Invalidation

Revisit if the pinned encoder changes, a model gains a different context budget,
a trustworthy native popup relation is available, or an executed/tied/mutable
output-head consumer is introduced. Keep those changes separate from this UI
context correction.

## Verification

Failing-before/passing-after tests cover raw context identity, permutation
invariance with a unique anchor, packet provenance and overflow refusal, token
truncation refusal before inference, and sparse/dense ASSESS with strong/weak
completion and safety veto. Fixtures forbid candidate construction, grounding
and action execution. Real task evidence is recorded separately in V2STATUS;
unit pass counts alone are not a Blender completion claim.
