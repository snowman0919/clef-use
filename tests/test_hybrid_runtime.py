from types import SimpleNamespace

import pytest

from clef_use.benchmark import FixtureDesktop
from clef_use.config import Config
from clef_use.grounding import GroundingQueryTooLong, GroundingStrategyUnsupported
from clef_use.runtime import Session, SessionRuntime
from clef_use.schema import Contract, Decision, VisualIntent


class DenseDesktop(FixtureDesktop):
    def parse(self, image):
        return tuple(self._object(i) for i in range(160)) if self.stage == 0 else ()

    def _object(self, i):
        from clef_use.schema import BoundingBox, UIObject

        return UIObject(
            id=str(i),
            label="Settings",
            actions=frozenset({"click"}),
            bbox=BoundingBox(x1=0.1, y1=0.2, x2=0.6, y2=0.5),
        )

    def decide(self, observation, goal, candidates, history):
        if self.stage:
            return Decision(
                mode="COMPLETED",
                confidence=0.99,
                goal_probability=0.99,
                condition_probabilities=(0.99,),
            )
        if not candidates:
            return Decision(mode="BLOCKED", confidence=0.0)
        return Decision(action=candidates[0].id, confidence=0.99)


class FixedGrounder:
    def __init__(self, confidence=0.9):
        self.confidence = confidence

    def ground(
        self, image, query, region=None, refinement=0, geometry="point", coarse_strategy="tiled"
    ):
        point = (160.0, 80.0) if "right region" in query else (100.0, 80.0)
        return SimpleNamespace(
            point=point,
            confidence=self.confidence,
            entropy=0.1,
            coarse_roi=(50, 40, 150, 120),
            fine_target=(100.0, 80.0),
        )


def runtime(desktop, grounder):
    return SessionRuntime(
        desktop,
        desktop,
        desktop,
        desktop,
        Config(settle_seconds=0, screen_interval=0.005),
        grounder=grounder,
    )


@pytest.mark.parametrize(
    ("probability", "safety", "status"),
    [(0.99, 0.0, "COMPLETED"), (0.8, 0.0, "NEEDS_REPLAN"), (0.99, 0.75, "SAFETY_BLOCK")],
)
def test_visible_dense_goal_is_assessed_before_grounding_or_input(probability, safety, status):
    class SatisfiedDesktop(DenseDesktop):
        def __init__(self):
            super().__init__()
            self.stage = 1

        def parse(self, image):
            return tuple(self._object(i) for i in range(160))

        def decide(self, observation, goal, candidates, history):
            assert not candidates
            return Decision(
                mode="COMPLETED",
                confidence=0.0,
                goal_probability=probability,
                condition_probabilities=(probability,),
                safety_probability=safety,
            )

        def execute(self, action, observation, cancelled):
            pytest.fail("already-visible goal must not trigger redundant input")

    class NoActionGrounder:
        def ground(self, *args, **kwargs):
            pytest.fail("completion does not require a new grounded input target")

    desktop = SatisfiedDesktop()
    session = Session(Contract(goal="Settings", success_conditions=["Settings open"], max_steps=3))
    result = runtime(desktop, NoActionGrounder()).execute(session)
    assert result["status"] == status, result
    assert result["steps"] == 0
    assert session.last_effect is None
    if status == "COMPLETED":
        assert result["rounds"] == 2
        assert result["reason"] == "goal and conditions verified on two fresh observations"


@pytest.mark.parametrize("dense", [False, True])
@pytest.mark.parametrize(
    ("mode", "goal_probability", "safety", "expected"),
    [
        ("ACT", 0.2, 0.0, "NEEDS_REPLAN"),
        ("COMPLETED", 0.99, 0.0, "COMPLETED"),
        ("COMPLETED", 0.8, 0.0, "NEEDS_REPLAN"),
        ("COMPLETED", 0.99, 0.75, "SAFETY_BLOCK"),
    ],
)
def test_assessment_contract_never_creates_or_executes_input(
    dense,
    mode,
    goal_probability,
    safety,
    expected,
):
    class AssessmentDesktop(DenseDesktop):
        def parse(self, image):
            return tuple(self._object(i) for i in range(160 if dense else 1))

        def decide(self, observation, goal, candidates, history):
            assert candidates == ()
            return Decision(
                mode=mode,
                confidence=1.0,
                goal_probability=goal_probability,
                condition_probabilities=(goal_probability,),
                safety_probability=safety,
            )

        def execute(self, *args):
            pytest.fail("assessment is not permission to repeat input")

    class ForbiddenInputPath:
        def build(self, *args):
            pytest.fail("read-only assessment must not create candidates")

        def ground(self, *args, **kwargs):
            pytest.fail("read-only assessment must not seek an input point")

    desktop = AssessmentDesktop()
    session = Session(
        Contract(
            goal="Settings",
            success_conditions=["Settings open"],
            execution_mode="ASSESS",
            max_steps=3,
        )
    )
    executor = runtime(desktop, ForbiddenInputPath())
    executor.builder = ForbiddenInputPath()
    result = executor.execute(session)
    assert result["status"] == expected
    assert result["steps"] == 0 and session.last_effect is None
    assert result["rounds"] == (2 if expected == "COMPLETED" else 1)
    trace = session.history[0]["clef_decisions"][0]
    assert trace["goal_probability"] == goal_probability
    assert trace["condition_probabilities"] == [goal_probability]
    assert trace["safety_probability"] == safety
    assert trace["candidate_count"] == 0


def test_dense_runtime_executes_visual_and_verifies_completion():
    desktop = DenseDesktop()
    session = Session(Contract(goal="Settings", success_conditions=["Settings open"], max_steps=5))
    result = runtime(desktop, FixedGrounder()).execute(session)
    assert result["status"] == "COMPLETED"
    assert result["steps"] == 1
    row = session.history[0]
    assert row["mode"] == "VISUAL"
    assert row["candidate_count"] == 160
    assert row["clef_candidate_count"] == 1
    assert row["action"]["pointer"]["points"][0]["x"] == pytest.approx(0.25)


def test_step_latency_includes_wait_intervals_without_logging_internal_clock(monkeypatch):
    elapsed = [0.0]
    monkeypatch.setattr("clef_use.runtime.time.perf_counter", lambda: elapsed[0])
    desktop = DenseDesktop()
    executor = runtime(desktop, FixedGrounder())
    executor.waiter.clock = lambda: elapsed[0]

    def pause(cancelled, seconds):
        elapsed[0] += seconds
        return cancelled.is_set()

    executor.waiter.pause = pause
    session = Session(Contract(goal="Settings", success_conditions=["Settings open"], max_steps=5))
    assert executor.execute(session)["status"] == "COMPLETED"
    action = next(row for row in session.history if row.get("action"))
    assert action["wait_ms"] > 0
    assert action["step_latency_ms"] >= action["wait_ms"]
    assert all("_step_started" not in row for row in session.history)


def test_dense_ocr_target_uses_bounded_clef_selection_before_visual_grounding():
    from clef_use.schema import BoundingBox, UIObject

    class MenuDesktop(DenseDesktop):
        def parse(self, image):
            objects = super().parse(image)
            # Opening a menu leaves its menubar entry present.
            return (
                *objects,
                UIObject(
                    id="execute-menu",
                    label="Execute ",
                    bbox=BoundingBox(x1=0.1, y1=0.2, x2=0.6, y2=0.5),
                    actions=frozenset({"click", "double_click"}),
                    source=("box_yolo_content_ocr",),
                ),
            )

        def execute(self, action, observation, cancelled):
            assert action.target == "execute-menu"
            assert action.operation == "click"
            return super().execute(action, observation, cancelled)

    desktop = MenuDesktop()
    session = Session(
        Contract(
            goal="Open the Execute menu and stop when it is visible",
            success_conditions=["Execute menu visible"],
            visual_intent=VisualIntent(query="Execute"),
            max_steps=3,
        )
    )
    result = runtime(desktop, FixedGrounder(0.1)).execute(session)
    assert result["status"] == "COMPLETED", result
    assert result["steps"] == 1
    assert desktop.stage == 1
    first = session.history[0]
    assert first["mode"] == "STRUCTURED"
    assert first["clef_candidate_count"] == 1
    assert first["clef_calls"] == 1
    assert not first.get("native_direct")
    assert first["clef_confidence"] == 0.99
    assert "visual_grounding" not in first


def test_semantic_subset_cannot_drop_ambiguous_targets_at_the_action_budget():
    class AmbiguousMenus(DenseDesktop):
        def _object(self, i):
            obj = super()._object(i)
            return (
                obj.model_copy(
                    update={
                        "label": "Execute",
                        "source": ("ocr",),
                        "actions": frozenset({"click", "double_click"}),
                    }
                )
                if i < 12
                else obj
            )

    desktop = AmbiguousMenus()
    executor = SessionRuntime(
        desktop,
        desktop,
        desktop,
        desktop,
        Config(max_candidates=12, settle_seconds=0, screen_interval=0.005),
        grounder=FixedGrounder(0.1),
    )
    session = Session(
        Contract(
            goal="Open Execute menu",
            visual_intent=VisualIntent(query="Execute"),
            max_steps=1,
        )
    )
    result = executor.execute(session)
    assert result["status"] == "NEEDS_REPLAN"
    assert result["steps"] == 0
    assert desktop.stage == 0


@pytest.mark.parametrize("unsafe", [False, True])
def test_ocr_semantic_subset_does_not_bypass_clef_confidence_or_safety(unsafe):
    class UnapprovedMenu(DenseDesktop):
        def _object(self, i):
            obj = super()._object(i)
            return obj.model_copy(update={"source": ("ocr",)}) if i == 0 else obj

        def decide(self, observation, goal, candidates, history):
            return Decision(
                action=candidates[0].id,
                confidence=0.2,
                safety_probability=0.9 if unsafe else 0,
            )

    desktop = UnapprovedMenu()
    session = Session(Contract(goal="Settings", visual_intent=VisualIntent(query="Settings")))
    result = runtime(desktop, FixedGrounder(0.1)).execute(session)
    assert result["status"] == ("SAFETY_BLOCK" if unsafe else "NEEDS_REPLAN")
    assert result["steps"] == 0
    assert desktop.stage == 0
    assert not session.history[0].get("native_direct")
    assert session.history[0]["clef_calls"] == 1


def test_low_visual_confidence_escalates_without_input():
    desktop = DenseDesktop()
    session = Session(Contract(goal="Settings"))
    result = runtime(desktop, FixedGrounder(0.1)).execute(session)
    assert result["status"] == "NEEDS_REPLAN"
    assert desktop.stage == 0
    assert len(session.history[0]["visual_grounding"]) == 3


@pytest.mark.parametrize("error", [GroundingQueryTooLong, GroundingStrategyUnsupported])
def test_unusable_visual_request_escalates_without_input(error):
    class LimitedGrounder(FixedGrounder):
        def ground(self, *args, **kwargs):
            raise error("visual request unsupported by the loaded model")

    desktop = DenseDesktop()
    session = Session(Contract(goal="Settings"))
    result = runtime(desktop, LimitedGrounder()).execute(session)
    assert result["status"] == "NEEDS_REPLAN"
    assert desktop.stage == 0


def test_clef_safety_veto_is_not_overridden_by_visual_fallback():
    class Unsafe(DenseDesktop):
        def parse(self, image):
            return (self._object(0),)

        def decide(self, *args):
            return Decision(confidence=0.1, safety_probability=0.9)

    desktop = Unsafe()
    session = Session(Contract(goal="Settings"))
    result = runtime(desktop, FixedGrounder()).execute(session)
    assert result["status"] == "SAFETY_BLOCK"
    assert desktop.stage == 0
    assert "visual_grounding" not in session.history[0]


def test_clef_uncertainty_falls_back_to_visual():
    class Uncertain(DenseDesktop):
        def parse(self, image):
            return (self._object(0),)

        def decide(self, observation, goal, candidates, history):
            if not self.stage and candidates[0].pointer is None:
                return Decision(action=candidates[0].id, confidence=0.2)
            return super().decide(observation, goal, candidates, history)

    desktop = Uncertain()
    session = Session(Contract(goal="Settings", success_conditions=["Settings open"], max_steps=5))
    result = runtime(desktop, FixedGrounder()).execute(session)
    assert result["status"] == "COMPLETED"
    assert session.history[0]["clef_calls"] == 2
    assert session.history[0]["mode"] == "VISUAL"


def test_canvas_drag_is_frame_bound_and_verified():
    desktop = DenseDesktop()
    session = Session(
        Contract(
            goal="Move mesh",
            execution_mode="CANVAS",
            max_steps=5,
            success_conditions=["mesh moved"],
            visual_intent=VisualIntent(query="mesh", operation="drag", end_query="right region"),
        )
    )
    result = runtime(desktop, FixedGrounder()).execute(session)
    assert result["status"] == "COMPLETED"
    assert session.last_action["operation"] == "drag"
    assert len(session.last_action["pointer"]["points"]) == 2


def test_disappearing_visual_target_does_not_prevent_completion():
    desktop = DenseDesktop()

    class DisappearingGrounder(FixedGrounder):
        def ground(self, *args, **kwargs):
            self.confidence = 0.9 if desktop.stage == 0 else 0.1
            return super().ground(*args, **kwargs)

    session = Session(Contract(goal="Settings", success_conditions=["Settings open"], max_steps=5))
    result = runtime(desktop, DisappearingGrounder()).execute(session)
    assert result["status"] == "COMPLETED"
    assert result["steps"] == 1


def test_unverified_completion_preserves_the_visible_result_without_repeating_input():
    from clef_use.schema import ActionResult

    class ToggleDesktop(DenseDesktop):
        def execute(self, action, observation, cancelled):
            self.stage = 1 - self.stage
            return ActionResult(ok=True)

        def decide(self, observation, goal, candidates, history):
            if self.stage and not candidates:
                return Decision(
                    mode="COMPLETED",
                    confidence=0.85,
                    goal_probability=0.87,
                    condition_probabilities=(0.86,),
                )
            if not candidates:
                return Decision(mode="BLOCKED", confidence=0.99)
            return Decision(action=candidates[0].id, confidence=0.99)

    desktop = ToggleDesktop()
    session = Session(
        Contract(
            goal="Enable setting",
            execution_mode="VISUAL",
            success_conditions=["setting enabled"],
            max_steps=4,
        )
    )
    result = runtime(desktop, FixedGrounder()).execute(session)
    # A measured effect cannot establish all of a weak final completion claim.
    assert result["status"] == "NEEDS_REPLAN", result
    assert desktop.stage == 1
    assert result["steps"] == 1
    assert result["blocker"]["kind"] == "COMPLETION_UNVERIFIED"
    assert result["blocker"]["observed"]["required_probability"] == 0.9


def test_empty_completion_assessment_does_not_block_next_visual_action():
    class TwoStep(DenseDesktop):
        def decide(self, observation, goal, candidates, history):
            if self.stage == 2:
                return Decision(
                    mode="COMPLETED",
                    confidence=0.99,
                    goal_probability=0.99,
                    condition_probabilities=(0.99,),
                )
            if not candidates:
                return Decision(mode="BLOCKED", confidence=0.99)
            return Decision(action=candidates[0].id, confidence=0.99)

    desktop = TwoStep()
    session = Session(
        Contract(
            goal="Apply size",
            execution_mode="VISUAL",
            max_steps=6,
            success_conditions=["size applied"],
        )
    )
    result = runtime(desktop, FixedGrounder()).execute(session)
    assert result["status"] == "COMPLETED"
    assert result["steps"] == 2
    assert desktop.stage == 2


def test_collapsed_visual_drag_escalates_before_input():
    class CollapsedGrounder(FixedGrounder):
        def ground(self, image, query, **kwargs):
            return super().ground(image, "same point", **kwargs)

    desktop = DenseDesktop()
    session = Session(
        Contract(
            goal="Move mesh",
            execution_mode="CANVAS",
            visual_intent=VisualIntent(query="mesh", operation="drag", end_query="right region"),
        )
    )
    assert runtime(desktop, CollapsedGrounder()).execute(session)["status"] == "NEEDS_REPLAN"
    assert desktop.stage == 0


def test_explicit_canvas_wait_observes_its_supplied_region():
    from PIL import Image

    from clef_use.schema import BoundingBox, Frame

    class WaitingDesktop(DenseDesktop):
        def capture(self):
            # First capture binds the loading state; subsequent frames show the result.
            self.stage += 1
            return Frame(Image.new("RGB", (400, 240), "white" if self.stage == 1 else "black"))

        def parse(self, image):
            return ()

        def decide(self, observation, goal, candidates, history):
            return (
                Decision(mode="WAIT", confidence=0.99)
                if self.stage == 1
                else Decision(
                    mode="COMPLETED",
                    confidence=0.99,
                    goal_probability=0.99,
                    condition_probabilities=(0.99,),
                )
            )

    desktop = WaitingDesktop()
    session = Session(
        Contract(
            goal="Wait for viewport update",
            execution_mode="CANVAS",
            success_conditions=["viewport updated"],
            max_steps=5,
            visual_intent=VisualIntent(
                query="viewport",
                operation="wait",
                region=BoundingBox(x1=0.1, y1=0.1, x2=0.9, y2=0.9),
            ),
        )
    )
    result = runtime(desktop, FixedGrounder()).execute(session)
    assert result["status"] == "COMPLETED"
    assert result["steps"] == 0


class ShadingDesktop(DenseDesktop):
    """A one-pixel redraw outside the pointer surface during model inference."""

    def __init__(self, persistent=False):
        super().__init__()
        self.shading = 0
        self.persistent = persistent
        self.delivered = []

    def capture(self):
        from dataclasses import replace

        frame = super().capture()
        frame.image.putpixel((399, 239), (self.shading, 0, 0))
        return replace(frame, foreground_window=1, foreground_bounds=(0, 0, 400, 240))

    def decide(self, observation, goal, candidates, history):
        decision = super().decide(observation, goal, candidates, history)
        if self.stage == 0 and (self.persistent or self.shading == 0):
            self.shading += 1
        return decision

    def execute(self, action, observation, cancelled):
        assert (
            action.pointer.reference == observation.frame.reference() == self.capture().reference()
        )
        assert action.pointer.points[0].x == pytest.approx((100 + 10 * self.shading) / 400)
        self.delivered.append(action.pointer)
        return super().execute(action, observation, cancelled)


class ShadingGrounder(FixedGrounder):
    def ground(
        self, image, query, region=None, refinement=0, geometry="point", coarse_strategy="tiled"
    ):
        x = 100 + 10 * image.getpixel((399, 239))[0]
        return SimpleNamespace(
            point=(float(x), 80.0),
            confidence=0.9,
            entropy=0.1,
            coarse_roi=(50, 40, 150, 120),
            fine_target=(float(x), 80.0),
        )


class ThumbnailDesktop(ShadingDesktop):
    """Permanent small material-thumbnail redraw inside the intended effect ROI."""

    def capture(self):
        from PIL import ImageDraw

        frame = super().capture()
        ImageDraw.Draw(frame.image).rectangle((180, 88, 192, 100), fill=(self.shading * 32, 0, 0))
        return frame


@pytest.mark.parametrize("persistent", [False, True])
def test_large_same_window_redraw_is_regrounded_with_bounded_fresh_input(persistent):
    from PIL import ImageDraw

    class TooltipDesktop(ShadingDesktop):
        def capture(self):
            frame = super().capture()
            ImageDraw.Draw(frame.image).rectangle(
                (180, 88, 220, 114), fill=(self.shading * 32, 0, 0)
            )
            return frame

    desktop = TooltipDesktop(persistent=persistent)
    session = Session(shading_contract())
    result = runtime(desktop, ShadingGrounder()).execute(session)
    if persistent:
        assert result["status"] == "NEEDS_REPLAN"
        assert desktop.stage == 0 and not desktop.delivered
        assert session.rounds == 3
    else:
        assert result["status"] == "COMPLETED"
        assert desktop.stage == 1 and result["steps"] == 1
        assert desktop.delivered[0].points[0].x == pytest.approx(0.275)
    assert session.history[0]["visual_stale_retry"]["input_sent"] is False


def thumbnail_runtime(desktop):
    return SessionRuntime(
        desktop,
        desktop,
        desktop,
        desktop,
        Config(settle_seconds=0, screen_interval=0.005, screen_timeout=0.05),
        grounder=ShadingGrounder(),
    )


@pytest.mark.parametrize("mode", ["VISUAL", "CANVAS"])
def test_permanent_roi_redraw_stabilizes_then_regrounds_before_fresh_input(mode):
    desktop = ThumbnailDesktop()
    session = Session(shading_contract(execution_mode=mode))
    result = thumbnail_runtime(desktop).execute(session)
    assert result["status"] == "COMPLETED"
    assert result["steps"] == len(desktop.delivered) == 1
    assert desktop.delivered[0].points[0].x == pytest.approx(0.275)
    first = session.history[0]
    assert first["pre_input_readiness"] in {"STABLE", "ALREADY_TRUE"}
    assert first["wait_frames"] >= 2
    assert first["visual_stale_retry"]["input_sent"] is False


@pytest.mark.parametrize("mode", ["VISUAL", "CANVAS"])
def test_thumbnail_changes_during_readiness_then_regrounds_from_final_stable_pixels(mode):
    class LoadingDesktop(ThumbnailDesktop):
        def __init__(self):
            super().__init__()
            self.loading_captures = 0

        def capture(self):
            if self.stage == 0 and self.shading:
                self.loading_captures += 1
                # The first post-decision capture is still loading; the first
                # waiter poll shows a permanent thumbnail, then remains stable.
                if self.loading_captures == 2:
                    self.shading = 2
            return super().capture()

    desktop = LoadingDesktop()
    session = Session(shading_contract(execution_mode=mode))
    result = thumbnail_runtime(desktop).execute(session)
    assert result["status"] == "COMPLETED"
    assert result["steps"] == len(desktop.delivered) == 1
    assert desktop.delivered[0].points[0].x == pytest.approx(0.3)
    retry = session.history[0]
    assert retry["wait_frames"] >= 3
    assert retry["visual_stale_retry"]["input_sent"] is False
    assert retry["visual_stale_retry"]["to_reference"] == desktop.delivered[0].reference.model_dump(
        mode="json"
    )


def test_persistent_roi_redraws_exhaust_stale_budget_without_old_pointer_input():
    desktop = ThumbnailDesktop(persistent=True)
    session = Session(shading_contract())
    result = thumbnail_runtime(desktop).execute(session)
    assert result["status"] == "NEEDS_REPLAN"
    assert session.rounds == 3 and not desktop.delivered
    assert result["steps"] == 0
    assert [
        row["visual_stale_retry"]["attempt"]
        for row in session.history
        if "visual_stale_retry" in row
    ] == [1, 2]


@pytest.mark.parametrize("mode", ["VISUAL", "CANVAS"])
@pytest.mark.parametrize("window,bounds", [(None, None), (1, None), (None, (0, 0, 400, 240))])
def test_unknown_foreground_identity_does_not_authorize_redraw_retry(mode, window, bounds):
    from dataclasses import replace

    class UnknownDesktop(ThumbnailDesktop):
        def capture(self):
            return replace(super().capture(), foreground_window=window, foreground_bounds=bounds)

    desktop = UnknownDesktop()
    session = Session(shading_contract(execution_mode=mode))
    result = thumbnail_runtime(desktop).execute(session)
    assert result["status"] == "NEEDS_REPLAN"
    assert result["steps"] == 0
    assert desktop.stage == 0 and not desktop.delivered


@pytest.mark.parametrize("planner_pointer", [False, True])
def test_permanent_roi_redraw_does_not_relax_planner_or_foreground_guards(planner_pointer):
    from dataclasses import replace

    from clef_use.schema import BoundingBox, PointerInput, PointerPoint

    class ContextDesktop(ThumbnailDesktop):
        def capture(self):
            frame = super().capture()
            return frame if planner_pointer else replace(frame, foreground_window=self.shading + 1)

    desktop = ContextDesktop()
    if planner_pointer:
        pointer = PointerInput(
            operation="click",
            label="Settings",
            reference=desktop.capture().reference(),
            surface=BoundingBox(x1=0.1, y1=0.2, x2=0.6, y2=0.5),
            points=(PointerPoint(x=0.25, y=1 / 3),),
        )
        contract = Contract(goal="Settings", pointer_inputs=[pointer])
    else:
        contract = shading_contract()
    session = Session(contract)
    assert thumbnail_runtime(desktop).execute(session)["status"] == "NEEDS_REPLAN"
    assert not desktop.delivered and session.rounds == 1
    assert all("visual_stale_retry" not in row for row in session.history)


def shading_contract(execution_mode="VISUAL", max_steps=6, **kwargs):
    from clef_use.schema import BoundingBox

    return Contract(
        goal="Settings",
        execution_mode=execution_mode,
        max_steps=max_steps,
        success_conditions=["Settings open"],
        visual_intent=VisualIntent(
            query="Settings", operation="click", region=BoundingBox(x1=0.1, y1=0.2, x2=0.6, y2=0.5)
        ),
        **kwargs,
    )


@pytest.mark.parametrize("mode", ["VISUAL", "CANVAS"])
def test_stale_model_pointer_is_regrounded_and_redecided_before_one_fresh_input(mode):
    desktop = ShadingDesktop()
    session = Session(shading_contract(execution_mode=mode))
    result = runtime(desktop, ShadingGrounder()).execute(session)
    assert result["status"] == "COMPLETED"
    assert result["steps"] == len(desktop.delivered) == 1
    assert desktop.delivered[0].points[0].x == pytest.approx(0.275)
    assert session.history[0]["visual_stale_retry"]["input_sent"] is False
    assert session.history[0]["execution_ms"] == 0
    assert session.action_history[0]["verification"] != "PENDING"


def test_persistent_model_pointer_redraws_exhaust_two_retries_without_input():
    desktop = ShadingDesktop(persistent=True)
    session = Session(shading_contract())
    result = runtime(desktop, ShadingGrounder()).execute(session)
    assert result["status"] == "NEEDS_REPLAN"
    assert result["reason"] == "supplied pointer frame changed before input"
    assert result["steps"] == 0 and not desktop.delivered
    assert session.rounds == 3
    assert [
        row["visual_stale_retry"]["attempt"]
        for row in session.history
        if "visual_stale_retry" in row
    ] == [1, 2]


def test_stale_model_reobservation_spends_the_contract_decision_budget():
    desktop = ShadingDesktop(persistent=True)
    session = Session(shading_contract(max_steps=1))
    result = runtime(desktop, ShadingGrounder()).execute(session)
    assert result["status"] == "STEP_BUDGET_EXHAUSTED"
    assert session.rounds == 1 and not desktop.delivered
    assert result["steps"] == 0


def test_supplied_planner_pointer_still_refuses_redraw_without_retry():
    from clef_use.schema import BoundingBox, PointerInput, PointerPoint

    desktop = ShadingDesktop()
    pointer = PointerInput(
        operation="click",
        label="Settings",
        reference=desktop.capture().reference(),
        surface=BoundingBox(x1=0.1, y1=0.2, x2=0.6, y2=0.5),
        points=(PointerPoint(x=0.25, y=1 / 3),),
    )
    session = Session(Contract(goal="Settings", pointer_inputs=[pointer], max_steps=6))
    result = runtime(desktop, ShadingGrounder()).execute(session)
    assert result["status"] == "NEEDS_REPLAN"
    assert result["reason"] == "supplied pointer frame changed before input"
    assert result["steps"] == 0 and not desktop.delivered
    assert session.rounds == 1
    assert all("visual_stale_retry" not in row for row in session.history)


def test_stale_retry_budget_resets_after_each_actual_model_action():
    class TwoActionDesktop(ShadingDesktop):
        def __init__(self):
            super().__init__()
            self.shaded_stages = set()

        def decide(self, observation, goal, candidates, history):
            if self.stage == 2:
                return Decision(
                    mode="COMPLETED",
                    confidence=0.99,
                    goal_probability=0.99,
                    condition_probabilities=(0.99,),
                )
            if not candidates:
                return Decision(mode="BLOCKED", confidence=0.99)
            if self.stage not in self.shaded_stages:
                self.shaded_stages.add(self.stage)
                self.shading += 1
            return Decision(action=candidates[0].id, confidence=0.99)

    desktop = TwoActionDesktop()
    executor = SessionRuntime(
        desktop,
        desktop,
        desktop,
        desktop,
        Config(settle_seconds=0, screen_interval=0.005, visual_stale_retries=1),
        grounder=ShadingGrounder(),
    )
    session = Session(shading_contract(max_steps=8))
    result = executor.execute(session)
    assert result["status"] == "COMPLETED"
    assert result["steps"] == len(desktop.delivered) == 2
    assert [
        row["visual_stale_retry"]["attempt"]
        for row in session.history
        if "visual_stale_retry" in row
    ] == [1, 1]


@pytest.mark.parametrize("change_context", [False, True])
def test_zero_stale_retries_and_foreground_changes_refuse_input(change_context):
    from dataclasses import replace

    class ContextDesktop(ShadingDesktop):
        def capture(self):
            frame = super().capture()
            return replace(frame, foreground_window=self.shading + 1) if change_context else frame

    desktop = ContextDesktop()
    executor = SessionRuntime(
        desktop,
        desktop,
        desktop,
        desktop,
        Config(
            settle_seconds=0,
            screen_interval=0.005,
            visual_stale_retries=0 if not change_context else 2,
        ),
        grounder=ShadingGrounder(),
    )
    session = Session(shading_contract())
    assert executor.execute(session)["status"] == "NEEDS_REPLAN"
    assert not desktop.delivered and session.rounds == 1
    assert all("visual_stale_retry" not in row for row in session.history)


@pytest.mark.parametrize("value", [-1, 5])
def test_visual_stale_retry_config_rejects_out_of_bounds_values(value):
    with pytest.raises(ValueError):
        Config(visual_stale_retries=value)
