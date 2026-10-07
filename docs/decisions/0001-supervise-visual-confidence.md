# 0001. Supervise visual target scores and subpatch locations

Status: accepted
Date: 2026-10-07
Scope: grounding head, head checkpoints and training manifests

## Context

The first frozen SigLIP2 readout plus residual query projection placed six of
seven held-out targets inside annotations, but did not pass confidence for
viewport or divider actions. A three-pixel divider can lie between patch
centers. Increasing contrastive scale accepted an incorrect divider and absent
targets. Retraining at that scale improved two controls but did not resolve the
remaining cases. Raw spatial sharpness does not establish target presence.

The first dense head rejected all 69 executed absent-target controls, but a real
six-case v13 retry sent no input. Fine predictions changed with crop position;
full-screen competitors obscured Outliner and divider targets. Train the supplied
serving regions and half-patch crop translations. Label viewport selection with
the nose landmark of the same Face object, avoiding inconsistent boxes spanning
other selectable eye/hair objects. This preserves the object-selection objective.
Real native input later showed that the nose landmark belongs to the separate
`Nose contour` mesh. Replace that supervision with clean skin below the
image-left eye using only existing v10 screenshots. Keep Face as the goal and
retain the failed nose trials. This changes a target annotation, not the
required object-selection outcome.

The invariant is that a model must provide an observation-bound target and
support its uncertainty assessment before native input. Lowering the gate to
force a demonstration does not repair missing supervision.

## Decision

Keep both Foundation ViT encoders frozen. Replace the residual query projection
with a small shared image/text head that predicts target scores and bounded
offsets within each patch. Train patches intersecting a precise annotated target
region toward reachable points inside that intersection, and train explicitly
absent queries/screens with all-negative labels.
An absent query scoped to a region labels only that region negative; it never
asserts absence elsewhere in the screenshot.
Keep binary presence across the whole annotation, but weight localization toward
its interior with a Gaussian density. The earlier uniform positive cross-entropy
required a plateau, while the serving margin required concentrated support.
Executed cheek, Outliner and Modeling heatmaps had high binary target peaks
but fragmented spatial support; even annotation-centered cheek crops failed
their confidence gate. Gaussian supervision retained the gate and serving
confidence. Its 189-pass audit rejected all 144 absent controls at 0.55, but
three absent targets passed 0.35; that threshold is prohibited for this
checkpoint. Its v13 runtime retry completed three task states, while viewport,
drag and workspace abstained. Face selection remained unresolved in that run. A separate
native label check established that clean cheek and chin points really select
Face in the same fixture.
Native ray casting subsequently found that retained rejected predictions hit
hair or empty space. Eleven of twelve held-out cheek coarse ROIs missed the
annotation. The training loop gave every context its own optimizer update:
71 coarse versus 499 fine contexts, with seven-and-a-half fine augmentations
per coarse context for cheek rows. Aggregate context hit rates could therefore
conceal complete coarse failure. Balance losses within each serving stage,
combine stages equally per annotation row, and report stage metrics separately.
The augmentation-count regression preserves resulting predictions when an
entire fine-context bank is duplicated. Whether this correction fixes actual
Face selection must be established by a newly trained head and native retry;
the imbalance alone does not establish causation. The first balanced head still
missed every held-out cheek target and regressed the other controls. Its fixed
manifest order ended each epoch on 22 absent rows. Shuffle each epoch with the
training seed while retaining all rows and the objective. Test that isolated
change before claiming it fixes actual localization or changing serving gates.
The order-only comparison improved cheek coarse ROI overlap from two to nine
of twelve passes, but accepted none of the cheek targets. Preserve that failed
result. Add an explicit whole-region overview strategy for coarse semantic
localization, retaining native magnified fine crops and default tiles for small
controls. Train the overview strategy on the original Face query; changing the
serving view without matching supervision had already failed. Strategy coverage
must include positive and negative rows in both splits, and V3 checkpoints
refuse strategies they were not trained to serve.
Keep every valid overview patch, including partial patches at letterbox edges.
Tile fusion is only needed for overlapping native tiles; applying its integer
anchor bins to a single overview merged distinct edge patches. Fine crop phase
augmentation uses the actual fine-context patch pitch, including clipped crops,
rather than the coarse overview scale. These geometry corrections do not
establish semantic accuracy; loaded-head controls and native retry remain
required before adoption.
Use the native patch anchors for spatial fusion and ambiguity checks; apply
offsets through separate exact inverse x/y scales when selecting a crop and
returning a point.

The trained sigmoid is a class-weighted score, not calibrated correctness
probability. Retain the default confidence gate and global spatial
ambiguity check. Evaluate absent queries across the full native tile count.
For a supervised fine crop only, allow all valid patches to carry positive
target evidence: an annotation can legitimately cover the entire magnified
crop. Keep the coarse global ambiguity gate, and use the minimum valid fine
binary score as the alternative to fine component evidence. Unsupervised flat
maps retain zero confidence; spatial entropy remains separately observable.

The V3 loaded-head retry exposed correct, high-presence targets rejected by
full-map mass subtraction. One correct fine prediction had only one active
component, yet diffuse background held 0.742034 of the posterior. Use the
classifier's natural 0.5 support boundary and compare primary with the largest
competitor through their conditional signed mass ratio. Cap that ratio by
peak presence and require the configurable 0.9 peak floor in both stages.
Keep the 0.55 action gate and every point/crop unchanged. Fine crops with all
valid binary scores >= 0.9 retain their existing uniform-target alternative.
This ratio excludes other active components as well as background; it is not
calibrated success probability. The actual unchanged-head 321-pass diagnostic
accepted 30/45 positive configurations, including eight annotation-box misses,
and none of 276 absent configurations. Subsequent original v13 and previously
untouched v12 native diagnostics each completed all six cases with the fixed
head, gate and policy. Those diagnostics omitted CLEF and OmniParser; the
full-model comparison remains a separate acceptance check. Finite negative
controls cannot establish general safety.

An explicit horizontal-line query combines fragmented responses whose decoded
y coordinates lie within one patch pitch of the peak. Require a two-patch x
span and subtract the strongest competing parallel band. This addresses actual
divider fragments without changing point-query scoring or assuming Blender
coordinates. Drag endpoints retain point geometry.
Parallel lines within the one-pitch tolerance can merge; this decoder does not
establish subpatch boundary separation. Fresh action verification remains required.

The adopted action gate remains 0.55, with a 0.9 presence floor. Earlier 0.35
and 0.25 control evaluations are historical evidence, not serving profiles.
Their correlated negative controls did not establish correctness probability,
and later audits exposed accepted absent targets. Do not lower the gate to
make a rejected action pass.

Cut over the private head format and every training/reference caller together.
Reject obsolete head checkpoints. Preserve previous local artifacts as
historical evidence; no compatibility loader or untrained head is served.

## Alternatives considered

- Change inference temperature to force acceptance: rejected because executed
  controls showed confidently wrong and absent targets. Configuration calibration
  requires separate control measurements and independent evaluation.
- Return only patch centers: rejected because actual narrow controls fall
  between centers, even when the correct neighborhood is identified.
- Unfreeze the backbone or introduce another large model: rejected because the
  current need is supervised presence and coordinate precision in a small head;
  those changes exceed the minimum vertical slice.

## Costs and consequences

Training needs positive and negative annotations in both independent splits.
Offsets and confidence supervision add parameters and checkpoint validation.
Small application samples do not establish general GUI accuracy. The original
v13 scene is a reused development/regression scene because its failures informed
the work; a separate untouched snapshot is required for a blind claim.

## Invalidation

Reject this implementation if held-out target absence, coordinate precision or
real native-action readback fails. Further model work must follow those failures,
without weakening safety/verification or pretending successful grounding implies
task completion.

## Verification

The executed readout failures, rejected scale changes, unchanged-head control
audit and original/blind native retries are recorded in
[HYBRID_VALIDATION.md](../HYBRID_VALIDATION.md). Native diagnostic success does
not establish full CLEF/OmniParser loop completion or general GUI accuracy.
