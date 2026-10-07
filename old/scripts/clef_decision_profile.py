"""Profile a canonical CLEF request on generated pixels without desktop input."""

import argparse
import copy
import hashlib
import importlib.metadata
import json
import statistics
import sys
import time
import tomllib
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--request-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--detail-layers", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("evidence output already exists")
    import torch

    sys.path.insert(0, str(args.package_root))
    from model_worker import ClefWorker
    from models import MODEL_REVISIONS

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    config.setdefault("decision_model", "Cloudflare/clef-flash")
    config.setdefault("ml_profile", "auto")
    record = json.loads(args.request_file.read_text(encoding="utf-8"))
    started = time.perf_counter()
    worker = ClefWorker(config)
    load_seconds = time.perf_counter() - started
    if worker.backend not in {"cuda", "rocm", "mps"}:
        raise ValueError("this diagnostic requires CUDA, ROCm or MPS")
    synchronize = torch.mps.synchronize if worker.backend == "mps" else torch.cuda.synchronize
    import joint_schema_model as upstream

    rows, timings, handles, originals = [], {}, [], {}

    def timed_function(name, function):
        def call(*positional, **keywords):
            synchronize()
            start = time.perf_counter()
            result = function(*positional, **keywords)
            synchronize()
            timings[name] = timings.get(name, 0) + time.perf_counter() - start
            return result

        return call

    def instrument_module(name, module):
        starts = []

        def before(_module, _arguments):
            synchronize()
            starts.append(time.perf_counter())

        def after(_module, _arguments, _result):
            synchronize()
            timings[name] = timings.get(name, 0) + time.perf_counter() - starts.pop()

        handles.extend(
            [module.register_forward_pre_hook(before), module.register_forward_hook(after)]
        )

    try:
        for mode in ("baseline", "instrumented"):
            if mode == "instrumented":
                for name in ("encode_record", "collate_records"):
                    originals[name] = getattr(upstream, name)
                    setattr(upstream, name, timed_function(name, originals[name]))
                backbone = worker.model.language_model.model
                instrument_module("backbone", backbone)
                instrument_module("head", worker.model.head)
                for name in ("visual", "language_model"):
                    if hasattr(backbone, name):
                        instrument_module(name, getattr(backbone, name))
                if args.detail_layers:
                    for module in backbone.modules():
                        name = type(module).__name__
                        if name in {"Qwen3_5GatedDeltaNet", "Qwen3_5Attention", "Qwen3_5MLP"}:
                            instrument_module(name, module)
            for repetition in range(3):
                timings.clear()
                synchronize()
                start = time.perf_counter()
                response = worker.request(copy.deepcopy(record))
                synchronize()
                row = {
                    "mode": mode,
                    "repetition": repetition,
                    "seconds": time.perf_counter() - start,
                    "stages_seconds": dict(timings),
                    "usage": response["usage"],
                    "answers": response["answers"],
                }
                rows.append(row)
                print(json.dumps({k: v for k, v in row.items() if k != "answers"}), flush=True)
    finally:
        for handle in handles:
            handle.remove()
        for name, function in originals.items():
            setattr(upstream, name, function)
    report = {
        "scope": (
            "same generated-pixel request; no desktop input, no parser, no runtime optimization"
        ),
        "method": (
            "three baseline requests then three synchronized instrumented requests; "
            "nested stages overlap"
        ),
        "limitation": (
            "instrumentation adds synchronization overhead; "
            "one request/setup, not stability or speedup proof"
        ),
        "backend": worker.backend,
        "quantization": config.get("quantization", "none"),
        "torch": torch.__version__,
        "transformers": importlib.metadata.version("transformers"),
        "bitsandbytes": importlib.metadata.version("bitsandbytes")
        if config.get("quantization") == "4bit"
        else None,
        "detail_layers": args.detail_layers,
        "gpu": torch.cuda.get_device_name() if worker.backend != "mps" else "Apple MPS",
        "revision": MODEL_REVISIONS[config["decision_model"]],
        "worker_sha256": hashlib.sha256(
            (args.package_root / "model_worker.py").read_bytes()
        ).hexdigest(),
        "request_sha256": hashlib.sha256(args.request_file.read_bytes()).hexdigest(),
        "load_seconds": load_seconds,
        "baseline_later_mean_seconds": statistics.mean(r["seconds"] for r in rows[1:3]),
        "answers_identical": all(r["answers"] == rows[0]["answers"] for r in rows),
        "rows": rows,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not report["answers_identical"]:
        raise RuntimeError("instrumentation changed answers; inspect evidence")


if __name__ == "__main__":
    main()
