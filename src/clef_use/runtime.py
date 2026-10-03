from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .candidates import CandidateBuilder
from .config import Config
from .interfaces import ActionBackend, CaptureBackend, DecisionBackend, PerceptionBackend, Verifier
from .schema import Contract, Observation, Status
from .verification import ProgressTracker, VisualVerifier


@contextmanager
def _timing(row, field):
    started = time.perf_counter()
    try:
        yield
    finally:
        row[field] = row.get(field, 0.0) + (time.perf_counter() - started) * 1000


@dataclass
class Session:
    contract: Contract
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: Status = Status.RUNNING
    steps: int = 0
    rounds: int = 0
    confidence: float | None = None
    last_action: dict | None = None
    reason: str = "execution started"
    history: list[dict] = field(default_factory=list)
    action_history: list[dict] = field(default_factory=list)
    cancelled: threading.Event = field(default_factory=threading.Event)
    observation: Observation | None = None
    guidance: list[str] = field(default_factory=list)
    lock: threading.RLock = field(default_factory=threading.RLock)

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "session_id": self.id,
                "status": self.status.value,
                "steps": self.steps,
                "rounds": self.rounds,
                "last_action": self.last_action,
                "confidence": self.confidence,
                "reason": self.reason,
                "summary": (
                    f"{self.status.value} after {self.steps} actions, {self.rounds} decisions"
                ),
            }


class SessionRuntime:
    def __init__(
        self,
        capture: CaptureBackend,
        perception: PerceptionBackend,
        decision: DecisionBackend,
        action: ActionBackend,
        config: Config | None = None,
        verifier: Verifier | None = None,
        log_path: Path | None = None,
    ):
        self.capture = capture
        self.perception = perception
        self.decision = decision
        self.action = action
        self.config = config or Config()
        self.verifier = verifier or VisualVerifier()
        self.builder = CandidateBuilder(self.config.max_candidates)
        self.log_path = log_path
        self.desktop_lock = threading.Lock()

    def abort(self, session: Session) -> dict:
        session.cancelled.set()
        with session.lock:
            if session.status == Status.RUNNING:
                session.status, session.reason = Status.ABORTED, "explicit abort requested"
        self.action.release()
        return session.snapshot()

    def _finish(self, session: Session, status: Status, reason: str) -> dict:
        with session.lock:
            session.status = Status.ABORTED if session.cancelled.is_set() else status
            session.reason = "explicit abort requested" if session.cancelled.is_set() else reason
        return session.snapshot()

    def _record(self, session: Session, row: dict) -> None:
        row.update(
            timestamp=datetime.now(UTC).isoformat(),
            session_id=session.id,
            step=session.steps,
            terminal_event=session.status.value,
        )
        with session.lock:
            session.history.append(row)
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with self.log_path.open("a", encoding="utf-8") as stream:
                self.log_path.chmod(0o600)
                stream.write(json.dumps(row) + "\n")

    def execute(self, session: Session) -> dict:
        if not self.desktop_lock.acquire(blocking=False):
            result = self._finish(
                session, Status.SAFETY_BLOCK, "another session owns desktop input"
            )
            self._record(session, {"event": "terminal", "reason": session.reason})
            return result
        tracker = ProgressTracker(self.config.no_progress_limit)
        completion_predictions = 0
        row = {}
        try:
            while session.rounds < session.contract.max_steps:
                if session.cancelled.is_set():
                    return self._finish(session, Status.ABORTED, "abort requested")
                row = {
                    "capture_ms": 0.0,
                    "parser_ms": 0.0,
                    "decision_ms": 0.0,
                    "execution_ms": 0.0,
                    "state_change_score": None,
                }
                with _timing(row, "capture_ms"):
                    frame = self.capture.capture()
                with _timing(row, "parser_ms"):
                    objects = self.perception.parse(frame.image)
                observation = Observation(uuid.uuid4().hex, frame, objects)
                with session.lock:
                    session.observation = observation
                candidates = self.builder.build(observation, session.contract)
                history = [{"guidance": g} for g in session.guidance] + session.action_history[-6:]
                with _timing(row, "decision_ms"):
                    decision = self.decision.decide(
                        observation, session.contract, candidates, history
                    )
                row.update(confidence=decision.confidence, progress=decision.progress)
                row.update(
                    goal_probability=decision.goal_probability,
                    condition_probabilities=decision.condition_probabilities,
                    replan_probability=decision.replan_probability,
                    safety_probability=decision.safety_probability,
                )
                if self.config.debug:
                    row.update(
                        object_count=len(objects),
                        candidate_count=len(candidates),
                        observation_id=observation.id,
                    )
                with session.lock:
                    session.rounds += 1
                    session.confidence = decision.confidence
                if session.cancelled.is_set():
                    return self._finish(session, Status.ABORTED, "abort requested")
                if decision.safety_probability >= 0.5:
                    return self._finish(
                        session, Status.SAFETY_BLOCK, "constraint or safety decision"
                    )
                if decision.replan_probability >= 0.8:
                    return self._finish(
                        session, Status.NEEDS_REPLAN, "executor needs planner guidance"
                    )
                conditions = decision.condition_probabilities
                completed = (
                    decision.goal_probability >= 0.9
                    and len(conditions) == len(session.contract.success_conditions)
                    and all(p >= 0.9 for p in conditions)
                )
                if completed:
                    with _timing(row, "capture_ms"):
                        fresh = self.capture.capture()
                    if self.verifier.change(frame, fresh) > 0.08:
                        return self._finish(
                            session,
                            Status.NEEDS_REPLAN,
                            "screen changed during completion verification",
                        )
                    completion_predictions += 1
                    if completion_predictions >= 2:
                        return self._finish(
                            session,
                            Status.COMPLETED,
                            "goal and conditions verified on two fresh observations",
                        )
                    self._record(session, row)
                    if session.cancelled.wait(self.config.settle_seconds):
                        return self._finish(session, Status.ABORTED, "abort requested")
                    continue
                completion_predictions = 0
                if decision.confidence < session.contract.confidence_threshold:
                    return self._finish(
                        session, Status.LOW_CONFIDENCE, "action confidence below threshold"
                    )
                selected = next((a for a in candidates if a.id == decision.action), None)
                if selected is None:
                    return self._finish(
                        session, Status.ERROR, "decision selected an unknown candidate"
                    )
                # Never act on a screen that materially changed during model inference.
                with _timing(row, "capture_ms"):
                    fresh = self.capture.capture()
                if self.verifier.change(frame, fresh) > 0.08:
                    return self._finish(
                        session, Status.NEEDS_REPLAN, "screen changed during decision"
                    )
                with _timing(row, "execution_ms"):
                    result = self.action.execute(selected, observation, session.cancelled)
                row["action"] = selected.audit()
                row["execution_ok"] = result.ok
                if session.cancelled.is_set():
                    return self._finish(session, Status.ABORTED, "abort requested")
                if not result.ok:
                    return self._finish(
                        session, Status.ERROR, "action adapter refused or failed execution"
                    )
                with session.lock:
                    session.steps += 1
                    session.last_action = selected.audit()
                    session.action_history.append(
                        {"operation": selected.operation, "description": selected.description}
                    )
                session.cancelled.wait(self.config.settle_seconds)
                with _timing(row, "capture_ms"):
                    after = self.capture.capture()
                score = self.verifier.change(frame, after)
                row["state_change_score"] = score
                if tracker.update(score, self.verifier.fingerprint(after)):
                    return self._finish(
                        session, Status.NO_PROGRESS, "unchanged or repeated visual state"
                    )
                self._record(session, row)
                row = {}
            return self._finish(
                session, Status.STEP_BUDGET_EXHAUSTED, "hard decision budget exhausted"
            )
        except Exception as exc:
            # Third-party exceptions may contain typed payloads or local credentials.
            diagnostic = getattr(exc, "diagnostic", None)
            if diagnostic:
                row["backend_error"] = diagnostic
            return self._finish(session, Status.ERROR, f"{type(exc).__name__} in runtime backend")
        finally:
            try:
                self.action.release()
            finally:
                self.desktop_lock.release()
                if row:
                    row["reason"] = session.reason
                    self._record(session, row)
                elif session.status != Status.RUNNING:
                    self._record(session, {"event": "terminal", "reason": session.reason})

    def observe(self, session: Session, *, refresh=True, include_image=False) -> dict:
        fresh = False
        if refresh and self.desktop_lock.acquire(blocking=False):
            try:
                frame = self.capture.capture()
                objects = self.perception.parse(frame.image)
                with session.lock:
                    session.observation = Observation(uuid.uuid4().hex, frame, objects)
                fresh = True
            finally:
                self.desktop_lock.release()
        with session.lock:
            observation = session.observation
            result = {
                **session.snapshot(),
                "goal": session.contract.goal,
                "recent_actions": [
                    r.get("action") for r in session.history[-6:] if r.get("action")
                ],
                "objects": [o.model_dump(mode="json") for o in observation.objects[:100]]
                if observation
                else [],
                "observation_id": observation.id if observation else None,
                "observation_fresh": fresh,
                "image_sha256": hashlib.sha256(observation.frame.image.tobytes()).hexdigest()
                if observation
                else None,
            }
            image = observation.frame.image.copy() if include_image and observation else None
        if image is not None:
            from .backends import encode_image

            image.thumbnail((1280, 1280))
            result["image_png"] = encode_image(image)
        return result
