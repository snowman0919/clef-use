import ast
import hmac
import importlib.util
import json
import socket
from pathlib import Path
from threading import Event

import pytest
from PIL import Image

from clef_use.backends import DesktopAction
from clef_use.schema import (
    ActionCandidate,
    BoundingBox,
    Frame,
    Observation,
    PointerInput,
    PointerPoint,
)

spec = importlib.util.spec_from_file_location(
    "blender_hybrid_benchmark", Path(__file__).parents[1] / "scripts/blender_hybrid_benchmark.py"
)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


@pytest.mark.parametrize("raise_error", [True, False])
def test_recording_retains_partial_drag_failure_and_planned_endpoints(raise_error, tmp_path):
    cancelled = Event()
    journal = tmp_path / "input-attempts.json"

    class FailingDevice:
        FAILSAFE = True

        def __init__(self):
            self.held = False
            self.presses = self.releases = 0

        def moveTo(self, x, y, **kwargs):
            if self.held:
                raise RuntimeError("input connection lost during drag")

        def mouseDown(self, button):
            pending = json.loads(journal.read_text())
            assert pending[0]["delivery"] == "partial_or_unknown"
            assert pending[0]["points"] == [[0.2, 0.4], [0.8, 0.4]]
            self.held = True
            self.presses += 1
            if not raise_error:
                cancelled.set()

        def mouseUp(self, button):
            self.held = False
            self.releases += 1

    # Run the canonical wrapper and native gesture implementation, with only
    # OS delivery replaced by a device that fails after the button press.
    wrapper = next(
        node
        for node in ast.walk(ast.parse(Path(spec.origin).read_text()))
        if isinstance(node, ast.ClassDef) and node.name == "RecordingAction"
    )
    namespace = {"DesktopAction": DesktopAction}
    exec(
        compile(ast.Module(body=[wrapper], type_ignores=[]), "recording-action", "exec"), namespace
    )
    device = FailingDevice()

    def persist():
        journal.write_text(json.dumps(recorder.attempts))

    recorder = namespace["RecordingAction"](persist=persist)
    recorder.gui = device
    frame = Frame(Image.new("RGB", (100, 100)))
    observation = Observation("drag-frame", frame, ())
    pointer = PointerInput(
        operation="drag",
        label="canvas",
        reference=frame.reference(),
        surface=BoundingBox(x1=0.1, y1=0.1, x2=0.9, y2=0.9),
        points=(PointerPoint(x=0.2, y=0.4), PointerPoint(x=0.8, y=0.4)),
    )
    action = ActionCandidate(
        id="drag",
        operation="drag",
        observation_id=observation.id,
        description="drag",
        pointer=pointer,
    )
    if raise_error:
        with pytest.raises(RuntimeError, match="connection lost"):
            recorder.execute(action, observation, cancelled)
    else:
        assert not recorder.execute(action, observation, cancelled).ok
    assert (device.presses, device.releases, device.held) == (1, 1, False)
    expected = {
        "operation": "drag",
        "points": [(0.2, 0.4), (0.8, 0.4)],
        "size": (100, 100),
        "ok": False,
        "delivery": "partial_or_unknown" if raise_error else "not_completed",
    }
    if raise_error:
        expected["error"] = "RuntimeError"
    assert recorder.attempts == [expected]
    assert json.loads(journal.read_text()) == json.loads(json.dumps([expected]))


def test_real_fixture_socket_denies_untrusted_requests_before_state_readback(tmp_path):
    # Execute the canonical protocol handler with real sockets and persisted state.
    # Blender's unrelated UI setup is excluded from this boundary regression.
    handler = next(
        node
        for node in ast.parse(benchmark.STARTUP).body
        if isinstance(node, ast.FunctionDef) and node.name == "tick"
    )
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"workspace": "Layout", "thin_wall": False}))
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(4)
        server.setblocking(False)
        namespace = {
            "server": server,
            "clients": {},
            "hmac": hmac,
            "json": json,
            "token": b"private-fixture-key",
            "state": lambda: json.loads(state_path.read_text()),
        }
        exec(
            compile(ast.Module(body=[handler], type_ignores=[]), "fixture-handler", "exec"),
            namespace,
        )

        def exchange(payload):
            with socket.create_connection(server.getsockname(), timeout=2) as client:
                client.sendall(json.dumps(payload).encode() + b"\n")
                namespace["tick"]()
                return json.loads(client.recv(65536))

        for payload in (
            {"operation": "readback"},
            {"operation": "reset", "case": "outliner", "token": "wrong"},
            {"operation": "readback", "token": ["private-fixture-key"]},
            {"operation": "readback", "token": "\u2713"},
            [],
        ):
            assert exchange(payload) == {"error": "unauthorized fixture request"}
        assert exchange({"operation": "readback", "token": "private-fixture-key"}) == {
            "workspace": "Layout",
            "thin_wall": False,
        }


def test_failures_remain_in_denominator_and_latency():
    rows = [
        dict(
            variant="hybrid",
            success=True,
            status="COMPLETED",
            mode="VISUAL",
            end_to_end_ms=100,
            grounding_ms=20,
        ),
        dict(
            variant="hybrid",
            success=False,
            status="BLOCKED",
            mode="VISUAL",
            end_to_end_ms=10,
            grounding_ms=2,
        ),
        dict(
            variant="hybrid",
            success=True,
            status="NEEDS_REPLAN",
            mode="STRUCTURED",
            end_to_end_ms=200,
        ),
    ]
    summary = benchmark.summarize(rows)["hybrid"]
    assert summary["success_rate"] == 2 / 3
    assert summary["escalation_frequency"] == 1 / 3
    assert summary["end_to_end_ms"] == dict(count=3, min=10, max=200, p50=100, p95=200)
    assert summary["successful_end_to_end_ms"]["p50"] == 150
    assert summary["visual_successes"] == summary["structured_successes"] == 1


def test_unmeasured_and_nonfinite_latency_are_not_zero_samples():
    summary = benchmark.summarize(
        [dict(variant="baseline", status="ERROR", success=False, end_to_end_ms=float("nan"))]
    )["baseline"]
    assert summary["end_to_end_ms"] is None
    assert summary["grounding_ms"] is None
    assert summary["success_rate"] == 0


def test_unverified_native_outcome_stays_in_success_denominator_without_becoming_failure():
    summary = benchmark.summarize(
        [
            dict(variant="hybrid", status="COMPLETED", success=True),
            dict(
                variant="hybrid",
                status="COMPLETED",
                success=None,
                outcome_error="readback connection closed",
            ),
            dict(variant="hybrid", status="ERROR", success=False),
        ]
    )["hybrid"]
    assert summary["trials"] == 3
    assert summary["successes"] == summary["unverified_outcomes"] == 1
    assert summary["confirmed_failures"] == 1
    assert summary["success_rate"] == pytest.approx(1 / 3)


def test_grounding_summary_counts_only_measured_region_errors():
    region = dict(x1=0.2, y1=0.2, x2=0.6, y2=0.6)
    rows = [
        dict(
            variant="hybrid",
            status="COMPLETED",
            success=True,
            grounding_error=benchmark.region_error(point, region, (200, 100)),
            grounding_error_method="editor region containment only",
        )
        for point in [(0.4, 0.4), (0.8, 0.6)]
    ]
    rows += [
        dict(variant="hybrid", status="NEEDS_REPLAN", success=False, grounding_error=value)
        for value in [None, float("nan")]
    ]
    summary = benchmark.summarize(rows)["hybrid"]
    assert summary["grounding_error"]["count"] == 2
    assert summary["grounding_error"]["p50"] == pytest.approx(20)
    assert summary["grounding_error"]["p95"] == pytest.approx(40)
    assert summary["grounding_error_methods"] == ["editor region containment only"]


def test_selection_requires_actual_state_transition():
    before = dict(active_object="Face", target_object="Face")
    assert not benchmark.outcome("outliner", before, dict(active_object="Face"))
    before["active_object"] = None
    assert benchmark.outcome("outliner", before, dict(active_object="Face")) is None
    assert not benchmark.outcome("viewport_selection", before, dict(active_object="Hair"))


def selection_state(active=None):
    return dict(
        active_object=active,
        target_object="Face",
        areas=[
            dict(type="VIEW_3D", x1=0, y1=0, x2=0.8, y2=1),
            dict(type="OUTLINER", x1=0.8, y1=0, x2=1, y2=0.3),
        ],
    )


def selection_attempt(point, before=None, after=None, **values):
    return dict(
        operation="click",
        points=[point],
        ok=True,
        delivery="completed",
        native_before=selection_state(before),
        native_after=selection_state(after),
        **values,
    )


@pytest.mark.parametrize(
    ("case", "point", "expected"),
    [
        ("viewport_selection", (0.4, 0.5), True),
        ("viewport_selection", (0.9, 0.1), False),
        ("outliner", (0.9, 0.1), True),
        ("outliner", (0.4, 0.5), False),
    ],
)
def test_selection_success_requires_transition_through_requested_editor(case, point, expected):
    attempt = selection_attempt(point, after="Face")
    assert (
        benchmark.outcome(
            case, selection_state(), selection_state("Face"), input_attempts=[attempt]
        )
        is expected
    )


def test_earlier_correct_area_click_cannot_credit_later_wrong_area_selection():
    attempts = [selection_attempt((0.4, 0.5)), selection_attempt((0.9, 0.1), after="Face")]
    assert (
        benchmark.outcome(
            "viewport_selection",
            selection_state(),
            selection_state("Face"),
            input_attempts=attempts,
        )
        is False
    )


@pytest.mark.parametrize("gap", ["delivery", "before", "after"])
def test_selection_without_delivery_or_state_evidence_is_unverified(gap):
    attempt = selection_attempt((0.4, 0.5), after="Face")
    if gap == "delivery":
        attempt.update(ok=False, delivery="partial_or_unknown")
    elif gap == "before":
        attempt.pop("native_before")
    else:
        attempt.pop("native_after")
    # An intervening attempt prevents attributing the final snapshot to the first click.
    attempts = [attempt, dict(operation="click", ok=False, delivery="not_completed")]
    assert (
        benchmark.outcome(
            "viewport_selection",
            selection_state(),
            selection_state("Face"),
            input_attempts=attempts,
        )
        is None
    )


def test_delayed_selection_uses_only_immediately_following_before_boundary():
    first = selection_attempt((0.4, 0.5))
    second = selection_attempt((0.9, 0.1), before="Face", after="Face")
    assert (
        benchmark.outcome(
            "viewport_selection",
            selection_state(),
            selection_state("Face"),
            input_attempts=[first, second],
        )
        is True
    )
    interrupted = dict(operation="click", ok=False, delivery="partial_or_unknown")
    assert (
        benchmark.outcome(
            "viewport_selection",
            selection_state(),
            selection_state("Face"),
            input_attempts=[first, interrupted, second],
        )
        is None
    )


def test_last_completed_click_can_use_final_readback_after_delayed_delivery():
    attempt = selection_attempt((0.4, 0.5))
    assert (
        benchmark.outcome(
            "viewport_selection",
            selection_state(),
            selection_state("Face"),
            input_attempts=[attempt],
        )
        is True
    )


@pytest.mark.parametrize("failed_readback", ["before", "after"])
def test_selection_readback_failure_preserves_native_click_and_durable_result(
    failed_readback, tmp_path
):
    journal, state_path = tmp_path / "attempts.json", tmp_path / "state.json"
    state_path.write_text(json.dumps(selection_state()))

    class SelectionDevice:
        FAILSAFE = True

        def __init__(self):
            self.presses = self.releases = 0
            self.held = False

        def moveTo(self, x, y):
            assert (x, y) == (40, 50)

        def mouseDown(self, button):
            assert json.loads(journal.read_text())[0]["delivery"] == "partial_or_unknown"
            self.presses += 1
            self.held = True

        def mouseUp(self, button):
            self.releases += 1
            self.held = False
            state_path.write_text(json.dumps(selection_state("Face")))

    device = SelectionDevice()

    def readback():
        phase = "after" if device.presses else "before"
        if phase == "after":
            persisted = json.loads(journal.read_text())[0]
            assert persisted["ok"] is True and persisted["delivery"] == "completed"
        if phase == failed_readback:
            raise ConnectionError("fixture readback unavailable")
        return json.loads(state_path.read_text())

    wrapper = next(
        node
        for node in ast.walk(ast.parse(Path(spec.origin).read_text()))
        if isinstance(node, ast.ClassDef) and node.name == "RecordingAction"
    )
    namespace = {"DesktopAction": DesktopAction}
    exec(
        compile(ast.Module(body=[wrapper], type_ignores=[]), "recording-action", "exec"), namespace
    )
    recorder = namespace["RecordingAction"](
        persist=lambda: journal.write_text(json.dumps(recorder.attempts)),
        selection_readback=readback,
    )
    recorder.gui = device
    frame = Frame(Image.new("RGB", (100, 100)))
    observation = Observation("selection", frame, ())
    pointer = PointerInput(
        operation="click",
        label="Face",
        reference=frame.reference(),
        surface=BoundingBox(x1=0, y1=0, x2=0.8, y2=1),
        points=(PointerPoint(x=0.4, y=0.5),),
    )
    action = ActionCandidate(
        id="select",
        operation="click",
        observation_id=observation.id,
        description="select Face",
        pointer=pointer,
    )
    assert recorder.execute(action, observation, Event()).ok
    assert (device.presses, device.releases, device.held) == (1, 1, False)
    attempts = json.loads(journal.read_text())
    assert attempts[0]["native_" + failed_readback + "_error"] == "ConnectionError"
    assert benchmark.outcome(
        "viewport_selection",
        selection_state(),
        json.loads(state_path.read_text()),
        input_attempts=attempts,
    ) is (True if failed_readback == "after" else None)


def test_drag_requires_outliner_height_reduction():
    assert benchmark.outcome("drag", dict(outliner_height=200), dict(outliner_height=180))
    assert not benchmark.outcome("drag", dict(outliner_height=200), dict(outliner_height=198))
    assert not benchmark.outcome("drag", dict(outliner_height=200), dict(outliner_height=220))


def test_editor_error_does_not_invent_target_point():
    region = dict(x1=0.5, y1=0.2, x2=0.9, y2=0.8)
    assert benchmark.region_error((0.6, 0.3), region, (1000, 1000)) == 0
    assert benchmark.region_error((0.4, 0.3), region, (1000, 1000)) == pytest.approx(100)
    assert benchmark.region_error(None, region, (1000, 1000)) is None


def test_terminal_only_row_preserves_last_grounding_decision():
    decision = dict(mode="VISUAL", candidate_count=4, confidence=0.7)
    assert benchmark.last_decision([decision, dict(terminal_event="NEEDS_REPLAN")]) == decision
    assert benchmark.last_decision([dict(terminal_event="ERROR")]) == {}


def test_visual_execution_is_not_reclassified_by_structured_completion():
    history = [
        dict(
            mode="VISUAL",
            candidate_count=100,
            execution_ok=True,
            execution_ms=2,
            grounding_ms=10,
            step_latency_ms=30,
            confidence=0.9,
        ),
        dict(
            mode="STRUCTURED",
            candidate_count=80,
            decision_mode="COMPLETED",
            execution_ms=0,
            grounding_ms=0,
            step_latency_ms=20,
            confidence=0.8,
        ),
    ]
    metrics = benchmark.trial_metrics(
        history, [{"candidates": 48}, {"candidates": 1}, {"candidates": 0}]
    )
    summary = benchmark.summarize(
        [dict(variant="hybrid", success=True, status="COMPLETED", **metrics)]
    )["hybrid"]
    assert metrics["mode"] == "VISUAL"
    assert metrics["terminal_mode"] == "STRUCTURED"
    assert summary["visual_successes"] == 1
    assert summary["structured_successes"] == 0
    assert summary["step_latency_ms"]["count"] == 2
    assert summary["step_latency_ms"]["p50"] == 25
    assert summary["grounding_ms"]["p50"] == 10
    assert summary["raw_candidate_count_vs_success"]["100"]["successes"] == 1
    assert summary["clef_choice_count_vs_success"]["48"]["successes"] == 1
    assert summary["clef_choice_count_vs_success"]["1"]["successes"] == 1
    assert summary["clef_zero_choice_calls"] == 1
    assert "0" not in summary["clef_choice_count_vs_success"]


def test_mixed_execution_and_failed_stale_rounds_remain_in_metrics():
    metrics = benchmark.trial_metrics(
        [
            dict(mode="STRUCTURED", candidate_count=40, execution_ok=True, step_latency_ms=10),
            dict(
                mode="VISUAL",
                candidate_count=80,
                visual_stale_retry={"input_sent": False},
                execution_ms=0,
                step_latency_ms=15,
            ),
            dict(
                mode="VISUAL",
                candidate_count=80,
                execution_ok=False,
                execution_ms=5,
                step_latency_ms=20,
            ),
            dict(terminal_event="ERROR", step_latency_ms=None),
        ],
        [{"candidates": 24}, {"candidates": 1}, {"candidates": 1}],
    )
    assert metrics["mode"] == "MIXED"
    assert metrics["execution_modes"] == ["STRUCTURED", "VISUAL"]
    summary = benchmark.summarize(
        [dict(variant="hybrid", success=False, status="ERROR", **metrics)]
    )["hybrid"]
    assert summary["step_latency_ms"]["count"] == 3
    assert summary["clef_choice_count_vs_success"]["1"]["trials"] == 1
    assert summary["clef_choice_count_vs_success"]["1"]["calls"] == 2


def test_success_rates_use_each_mode_and_candidate_group_denominator():
    rows = [
        dict(
            variant="hybrid",
            mode="VISUAL",
            raw_candidate_counts=[80],
            clef_choice_counts=[4],
            success=True,
            status="COMPLETED",
            runtime_ms=12,
        ),
        dict(
            variant="hybrid",
            mode="VISUAL",
            raw_candidate_counts=[80],
            clef_choice_counts=[4],
            success=False,
            status="BLOCKED",
            runtime_ms=8,
        ),
        dict(
            variant="hybrid",
            mode="STRUCTURED",
            raw_candidate_counts=[100],
            clef_choice_counts=[48],
            success=False,
            status="BLOCKED",
            runtime_ms=20,
        ),
    ]
    summary = benchmark.summarize(rows)["hybrid"]
    assert summary["by_mode"]["VISUAL"]["success_rate"] == 0.5
    assert summary["by_mode"]["STRUCTURED"]["success_rate"] == 0
    assert summary["clef_choice_count_vs_success"]["4"]["success_rate"] == 0.5
    assert summary["clef_choice_count_vs_success"]["48"]["trials"] == 1
    assert summary["raw_candidate_count_vs_success"]["80"]["success_rate"] == 0.5
    assert summary["runtime_ms"]["p50"] == 12


def test_planner_escalation_excludes_resource_errors_and_explicit_abort():
    rows = [
        dict(variant="hybrid", success=False, status=status)
        for status in ("NEEDS_REPLAN", "ERROR", "ABORTED", "BLOCKED")
    ]
    summary = benchmark.summarize(rows)["hybrid"]
    assert summary["escalations"] == 1
    assert summary["escalation_frequency"] == 0.25


def test_dead_fixture_unattempted_trials_are_not_counted_as_failures():
    attempted = [dict(case="drag", repetition=0, variant="baseline")]
    missing = benchmark.missing_trials(["drag"], 2, attempted)
    assert missing == [
        dict(case="drag", repetition=0, variant="hybrid", status="NOT_RUN"),
        dict(case="drag", repetition=1, variant="baseline", status="NOT_RUN"),
        dict(case="drag", repetition=1, variant="hybrid", status="NOT_RUN"),
    ]


def test_material_fixture_requires_unchecked_thin_wall_and_existing_editors():
    state = dict(
        workspace="Layout",
        target_object="Face",
        active_object="Face",
        properties_context="MATERIAL",
        thin_wall=False,
        areas=[dict(type=name) for name in ["PROPERTIES", "OUTLINER", "VIEW_3D"]],
    )
    assert benchmark.fixture_ready("material_property", state)
    assert not benchmark.fixture_ready("material_property", {**state, "thin_wall": True})
    assert not benchmark.fixture_ready("material_property", {**state, "areas": []})


def test_unselected_outliner_fixture_allows_blender_scene_properties_context():
    state = dict(
        workspace="Layout",
        target_object="Face",
        active_object=None,
        properties_context="SCENE",
        target_visible=True,
        outliner_height=200,
        areas=[dict(type=name) for name in ["PROPERTIES", "OUTLINER", "VIEW_3D"]],
    )
    assert benchmark.fixture_ready("outliner", state)
    assert benchmark.fixture_ready("viewport_selection", state)
    assert benchmark.fixture_ready("drag", state)
    assert not benchmark.fixture_ready("outliner", {**state, "target_visible": False})


def test_drag_region_contains_both_boundary_and_destination_editors():
    areas = [
        dict(type="OUTLINER", x1=0.7, y1=0.05, x2=1.0, y2=0.3),
        dict(type="PROPERTIES", x1=0.7, y1=0.3, x2=1.0, y2=0.97),
    ]
    assert benchmark.case_region("drag", areas, "OUTLINER") == dict(
        x1=0.7, y1=0.05, x2=1.0, y2=0.97
    )


def test_material_success_requires_independent_shader_value():
    assert benchmark.outcome("material_property", {}, {"thin_wall": True})
    assert not benchmark.outcome("material_property", {}, {"thin_wall": False})
