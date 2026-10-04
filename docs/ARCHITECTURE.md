# Architecture

`cli.py` and `mcp_server.py` both use `RuntimeClient` to reach one authenticated
loopback service. `SessionManager` owns sessions, the exclusive desktop lease,
and a lazily initialized `SessionRuntime`. ML subprocesses remain resident in
separate pinned Python 3.11 environments because CLEF and Florence require
incompatible Transformers versions. They are components of one runtime.

`SessionRuntime.execute` captures a fresh frame, parses it into project-owned
`UIObject` records, builds bounded `ActionCandidate` records, requests typed joint
CLEF answers, evaluates escalation gates, executes a deterministic adapter, and
checks progress. Candidate IDs are bound to one observation. The model never
produces mouse coordinates. `Frame.point` maps normalized box centers to the
primary monitor's logical coordinate space, including Retina scaling.

The OmniParser wrapper composes official detection, overlap/OCR fusion and
caption primitives. This avoids its annotation helper's empty-OCR and -1 caption
index failures. The pinned local Florence model identity must contain lowercase
`florence` because upstream uses a case-sensitive string to select its prompt
and documented image generation arguments.

The decision budget counts model rounds, including completion checks; actions
are counted separately. Completion needs strong predictions for the goal and
all supplied conditions on two fresh observations. Changed screens trigger
replanning. A no-effect action stops at the screen deadline without repeated
input; repeated visual cycles also stop execution. Session resumption
never resets the original budget. Sessions live in memory; service restart drops
resumable context. Step logs survive restart.

Cancellation sets a session event before releasing owned input. A model forward
pass cannot currently be preempted safely, but its late result cannot trigger
input after cancellation. Keyboard/mouse/Unicode cleanup bypasses the corner
failsafe only while releasing tracked inputs. Windows uses checked Win32 input,
physical capture coordinates and captured foreground identity; UTF-16 text does
not change the clipboard. Other platforms restore the previous plain-text
clipboard for Unicode; rich clipboard representations are not preserved.
See WINDOWS_INPUT.md for the cua reference and native Windows evidence.

`computer_observe` refreshes the screen/object map while idle and marks cached
observations while busy. It reserves the shared desktop during parsing, with
no decision or input action, and returns one coherent image/object epoch,
not an independent live desktop poll. Labels/images are returned only on request;
logs omit goal text, labels and typed values. Diagnostic logging adds object and
candidate counts, not raw screen content. Constraint decisions are probabilistic;
there is no OS sandbox, app allowlist or independent security policy engine.

`installer.py` is canonical for install and update. Both generated bootstraps
embed its source. Releases bundle hashed platform-specific wheels, not weights.
Staging installs offline and runs version/state-machine smoke checks before one
atomic activation. POSIX uses a `current` symlink; Windows atomically replaces a
managed CMD launcher. Updated clients restart an idle older resident service and
refuse to switch a service with active desktop ownership.

## Visual readiness revision, 0.1.5

The user requested replacing fixed post-action sleeps with bounded visual
condition waiting. The selected design keeps one canonical runtime and one joint
CLEF request: a separate fixed-choice mode selects ACT/WAIT/BLOCKED/NEEDS_REPLAN
or proposed completion, while existing goal/condition noul checks retain final
completion authority. Screen polling uses capture/Pillow only, a monotonic
screen deadline and cancellation-aware sampling; it never consumes model rounds.
Action targets and nearby expected-result regions drive change/stability checks.
A changed pixel is readiness evidence, not proof of the requested result.

Action expectations and observed effects become bounded structured history.
Unknown editability/occlusion remains unknown; explicit negative states refuse
input. Fresh capture/foreground/geometry and local target differences block stale
coordinates, including small movement/modals. Text stays exact and scoped.
No-effect input is not blindly repeated. Exact-image perception caching is one
entry, pinned to parser identity and full capture geometry/foreground; normalized
objects can be reused, decisions/completion claims cannot.

References: Playwright actionability/assertions and SikuliX region/change waiting
inform these principles; their DOM/event guarantees are not claimed by a pixel
runtime. UFO multi-action and Agent S2 grounding remain measured follow-up options,
not new frameworks or unsupported CLEF batch generation. See
VISUAL_READINESS.md for contracts, heuristic limits and the controlled
wait/cache ablation. Readiness and perception reuse are ablated separately. Repeated MPS backend
failures prevented an accepted performance comparison; no speed claim is made.

## Standalone CLEF GGUF preparation

The requested monad conversion uses the original Flash snapshot
`17f0b0ad64efb65d273590632833508766b2aae6` and llama.cpp
`0504396140d1c882f5f6ee34466a42db7ae90114`. Upstream now has a dedicated
`ClefModel` converter and `/v1/systemone` server endpoint. This preserves joint
typed decisions rather than substituting chat generation. The converter embeds
the joint head; Q4_K_M quantization keeps `decision.*` and `dec.*` tensors in
floating point. Original head/config/code sidecars and model-card license text
are retained for provenance, outside the installed runtime.

`scripts/prepare_clef_gguf.py` checks both source identities, builds in a private
staging directory, verifies the CLEF architecture and floating head, records
tensor types and SHA-256 hashes, and activates a new artifact directory only
after those checks. `scripts/smoke_clef_gguf.py` starts a temporary loopback CPU
server, checks choice/noul/score responses against a changed numeric input, and
stops its own server even on failure. This is a small semantic smoke test, not
a BF16 parity or broad accuracy benchmark.

The pinned upstream CLEF implementation explicitly rejects image input; its
vision converter raises `NotImplementedError` pending upstream PR 29622.
Therefore the GGUF is a text-only standalone artifact. It does not replace the
canonical screenshot decision worker or change deployed installers. Parser
dependency size is also unchanged. Raw files and logs live on monad under
`~/clef-use-gguf`; accepted results are recorded in `docs/evidence/gguf-monad.json`.

## Serving investigation, 2026-10-04

Human put GGUF publication/download routing on hold. No GGUF was uploaded to
the public installation site and no downloader or installer was changed.
The current recommendation is a single resident typed-decision worker, selected
for the installed hardware, behind the existing runtime protocol. This is a
compatibility and implementation-cost recommendation, not a measured fastest
backend. Existing `JsonWorker` already loads once and serializes requests; adding
another HTTP service does not by itself remove inference work.

| Candidate | Current evidence | Selection |
| --- | --- | --- |
| Apple Silicon MLX 4bit + `clef_mlx.py` | Pinned loader preserves vision and joint head, evaluates outputs with `mx.eval`; earlier synthetic-image and text perturbation smoke passed | Leading Mac candidate; not yet validated in canonical GUI path |
| CUDA/ROCm saved NF4 + official `systemone` | Canonical Windows ROCm image/GUI path passed using load-time NF4; tiny fixture checkpoint roundtrip passed separately | Leading Windows/Linux candidate; full CLEF prequantized save/reload parity still required |
| llama.cpp CLEF GGUF | Joint text answers passed; actual image request returns501; upstream PR29622 still open | Retain text artifact; unsuitable for current screenshot decision path |
| vLLM | Pooling/hidden-state extension interfaces exist, but no Clef entry found in current registry; pooling speed advantage is explicitly not guaranteed | Consider only after demonstrating exact joint-head/vision semantics and a throughput need |
| ONNX Runtime | Execution providers and quantization tools exist; no exported full CLEF graph/parity evidence here | Defer model-specific export until it has a measured device/dependency benefit |

CLEF's official forward calls the backbone without KV caching and passes its
hidden states to the joint head. Serving only the backbone through chat
completion is not an equivalent decision API. Source inspection of the pinned
MLX loader also shows a full backbone and joint-head evaluation per request.
Prefix/vision-feature caching needs separate correctness and changed-image
invalidation checks; it is not assumed to be available or safe already.

Prequantized weights address initialization work, not necessarily steady-state
latency. Compilation, attention kernels, per-request allocator-cache clearing
and token/image limits are profiling hypotheses, not accepted improvements.
The uncommitted MLX/checkpoint/residency prototypes remain separate from deployed
0.1.8; this investigation does not integrate them or regress canonical HIP SDPA
and both image pixel bounds.

Compare the same pinned Flash model, typed questions, text length and image
pixels at concurrency1. Separate preparation, process load, warmup, token/image
preprocessing, vision, backbone, joint head, IPC and complete request. Force
device completion when timing; measure changed inputs, not only repeated cached
answers. Report p50/p95, peak device/host memory, exact versions and correctness
against a floating-point reference before selecting a backend. The earlier
4.2s CPU341-token GGUF smoke and a claimed Mac20ms result are not a controlled
comparison. Published38.8ms Flash median also is not a local-device SLO.

No new performance comparison was run in this investigation. The Mac SSD/model
environment is currently disconnected. The user was asked for the20ms execution
code and timing boundary; that evidence is still pending.

Primary references:
- https://huggingface.co/mlx-community/clef-flash-4bit
- https://huggingface.co/Cloudflare/clef-flash
- https://github.com/ggml-org/llama.cpp/pull/29622
- https://github.com/vllm-project/vllm/blob/main/vllm/model_executor/models/registry.py
- https://docs.vllm.ai/en/latest/models/pooling_models/
- https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html
