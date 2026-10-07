# Hybrid execution implementation plan

Goal: preserve CLEF and OmniParser while adding direct Foundation ViT grounding
for dense GUI and canvas contracts. The user's V2 request supplies the design and
explicitly authorizes implementation, real Blender validation, and a local commit.

Architecture: route before bounded candidate construction; keep execution mode
separate from CLEF's ACT/WAIT/COMPLETED decision. Generate observation-bound pixel
actions through the existing ActionBackend and retain its verification loop.
Use frozen SigLIP2 through an isolated resident model worker, spatial grounding,
coarse-to-fine crops and original-image coordinate mapping. No GUI-specific full
model training, new segmentation model, Blender coordinates, or remote publish.

State: canonical root /home/monad/develop/clef-use, main@c1ee22c, origin/main,
one worktree, no submodules. Pre-existing dirty docs/REICI_PRODUCTION.md is owned
by the user and excluded from this change. Other Blender sessions are active;
validation must use a new isolated display and a copied VRM scene.

1. Add routing/visual contract and tests for raw candidate explosion, native
   semantic precedence, uncertainty, safety vetoes, and bounded refinement.
2. Add interchangeable image/text/head interfaces and frozen SigLIP2 inference;
   test aspect ratio, crop/border mapping, finite scores and query participation.
3. Integrate worker/config/factory and visual/canvas actions into the existing
   runtime, preserving fresh-frame, sensitive-region, completion and abort gates.
4. Run original structured regression tests and hybrid runtime tests. Exercise
   actual model inference and an isolated Blender GUI with native input.
5. Benchmark baseline and hybrid on identical Blender observations/tasks;
   retain raw timings, success/failure and independent Blender state readback.
6. Document configuration, limitations and acceptance evidence, review the
   integrated diff, run required checks and commit only owned files locally.

Acceptance: existing structured fixture completes; dense inputs route before
truncation; real SigLIP2 yields an original screenshot point; canvas click/drag
execute through ActionBackend; ambiguous/stale/unsafe inputs do not execute;
verification requires actual visible progress and two completion observations;
real Blender six-case stress evidence and comparable latency/success report exist;
unit/integration regressions pass; docs and coherent local commit exist.
