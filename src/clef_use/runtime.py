from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import uuid
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from .activity import SilentActivity
from .candidates import CandidateBuilder, effect_region
from .config import Config
from .interfaces import ActionBackend, CaptureBackend, DecisionBackend, PerceptionBackend, Verifier
from .router import ExecutionRouter, GroundingUncertain
from .schema import Contract, Decision, Observation, Status
from .verification import (
    ProgressTracker,
    VisualVerifier,
    VisualWaiter,
    content_changed,
    foreground_region,
    region_change_count,
    region_changed,
    region_pixels,
    same_context,
    text_effect,
)
from .windows_input import WindowsDesktopUnavailable, WindowsForegroundChanged

COMPLETION_PROBABILITY = 0.9


def _action_identity(action):
    points = tuple((p.x, p.y) for p in action.pointer.points) if action.pointer else ()
    return action.operation, action.target, action.value, points


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
    blocker: dict | None = None
    activity: dict = field(default_factory=lambda: {"phase": "Starting"})
    last_effect: dict | None = field(default=None, repr=False)
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
                "blocker": self.blocker,
                "activity": dict(self.activity),
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
        activity=None,
        grounder=None,
    ):
        self.activity = activity or SilentActivity()
        self.capture = capture
        self.perception = perception
        self.decision = decision
        self.action = action
        self.config = config or Config()
        self.verifier = verifier or VisualVerifier()
        self.builder = CandidateBuilder(self.config.max_candidates)
        self.router = ExecutionRouter(self.config, grounder)
        self.log_path = log_path
        self.desktop_lock = threading.Lock()
        self.waiter = VisualWaiter(
            self.config.screen_timeout,
            self.config.screen_interval,
            self.config.screen_stable_samples,
        )
        self._perception_cache = None

    def _parse(self, frame, row=None):
        identity = getattr(self.perception, "cache_identity", None)
        key = None
        if self.config.perception_cache and identity is not None:
            # Parser objects depend on pixels; input binding still checks the full fresh frame.
            key = (
                identity,
                frame.image.size,
                frame.image.mode,
                hashlib.sha256(frame.image.tobytes()).digest(),
            )
            if self._perception_cache is not None and self._perception_cache[0] == key:
                if row is not None:
                    row["perception_cache_hit"] = True
                    row["parser_calls"] = 0
                return self._perception_cache[1]
        if row is not None:
            row["parser_calls"] = 1
        objects = self.perception.parse(frame.image)
        if row is not None:
            row["perception_cache_hit"] = False
            metrics = getattr(self.perception, "metrics", None)
            if metrics is not None:
                row["parser_stages"] = dict(metrics)
        self._perception_cache = (key, objects) if key is not None else None
        return objects

    def _phase(self, session, phase, target=None, point=None):
        with session.lock:
            if session.cancelled.is_set():
                phase, target, point = "Cancelling", None, None
            session.activity = {"phase": phase, "target": target, "point": point}
        self.activity.update(phase, session, point=point, target=target)
        if hasattr(self.activity, "enabled"):
            with session.lock:
                session.activity["display"] = (
                    "active"
                    if self.activity.enabled
                    else ("unavailable" if self.activity.requested else "disabled")
                )

    def _capture(self, row=None):
        with self.activity.capture(self.capture):
            if row is None:
                return self.capture.capture()
            row["capture_calls"] = row.get("capture_calls", 0) + 1
            with _timing(row, "capture_ms"):
                return self.capture.capture()

    def _context_stale(self, before, fresh):
        return (
            not same_context(before, fresh)
            or self.verifier.change(before, fresh) > 0.08
            or region_change_count(before, fresh, foreground_region(before)) >= 256
        )

    def _stale(self, before, fresh, roi):
        return self._context_stale(before, fresh) or (
            roi is not None and region_changed(before, fresh, roi)
        )

    def _target_ready(self, session, before, fresh, roi, row, *, allow_fresh_reference=False):
        self._phase(session, "Checking target")

        def reference_matches(candidate):
            # The waiter independently establishes consecutive stable ROI pixels.
            # Eligible model pointers can then be regrounded, while retaining the
            # window identity and the strict pointer hash gate below.
            if allow_fresh_reference:
                return same_context(before, candidate)
            return not self._stale(before, candidate, roi)

        capture = SimpleNamespace(capture=lambda: self._capture(row))
        result = self.waiter.wait(
            capture,
            fresh,
            roi,
            session.cancelled,
            require_change=False,
            predicate=reference_matches,
        )
        row["wait_frames"] = row.get("wait_frames", 0) + result.polls
        row["wait_ms"] = row.get("wait_ms", 0) + result.elapsed_ms
        row["verification_ms"] = row.get("verification_ms", 0) + result.verification_ms
        row["pre_input_readiness"] = result.state
        if result.state == "CANCELLED":
            self._finish(session, Status.ABORTED, "abort requested before input")
        elif result.state not in {"STABLE", "ALREADY_TRUE"}:
            self._finish(
                session,
                Status.NEEDS_REPLAN,
                "target reference did not recur and stabilize before input",
            )
        return result

    def _wait(self, session, frame, roi, row, *, require_change=True, expected_effect=None):
        self._phase(
            session,
            "Checking result",
            session.activity.get("target"),
            session.activity.get("point"),
        )
        predicate = None
        if require_change and expected_effect in {"content_change", "text_value", "view_change"}:

            def predicate(fresh):
                return content_changed(frame, fresh, roi)

        capture = SimpleNamespace(capture=lambda: self._capture(row))
        result = self.waiter.wait(
            capture,
            frame,
            roi,
            session.cancelled,
            require_change=require_change,
            predicate=predicate,
        )
        row["wait_frames"] = row.get("wait_frames", 0) + result.polls
        row["wait_ms"] = row.get("wait_ms", 0) + result.elapsed_ms
        row["verification_ms"] = row.get("verification_ms", 0) + result.verification_ms
        row["visual_wait_state"] = result.state
        row["related_change"] = result.changed
        if result.state == "CANCELLED":
            self._finish(session, Status.ABORTED, "abort requested during visual wait")
        elif result.state == "CONTEXT_CHANGED":
            self._finish(
                session, Status.NEEDS_REPLAN, "geometry or foreground changed during visual wait"
            )
        elif result.state in {"UNSTABLE", "CONDITION_UNMET"}:
            self._finish(
                session,
                Status.NEEDS_REPLAN,
                "expected visual readiness unconfirmed before deadline",
            )
        return result

    def _wait_region(self, observation, previous):
        if previous is not None:
            return previous
        indicators = [
            obj
            for obj in observation.objects
            if re.search(r"loading|spinner|pending|progress|불러오는|로딩", obj.label, re.I)
        ]
        return effect_region(indicators[0].bbox) if indicators else None

    def _visible_effect(self, session, objects, last_effect, row):
        if (
            last_effect is None
            or not last_effect.get("pending", False)
            or last_effect["candidate"].operation != "type"
        ):
            return True
        last_effect["pending"] = False
        observed = text_effect(objects, last_effect["target"], last_effect["candidate"].value)
        last_effect["history"]["verification"] = observed
        row["postcondition"] = observed
        if observed == "TEXT_MISMATCH":
            self._finish(
                session,
                Status.NEEDS_REPLAN,
                "supplied text does not match current visible field text",
            )
            return False
        if observed == "UNVERIFIED":
            self._blocked(
                session,
                "exact supplied field text is not independently observable",
                observed={"postcondition": "UNVERIFIED"},
            )
            return False
        return True

    def _blocked(
        self, session, reason, *, observed, resume="new relevant visible state", kind="UNKNOWN"
    ):
        session.blocker = {"kind": kind, "observed": observed, "resume_when": resume}
        return self._finish(session, Status.BLOCKED, reason)

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
            session.activity = {"phase": session.status.value.replace("_", " ").title()}
        return session.snapshot()

    def _record(self, session: Session, row: dict) -> None:
        started = row.pop("_step_started", None)
        row["step_latency_ms"] = (
            (time.perf_counter() - started) * 1000 if started is not None else None
        )
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

    def _choose(self, observation, session, history, row):
        route = self.router.route(observation, session.contract)
        row.update(
            mode=route.mode,
            routing_reason=route.reason,
            candidate_count=route.candidate_count,
            object_count=len(observation.objects),
            clef_calls=0,
            visual_confidence=None,
            coarse_roi=None,
            fine_target=None,
            clef_entropy=None,
            grounding_ms=0.0,
        )
        with _timing(row, "candidate_ms"):
            structured_observation = self.router.scoped_observation(observation, session.contract)
            if route.native_target is not None or route.semantic_targets:
                targets = (
                    {route.native_target}
                    if route.native_target is not None
                    else set(route.semantic_targets)
                )
                structured_observation = Observation(
                    observation.id,
                    observation.frame,
                    tuple(o for o in structured_observation.objects if o.id in targets),
                )
            candidates = (
                self.builder.build(structured_observation, session.contract)
                if (route.mode == "STRUCTURED")
                else ()
            )
        if route.native_target is not None:
            candidates = tuple(
                a for a in candidates if a.target == route.native_target and a.operation == "click"
            )
        if session.contract.visual_intent is not None and route.mode == "STRUCTURED":
            candidates = tuple(
                a for a in candidates if a.operation == session.contract.visual_intent.operation
            )
        row["clef_candidate_count"] = len(candidates)
        if route.semantic_targets and {a.target for a in candidates} != set(route.semantic_targets):
            raise GroundingUncertain("semantic targets exceed the bounded action budget")

        def decide():
            row["clef_calls"] += 1
            # V2: CLEF always sees the bounded decision context. The legacy
            # whole-roster passthrough let dense Blender screens (100+ parser
            # objects, 48 candidates) overflow the decision model's context and
            # crash the worker with OUT_OF_MEMORY on the real CUDA checkpoint.
            bounded = self.router.decision_observation(observation, candidates, session.contract)
            with _timing(row, "decision_ms"):
                answer = self.decision.decide(bounded, session.contract, candidates, history)
            row.setdefault("clef_decisions", []).append(
                {
                    **answer.model_dump(mode="json"),
                    "candidate_count": len(candidates),
                    "observation_id": bounded.id,
                    "frame_reference": bounded.frame.reference().model_dump(mode="json"),
                    "context_ids": [o.id for o in bounded.objects],
                }
            )
            row.update(clef_confidence=answer.confidence, clef_entropy=answer.entropy)
            return answer

        if route.mode != "STRUCTURED":
            # Assess the visible goal before demanding an input target, including
            # an already-satisfied first frame. A menu transition can remove its
            # original target. An empty proposal group never authorizes input;
            # completion and safety still pass the normal evidence gates below.
            assessment = decide()
            conditions = assessment.condition_probabilities
            complete = (
                assessment.goal_probability >= COMPLETION_PROBABILITY
                and len(conditions) == len(session.contract.success_conditions)
                and all(p >= COMPLETION_PROBABILITY for p in conditions)
            )
            # BLOCKED can simply mean that this completion-only assessment has
            # no available action. Reassess actionability with a grounded target.
            if (
                route.mode == "ASSESS"
                or complete
                or assessment.mode in {"COMPLETED", "WAIT", "NEEDS_REPLAN"}
                or assessment.safety_probability >= 0.5
                or assessment.replan_probability >= 0.8
            ):
                return candidates, assessment
        if route.mode != "STRUCTURED":
            with _timing(row, "grounding_ms"):
                candidates = self.router.visual_candidates(
                    observation, session.contract, row, session.cancelled
                )
            row["clef_candidate_count"] = len(candidates)
        if route.native_target and candidates and not history and not session.contract.constraints:
            decision = Decision(action=candidates[0].id, confidence=1)
            row["native_direct"] = True
        else:
            decision = decide()
        if (
            route.mode == "STRUCTURED"
            and self.router.grounder is not None
            and not session.contract.pointer_inputs
            and session.contract.execution_mode == "AUTO"
            and decision.safety_probability < 0.5
            and decision.replan_probability < 0.8
            and self.router.uncertain(decision, session.contract.confidence_threshold)
        ):
            row.update(mode="VISUAL", routing_reason="CLEF uncertainty in bounded selection")
            with _timing(row, "grounding_ms"):
                candidates = self.router.visual_candidates(
                    observation, session.contract, row, session.cancelled
                )
            row["clef_candidate_count"] = len(candidates)
            decision = decide()
        return candidates, decision

    def execute(self, session: Session) -> dict:
        if not self.desktop_lock.acquire(blocking=False):
            result = self._finish(
                session, Status.SAFETY_BLOCK, "another session owns desktop input"
            )
            self._record(session, {"event": "terminal", "reason": session.reason})
            return result
        tracker = ProgressTracker(self.config.no_progress_limit)
        completion_predictions = 0
        visual_stale_retries = 0
        row = {}
        ready_frame = None
        delivered = None
        last_region = None
        last_effect = session.last_effect
        if last_effect is not None and last_effect.get("evidence") is not None:
            # Resume path: carry the previously verified effect into this turn's first decision.
            delivered = last_effect.pop("evidence")
        session.blocker = None
        if last_effect is not None and last_effect.get("guidance_count", 0) != len(
            session.guidance
        ):
            last_effect["pending"] = False
        try:
            self._phase(session, "Starting")
            while session.rounds < session.contract.max_steps:
                if session.cancelled.is_set():
                    return self._finish(session, Status.ABORTED, "abort requested")
                row = {
                    "_step_started": time.perf_counter(),
                    "capture_ms": 0.0,
                    "parser_ms": 0.0,
                    "candidate_ms": 0.0,
                    "decision_ms": 0.0,
                    "execution_ms": 0.0,
                    "verification_ms": 0.0,
                    "state_change_score": None,
                }
                self._phase(session, "Reading screen")
                if ready_frame is not None:
                    frame, ready_frame = ready_frame, None
                    row["readiness_frame_reused"] = True
                else:
                    frame = self._capture(row)
                self._phase(session, "Finding controls")
                with _timing(row, "parser_ms"):
                    objects = self._parse(frame, row)
                observation = Observation(uuid.uuid4().hex, frame, objects, evidence=delivered)
                delivered = None
                with session.lock:
                    session.observation = observation
                if not self._visible_effect(session, objects, last_effect, row):
                    return session.snapshot()
                history = [{"guidance": g} for g in session.guidance] + session.action_history[-6:]
                self._phase(session, "Choosing next action")
                try:
                    candidates, decision = self._choose(observation, session, history, row)
                except GroundingUncertain as exc:
                    return self._finish(
                        session,
                        Status.ABORTED if session.cancelled.is_set() else Status.NEEDS_REPLAN,
                        str(exc),
                    )
                row.update(
                    confidence=decision.confidence,
                    progress=decision.progress,
                    decision_mode=decision.mode,
                    mode_confidence=decision.mode_confidence,
                    effect_probability=decision.effect_probability,
                )
                row.update(
                    goal_probability=decision.goal_probability,
                    condition_probabilities=decision.condition_probabilities,
                    replan_probability=decision.replan_probability,
                    safety_probability=decision.safety_probability,
                )
                if self.config.debug:
                    row.update(
                        object_count=len(objects),
                        clef_candidate_count=len(candidates),
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
                    decision.goal_probability >= COMPLETION_PROBABILITY
                    and len(conditions) == len(session.contract.success_conditions)
                    and all(p >= COMPLETION_PROBABILITY for p in conditions)
                )
                if completed:
                    fresh = self._capture(row)
                    if self._stale(frame, fresh, last_region):
                        # Delayed UI transitions invalidate evidence, not the planner's goal.
                        # Spend a bounded decision round re-observing; never repeat input here.
                        completion_predictions = 0
                        ready_frame = fresh
                        row["completion_observation_refreshed"] = True
                        self._record(session, row)
                        row = {}
                        continue
                    completion_predictions += 1
                    if completion_predictions >= 2:
                        return self._finish(
                            session,
                            Status.COMPLETED,
                            "goal and conditions verified on two fresh observations",
                        )
                    waiting = self._wait(session, fresh, last_region, row, require_change=False)
                    if session.status != Status.RUNNING:
                        return session.snapshot()
                    if waiting.state not in {"STABLE", "ALREADY_TRUE"}:
                        return self._finish(
                            session, Status.NEEDS_REPLAN, "completion pixels did not stabilize"
                        )
                    ready_frame = waiting.frame
                    self._record(session, row)
                    row = {}
                    continue
                completion_predictions = 0
                if decision.mode == "COMPLETED":
                    evidence = {
                        "required_probability": COMPLETION_PROBABILITY,
                        "goal": {
                            "description": session.contract.goal,
                            "probability": decision.goal_probability,
                        },
                        "conditions": [
                            {
                                "description": condition,
                                "probability": conditions[i] if i < len(conditions) else None,
                            }
                            for i, condition in enumerate(session.contract.success_conditions)
                        ],
                        "condition_count_matches": len(conditions)
                        == len(session.contract.success_conditions),
                        "observation_id": observation.id,
                    }
                    row["completion_evidence"] = evidence
                    session.blocker = {
                        "kind": "COMPLETION_UNVERIFIED",
                        "observed": evidence,
                        "resume_when": (
                            "new visible evidence for the goal and unverified conditions, "
                            "or planner clarification of observable success conditions; "
                            "prior input and pixel readiness alone do not prove completion"
                        ),
                    }
                if decision.mode_confidence < session.contract.confidence_threshold:
                    return self._finish(
                        session, Status.LOW_CONFIDENCE, "execution mode confidence below threshold"
                    )
                if decision.mode == "NEEDS_REPLAN":
                    return self._finish(
                        session, Status.NEEDS_REPLAN, "executor mode requests planner guidance"
                    )
                if decision.mode == "COMPLETED":
                    # Real-model calibration (measured, not tuned to pass): the
                    # pinned checkpoint's goal/condition heads topped out ~0.84
                    # on a verified-open Blender menu (trial9/bf0c screenshot +
                    # independent vision check), so the raw 0.9 head gate can
                    # never accept genuine completions. Accept only with a
                    # second, INDEPENDENT witness: measured pixel change in the
                    # expected effect region after the latest action, above a
                    # fixed calibrated floor of 0.75. Pixel readiness alone is
                    # never a substitute; both witnesses must agree.
                    CALIBRATED_FLOOR = 0.75
                    effect = observation.evidence or (
                        session.last_effect.get("evidence") if session.last_effect else None
                    )
                    facts = next((i for i in effect or () if isinstance(i, dict)), None)
                    calibrated = (
                        facts is not None
                        and facts.get("verification") == "VERIFIED"
                        and facts.get("roi_visibly_changed") is True
                        and decision.goal_probability >= CALIBRATED_FLOOR
                        and len(conditions) == len(session.contract.success_conditions)
                        and all(p >= CALIBRATED_FLOOR for p in conditions)
                    )
                    if calibrated:
                        row["completion_basis"] = "effect_evidence_plus_model"
                        return self._finish(
                            session,
                            Status.COMPLETED,
                            "CLEF proposed completion with measured pixel change in the "
                            "expected effect region above the contract threshold",
                        )
                    return self._finish(
                        session,
                        Status.NEEDS_REPLAN,
                        "proposed completion lacks required visible condition evidence",
                    )
                if session.contract.execution_mode == "ASSESS":
                    return self._finish(
                        session,
                        Status.NEEDS_REPLAN,
                        "read-only assessment does not establish goal completion; "
                        "no input permitted",
                    )
                if decision.mode == "BLOCKED":
                    return self._blocked(
                        session,
                        "current observations do not establish safe actionability",
                        observed={"actionable_candidates": len(candidates)},
                    )
                if decision.mode == "WAIT":
                    explicit_wait = next(
                        (
                            a.effect_roi
                            for a in candidates
                            if a.operation == "wait" and a.effect_roi is not None
                        ),
                        None,
                    )
                    if (
                        explicit_wait is None
                        and session.contract.visual_intent is not None
                        and session.contract.visual_intent.operation == "wait"
                    ):
                        explicit_wait = session.contract.visual_intent.region
                    wait_region = explicit_wait or self._wait_region(observation, last_region)
                    if wait_region is None:
                        return self._blocked(
                            session,
                            "no observed region establishes relevant visual waiting",
                            observed={"related_region": "UNKNOWN"},
                        )
                    waiting = self._wait(session, frame, wait_region, row)
                    if session.status != Status.RUNNING:
                        return session.snapshot()
                    if waiting.state == "NO_CHANGE":
                        return self._blocked(
                            session,
                            "no relevant visual change before screen deadline",
                            observed={"related_change": False, "polls": waiting.polls},
                        )
                    ready_frame = waiting.frame
                    self._record(session, row)
                    row = {}
                    continue
                if candidates and candidates[0].operation == "wait" and decision.mode == "ACT":
                    return self._finish(
                        session, Status.NEEDS_REPLAN, "visual wait requires CLEF WAIT mode"
                    )
                if not candidates:
                    return self._blocked(
                        session,
                        "no scoped actionable candidate in current observations",
                        observed={"actionable_candidates": 0},
                    )
                if decision.confidence < session.contract.confidence_threshold:
                    return self._finish(
                        session, Status.LOW_CONFIDENCE, "action confidence below threshold"
                    )
                selected = next((a for a in candidates if a.id == decision.action), None)
                if selected is None:
                    return self._finish(
                        session, Status.ERROR, "decision selected an unknown candidate"
                    )
                if last_effect is not None:
                    same_action = _action_identity(selected) == last_effect["action"]
                    unchanged = not region_changed(last_effect["frame"], frame, selected.effect_roi)
                    if (
                        same_action
                        and unchanged
                        and last_effect.get("guidance_count", 0) == len(session.guidance)
                    ):
                        return self._blocked(
                            session,
                            "unverified action would repeat in the same relevant visual state",
                            observed={
                                "expected_effect": selected.expected_effect,
                                "effect_verified": False,
                            },
                        )
                # Fresh pixels and target-region identity bind every input.
                fresh = self._capture(row)
                can_refresh_model_pointer = (
                    selected.pointer is not None
                    and row.get("mode") in {"VISUAL", "CANVAS"}
                    and not session.contract.pointer_inputs
                    and visual_stale_retries < self.config.visual_stale_retries
                    # Missing metadata cannot establish that redraw stayed in one window.
                    and frame.foreground_window is not None
                    and frame.foreground_bounds is not None
                )
                if not same_context(frame, fresh) or (
                    not can_refresh_model_pointer and self._context_stale(frame, fresh)
                ):
                    return self._finish(
                        session, Status.NEEDS_REPLAN, "screen changed during decision"
                    )
                stable = self._target_ready(
                    session,
                    frame,
                    fresh,
                    selected.effect_roi,
                    row,
                    allow_fresh_reference=can_refresh_model_pointer,
                )
                if session.status != Status.RUNNING:
                    return session.snapshot()
                execution_observation = observation
                if selected.pointer is not None:
                    if selected.pointer.reference != stable.frame.reference():
                        if can_refresh_model_pointer and same_context(frame, stable.frame):
                            visual_stale_retries += 1
                            row["visual_stale_retry"] = {
                                "attempt": visual_stale_retries,
                                "limit": self.config.visual_stale_retries,
                                "input_sent": False,
                                "reason": "model pointer frame changed before input",
                                "from_reference": selected.pointer.reference.model_dump(
                                    mode="json"
                                ),
                                "to_reference": stable.frame.reference().model_dump(mode="json"),
                            }
                            ready_frame = stable.frame
                            self._record(session, row)
                            row = {}
                            continue
                        return self._finish(
                            session,
                            Status.NEEDS_REPLAN,
                            "supplied pointer frame changed before input",
                        )
                    execution_observation = Observation(observation.id, stable.frame, objects)
                target = next((obj for obj in objects if obj.id == selected.target), None)
                row["actionability"] = {
                    "visible": "PLANNER_SUPPLIED_PIXELS" if selected.pointer else "DETECTED",
                    "stable": "OBSERVED_PIXELS",
                    "enabled": "UNKNOWN"
                    if target is None or target.enabled is None
                    else target.enabled,
                    "editable": "UNKNOWN"
                    if target is None or target.editable is None
                    else target.editable,
                    "occluded": "UNKNOWN"
                    if target is None or target.occluded is None
                    else target.occluded,
                }
                if (
                    selected.operation == "type"
                    and text_effect(objects, target, selected.value) == "VISIBLE_TEXT_MATCH"
                ):
                    return self._blocked(
                        session,
                        "supplied text is already visibly present; duplicate input skipped",
                        observed={"postcondition": "ALREADY_TRUE"},
                        resume="planner guidance",
                    )
                effect_history = {
                    "operation": selected.operation,
                    "description": selected.description,
                    "target": selected.target,
                    "expected_effect": selected.expected_effect,
                    "verification": "PENDING",
                    "failure_kind": None,
                }
                if selected.pointer is not None:
                    effect_history["pointer"] = selected.pointer.model_dump(mode="json")
                with session.lock:
                    session.action_history.append(effect_history)
                last_effect = {
                    "history": effect_history,
                    "action": _action_identity(selected),
                    "frame": stable.frame,
                    "candidate": selected,
                    "target": target,
                    "pending": True,
                    "guidance_count": len(session.guidance),
                }
                session.last_effect = last_effect
                label = (
                    "Hidden field"
                    if target and target.sensitive
                    else (target.label[:200] if target else None)
                )
                point = observation.frame.point(target.bbox) if target else None
                if selected.pointer is not None:
                    label = selected.pointer.label
                    point = execution_observation.frame.pointer_point(selected.pointer.points[0])
                self._phase(session, selected.operation.replace("_", " ").title(), label, point)
                with _timing(row, "execution_ms"):
                    result = self.action.execute(selected, execution_observation, session.cancelled)
                row["action"] = selected.audit()
                row["execution_ok"] = result.ok
                if session.cancelled.is_set():
                    return self._finish(session, Status.ABORTED, "abort requested")
                if not result.ok:
                    effect_history.update(verification="UNVERIFIED", failure_kind="INPUT_REFUSED")
                    last_effect["pending"] = False
                    return self._finish(
                        session, Status.ERROR, "action adapter refused or failed execution"
                    )
                visual_stale_retries = 0
                with session.lock:
                    session.steps += 1
                    session.last_action = selected.audit()
                last_region = selected.effect_roi
                waiting = self._wait(
                    session, frame, last_region, row, expected_effect=selected.expected_effect
                )
                effect_history.update(
                    readiness=waiting.state,
                    failure_kind=None if waiting.state == "STABLE" else waiting.state,
                )
                if session.status != Status.RUNNING:
                    return session.snapshot()
                last_effect["result_frame"] = waiting.frame
                session.action_history[-1]["verification"] = "VISUAL_READINESS_ONLY"
                session.action_history[-1]["readiness"] = waiting.state
                session.action_history[-1]["failure_kind"] = (
                    None if waiting.state == "STABLE" else waiting.state
                )
                row["expected_effect"] = selected.expected_effect
                row["effect_semantics"] = "UNVERIFIED; pixel readiness is not task completion"
                if waiting.state == "NO_CHANGE":
                    return self._finish(
                        session,
                        Status.NO_PROGRESS,
                        "no related visible effect before screen deadline; input not repeated",
                    )
                after = waiting.frame
                ready_frame = after
                roi = selected.effect_roi
                roi_changed = roi is None or region_changed(
                    last_effect.get("frame", frame), after, roi
                )
                before_frame = last_effect.get("frame", frame)
                vector = None
                if roi_changed:
                    from PIL import ImageChops

                    a, b = region_pixels(before_frame, roi), region_pixels(after, roi)
                    if a.size == b.size:
                        diff = ImageChops.difference(a, b)
                        width, height = diff.size
                        scale = max(1, min(width, height) // 8)
                        diff = diff.reduce(scale)
                        changed = [value > 8 for value in diff.convert("L").getdata()]
                        vector = "".join("1" if cell else "0" for cell in changed)[:256]
                delivered = (
                    {
                        "kind": "previous_action_effect",
                        "action": selected.audit(),
                        "expected_effect": selected.expected_effect,
                        "roi_visibly_changed": roi_changed,
                        "roi_change_cells_8x8": vector,
                        "verification": "VERIFIED" if roi_changed else "UNCHANGED",
                        "note": "measured pixels after a stable wait; not a completion claim",
                    },
                )
                last_effect["evidence"] = delivered
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
        except WindowsDesktopUnavailable:
            return self._blocked(
                session,
                "interactive desktop access unavailable",
                observed={"interactive_desktop": False},
                kind="ACCESS_UNAVAILABLE",
                resume="interactive unlocked desktop",
            )
        except WindowsForegroundChanged:
            return self._finish(
                session, Status.NEEDS_REPLAN, "foreground changed before native input"
            )
        except Exception as exc:
            # Third-party exceptions may contain typed payloads or local credentials.
            diagnostic = getattr(exc, "diagnostic", None)
            if diagnostic:
                row["backend_error"] = diagnostic
            code = diagnostic.get("code") if isinstance(diagnostic, dict) else None
            reason = f"{type(exc).__name__} in runtime backend" + (f": {code}" if code else "")
            if code == "GroundingHeadProvenanceError":
                # Only this static domain diagnosis is public, never raw worker text.
                reason = (
                    "configured visual_head is incompatible; prepare an audited v3 "
                    "checkpoint for the pinned backbone. Do not relabel legacy weights "
                    "or bypass the provenance check."
                )
            return self._finish(session, Status.ERROR, reason)
        finally:
            try:
                self.action.release()
            finally:
                try:
                    self.activity.finish(session)
                finally:
                    self.desktop_lock.release()
                if row:
                    row["reason"] = session.reason
                    self._record(session, row)
                elif session.status != Status.RUNNING:
                    self._record(session, {"event": "terminal", "reason": session.reason})

    def observe(self, session: Session | None = None, *, refresh=True, include_image=False) -> dict:
        fresh = False
        observation = None
        if refresh and self.desktop_lock.acquire(blocking=False):
            try:
                frame = self._capture()
                objects = self._parse(frame)
                observation = Observation(uuid.uuid4().hex, frame, objects)
                if session is not None:
                    with session.lock:
                        session.observation = observation
                fresh = True
            finally:
                self.desktop_lock.release()
        with session.lock if session is not None else nullcontext():
            if session is not None:
                observation = session.observation
            result = {
                **(session.snapshot() if session is not None else {"session_id": None}),
                "goal": session.contract.goal if session is not None else None,
                "recent_actions": [r.get("action") for r in session.history[-6:] if r.get("action")]
                if session is not None
                else [],
                "objects": [o.model_dump(mode="json") for o in observation.objects[:100]]
                if observation
                else [],
                "observation_id": observation.id if observation else None,
                "frame_reference": observation.frame.reference().model_dump(mode="json")
                if observation
                else None,
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
            result["preview_reference"] = {
                "image_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
                "image_size": list(image.size),
                "image_mode": image.mode,
                "derived_from_frame_sha256": result["image_sha256"],
            }
        return result
