import json
import threading

import pytest
from PIL import Image
from pydantic import ValidationError

from clef_use.benchmark import FixtureDesktop, fixture_runtime
from clef_use.candidates import CandidateBuilder
from clef_use.config import Config
from clef_use.objects import normalize_omni
from clef_use.runtime import Session, SessionRuntime
from clef_use.schema import Contract, Decision, Frame, Observation, Status
from clef_use.verification import ProgressTracker, VisualVerifier


@pytest.mark.parametrize(
    "fields",
    [
        {"goal": " "},
        {"goal": "x", "max_steps": 0},
        {"goal": "x", "max_steps": 101},
        {"goal": "x", "confidence_threshold": float("nan")},
        {"goal": "x", "constraints": ["a" * 1001]},
        {"goal": "x", "extra": True},
    ],
)
def test_contract_rejects_unbounded_or_invalid_fields(fields):
    with pytest.raises(ValidationError):
        Contract(**fields)


def test_normalization_ids_geometry_and_unknown_confidence():
    raw = [
        {
            "type": "icon",
            "content": "Settings",
            "interactivity": True,
            "bbox": [0.1, 0.2, 0.3, 0.4],
        },
        {"type": "text", "content": "title", "interactivity": False, "bbox": [0.5, 0.2, 0.8, 0.4]},
    ]
    objects = normalize_omni(raw)
    assert objects[0].id == normalize_omni(raw[::-1])[1].id
    assert objects[0].confidence is None
    assert "click" in objects[0].actions and not objects[1].actions
    frame = Frame(Image.new("RGB", (2000, 1000)), origin=(20, 30), logical_size=(1000, 500))
    assert frame.point(objects[0].bbox) == (220, 180)
    with pytest.raises(ValidationError):
        normalize_omni([{**raw[0], "bbox": [0.4, 0.2, 0.3, 0.4]}])


def test_bounded_candidates_preserve_exact_text_and_observation_binding():
    desktop = FixtureDesktop()
    inputs = normalize_omni(
        [
            {
                "type": "input",
                "content": "Address input",
                "interactivity": True,
                "bbox": [0.1, 0.2, 0.6, 0.5],
            }
        ]
    )
    obs = Observation("epoch", desktop.capture(), inputs)
    candidates = CandidateBuilder(12).build(obs, Contract(goal='Enter "https://example.test"'))
    assert len(candidates) <= 12
    assert all(a.observation_id == "epoch" for a in candidates)
    assert any(a.operation == "type" and a.value == "https://example.test" for a in candidates)
    assert all(a.target is None or a.target == obs.objects[0].id for a in candidates)


@pytest.mark.parametrize(
    "continuous_transition, expected_status",
    [(False, "COMPLETED"), (True, "STEP_BUDGET_EXHAUSTED")],
)
def test_completion_reobserves_transition_without_repeating_input(
    continuous_transition, expected_status
):
    before = Image.new("RGB", (80, 60), "gray")
    after = before.copy()
    after.paste("black", (0, 0, 40, 20))

    class TransitionDesktop(FixtureDesktop):
        captures = 0

        def capture(self):
            self.captures += 1
            return Frame(
                before
                if (self.captures % 2 if continuous_transition else self.captures == 1)
                else after
            )

    class CompletedDecision:
        def decide(self, *args):
            return Decision(
                mode="COMPLETED",
                mode_confidence=0.99,
                confidence=0.99,
                goal_probability=0.99,
                condition_probabilities=(0.99,),
            )

    desktop = TransitionDesktop()
    executor = SessionRuntime(
        desktop, desktop, CompletedDecision(), desktop, Config(settle_seconds=0)
    )
    session = Session(
        Contract(goal="Verify active workspace", success_conditions=["active"], max_steps=3)
    )
    result = executor.execute(session)
    assert result["status"] == expected_status
    assert session.steps == 0 and session.rounds == 3
    assert desktop.stage == 0
    assert session.history[0]["completion_observation_refreshed"] is True
    assert sum(row.get("clef_calls", 0) for row in session.history) == session.rounds
    assert len({id(row) for row in session.history}) == len(session.history)


def test_action_then_stale_completion_uses_new_frame_without_repeating_click():
    class TransitionDesktop(FixtureDesktop):
        settled = False
        input_count = 0

        def capture(self):
            if self.settled:
                return Frame(Image.new("RGB", (400, 240), "lightgreen"))
            return super().capture()

        def execute(self, action, observation, cancelled):
            self.input_count += 1
            return super().execute(action, observation, cancelled)

    desktop = TransitionDesktop()
    observed_pixels = []

    class TransitionDecision:
        def decide(self, observation, goal, candidates, history):
            observed_pixels.append(observation.frame.image.getpixel((399, 239)))
            if desktop.stage == 0:
                chosen = next(a for a in candidates if a.operation == "click")
                return Decision(action=chosen.id, confidence=0.99)
            desktop.settled = True
            return Decision(
                mode="COMPLETED",
                mode_confidence=0.99,
                confidence=0.99,
                goal_probability=0.99,
                condition_probabilities=(0.99,),
            )

    executor = SessionRuntime(
        desktop, desktop, TransitionDecision(), desktop, Config(settle_seconds=0)
    )
    session = Session(Contract(goal="Open Settings", success_conditions=["active"], max_steps=4))
    result = executor.execute(session)
    assert result["status"] == "COMPLETED"
    assert desktop.input_count == session.steps == 1
    assert session.rounds == 4
    assert observed_pixels[-1] == observed_pixels[-2] == (144, 238, 144)
    assert observed_pixels[1] != observed_pixels[2]
    assert any(row.get("completion_observation_refreshed") for row in session.history)
    assert sum(row.get("clef_calls", 0) for row in session.history) == session.rounds


def test_last_round_positive_completion_records_each_inference_once():
    desktop = FixtureDesktop()

    class OneActionThenComplete:
        def decide(self, observation, goal, candidates, history):
            if desktop.stage == 0:
                action = next(a for a in candidates if a.operation == "click")
                return Decision(action=action.id, confidence=0.99)
            return Decision(
                mode="COMPLETED",
                mode_confidence=0.99,
                confidence=0.99,
                goal_probability=0.99,
                condition_probabilities=(0.99,),
            )

    runtime = SessionRuntime(
        desktop, desktop, OneActionThenComplete(), desktop, Config(settle_seconds=0)
    )
    session = Session(Contract(goal="Open Settings", success_conditions=["active"], max_steps=2))
    result = runtime.execute(session)
    # One positive completion observation must not fabricate the second proof.
    assert result["status"] == "STEP_BUDGET_EXHAUSTED"
    assert session.steps == 1 and session.rounds == 2
    assert sum(row.get("clef_calls", 0) for row in session.history) == session.rounds
    assert len({id(row) for row in session.history}) == len(session.history)


def test_multiaction_session_and_double_completion_verification():
    executor = fixture_runtime()
    session = Session(
        Contract(
            goal="Open Settings and apply size 16", max_steps=8, success_conditions=["Font size 16"]
        )
    )
    result = executor.execute(session)
    assert result["status"] == "COMPLETED"
    assert result["steps"] == 2 and result["rounds"] == 4
    assert executor.action.released == 1
    assert len(session.history) == 4


@pytest.mark.parametrize("conditions", [(0.95, 0.7), (0.95,), (0.95, 0.95, 0.95)])
def test_unverified_completion_reports_missing_visual_evidence_without_input(conditions):
    desktop = FixtureDesktop()

    class UnverifiedCompletion:
        def decide(self, *args):
            return Decision(
                mode="COMPLETED",
                confidence=0.99,
                goal_probability=0.7,
                condition_probabilities=conditions,
            )

    session = Session(
        Contract(goal="Apply size 16", success_conditions=["Size is 16", "Applied is visible"])
    )
    executor = SessionRuntime(desktop, desktop, UnverifiedCompletion(), desktop)
    result = executor.execute(session)
    assert result["status"] == "NEEDS_REPLAN" and result["steps"] == desktop.stage == 0
    evidence = result["blocker"]["observed"]
    assert result["blocker"]["kind"] == "COMPLETION_UNVERIFIED"
    assert evidence["goal"] == {"description": "Apply size 16", "probability": 0.7}
    assert evidence["required_probability"] == 0.9
    assert evidence["conditions"][1] == {
        "description": "Applied is visible",
        "probability": conditions[1] if len(conditions) > 1 else None,
    }
    assert evidence["condition_count_matches"] == (len(conditions) == 2)
    assert evidence["observation_id"] == session.observation.id
    assert session.history[-1]["completion_evidence"] == evidence


@pytest.mark.parametrize(
    "decision,status",
    [
        (Decision(action="a0", confidence=0.2), Status.LOW_CONFIDENCE),
        (Decision(action="a0", confidence=0.99, safety_probability=0.6), Status.SAFETY_BLOCK),
        (Decision(action="a0", confidence=0.99, replan_probability=0.9), Status.NEEDS_REPLAN),
        (Decision(action="not_a_candidate", confidence=0.99), Status.ERROR),
    ],
)
def test_escalation_never_injects_input(decision, status):
    desktop = FixtureDesktop()

    class FixedDecision:
        def decide(self, *args):
            return decision

    executor = SessionRuntime(desktop, desktop, FixedDecision(), desktop, Config(settle_seconds=0))
    session = Session(Contract(goal="test"))
    executor.execute(session)
    assert session.status == status and desktop.stage == 0 and desktop.released == 1


def test_hard_budget_includes_verification_decisions():
    executor = fixture_runtime()
    session = Session(Contract(goal="change UI", max_steps=1))
    executor.execute(session)
    assert session.status == Status.STEP_BUDGET_EXHAUSTED
    assert session.steps == 1 and session.rounds == 1


def test_budget_exit_records_terminal_reason_without_phantom_inference(tmp_path):
    from clef_use.benchmark import summarize

    executor = fixture_runtime()
    executor.log_path = tmp_path / "steps.jsonl"
    session = Session(Contract(goal="change UI", max_steps=1))
    executor.execute(session)
    rows = [json.loads(line) for line in executor.log_path.read_text().splitlines()]
    assert rows[-1]["terminal_event"] == "STEP_BUDGET_EXHAUSTED"
    assert rows[-1]["reason"] == session.reason
    measured = summarize(session, 1)
    assert measured["parser_ms_mean"] == rows[0]["parser_ms"]
    assert measured["clef_ms_mean"] == rows[0]["decision_ms"]


def test_failed_inference_time_is_retained_in_terminal_log(monkeypatch):
    import itertools

    class FailedDecision:
        def decide(self, *args):
            raise RuntimeError("failure")

    executor = fixture_runtime()
    executor.decision = FailedDecision()
    monkeypatch.setattr("clef_use.runtime.time.perf_counter", lambda: next(clock))
    clock = itertools.count(1.0)
    session = Session(Contract(goal="test"))
    executor.execute(session)
    assert session.status == Status.ERROR
    assert session.history[-1]["decision_ms"] == 1000


def test_exclusive_desktop_refusal_records_reason_without_releasing_owner():
    executor = fixture_runtime()
    session = Session(Contract(goal="test"))
    executor.desktop_lock.acquire()
    try:
        executor.execute(session)
    finally:
        executor.desktop_lock.release()
    assert session.status == Status.SAFETY_BLOCK
    assert session.history[-1]["reason"] == session.reason
    assert executor.action.released == 0


def test_repeated_cycles_and_near_identical_frames():
    tracker = ProgressTracker(3)
    assert not tracker.update(0.2, b"a")
    assert not tracker.update(0.2, b"b")
    assert not tracker.update(0.2, b"a")
    assert not tracker.update(0.2, b"b")
    assert tracker.update(0.2, b"a")
    verifier = VisualVerifier()
    frame = Frame(Image.new("RGB", (80, 60), "white"))
    assert verifier.change(frame, frame) == 0


def test_abort_during_decision_blocks_late_action_and_releases():
    desktop = FixtureDesktop()
    entered, unblock = threading.Event(), threading.Event()

    class BlockingDecision:
        def decide(self, *args):
            entered.set()
            assert unblock.wait(5)
            return Decision(action="a9", confidence=0.99)

    executor = SessionRuntime(desktop, desktop, BlockingDecision(), desktop)
    session = Session(Contract(goal="test"))
    thread = threading.Thread(target=executor.execute, args=(session,))
    thread.start()
    assert entered.wait(5)
    assert executor.abort(session)["status"] == "ABORTED"
    unblock.set()
    thread.join(timeout=5)
    assert not thread.is_alive() and desktop.stage == 0 and desktop.released >= 1


def test_backend_failure_redacts_exception_and_releases_input():
    desktop = FixtureDesktop()

    class BrokenParser:
        def parse(self, image):
            raise ValueError("secret typed payload")

    session = Session(Contract(goal="test"))
    executor = SessionRuntime(desktop, BrokenParser(), desktop, desktop)
    result = executor.execute(session)
    assert result["status"] == "ERROR" and "secret" not in str(result)
    assert desktop.released == 1


def test_detect_no_progress_from_actual_unchanged_images():
    desktop = FixtureDesktop()

    class WaitingDecision:
        def decide(self, *args):
            return Decision(action="a0", confidence=0.99)

    class NoopAction:
        def execute(self, *args):
            from clef_use.schema import ActionResult

            return ActionResult(ok=True)

        def release(self):
            pass

    executor = SessionRuntime(
        desktop,
        desktop,
        WaitingDecision(),
        NoopAction(),
        Config(screen_timeout=0.05, screen_interval=0.005),
    )
    session = Session(Contract(goal="test"))
    executor.execute(session)
    assert session.status == Status.NO_PROGRESS and session.steps == 1
    assert session.rounds == 1 and session.history[-1]["wait_frames"] >= 2


def test_goal_requires_all_success_conditions():
    desktop = FixtureDesktop()

    class FalseCompletion:
        def decide(self, *args):
            return Decision(
                action="a0", confidence=0.99, goal_probability=0.99, condition_probabilities=(0.1,)
            )

    executor = SessionRuntime(
        desktop, desktop, FalseCompletion(), desktop, Config(settle_seconds=0)
    )
    session = Session(Contract(goal="test", success_conditions=["not satisfied"], max_steps=1))
    executor.execute(session)
    assert session.status != Status.COMPLETED
