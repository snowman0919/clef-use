"""Compare a compiled GatedDeltaNet fallback inside an isolated real CLEF worker."""

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
    parser.add_argument("--emulate-precision", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("evidence output already exists")
    import torch

    sys.path.insert(0, str(args.package_root))
    from model_worker import ClefWorker

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    config.setdefault("decision_model", "Cloudflare/clef-flash")
    request = json.loads(args.request_file.read_text(encoding="utf-8"))
    report = {
        "scope": "isolated generated-pixel request; no desktop input or runtime integration",
        "torch": torch.__version__,
        "transformers": importlib.metadata.version("transformers"),
        "compiler": "inductor; fullgraph=True, dynamic=False, default mode",
        "emulate_precision_casts": args.emulate_precision,
        "answer_tolerance": 0.001,
        "worker_sha256": hashlib.sha256(
            (args.package_root / "model_worker.py").read_bytes()
        ).hexdigest(),
        "request_sha256": hashlib.sha256(args.request_file.read_bytes()).hexdigest(),
        "rows": [],
        "kernel_checks": [],
    }
    replacements = []
    try:
        worker = ClefWorker(config)
        if worker.backend != "cuda":
            raise ValueError("this experiment requires NVIDIA CUDA")
        report["gpu"] = torch.cuda.get_device_name()
        modules = [
            module
            for module in worker.model.modules()
            if type(module).__name__ == "Qwen3_5GatedDeltaNet"
        ]
        if not modules:
            raise ValueError("no GatedDeltaNet modules found")
        original = modules[0].chunk_gated_delta_rule
        if original.__name__ != "torch_chunk_gated_delta_rule":
            raise ValueError("expected the canonical torch fallback")
        compiled = torch.compile(
            original,
            fullgraph=True,
            dynamic=False,
            options={"emulate_precision_casts": args.emulate_precision},
        )
        checked = False

        def checked_kernel(*positional, **keywords):
            nonlocal checked
            actual = compiled(*positional, **keywords)
            if not checked:
                expected = original(*positional, **keywords)
                delta = (actual[0].float() - expected[0].float()).abs().max().item()
                report["kernel_checks"].append(
                    {"max_abs_delta": delta, "shape": list(actual[0].shape)}
                )
                torch.testing.assert_close(actual[0], expected[0], atol=0.001, rtol=0.001)
                checked = True
            return actual

        for mode in ("eager", "compiled", "restored"):
            if mode == "compiled":
                for module in modules:
                    replacements.append((module, module.chunk_gated_delta_rule))
                    module.chunk_gated_delta_rule = checked_kernel
            if mode == "restored":
                for module, function in replacements:
                    module.chunk_gated_delta_rule = function
            for repetition in range(3):
                torch.cuda.synchronize()
                started = time.perf_counter()
                response = worker.request(copy.deepcopy(request))
                torch.cuda.synchronize()
                row = {
                    "mode": mode,
                    "repetition": repetition,
                    "seconds": time.perf_counter() - started,
                    "answers": response["answers"],
                    "usage": response["usage"],
                }
                report["rows"].append(row)
                args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                print(json.dumps({k: v for k, v in row.items() if k != "answers"}), flush=True)
        report["later_mean_seconds"] = {
            mode: statistics.mean(
                row["seconds"]
                for row in report["rows"]
                if row["mode"] == mode and row["repetition"] > 0
            )
            for mode in ("eager", "compiled", "restored")
        }
        reference = report["rows"][0]["answers"]
        deltas = []
        for row in report["rows"]:
            for name, answer in reference.items():
                actual = row["answers"][name]
                if answer["type"] == "choice":
                    if actual["choice"] != answer["choice"]:
                        raise AssertionError("compiled choice changed")
                for key in ("confidence", "noul", "score"):
                    if key in answer:
                        deltas.append(abs(actual[key] - answer[key]))
                for key, value in answer.get("probabilities", {}).items():
                    deltas.append(abs(actual["probabilities"][key] - value))
        report["answer_max_abs_delta"] = max(deltas)
        if report["answer_max_abs_delta"] > 0.001:
            raise AssertionError("compiled answer tolerance exceeded")
        report["status"] = "PASSED"
    except Exception as exc:
        report["status"] = "FAILED"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        for module, function in replacements:
            module.chunk_gated_delta_rule = function
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
