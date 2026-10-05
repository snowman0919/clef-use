# Benchmark methodology

`clef-use benchmark --repetitions 5` runs deterministic fixtures. Its results
measure control-flow overhead and prove no model-quality or desktop-speed claim.

For an operator-controlled desktop, provide a JSON list of ordinary contracts:

```json
[{"goal":"In the open Calculator compute 123 * 456",
  "success_conditions":["Calculator shows 56088"],"max_steps":20}]
```

```sh
clef-use benchmark --tasks tasks.json --repetitions 1
```

This command performs real desktop input. Arrange/reset the intended application
before each task; there is no hidden setup or external paid API. Record versions,
hardware, cold/warm status, display scale and start state. Output includes success,
wall time, action count, zero outer planner interventions for this autonomous
baseline, mean parser/CLEF latency, confidence samples and no-progress/replan count.
Logs contain per-round capture/parser/decision/execution timing. Model cold loads
are included in the first parser/decision round, and must be separated before
making steady-state claims. Compare the same tasks and hardware against a VLM
baseline before claiming improvement. No such comparison has been run yet.

`scripts/model_smoke.py` tests actual pinned models on rendered multi-stage pixels
with a deterministic image state transition. It injects no OS input and is
separately labelled REAL_MODELS_SYNTHETIC_PIXELS. Current results and GUI deferral
are recorded in [validation](evidence/VALIDATION.md).

## Recorded 0.1.20 baseline

[Measured samples](evidence/latency-0.1.20.json) come from one recorded trial per
setup. “Later decision” excludes the first measured decision, whose time includes
initialization; it is not an isolated kernel benchmark.

| Setup | Actions / decisions | First decision | Later decision mean | Outer interventions |
| --- | --- | --- | --- | --- |
| Windows native GUI, ROCm/NF4 CLEF, CPU Omni | 2 / 4 | 119.609s | 17.532s | 0 |
| Monad Xvfb, CUDA/NF4 CLEF, CPU Omni | 2 / 5 | 16.654s | 0.816s | 1 continue |
| macOS generated pixels, MPS CLEF, CPU Omni | 2 / 4 | 48.598s | 6.760s | 0 |

Tasks, hardware and display environments differ: these rows cannot rank backends
or demonstrate a speedup. Monad needed recovery after delayed rendering; macOS
used no desktop input. Windows total wall time was not measured. Both cold loads
and later decisions remain material costs. No 20ms decision claim is supported.
