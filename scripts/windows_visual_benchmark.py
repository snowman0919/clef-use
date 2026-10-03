"""Controlled wait/cache ablation using the canonical runtime and real Windows GUI."""

import json
import math
import platform
import statistics
import time

from clef_use.models import MODEL_REVISIONS, OMNI_SOURCE_REVISION
from clef_use.runtime import Session, SessionRuntime
from clef_use.schema import Contract, Status
from clef_use.verification import VisualWaitResult


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


class FixedDelayRuntime(SessionRuntime):
    """Diagnostic ablation only; retain fresh target checks and semantic completion."""

    def _wait(self, session, frame, roi, row, *, require_change=True, expected_effect=None):
        started = time.perf_counter()
        if session.cancelled.wait(0.3):
            self._finish(session, Status.ABORTED, "abort requested during fixed-delay ablation")
            return VisualWaitResult("CANCELLED", frame, 0, 300)
        fresh = self._capture(row)
        result = VisualWaitResult("STABLE", fresh, 1, (time.perf_counter() - started) * 1000)
        row.update(
            visual_wait_state="FIXED_DELAY_ABLATION",
            wait_frames=row.get("wait_frames", 0) + 1,
            wait_ms=row.get("wait_ms", 0) + result.elapsed_ms,
        )
        return result


class MeasuredRuntime(SessionRuntime):
    def _wait(self, *args, **kwargs):
        result = super()._wait(*args, **kwargs)
        self.early_advance += bool(
            result.state in {"STABLE", "ALREADY_TRUE"}
            and self.capture.last_pending
            and kwargs.get("require_change", True)
        )
        return result


class MeasuredFixedRuntime(FixedDelayRuntime):
    def _wait(self, *args, **kwargs):
        result = super()._wait(*args, **kwargs)
        self.early_advance += bool(
            result.state in {"STABLE", "ALREADY_TRUE"}
            and self.capture.last_pending
            and kwargs.get("require_change", True)
        )
        return result


def run_benchmark(args, config, perception, decision, desktop, request):
    if not 1 <= args.repeats <= 10:
        raise ValueError("repeats must be 1..10")
    report = {
        "kind": "MEASURED_REAL_WINDOWS_GUI_MAC_MODELS_SSH_DIAGNOSTIC",
        "inference_host": platform.platform(),
        "input_host": "Windows 11",
        "models": MODEL_REVISIONS,
        "omni_source_revision": OMNI_SOURCE_REVISION,
        "device": config.device,
        "parser_device": config.parser_device,
        "method": (
            "Same workers/model/task/start UI; balanced order; 500ms delayed GUI rendering; "
            "fixed-delay is a diagnostic ablation, not the previous product version."
        ),
        "repeats_per_variant": args.repeats,
        "runs": [],
        "cold": None,
        "render_delay_ms": 500,
        "fixed_delay_seconds": 0.3,
        "screen_interval_seconds": config.screen_interval,
        "screen_timeout_seconds": config.screen_timeout,
    }
    variants = ["fixed_delay_no_cache", "visual_wait_no_cache", "visual_wait_cache"]
    runtimes = {}
    for variant in variants:
        cls = MeasuredFixedRuntime if variant.startswith("fixed") else MeasuredRuntime
        local = config.model_copy(update={"perception_cache": variant.endswith("wait_cache")})
        runtimes[variant] = cls(desktop, perception, decision, desktop, local)

    def save():
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    def run(variant, phase, *, no_effect=False):
        request("reset", {"delay_ms": 0 if no_effect else 500, "no_effect": no_effect})
        runtime = runtimes[variant]
        runtime.early_advance = 0
        runtime.log_path = args.output.with_name(
            f"{args.output.stem}-{phase}-{variant}.steps.jsonl"
        )
        session = Session(
            Contract(
                goal="Make Task complete visible using the available Continue and Confirm buttons.",
                success_conditions=["The text Task complete is visible"],
                max_steps=8,
            )
        )
        actual_cold = any(
            worker.process is None or worker.process.poll() is not None
            for worker in (perception.worker, decision.worker)
        )
        started = time.perf_counter()
        result = runtime.execute(session)
        elapsed = time.perf_counter() - started
        readback = request("result")
        wrong = sum(not attempt["correct"] for attempt in readback["input_attempts"])
        completed = result["status"] == "COMPLETED"
        measured = {
            "variant": variant,
            "phase": phase,
            "actual_cold_workers": actual_cold,
            "seconds": elapsed,
            "status": result["status"],
            "reason": result["reason"],
            "success": completed
            and readback["stage"] == 2
            and readback["visible_result"] == "Task complete",
            "false_completion": completed and readback["visible_result"] != "Task complete",
            "wrong_input": wrong,
            "early_advance": runtime.early_advance,
            "act": session.steps,
            "clef_calls": sum(row.get("clef_calls", 0) for row in session.history),
            "parser_calls": sum(row.get("parser_calls", 0) for row in session.history),
            "wait_frames": sum(row.get("wait_frames", 0) for row in session.history),
            "wait_ms": sum(row.get("wait_ms", 0) for row in session.history),
            "verification_ms": sum(row.get("verification_ms", 0) for row in session.history),
            "parser_ms": sum(row.get("parser_ms", 0) for row in session.history),
            "clef_ms": sum(row.get("decision_ms", 0) for row in session.history),
            "readback": readback,
            "metrics": session.history,
            "observed_objects": [obj.model_dump(mode="json") for obj in session.observation.objects]
            if session.observation
            else [],
        }
        print(
            json.dumps(
                {
                    k: v
                    for k, v in measured.items()
                    if k not in {"metrics", "readback", "observed_objects"}
                }
            ),
            flush=True,
        )
        return measured

    def summarize():
        report["summary"] = {}
        for variant in variants:
            rows = [row for row in report["runs"] if row["variant"] == variant]
            warm = [row for row in rows if not row["actual_cold_workers"]]
            report["summary"][variant] = {
                "n": len(rows),
                "actual_warm_runs": len(warm),
                "warm_p50_seconds": statistics.median(row["seconds"] for row in warm)
                if warm
                else None,
                "warm_p95_seconds": percentile([row["seconds"] for row in warm], 0.95)
                if warm
                else None,
                "successes": sum(row["success"] for row in rows),
                "actual_cold_runs": sum(row["actual_cold_workers"] for row in rows),
                **{
                    key: sum(row[key] for row in rows)
                    for key in (
                        "wrong_input",
                        "early_advance",
                        "false_completion",
                        "act",
                        "clef_calls",
                        "parser_calls",
                        "wait_frames",
                        "wait_ms",
                        "verification_ms",
                    )
                },
            }

    backend_failures = 0
    report["status"] = "RUNNING"
    try:
        report["cold"] = run("visual_wait_no_cache", "cold")
        backend_failures += report["cold"]["status"] == "ERROR"
        save()
        for repetition in range(args.repeats):
            for offset in range(len(variants)):
                variant = variants[(repetition + offset) % len(variants)]
                row = run(variant, f"warm-{repetition}")
                report["runs"].append(row)
                backend_failures = backend_failures + 1 if row["status"] == "ERROR" else 0
                save()
                if backend_failures >= 3:
                    break
            if backend_failures >= 3:
                break
        if backend_failures >= 3:
            report["status"] = "BACKEND_UNAVAILABLE"
            report["no_effect"] = {"status": "NOT_RUN", "reason": "Repeated backend errors"}
        else:
            report["no_effect"] = run("visual_wait_cache", "no-effect", no_effect=True)
            report["status"] = (
                "PASSED" if all(row["success"] for row in report["runs"]) else "FAILED"
            )
    except BaseException as exc:
        report["status"] = "INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "ERROR"
        report["diagnostic_error"] = type(exc).__name__
        raise
    finally:
        summarize()
        save()
    report["limitations"] = [
        "Known MPS failures retained; worker restarts are marked actual_cold_workers",
        "Mixed cold/warm latency cannot establish a speed improvement",
        "Small empirical sample; not a general app benchmark",
        "SSH capture/input transport included",
        "Windows-local model inference not tested",
        "Pixel readiness is not semantic proof",
        "Fixed ablation retains new safety/candidate/CLEF contracts",
    ]
    save()
    print(json.dumps(report["summary"], indent=2), flush=True)
    return report["status"] == "PASSED"
