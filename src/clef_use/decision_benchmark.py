"""Pinned, sequential real-model decision replay; deliberately never executes OS input."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import platform
import statistics
import time
from pathlib import Path

from PIL import Image

from .backends import JsonWorker
from .config import load_config
from .decision_contract import validate_answers
from .models import DECISION_MODELS, DEFAULT_DECISION_MODEL, MODEL_REVISIONS


def load_corpus(path: Path) -> list[dict]:
    document = json.loads(path.read_text())
    cases = document.get("cases")
    if (
        document.get("schema_version") != 1
        or not isinstance(cases, list)
        or not 1 <= len(cases) <= 100
    ):
        raise ValueError("decision corpus requires schema_version 1 and 1 to 100 cases")
    seen, rows = set(), []
    for case in cases:
        if not isinstance(case.get("id"), str) or not case["id"] or case["id"] in seen:
            raise ValueError("case identifiers must be unique nonempty strings")
        seen.add(case["id"])
        if case.get("platform") not in {"blender", "windows", "macos"}:
            raise ValueError("explicit Blender/Windows/macOS capture provenance required")
        provenance = case.get("provenance", {})
        if provenance.get("kind") not in {"independent_native_readback", "archived_unlabelled"}:
            raise ValueError("native readback or explicitly unlabelled archive required")
        expected = case.get("expected", {})
        if provenance["kind"] == "archived_unlabelled" and expected:
            raise ValueError("unlabelled failures cannot supply invented ground truth")
        image_path = path.parent / case["image"]
        data = image_path.read_bytes()
        if hashlib.sha256(data).hexdigest() != case.get("image_sha256"):
            raise ValueError(f"capture hash mismatch: {case['id']}")
        with Image.open(image_path) as image:
            image.load()
            pixels = image.convert("RGB")
            pixel_hash = hashlib.sha256(pixels.tobytes()).hexdigest()
            size = list(image.size)
        request = case["request"]
        if not isinstance(request.get("state"), dict) or not isinstance(
            request.get("questions"), dict
        ):
            raise ValueError("typed state/questions request required")
        if not request["questions"] or len(request["questions"]) > 64:
            raise ValueError("bounded nonempty decision questions required")
        if not isinstance(expected, dict) or not set(expected) <= set(request["questions"]):
            raise ValueError("ground truth must reference submitted questions")
        for question in request["questions"].values():
            if not isinstance(question.get("instructions"), str):
                raise ValueError("each typed decision question requires instructions")
            kind, criteria = question.get("type"), question.get("criteria")
            if kind == "choice" and (
                not isinstance(criteria, dict) or not 2 <= len(criteria) <= 100
            ):
                raise ValueError("choice requires 2 to 100 named alternatives")
            if kind == "score" and (not isinstance(criteria, list) or not 2 <= len(criteria) <= 10):
                raise ValueError("score requires 2 to 10 ordered levels")
            if kind not in {"choice", "score", "noul"}:
                raise ValueError("only typed choice/score/noul questions are supported")
        for name, truth in expected.items():
            question = request["questions"][name]
            if question["type"] == "choice":
                if not isinstance(truth, str) or truth not in question["criteria"]:
                    raise ValueError("ground truth must preserve a submitted choice identifier")
            else:
                bounds = truth.get("range") if isinstance(truth, dict) else None
                maximum = len(question["criteria"]) - 1 if question["type"] == "score" else 1
                if (
                    not isinstance(bounds, list)
                    or len(bounds) != 2
                    or any(
                        type(value) not in (int, float) or not math.isfinite(value)
                        for value in bounds
                    )
                    or not 0 <= bounds[0] <= bounds[1] <= maximum
                ):
                    raise ValueError("numeric truth requires a finite, in-domain ordered range")
        packet = {**request, "image": base64.b64encode(data).decode()}
        digest = hashlib.sha256(
            json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        rows.append(
            {
                **case,
                "request": packet,
                "input_sha256": digest,
                "pixel_sha256": pixel_hash,
                "image_size": size,
                "expected": expected,
            }
        )
    return rows


def score_answers(expected: dict, answers: dict) -> dict:
    correct = false_complete = 0
    for name, truth in expected.items():
        answer = answers[name]
        if isinstance(truth, str):
            correct += answer.get("choice") == truth
            if name == "complete" and truth == "no" and answer.get("choice") == "yes":
                false_complete += 1
        elif isinstance(truth, dict) and "range" in truth:
            lower, upper = truth["range"]
            value = answer.get("score", answer.get("noul"))
            correct += value is not None and lower <= value <= upper
        else:
            raise ValueError("truth must be an option identifier or explicit numeric range")
    return {
        "known_fields": len(expected),
        "correct_fields": correct,
        "false_completions": false_complete,
    }


def promotion_gate(report: dict) -> dict:
    # Replay accuracy is not execution success, no-effect recovery or safety proof.
    # No code path mutates config/default. Live paired evidence is a separate gate.
    blockers = ["replay_is_not_same_task_live_success_proof"]
    platforms = {
        row["platform"] for model in report.get("models", []) for row in model.get("samples", [])
    }
    blockers += [
        f"missing_{name}_live_paired_success_and_safety" for name in ("blender", "windows", "macos")
    ]
    if platforms != {"blender", "windows", "macos"}:
        blockers.append("incomplete_native_fixture_coverage")
    if any(model.get("status") != "OK" for model in report.get("models", [])):
        blockers.append("real_model_execution_failed")
    summaries = {model["model"]: model.get("summary", {}) for model in report.get("models", [])}
    baseline = summaries.get("Cloudflare/clef-flash", {})
    candidate = summaries.get("LiquidAI/d1-3B", {})
    if baseline.get("known_fields") == candidate.get("known_fields") and baseline.get(
        "known_fields"
    ):
        if candidate["field_accuracy"] < baseline["field_accuracy"]:
            blockers.append("known_field_accuracy_regressed")
        if candidate["false_completions"] > baseline["false_completions"]:
            blockers.append("false_completions_increased")
    return {"eligible": False, "default_model": DEFAULT_DECISION_MODEL, "blockers": blockers}


def run_benchmark(
    corpus_path: Path, config, *, models: list[str], repetitions=3, profile="deployment"
) -> dict:
    if not 1 <= repetitions <= 20:
        raise ValueError("repetitions must be between 1 and 20")
    if not models or len(set(models)) != len(models) or not set(models) <= set(DECISION_MODELS):
        raise ValueError("unique pinned decision models required")
    cases = load_corpus(corpus_path)
    report = {
        "schema_version": 1,
        "mode": "REAL_GUI_DECISION_REPLAY",
        "native_input": False,
        "scope": "decision only; no parser, grounding or OS input; not task-success proof",
        "corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        "case_count": len(cases),
        "repetitions": repetitions,
        "profile": profile,
        "seed": 0,
        "split": "fixed authentic GUI replay; no fitting or calibration",
        "hardware": {
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "cpu": platform.processor(),
            "logical_cpus": os.cpu_count(),
        },
        "models": [],
    }
    for model in models:
        spec = DECISION_MODELS[model]
        updates = {"decision_model": model, "backend_timeout": 600}
        if model == "LiquidAI/d1-3B":
            updates["quantization"] = "none"
        if profile == "cpu-bfloat16":
            updates.update(
                device="cpu",
                ml_profile="linux-cpu",
                quantization="none",
                cpu_compute_dtype="bfloat16",
            )
        # Explicit common SDK for a controlled full-precision comparison, separate processes.
        # Deployment profile retains each independently pinned production environment.
        if profile == "cpu-bfloat16":
            updates[spec.python_field] = config.d1_python
        selected = config.model_copy(update=updates)
        worker = JsonWorker(getattr(selected, spec.python_field), spec.worker_kind, selected)
        result = {
            "model": model,
            "revision": MODEL_REVISIONS[model],
            "status": "ERROR",
            "precision": selected.quantization,
            "samples": [],
        }
        report["models"].append(result)
        try:
            began = time.perf_counter()
            worker._start()
            result["load_seconds"] = time.perf_counter() - began
            result["worker_info"] = worker.ready
            result["python"] = str(getattr(selected, spec.python_field))
            # Mark first request cold separately; subsequent measurements remain raw.
            for repetition in range(repetitions):
                for case in cases:
                    start = time.perf_counter()
                    reply = worker.request(
                        {**case["request"], "benchmark_metrics": True, "benchmark_seed": 0}
                    )
                    latency = (time.perf_counter() - start) * 1000
                    answers = validate_answers(
                        case["request"]["questions"], reply, answer_decimals=spec.answer_decimals
                    )
                    result["samples"].append(
                        {
                            "case_id": case["id"],
                            "platform": case["platform"],
                            "input_sha256": case["input_sha256"],
                            "pixel_sha256": case["pixel_sha256"],
                            "provenance": case["provenance"],
                            "repetition": repetition,
                            "cold": not result["samples"],
                            "latency_ms": latency,
                            "answers": answers,
                            "usage": reply.get("usage"),
                            "memory": reply.get("benchmark_metrics"),
                            **score_answers(case["expected"], answers),
                        }
                    )
            samples = result["samples"]
            warm = [row["latency_ms"] for row in samples if not row["cold"]]
            known = sum(row["known_fields"] for row in samples)
            result["summary"] = {
                "samples": len(samples),
                "known_fields": known,
                "correct_fields": sum(row["correct_fields"] for row in samples),
                "field_accuracy": sum(row["correct_fields"] for row in samples) / known
                if known
                else None,
                "false_completions": sum(row["false_completions"] for row in samples),
                "cold_latency_ms": samples[0]["latency_ms"],
                "warm_latency_ms_mean": statistics.mean(warm) if warm else None,
                "warm_latency_ms_median": statistics.median(warm) if warm else None,
                "warm_latency_ms_stdev": statistics.stdev(warm) if len(warm) > 1 else None,
                "warm_latency_ms_range": [min(warm), max(warm)] if warm else None,
                "worker_peak_rss_bytes": max(
                    (row["memory"].get("peak_rss_bytes", 0) for row in samples if row["memory"]),
                    default=0,
                )
                or None,
                "gpu_peak_allocated_bytes": max(
                    (
                        row["memory"].get("gpu_peak_allocated_bytes", 0)
                        for row in samples
                        if row["memory"]
                    ),
                    default=0,
                )
                or None,
            }
            result["status"] = "OK"
        except Exception as exc:
            result["error"] = {
                "type": type(exc).__name__,
                "message": str(exc)[-1000:],
                "diagnostic": getattr(exc, "diagnostic", None),
            }
        finally:
            worker.close()
    report["promotion"] = promotion_gate(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--models",
        nargs="+",
        choices=list(DECISION_MODELS),
        default=["Cloudflare/clef-flash", "LiquidAI/d1-3B"],
    )
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--profile", choices=["deployment", "cpu-bfloat16"], default="deployment")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("benchmark evidence output already exists")
    report = run_benchmark(
        args.corpus,
        load_config(),
        models=args.models,
        repetitions=args.repetitions,
        profile=args.profile,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if all(row["status"] == "OK" for row in report["models"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
