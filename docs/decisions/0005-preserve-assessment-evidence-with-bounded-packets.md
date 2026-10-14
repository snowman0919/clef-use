# Preserve assessment evidence within bounded model packets

Status: accepted implementation boundary; actual menu quality remains FAIL.
Date: 2026-10-11.
Scope: `router.py` evidence selection and `backends.py` decision packets.

## Context

Actual Blender File/Edit/absent captures showed that the fixed eight hints omitted
distinguishing popup rows present in the parser. ASSESS reserved 32 unused target
slots. Filling the existing 40-object limit retained those rows, but three actual
model forwards failed in CUDA/NVML. The host driver/library versions differ;
memory queries failed, so OOM is not established. Being below 8192 encoded tokens
does not establish viable execution or accurate decisions.

## Decision

Use unreserved target slots for observed evidence without changing action sets,
ranking, confidence gates or the 40-object, 32768-byte and 8192-token guards.
Share explicit null/false object defaults once; preserve every non-default fact,
label, source, identifier and action. Missing fields inherit the declared defaults;
an explicit false overrides an unknown default.

Represent model-facing boxes as outward integer raster envelopes with declared
coordinate space and image dimensions. Each edge expands by less than one image
pixel. This is derived geometry, not lossless serialization of normalized boxes.
Native execution and input guards retain the original objects and exact frame
transformation. Evidence envelopes never authorize or supply OS input coordinates.

## Alternatives considered

- Eight nearest hints: observed popup evidence loss; leaves unused bounded space.
- Full 40-object serialization: exact facts, but actual forward execution failed.
- Column tables: lossless, but offline encoding remained above 6200 tokens and
  introduced a broader interpretation change without native input benefit.
- Lower confidence gates or select known positive menu labels: changes correctness
  criteria or overfits the fixture instead of preserving observed evidence.

## Costs and consequences

Models must interpret explicit shared defaults and raster geometry. Pixel envelopes
lose subpixel precision in model evidence; original execution geometry remains
exact. Token reduction is measured offline and proves neither VRAM viability nor
menu accuracy. Longer packets can still refuse; they must never truncate silently.

## Invalidation

Reconsider if actual forwards still fail, models confuse defaults or coordinate
spaces, or matched negative cases falsely complete. Retain failed results and
unexecuted cases rather than promoting a file or unit test to live success.

## Verification

Deterministic tests preserve known false/true versus unknown facts, provenance,
raw native geometry and input-free assessment on landscape and portrait frames.
The original full-packet forward errors remain recorded. The corrected installed
packet completed all fifteen model forwards without errors and preserved every
matched before-image. File completion remains zero of five; ten negative cases
have zero false completions, without proving correct menu classification. Raw
confidence changes do not pass the unchanged completion guards. No overall menu
accuracy improvement or 100 ms result is claimed.
