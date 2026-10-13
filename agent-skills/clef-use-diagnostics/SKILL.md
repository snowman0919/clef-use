---
name: clef-use-diagnostics
description: Diagnose clef-use setup, missing skills/tools, ambiguous choices, stale state, wrong focus or mode, input failures, and latency. Use on actual errors or requested audits; prefer read-only evidence and preserve user settings.
metadata:
  guide-contract: "1"
  authored-against: "0.1.29"
---

# Diagnose clef-use without manufacturing success

For an application-specific question, load the discovered core and application
guides when available before interpreting supported operations. For Blender,
including read-only menu assessment, load `clef-use-blender`. Diagnostics does
not replace those workflow guides or establish operation support.

Inspect real tool schemas and runtime versions first. Do not invent diagnostic
commands from a roadmap. CLI help, existing doctor/version/status, current
capabilities when advertised, and private runtime evidence are starting points.

## Classify before changing anything

Use [the failure taxonomy](references/FAILURES.md). Record current task, session,
source release, model revision, input type, observation age and actual error.
Separate missing installation, undiscovered guide, unread guide, invalid request,
perception error, decision ambiguity, stale context, input delivery, and bad
completion verification.

Do not disclose credentials, full environment dumps, private screen content,
purchased assets, or raw user text in a public issue. Preserve a minimal private
reproduction and create a synthetic/public fixture when possible.

## Installation failures

Check the active harness profile, effective skill path/realpath, duplicate names,
disabled sources, user-edited files, and the server executable actually launched.
A file existing is not proof that the harness discovered or loaded it. A claimed
skill hash echoed by the model is not proof of correct behavior or authorization.
Preserve conflicting settings and report the exact mismatch; do not reset all
user configuration or silently re-enable a disabled integration.

## Decision failures

Distinguish probability dispersion across options, raw-logit dispersion, and
variation across repeated requests. Check candidate coverage before interpreting
confidence. One candidate with probability 1 is not a safety or accuracy proof.
Do not sharpen distributions, lower thresholds, relabel missing targets, or
randomly reorder live actions merely to pass a gate.

## Timing failures

Separate capture, observation age, parsing, queueing, tokens, model inference,
input delivery, effect readiness, and verified task completion. Measure reaction
from a real state change to the correct relevant OS event, not an API ACK.
Report unsuccessful, refused, cold, and late attempts as well as fast successes.

## Repair and retry

When authorized to modify the project: reproduce; identify one cause; implement
a general fix; add regression tests; restore the original fixture; retry the
original real operation; compare quality and latency; then commit.
Use the existing KODEX only if this session is an authorized development task.
Ordinary runtime troubleshooting does not authorize source edits or publication.

If permissions or hardware prevent live verification, mark that check NOT_RUN
or BLOCKED. A fixture/mock test and a live desktop test are different outcomes.
Abort only the affected owned session and verify input release before resuming.
