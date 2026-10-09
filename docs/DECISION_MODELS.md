# Model-independent Decision Backend

The canonical `DecisionBackend` accepts the same bounded observation, contract,
candidates and effect evidence for each model. It emits the same runtime Decision;
OmniParser, SigLIP2 grounding, CANVAS, MCP/CLI and deterministic ActionBackend do
not change. A model chooses among submitted alternatives; it does not execute
input, generate a command, or acquire permission to act from screenshot text.

## Pinned models and isolated workers

- Default/baseline: `Cloudflare/clef-flash` at
  `17f0b0ad64efb65d273590632833508766b2aae6`.
- Optional larger CLEF fallback: `Cloudflare/clef` at
  `2f3de3dd85f379784083b0814d997ab627200f0c`.
- Candidate: `LiquidAI/d1-3B` at
  `051bcc464b01b9f92942b364d9586b0ef5912432`.

CLEF uses `clef_python` / `clef-env-<profile>`; d1 uses `d1_python` /
`d1-env-<profile>`. Each is a separate resident process and dependency environment.
The d1 SDK is pinned to Transformers **5.14.1**, not the CLEF dependency lock.
Runtime wheels include hash-locked dependency manifests, not checkpoint weights.
Worker startup reports the selected model, revision, actual compute dtype, PID
and installed Torch/Transformers/tokenizers versions. No model imports or weight
loads occur in the planner/gateway process.

CLEF's pinned `systemone` and d1's public `system_one(state, questions, images=...)`
map directly to the shared named `choice` / ordinal `score` / `noul` contract.
Questions include `instructions`; choices preserve their supplied identifiers.
Both receive one raster plus the same quantified effect evidence in state.
Malformed, incomplete, foreign-option, non-finite, incorrectly normalized or
generative answers fail closed before input execution. CLEF's documented
four-decimal serialization gets a bounded rounding allowance; probabilities are
not clipped or silently renormalized. Existing confidence and completion gates
are unchanged.

## Install, inspect, update

```sh
clef-use models list --decision-model LiquidAI/d1-3B --json
clef-use models prepare --decision-model LiquidAI/d1-3B --quantization none
clef-use update
```

Candidate preparation downloads the pinned snapshot, initializes d1 and
OmniParser, and saves its worker path **without activating d1 or changing the
active CLEF precision/device settings**. Cache paths remain configurable.
Preparation and subsequent repair reuse cached snapshots. d1 currently supports
original full-precision weights only; requesting CLEF NF4 for d1 fails before
installation. CLEF NF4 and its never-executed-head offload remain CLEF-specific.
The d1 tied output head executes and must not inherit that offload.

An explicit experimental configuration can set `decision_model = "LiquidAI/d1-3B"`
and `quantization = "none"` after preparation. This is an opt-in selection, not a
promotion or automatic fallback. A failing selected model fails closed; the
baseline remains available by explicit selection. `doctor` probes the selected
worker environment rather than always testing CLEF's environment.

## Licensing notice

The application license does not replace checkpoint/code licenses:

- Cloudflare CLEF checkpoints: Apache-2.0.
- Liquid AI d1 checkpoint and remote SDK code: **LFM Open License v1.0**,
  not the application's Apache license. Review commercial-use conditions in
  section 5 and the entire cached `LICENSE` before use or redistribution.
- Pinned d1 license source:
  <https://huggingface.co/LiquidAI/d1-3B/blob/051bcc464b01b9f92942b364d9586b0ef5912432/LICENSE>.

`models list` and preparation expose a separate checkpoint license notice.
The snapshot includes its original LICENSE. Models, avatar assets, private
screenshots and VRM files are not bundled into software releases.

## Authentic replay and promotion policy

```sh
python -m clef_use.decision_benchmark \
  --corpus /path/to/corpus.json --output /path/to/fresh-report.json \
  --repetitions 3 --profile deployment
```

A corpus contains `schema_version: 1`, unique cases, a real image path and SHA256,
explicit platform (`blender`, `windows`, `macos`), capture/readback provenance,
a typed `state` / `questions` request, and independently known `expected` fields.
Authentic archived failures with missing labels use `archived_unlabelled` and
empty expectations; their inference timing is measurable, their accuracy is not.
The reader verifies images and hashes the complete serialized model input.
Identical inputs are submitted to each pinned model sequentially; no ActionBackend
or desktop input runs during replay. Reports include raw answers, usage, cold and
warm latency, process peak RSS, GPU allocator peaks, source/library/precision
metadata and false-completion counts. CUDA peaks include resident model weights;
RSS includes loading. Missing/failed measurements are not synthesized.

`deployment` compares the actual independently pinned environments and precision
choices; a CLEF NF4 vs d1 BF16 result is a deployment comparison, **not a pure
architecture effect**. `cpu-bfloat16` uses the prepared d1 environment for both
separate workers with identical unquantized CPU BF16; that is a controlled SDK
comparison, not validation of the original CLEF environment. CPU BF16 is explicit;
the default CPU precision remains FP32.

Replay field accuracy is **not** live task success, no-effect recovery, GUI
permission validation or safety coverage. `promotion_gate` explicitly blocks
promotion for replay-only evidence. The default remains CLEF-Flash until paired
real Blender, Windows and macOS execution with independent readback establishes
maintained/improved same-task success and safety. Smaller latency or a successful
model initialization alone cannot satisfy that condition. A native AppKit
owned-view fixture is genuine macOS rendering, but is explicitly not OS-input
E2E evidence.

### Observed comparison: 2026-10-10

Authentic corpus: two archived Blender failure frames, one earlier Windows final
frame, three new Windows owned-client screenshots, and three new macOS AppKit
owned-view renders. Nine cases x three repeated requests x two isolated models
produced 54 real responses with identical per-case input hashes. Seven labelled
GUI cases supply 21 unique field judgments, repeated three times (63 per model);
these repeats are not 63 independent examples. Blender quality remains unlabelled.

Controlled profile: CPU BF16 on AMD Ryzen 7 9700X / 32GB-class host,
Torch 2.11.0+cu130 / Transformers 5.14.1 / tokenizers 0.22.2, seed 0.
NOT_RECORDED: replay-worker thread count; timings are not a portable guarantee.
Both workers use the same prepared SDK environment but retain their checkpoint's
native image processing. No fitting/calibration; ordinal truth tolerance is half
one declared level, fixed before this run. Resource bounds were MemoryHigh 10GiB,
MemoryMax 12GiB and MemorySwapMax 1GiB. GPU deployment baseline loading OOMed;
that separate failure is not combined with CPU timings.

- CLEF-Flash: 63/63 known fields, zero false-completion choices; warm median
  19.858s, mean 22.009s +/- 4.624s, range 17.513-30.610s; peak worker RSS 10.627GiB.
- d1: 54/63 known fields (85.71%), zero false-completion choices; warm median
  1.614s, mean 2.418s +/- 1.633s, range 1.432-7.702s; peak worker RSS 6.656GiB.

The warm distributions mix different case sizes, not just same-frame jitter.
Raw samples allow case-paired analysis. d1 underestimates progress on the earlier
Windows final frame and both new Confirm frames; completion/button choices remain
correct in this small split. Faster/lower-memory replay does not cancel this
accuracy regression or establish maintained live-task safety. **No promotion.**

Private canonical evidence: `reici-production/decision-backend-benchmark/` in the
separate goal workspace. `native-cpu-paired-v2.json` SHA256:
`9335be81e355628773e96df02a38adc8aa841f7a451967b5c02c3bc28c42380f`.
The corpus and raw GUI/Blender images are not software-release assets. Windows
build 26200.9457 / Session 1 readbacks and macOS 15.7.9 ARM64 runner
`37968411148` verify native fixture provenance, not live input or task E2E.
The canonical d1 `DecisionBackend` also ran on the real macOS Confirm raster;
its valid ACT/a0 result verifies adapter integration only, not action delivery.
