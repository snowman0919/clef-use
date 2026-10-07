from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from threading import Event

from PIL import Image, ImageDraw

from .config import Config
from .objects import normalize_omni
from .runtime import Session, SessionRuntime
from .schema import ActionResult, Contract, Decision, Frame


class FixtureDesktop:
    def __init__(self):
        self.stage = 0
        self.released = 0

    def capture(self):
        image = Image.new("RGB", (400, 240), ["white", "lightblue", "lightgreen"][self.stage])
        ImageDraw.Draw(image).text(
            (40, 60), ["Open Settings", "Apply size 16", "Font size 16"][self.stage], fill="black"
        )
        return Frame(image)

    def parse(self, image):
        return normalize_omni(
            [
                {
                    "type": "button",
                    "content": ["Settings", "Apply", "Font size 16"][self.stage],
                    "interactivity": self.stage < 2,
                    "bbox": [0.1, 0.2, 0.6, 0.5],
                }
            ]
        )

    def decide(self, observation, goal, candidates, history):
        if self.stage == 2:
            return Decision(
                confidence=0.99,
                goal_probability=0.99,
                condition_probabilities=tuple(0.99 for _ in goal.success_conditions),
            )
        chosen = next(a for a in candidates if a.operation == "click")
        return Decision(action=chosen.id, confidence=0.99, progress=self.stage / 2)

    def execute(self, action, observation, cancelled: Event):
        if cancelled.is_set():
            return ActionResult(ok=False)
        self.stage += 1
        return ActionResult(ok=True)

    def release(self):
        self.released += 1


def fixture_runtime():
    desktop = FixtureDesktop()
    return SessionRuntime(desktop, desktop, desktop, desktop, Config(settle_seconds=0))


def _mean_latency(rows, field):
    measured = [r[field] for r in rows if r.get(field, 0) > 0 and r.get("event") != "terminal"]
    return statistics.mean(measured) if measured else 0


def summarize(session, elapsed):
    rows = session.history
    return {
        "status": session.status.value,
        "task_success": session.status.value == "COMPLETED",
        "wall_seconds": elapsed,
        "low_level_actions": session.steps,
        "outer_llm_interventions": len(session.guidance),
        "parser_ms_mean": _mean_latency(rows, "parser_ms"),
        "clef_ms_mean": _mean_latency(rows, "decision_ms"),
        "confidence": [r["confidence"] for r in rows if "confidence" in r],
        "no_progress_replan_count": int(session.status.value in {"NO_PROGRESS", "NEEDS_REPLAN"}),
    }


def fixture_benchmark(repetitions=5):
    samples = []
    for _ in range(repetitions):
        session = Session(
            Contract(
                goal="Open Settings and apply font size 16",
                success_conditions=["Font size 16"],
                max_steps=8,
            )
        )
        executor = fixture_runtime()
        start = time.perf_counter()
        executor.execute(session)
        samples.append(summarize(session, time.perf_counter() - start))
    return {
        "mode": "DETERMINISTIC_FIXTURE",
        "proves": "control flow only; not ML quality or desktop speed",
        "samples": samples,
    }


def desktop_benchmark(tasks_path: Path, repetitions=1):
    from .client import RuntimeClient
    from .config import state_dir

    tasks = json.loads(tasks_path.read_text())
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 20:
        raise ValueError("benchmark task file must contain 1 to 20 contracts")
    contracts = [Contract.model_validate(task) for task in tasks]
    samples = []
    for _ in range(repetitions):
        for contract in contracts:
            start = time.perf_counter()
            result = RuntimeClient().run(contract)
            elapsed = time.perf_counter() - start
            path = state_dir() / "steps.jsonl"
            rows = (
                [json.loads(line) for line in path.read_text().splitlines()]
                if path.exists()
                else []
            )
            rows = [row for row in rows if row["session_id"] == result["session_id"]]
            samples.append(
                {
                    **result,
                    "task_success": result["status"] == "COMPLETED",
                    "wall_seconds": elapsed,
                    "low_level_actions": result["steps"],
                    "outer_llm_interventions": 0,
                    "parser_ms_mean": _mean_latency(rows, "parser_ms"),
                    "clef_ms_mean": _mean_latency(rows, "decision_ms"),
                    "confidence": [r["confidence"] for r in rows if "confidence" in r],
                    "no_progress_replan_count": int(
                        result["status"] in {"NO_PROGRESS", "NEEDS_REPLAN"}
                    ),
                }
            )
    return {"mode": "REAL_DESKTOP", "samples": samples}
