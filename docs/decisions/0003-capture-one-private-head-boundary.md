# 0003. Capture head-consumed numbers without changing inference

Status: accepted
Date: 2026-10-10
Scope: `model_worker.py`, `head_trace.py`; local POSIX diagnostics only

## Context

Actual File-menu ASSESS returned low mode/completion probabilities. SDK encoder,
option/noul meanings and forward wiring have no demonstrated scoring defect.
Synthetic CPU trained-head/lexical-row parity does not test real activations.
Head precision is a hypothesis, not grounds to change defaults or completion gates.

Invariant: capture only the actual numeric head inputs/outputs, unchanged, with
bounded additional copies and no action authority or completion-witness status.

## Decision

Only local `CLEF_USE_HEAD_TRACE_DIR` opts a CLEF worker into one capture attempt.
Model/MCP request fields cannot enable capture or choose destinations. Consume
the attempt before genuine inference, including failing attempts; later normal
requests do not automatically re-arm it. Default off. Remove the task-only opt-in
when diagnosis ends; do not leave a nonempty root configured across worker restarts.

Open every absolute POSIX path component descriptor-relatively with
`O_DIRECTORY|O_NOFOLLOW`, rather than resolve-then-open. Final directory must be
empty, same-UID and0700. Exclusively created files are0600 and all subsequent
operations use that directory descriptor. This is not a filesystem enclave or
protection against a malicious same-UID/privileged actor.

Store exact hidden/logit bytes, dtype/shape, token IDs/mask and their dtype, and
numeric question type/spans in original order. The pinned head consumes these
fields; it does not consume question_id/option_ids, record_id, prose or media
(joint_schema_model.py:350-459). Omit these strings entirely, not normalized
replacement IDs. This is a numeric head-boundary capture, NOT an SDK-request
replay. Pair output ordinals with the independently preserved original request
when reporting field meanings; do not infer a new authority from the trace.

Allowlist bounded scalar model/device provenance and exact image SHA256 values
before inference. Never copy the state/frame-reference/question dictionaries.
Hash image bytes during the already-required single decode, not a second decode.
Raw token IDs and latents remain sensitive even without prose: NEVER upload,
commit or distribute them with software or visual-review requests.

Hidden storage<=64MiB; slices<=2MiB; logit bytes<=32KiB; token/mask shapes<=8192;
questions<=128 and options<=4096. Validate lengths/types/spans before copying.
Stream a manifest of bounded primitives with an incremental512KiB byte limit;
never serialize an entire unvalidated dictionary then check size. Raw logits
retain signed-zero/infinity/NaN bits and original dtype, not JSON float conversion.

Pre/post hooks returnNone and are removed on success/failure. Close a descriptor
when fdopen fails. On failure, attempt removal of every exclusively created file;
retain the original exception, attach an incomplete-cleanup note/flag, and expose
a constant incomplete-cleanup warning through the normal worker diagnostic.

## Alternatives considered

- Change default dtype from one anecdotal score: rejected; no causal evidence,
  potentially more GPU memory and no same-task safety/success demonstration.
- Unchanged assessment replay: rejected; no information distinguishing head
  arithmetic from recognition/context quality.
- Another full GPU backbone or changed prompt: rejected; unnecessary for this
  boundary question and not permission to retry the denied probe.
- Full tensor/JSON serialization and identifiers: rejected; unbounded copies,
  avoidable plaintext leakage, and missing nonfinite-bit fidelity.

## Costs and consequences

Capture synchronizes device-to-host slices and writes private data. Its overhead
is not normal-path performance. POSIX-only opt-in; normal operation unchanged.
Invalid diagnostic destinations/metadata fail explicitly. No new MCP/config
schema. Cgroups bound charges, not all shared resident pages or filesystem access.

## Invalidation

Revisit for a changed head signature/consumed fields, concurrent inference or a
non-POSIX requirement. Review a separate raw-data contract before expanding it.

## Verification

- First independent review REJECTED: metadata/prose minimization, ancestor race,
  nonfinite fidelity, unbounded copies, success-only re-arm and cleanup defects.
  No live opt-in or actual model call occurred with that implementation.
- Six reviewed core defects reproduced failing-before, then passing-after in
  bounded real-Torch CPU tests. Two worker regressions failed-before then passed:
  failure consumes attempt; no full record serialization/repeated image decode.
- Current real-Torch CPU16passed includes FP16/BF16/FP32 bits/normal output,
  raw signed-zero/nonfinite logits, multichunk nonfinite hidden bits, unsafe/racy
  root refusal, streamed limits, post-write failure, FD and exhaustive cleanup.
  Tiny IO/numeric fixtures, not full-backbone or UI-quality evidence.
- Current local547passed/34skipped, Ruff/format/diff pass; existing41 Pillow warnings.
- Independent static re-review PASS; six code/test hashes and pinned SDK verified
  unchanged before first use. Original request and native-frame identity preserved
  independently; captured question/option token spans verified against canonical
  definitions before assigning semantic labels. No rewritten record identifiers.
- ACTUAL: original File contract ASSESS, one CUDA/NF4 decision/zero inputs;
  raw hidden/logit hashes/dtype and private permissions verified. LOW_CONFIDENCE,
  modeACT0.4503/goal0.0944/condition0.0775, not task completion. No service OOM;
  memory-limit pressure and swap occurred under the unchanged8GiB cap.
- MEASURED: one real captured input, CPU2GiB/swap0/two threads, no backbone or
  full vocabulary table. FP16 parameters/selected rows reproduced before widening
  the same values to FP32. Two deterministic FP16 repeats numerically identical
  under rtol=0/atol=0, not bytewise proof; finite lexical perturbation changes
  logits. GPU/CPU max probability delta0.0002417862
  passes the predeclared0.02 bridge tolerance. Arithmetic widening max probability
  delta0.0001989007; low completion scores persist, not evidence for a dtype fix.
  This does not recover already-rounded source or backbone/activation information.
- Independent static numerics review PASS for this one input. Historical artifact
  field baseline_bitwise_repeat_verified is misnamed: its rtol=0/atol=0 assertion
  establishes exact numerical equality, not signed-zero byte equality. Preserve
  the original artifact/helper and interpret it through this correction.
  Lexical checkpoint shard/index and tokenizer hashes were not recorded. Declared
  raw/head hashes and tolerance declaration timing were not independently rehashed
  or established within that static review; do not claim complete provenance.
- Removed the task-only opt-in and read back owned idle runtime/defaults/config/
  caps. Raw latents/token IDs remain private outside Git/releases. No actual task
  completion, accuracy improvement, default promotion or new release claim.
