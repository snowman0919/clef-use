from copy import deepcopy
from threading import Event
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from clef_use.benchmark import FixtureDesktop
from clef_use.candidates import CandidateBuilder
from clef_use.config import Config
from clef_use.runtime import Session, SessionRuntime
from clef_use.schema import BoundingBox, Contract, Decision, Frame, Observation, Status
from clef_use.verification import VisualVerifier, VisualWaiter, region_changed

ROI = BoundingBox(x1=0.2, y1=0.2, x2=0.5, y2=0.5)


def frame(color=None, outside=None, foreground=1):
    image = Image.new("RGB", (400, 240), "white")
    if color:
        ImageDraw.Draw(image).rectangle((110, 70, 113, 71), fill=color)
    if outside:
        ImageDraw.Draw(image).rectangle((350, 20, 360, 40), fill=outside)
    return Frame(image, foreground_window=foreground)


class Clock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now

    def pause(self, event, seconds):
        self.now += seconds
        return event.is_set()


class Sequence:
    def __init__(self, images):
        self.images, self.calls = images, 0

    def capture(self):
        image = self.images[min(self.calls, len(self.images) - 1)]
        self.calls += 1
        if isinstance(image, Exception):
            raise image
        return image


def waiter(timeout=0.3):
    clock = Clock()
    return VisualWaiter(timeout, 0.05, 2, clock, clock.pause), clock


def test_delayed_start_and_completion_require_related_change_then_stability():
    before, transition, after = frame(), frame("red"), frame("green")
    capture = Sequence([before, before, transition, after, after, after])
    wait, clock = waiter()
    result = wait.wait(capture, before, ROI, Event())
    assert result.state == "STABLE" and result.changed
    assert result.polls == 6 and clock.now == pytest.approx(0.25)
    assert result.frame.image.tobytes() == after.image.tobytes()


def test_tiny_target_change_survives_full_screen_average():
    before, after = frame(), frame("black")
    assert VisualVerifier().change(before, after) < 0.002
    assert region_changed(before, after, ROI)
    wait, _ = waiter()
    assert wait.wait(Sequence([after]), before, ROI, Event()).state == "STABLE"


def test_unrelated_blinking_is_not_readiness_and_no_change_hits_deadline():
    before = frame()
    capture = Sequence([frame(outside=c) for c in ("black", "red", "black", "red", "black")])
    wait, clock = waiter(0.2)
    result = wait.wait(capture, before, ROI, Event())
    assert result.state == "NO_CHANGE" and not result.changed
    assert clock.now == pytest.approx(0.2) and result.polls == 5


def test_wrong_stable_result_and_already_true_condition_are_distinct():
    before, wrong, correct = frame(), frame("red"), frame("green")

    def predicate(image):
        return image.image.getpixel((110, 70)) == (0, 128, 0)

    wait, _ = waiter(0.2)
    result = wait.wait(Sequence([wrong]), before, ROI, Event(), predicate=predicate)
    assert result.state == "CONDITION_UNMET"
    wait, _ = waiter()
    result = wait.wait(Sequence([correct]), correct, ROI, Event(), predicate=predicate)
    assert result.state == "ALREADY_TRUE" and not result.changed


def test_continuous_related_animation_is_bounded_and_not_stable():
    wait, clock = waiter(0.15)
    result = wait.wait(
        Sequence([frame("red"), frame("blue"), frame("red"), frame("blue")]), frame(), ROI, Event()
    )
    assert result.state == "UNSTABLE" and clock.now == pytest.approx(0.15)


def test_cancel_during_sampling_and_capture_error_do_not_pass():
    wait, clock = waiter()
    cancelled = Event()

    def pause(event, seconds):
        clock.now += seconds
        event.set()
        return True

    wait.pause = pause
    result = wait.wait(Sequence([frame()]), frame(), ROI, cancelled)
    assert result.state == "CANCELLED" and result.polls == 1
    wait, _ = waiter()
    with pytest.raises(RuntimeError, match="capture failure"):
        wait.wait(Sequence([RuntimeError("capture failure")]), frame(), ROI, Event())


def test_foreground_or_geometry_change_is_not_a_visible_effect():
    wait, _ = waiter()
    result = wait.wait(Sequence([frame("black", foreground=2)]), frame(), ROI, Event())
    assert result.state == "CONTEXT_CHANGED"
    before, after = frame(), Frame(frame("black").image, origin=(1, 0), foreground_window=1)
    assert wait.wait(Sequence([after]), before, ROI, Event()).state == "CONTEXT_CHANGED"


@pytest.mark.parametrize("mode", ["WAIT", "BLOCKED", "NEEDS_REPLAN", "COMPLETED"])
def test_non_action_decision_never_injects_or_repeats_model_during_wait(mode):
    desktop = FixtureDesktop()
    calls = []

    class DecisionBackend:
        def decide(self, *_):
            calls.append(1)
            return Decision(mode=mode, confidence=0.99)

    runtime = SessionRuntime(
        desktop,
        desktop,
        DecisionBackend(),
        desktop,
        Config(screen_timeout=0.05, screen_interval=0.005),
    )
    wait, _ = waiter(0.1)
    runtime.waiter = wait
    session = Session(Contract(goal="test", max_steps=5))
    runtime.execute(session)
    assert session.steps == desktop.stage == 0 and len(calls) == session.rounds == 1
    assert session.status in {Status.BLOCKED, Status.NEEDS_REPLAN}
    assert desktop.released == 1 and not runtime.desktop_lock.locked()


def test_stale_small_target_shift_stops_input_before_action():
    desktop = FixtureDesktop()
    old, shifted = frame(), frame("black")
    capture = Sequence([old, shifted])

    class Decisions:
        def decide(self, observation, contract, candidates, history):
            candidate = next(c for c in candidates if c.operation == "click")
            return Decision(action=candidate.id, confidence=0.99)

    runtime = SessionRuntime(capture, desktop, Decisions(), desktop)
    runtime.waiter = waiter(0.1)[0]
    session = Session(Contract(goal="Click Settings"))
    runtime.execute(session)
    assert session.status == Status.NEEDS_REPLAN and session.steps == desktop.stage == 0


def test_exact_image_cache_invalidates_changed_pixels_and_model_identity():
    class Parser:
        cache_identity = ("pinned-parser", 1)

        def __init__(self):
            self.calls = 0

        def parse(self, _):
            self.calls += 1
            return ()

    desktop, parser = FixtureDesktop(), Parser()
    runtime = SessionRuntime(desktop, parser, desktop, desktop)
    first = frame()
    runtime._parse(first)
    row = {}
    runtime._parse(frame(), row)
    assert parser.calls == 1 and row["perception_cache_hit"] and row["parser_calls"] == 0
    runtime._parse(frame(foreground=2))
    runtime._parse(Frame(first.image, origin=(1, 0), foreground_window=2))
    parser.cache_identity = ("pinned-parser", 2)
    runtime._parse(Frame(first.image, origin=(1, 0), foreground_window=2))
    assert parser.calls == 2
    runtime._parse(frame("black"))
    assert parser.calls == 3


def test_candidates_refuse_unscoped_text_and_unknown_generic_keyboard_focus():
    desktop = FixtureDesktop()
    observation = Observation("epoch", desktop.capture(), desktop.parse(None))
    candidates = CandidateBuilder().build(observation, Contract(goal='Enter "private text"'))
    assert not any(c.operation in {"type", "press", "hotkey", "wait"} for c in candidates)
    disabled = observation.objects[0].model_copy(update={"enabled": False})
    assert not CandidateBuilder().build(
        Observation("epoch", observation.frame, (disabled,)), Contract(goal="Click Settings")
    )


def test_loading_wait_has_no_input_or_poll_inference_and_releases_on_capture_error():
    from clef_use.schema import UIObject

    calls = []

    class Parser:
        def parse(self, _):
            return (UIObject(id="loading", label="Loading", role="text", bbox=ROI),)

    class Decisions:
        def decide(self, *_):
            calls.append(1)
            return Decision(mode="WAIT", confidence=0.99)

    for failure in (False, True):
        calls.clear()
        capture = Sequence([frame(), RuntimeError("failed") if failure else frame()])
        action = FixtureDesktop()
        runtime = SessionRuntime(capture, Parser(), Decisions(), action)
        runtime.waiter = waiter(0.2)[0]
        session = Session(Contract(goal="Wait for workspace"))
        runtime.execute(session)
        assert len(calls) == 1 and action.stage == session.steps == 0
        assert session.status == (Status.ERROR if failure else Status.BLOCKED)
        assert action.released == 1 and not runtime.desktop_lock.locked()
        if not failure:
            assert session.history[-1]["wait_frames"] == 5
            assert session.history[-1]["verification_ms"] >= 0


def test_caret_reference_recurrence_is_checked_without_masking_pixels():
    original, caret = frame(), frame("black")
    action = FixtureDesktop()
    capture = Sequence([caret, original, original, original])
    runtime = SessionRuntime(capture, action, action, action)
    runtime.waiter = waiter(0.2)[0]
    session = Session(Contract(goal="test"))
    row = {}
    result = runtime._target_ready(session, original, caret, ROI, row)
    assert result.state == "STABLE" and result.polls == 4
    assert session.status == Status.RUNNING and session.steps == 0
    assert result.frame.image.tobytes() == original.image.tobytes()


def test_visible_text_mismatch_precedes_model_or_next_input():
    from clef_use.schema import ActionCandidate, UIObject

    target = UIObject(id="field", label="Address input", role="input", bbox=ROI, actions=("type",))
    candidate = ActionCandidate(
        id="a",
        observation_id="epoch",
        operation="type",
        target="field",
        value="expected",
        description="Type expected into field",
    )
    action = FixtureDesktop()
    runtime = SessionRuntime(action, action, action, action)
    session = Session(Contract(goal="test"))
    history = {"verification": "PENDING"}
    effect = {"candidate": candidate, "target": target, "pending": True, "history": history}
    wrong = target.model_copy(update={"role": "text", "label": "wrong"})
    assert not runtime._visible_effect(session, (wrong,), effect, {})
    assert session.status == Status.NEEDS_REPLAN and history["verification"] == "TEXT_MISMATCH"
    assert action.stage == 0
    session = Session(Contract(goal="test"))
    effect["pending"] = True
    assert not runtime._visible_effect(session, (), effect, {})
    assert session.status == Status.BLOCKED and history["verification"] == "UNVERIFIED"


def test_unchanged_failed_effect_cannot_be_retried_using_model_confidence():
    from clef_use.schema import ActionResult

    desktop = FixtureDesktop()

    class Decisions:
        def decide(self, observation, contract, candidates, history):
            return Decision(action=candidates[0].id, confidence=0.99, effect_probability=1)

    class Refusal:
        calls = 0

        def execute(self, *_):
            self.calls += 1
            return ActionResult(ok=False)

        def release(self):
            pass

    action = Refusal()
    runtime = SessionRuntime(desktop, desktop, Decisions(), action)
    runtime.waiter = waiter(0.1)[0]
    session = Session(Contract(goal="Click Settings"))
    runtime.execute(session)
    assert session.status == Status.ERROR and action.calls == 1
    assert session.action_history[-1]["failure_kind"] == "INPUT_REFUSED"
    session.status = Status.RUNNING
    runtime.execute(session)
    assert session.status == Status.BLOCKED and action.calls == 1


@pytest.mark.parametrize("cold", [False, True])
def test_cached_observe_preserves_concurrent_fresh_owner_and_work(cold):
    from threading import Thread

    from clef_use.service import SessionManager

    entered, release = Event(), Event()
    factory_calls = []

    def pause():
        entered.set()
        if not release.wait(timeout=5):
            raise TimeoutError("test barrier was not released")

    class PausedDesktop(FixtureDesktop):
        captures = 0
        parses = 0

        def capture(self):
            self.captures += 1
            if not cold:
                pause()
            return frame("green")

        def parse(self, image):
            self.parses += 1
            return super().parse(image)

    desktop = PausedDesktop()
    executor = SessionRuntime(desktop, desktop, desktop, desktop)

    def factory():
        factory_calls.append(1)
        if cold:
            pause()
        return executor

    manager = SessionManager(factory)
    task = None
    if not cold:
        manager.runtime = executor
        task = Session(Contract(goal="Read the recorded menu"), status=Status.LOW_CONFIDENCE)
        task.observation = Observation("before-concurrent-refresh", frame("blue"), ())
        manager.sessions[task.id] = task
        manager.active = task.id
    results, errors = [], []

    def fresh():
        try:
            results.append(manager.dispatch("observe", {}))
        except BaseException as exc:
            errors.append(exc)

    thread = Thread(target=fresh)
    thread.start()
    try:
        assert entered.wait(timeout=5) and manager.busy
        before = (len(factory_calls), desktop.captures, desktop.parses)
        result = manager.dispatch("observe", {"refresh": False, "include_image": True})
        assert result["observation_fresh"] is False and manager.busy
        assert (len(factory_calls), desktop.captures, desktop.parses) == before
        if cold:
            assert manager.runtime is None and result["observation_id"] is None
            assert "image_png" not in result
        else:
            assert result["observation_id"] == task.observation.id == "before-concurrent-refresh"
            assert result["frame_reference"] == task.observation.frame.reference().model_dump(
                mode="json"
            )
            assert task.status == Status.LOW_CONFIDENCE and task.rounds == task.steps == 0
    finally:
        release.set()
        thread.join(timeout=5)
    assert not thread.is_alive() and not errors and len(results) == 1
    assert results[0]["observation_fresh"] and not manager.busy
    assert desktop.captures == desktop.parses == 1
    assert len(factory_calls) == int(cold)


@pytest.mark.parametrize(("busy", "stopping"), [(False, False), (True, False), (False, True)])
def test_cached_observe_without_recorded_frame_never_initializes_runtime(busy, stopping):
    from clef_use.service import SessionManager

    manager = SessionManager(lambda: pytest.fail("cache-only request initialized runtime"))
    manager.busy, manager.stopping = busy, stopping
    result = manager.dispatch("observe", {"refresh": False, "include_image": True})
    assert result["observation_fresh"] is False and result["frame_reference"] is None
    assert result["objects"] == [] and result["observation_id"] is None
    assert "image_png" not in result
    assert manager.runtime is None and manager.busy == busy and manager.stopping == stopping


@pytest.mark.parametrize("value", [None, 0, 1, "false", [], {}])
def test_service_rejects_non_boolean_observe_policy_before_runtime(value):
    from clef_use.service import SessionManager

    calls = []

    def factory():
        calls.append("initialized")
        return SessionRuntime(
            FixtureDesktop(), FixtureDesktop(), FixtureDesktop(), FixtureDesktop()
        )

    manager = SessionManager(factory)
    with pytest.raises(ValueError, match="refresh must be a boolean"):
        manager.dispatch("observe", {"refresh": value})
    assert not calls and manager.runtime is None and not manager.busy


def test_idle_service_cache_only_preserves_terminal_observation_without_capture():
    from clef_use.service import SessionManager

    capture = Sequence([frame("red")])
    desktop = FixtureDesktop()
    runtime = SessionRuntime(capture, desktop, desktop, desktop)
    manager = SessionManager(lambda: pytest.fail("cached read must not initialize runtime"))
    manager.runtime = runtime
    session = Session(
        Contract(goal="Inspect the recorded File dropdown"), status=Status.LOW_CONFIDENCE
    )
    session.rounds = 1
    session.blocker = {"kind": "CONFIDENCE_BELOW_THRESHOLD", "observed": {"probability": 0.4444}}
    recorded = Observation("recorded-menu-epoch", frame("blue"), desktop.parse(None))
    session.observation = recorded
    manager.sessions[session.id] = session
    manager.active = session.id
    before = session.snapshot()

    result = manager.dispatch("observe", {"session_id": session.id, "refresh": False})

    assert result["observation_fresh"] is False
    assert result["observation_id"] == recorded.id
    assert result["frame_reference"] == recorded.frame.reference().model_dump(mode="json")
    assert result["objects"] == [o.model_dump(mode="json") for o in recorded.objects]
    assert result["blocker"] == before["blocker"]
    assert session.snapshot() == before and session.observation is recorded
    assert capture.calls == 0 and desktop.stage == 0 and not manager.busy


def test_idle_observe_uses_exact_cache_and_busy_observe_does_not_capture():
    class Parser(FixtureDesktop):
        cache_identity = ("fixed", 1)
        calls = 0

        def parse(self, image):
            self.calls += 1
            return super().parse(image)

    capture, parser = Sequence([frame()]), Parser()
    runtime = SessionRuntime(capture, parser, parser, parser)
    session = Session(Contract(goal="test"))
    runtime.observe(session)
    runtime.observe(session)
    assert parser.calls == 1 and capture.calls == 2
    runtime.desktop_lock.acquire()
    try:
        result = runtime.observe(session)
        assert result["observation_fresh"] is False and capture.calls == 2
    finally:
        runtime.desktop_lock.release()


@pytest.mark.parametrize(
    ("status", "blocker"),
    [
        (Status.BLOCKED, {"kind": "VISIBLE_LOADING", "observed": {"overlay": "Loading"}}),
        (
            Status.LOW_CONFIDENCE,
            {"kind": "CONFIDENCE_BELOW_THRESHOLD", "observed": {"probability": 0.4444}},
        ),
        (
            Status.LOW_CONFIDENCE,
            {
                "kind": "COMPLETION_UNVERIFIED",
                "observed": {"goal_probability": 0.5},
                "confidence_gate": {"probability": 0.4},
            },
        ),
    ],
)
def test_resumed_service_clears_blocker_before_worker_runs(monkeypatch, status, blocker):
    from clef_use.service import SessionManager

    class DeferredWorkerThread:
        def __init__(self, *, target, args, daemon):
            pass

        def start(self):
            # Hold the scheduler boundary; all session transitions remain real service code.
            pass

    manager = SessionManager(lambda: pytest.fail("a deferred worker must not load a runtime"))
    session = Session(Contract(goal="test", max_steps=3), status=status, rounds=1)
    session.blocker = deepcopy(blocker)
    manager.sessions[session.id] = session
    terminal = session.snapshot()
    monkeypatch.setattr("clef_use.service.threading", SimpleNamespace(Thread=DeferredWorkerThread))
    result = manager.dispatch(
        "continue",
        {"session_id": session.id, "instruction": "Use the new visible evidence"},
    )
    concurrent_status = manager.dispatch("status", {"session_id": session.id})
    assert result["status"] == concurrent_status["status"] == "RUNNING"
    assert result["blocker"] is None and concurrent_status["blocker"] is None
    assert result["rounds"] == concurrent_status["rounds"] == 1
    assert session.contract.max_steps == 3
    assert session.guidance == ["Use the new visible evidence"]
    assert terminal["status"] == status.value and terminal["blocker"] == blocker
    assert manager.busy and manager.runtime is None


def test_uniform_hover_color_is_not_content_readiness_before_delayed_glyph():
    from clef_use.verification import content_changed

    before = Frame(Image.new("RGB", (400, 240), "white"), foreground_window=1)
    hover = Frame(Image.new("RGB", (400, 240), "gray"), foreground_window=1)
    after = frame("black")
    assert not content_changed(before, hover, ROI)
    assert content_changed(before, after, ROI)
    wait, _ = waiter(0.25)
    result = wait.wait(
        Sequence([hover, hover, after, after, after]),
        before,
        ROI,
        Event(),
        predicate=lambda current: content_changed(before, current, ROI),
    )
    assert result.state == "STABLE" and result.polls == 5


def test_foreground_window_bounds_change_is_not_stability():
    before = frame()
    before = Frame(before.image, foreground_window=1, foreground_bounds=(0, 0, 400, 240))
    after = frame()
    after = Frame(after.image, foreground_window=1, foreground_bounds=(1, 0, 400, 240))
    wait, _ = waiter()
    assert wait.wait(Sequence([after]), before, ROI, Event()).state == "CONTEXT_CHANGED"


def test_same_control_can_advance_again_after_relevant_state_actually_changes():
    from clef_use.schema import UIObject

    class Pages(FixtureDesktop):
        def parse(self, _):
            return (
                UIObject(id="same-next", role="button", label="Next", bbox=ROI, actions=("click",)),
            )

        def decide(self, observation, contract, candidates, history):
            if self.stage >= 2:
                return Decision(confidence=1, goal_probability=1, condition_probabilities=(1,))
            return Decision(action=candidates[0].id, confidence=0.99)

    desktop = Pages()
    runtime = SessionRuntime(desktop, desktop, desktop, desktop)
    session = Session(Contract(goal="Advance two pages", success_conditions=["second page"]))
    runtime.execute(session)
    assert session.status == Status.COMPLETED and session.steps == 2
