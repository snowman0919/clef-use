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

## Decision-stage profile

The [generated request](evidence/decision-profile-request-0.1.20.json) uses the
canonical request builder, eight typed questions, a manually specified Continue
object and a 600x400 generated image. Both setups saw 1,260 input tokens and chose
ACT/a0. This isolates decision inference; it includes no OmniParser, transport,
desktop capture or input. Each process loaded once, ran three baseline requests,
then three instrumented requests. Nested module timings overlap.

| Setup | Later baseline mean | Encode | Visual | Language model | Head |
| --- | --- | --- | --- | --- | --- |
| Monad RTX 3080 CUDA/NF4 | 0.598s | 0.005s | 0.028s | 0.559s | 0.0045s |
| Windows Radeon 890M ROCm/NF4 | 9.546s | 0.015s | 0.688s | 8.890s | 0.044s |

Stage means are synchronized instrumented calls, with additional measurement
overhead. This is a same-input diagnostic, not an E2E speedup or model quality
benchmark. Answers were identical within each setup before/after instrumentation;
probabilities differ slightly between backends. See [monad evidence](evidence/decision-profile-monad-0.1.20.json)
and [Windows evidence](evidence/decision-profile-windows-0.1.20.json).

Monad layer hooks measured aggregate GatedDeltaNet 0.265s, MLP 0.240s and regular
attention 0.030s. Both processes reported unavailable GatedDeltaNet fast-path
libraries and PyTorch fallback. Windows also reported disabled experimental AMD
efficient SDPA. These observations identify follow-up experiments, not proof that
installing kernels will improve runtime latency or preserve outputs.

Reproduce with canonical worker source and the existing pinned model environment:

```sh
mkdir -p /tmp/clef-profile-source
git archive v0.1.20 src/clef_use | tar -x -C /tmp/clef-profile-source
/path/to/clef-env/bin/python scripts/clef_decision_profile.py \
  --config /path/to/config.toml \
  --package-root /tmp/clef-profile-source/src/clef_use \
  --request-file docs/evidence/decision-profile-request-0.1.20.json \
  --output /tmp/clef-decision-profile.json
```

The output must not already exist. On Windows use the environment's
`Scripts/python.exe -X utf8` and extract the tagged source into a private path.
`--detail-layers` adds synchronized per-layer-family totals. Do not sum nested
stage totals or mistake the first request/load time for steady-state inference.

## Compiled fallback experiment: rejected

[Two isolated CUDA/NF4 trials](evidence/compile-probe-monad-0.1.20.json) replaced
only GatedDeltaNet's torch fallback in a private process. Each trial ran three
eager, three compiled, then three restored-eager calls on the same generated
1,260-token request. Kernel tolerance was atol/rtol 0.001; structured-answer
maximum absolute tolerance was 0.001, fixed before running.

| Compiler option | Eager later mean | Compiled later mean | Restored later mean | Maximum answer delta | Gate |
| --- | --- | --- | --- | --- | --- |
| Default | 0.5991s | 0.5444s | 0.5982s | 0.0021 | FAILED |
| Emulate precision casts | 0.5991s | 0.5467s | 0.5986s | 0.0015 | FAILED |

Warm isolated calls were 8.8–9.1% faster and choices remained unchanged, but both
exceeded the answer gate. The first compiled request included compilation and
kernel validation and took much longer. These results support neither runtime
integration nor an E2E speedup claim. No package, user setting or canonical worker
was changed. Windows/MPS compilation and variable-length requests were not run.

`scripts/clef_compile_probe.py` uses the same source/config/request arguments as
the stage profiler. Its default experiment must fail for this recorded setup;
`--emulate-precision` tests the second variant. Use a fresh output filename and
private `TORCHINDUCTOR_CACHE_DIR` / `TRITON_CACHE_DIR`, and remove owned compiler
caches afterward. The script writes evidence and restores module functions even
when a comparison fails. This is a reproducible rejected experiment, not an
optional production backend. The [PyTorch 2.11 compile contract](https://docs.pytorch.org/docs/2.11/generated/torch.compile.html)
and installed Inductor configuration were inspected before choosing options.
