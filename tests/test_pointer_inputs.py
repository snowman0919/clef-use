import base64
import hashlib
import io
import json
import os
import sys
import threading
from dataclasses import replace
from threading import Event

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image, ImageDraw
from pydantic import ValidationError

from clef_use.backends import DesktopAction, decision_request
from clef_use.candidates import CandidateBuilder
from clef_use.config import Config
from clef_use.runtime import Session, SessionRuntime
from clef_use.schema import (
    ActionCandidate,
    BoundingBox,
    Contract,
    Decision,
    Frame,
    Observation,
    UIObject,
)
from clef_use.service import SessionManager, make_server


def reference(frame):
    return {
        "image_sha256": hashlib.sha256(frame.image.tobytes()).hexdigest(),
        "image_size": frame.image.size,
        "origin": frame.origin,
        "logical_size": frame.logical_size,
        "foreground_window": frame.foreground_window,
        "foreground_bounds": frame.foreground_bounds,
    }


def stroke(frame, **changes):
    return {
        "operation": "stroke",
        "label": "Draw a short line inside the inspected canvas",
        "reference": reference(frame),
        "surface": {"x1": 0.1, "y1": 0.1, "x2": 0.9, "y2": 0.9},
        "points": [{"x": 0.2, "y": 0.4}, {"x": 0.5, "y": 0.4}, {"x": 0.8, "y": 0.4}],
        "duration": 0.05,
        **changes,
    }


def test_cached_pixels_do_not_keep_a_pointer_valid_after_foreground_or_geometry_changes():
    gui = RasterGui()
    first = Frame(gui.image.copy(), foreground_window=1)
    contract = Contract(goal="Draw inside canvas", pointer_inputs=[stroke(first)])

    class Parser:
        cache_identity = ("fixed-image-parser",)

        def parse(self, image):
            return ()

    runtime = SessionRuntime(None, Parser(), None, None)
    objects = runtime._parse(first)
    assert CandidateBuilder().build(Observation("first", first, objects), contract)
    for changed in [
        replace(first, foreground_window=2),
        replace(first, origin=(1, 0)),
        replace(first, logical_size=(50, 50)),
        replace(first, foreground_bounds=(1, 1, 99, 99)),
    ]:
        row = {}
        cached = runtime._parse(changed, row)
        assert row["perception_cache_hit"]
        observation = Observation("fresh", changed, cached)
        assert CandidateBuilder().build(observation, contract) == ()
        candidate = CandidateBuilder().build(Observation("first", first, objects), contract)[0]
        candidate = candidate.model_copy(update={"observation_id": observation.id})
        assert not DesktopAction(gui=gui).execute(candidate, observation, Event()).ok
    assert gui.presses == 0


class RasterGui:
    """Unit-only device substitute: held movement actually changes a raster."""

    FAILSAFE = True

    def __init__(self, size=(100, 100)):
        self.image = Image.new("RGB", size, "white")
        self.position = None
        self.held = False
        self.presses = 0

    def moveTo(self, x, y, **kwargs):
        if self.held:
            assert self.position is not None
            ImageDraw.Draw(self.image).line((self.position, (x, y)), fill="black", width=2)
        self.position = (x, y)

    def mouseDown(self, button):
        assert button == "left"
        self.held = True
        self.presses += 1

    def mouseUp(self, button):
        assert button == "left"
        self.held = False


def test_scoped_stroke_changes_canvas_continuously_and_releases_button():
    gui = RasterGui()
    frame = Frame(gui.image.copy())
    obs = Observation("fresh", frame, ())
    contract = Contract(goal="Draw the planned line", pointer_inputs=[stroke(frame)])
    actions = CandidateBuilder().build(obs, contract)
    assert len(actions) == 1 and actions[0].operation == "stroke"
    backend = DesktopAction(gui=gui)
    result = backend.execute(actions[0], obs, Event())
    assert result.ok and gui.image.getpixel((50, 40)) == (0, 0, 0)
    assert gui.image.getpixel((50, 50)) == (255, 255, 255)
    assert gui.presses == 1 and not gui.held and not backend.buttons
    assert gui.FAILSAFE


@pytest.mark.parametrize("boundary", ["candidate", "adapter"])
def test_sensitive_surface_refuses_supplied_pointer_at_both_boundaries(boundary):
    gui = RasterGui()
    frame = Frame(gui.image.copy())
    sensitive = UIObject(
        id="secret",
        label="Password",
        sensitive=True,
        bbox=BoundingBox(x1=0.4, y1=0.3, x2=0.6, y2=0.5),
    )
    obs = Observation("fresh", frame, (sensitive,))
    contract = Contract(goal="Draw the planned line", pointer_inputs=[stroke(frame)])
    if boundary == "candidate":
        assert not CandidateBuilder().build(obs, contract)
    else:
        action = ActionCandidate(
            id="supplied",
            operation="stroke",
            observation_id=obs.id,
            description="Draw line",
            pointer=contract.pointer_inputs[0],
        )
        result = DesktopAction(gui=gui).execute(action, obs, Event())
        assert not result.ok and gui.presses == 0


class RasterDesktop(RasterGui):
    def capture(self):
        return Frame(self.image.copy())

    def parse(self, image):
        return ()

    def decide(self, observation, contract, candidates, history):
        if self.image.getpixel((50, 40)) == (0, 0, 0):
            return Decision(
                mode="COMPLETED",
                confidence=0.99,
                goal_probability=0.99,
                effect_probability=0.99,
                progress=1,
                condition_probabilities=tuple(0.99 for _ in contract.success_conditions),
            )
        return Decision(action=candidates[0].id, confidence=0.99)


async def test_real_stdio_mcp_routes_supplied_stroke_through_shared_runtime(tmp_path, monkeypatch):
    desktop = RasterDesktop()
    executor = SessionRuntime(
        desktop, desktop, desktop, DesktopAction(gui=desktop), Config(settle_seconds=0)
    )
    manager = SessionManager(lambda: executor)
    server = make_server(manager, "pointer-fixture-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    (tmp_path / "endpoint.json").write_text(
        json.dumps(
            {
                "port": server.server_port,
                "token": "pointer-fixture-token",
                "pid": os.getpid(),
            }
        )
    )
    monkeypatch.setenv("CLEF_USE_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("CLEF_USE_CONFIG", str(tmp_path / "absent.toml"))
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "clef_use.cli", "mcp"],
        env=dict(os.environ),
    )
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                tools = await client.list_tools()
                run = next(t for t in tools.tools if t.name == "computer_run")
                assert "pointer_inputs" in run.inputSchema["properties"]
                observed = await client.call_tool("computer_observe", {"include_image": True})
                assert not observed.isError
                observed_data = json.loads(observed.content[0].text)
                image = Image.open(io.BytesIO(base64.b64decode(observed.content[1].data)))
                assert observed_data["observation_fresh"] and observed_data["session_id"] is None
                assert not manager.sessions
                assert (
                    observed_data["frame_reference"]["image_sha256"]
                    == hashlib.sha256(image.tobytes()).hexdigest()
                )
                planned = stroke(desktop.capture())
                planned["reference"] = observed_data["frame_reference"]
                result = await client.call_tool(
                    "computer_run",
                    {
                        "goal": "Draw the explicitly planned line",
                        "max_steps": 4,
                        "success_conditions": ["A black continuous line crosses the canvas"],
                        "pointer_inputs": [planned],
                    },
                )
                assert not result.isError
                data = result.structuredContent
                assert data["status"] == "COMPLETED" and data["steps"] == 1
                assert desktop.presses == 1 and not desktop.held
                assert data["last_action"]["pointer"]["points"][1] == {"x": 0.5, "y": 0.4}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)


def test_idle_observe_exports_exact_coordinate_and_pixel_reference():
    desktop = RasterDesktop()
    executor = SessionRuntime(
        desktop, desktop, desktop, DesktopAction(gui=desktop), Config(settle_seconds=0)
    )
    session = Session(Contract(goal="Inspect the canvas"))
    result = executor.observe(session, include_image=True)
    assert result["observation_fresh"]
    assert result["frame_reference"] == session.observation.frame.reference().model_dump(
        mode="json"
    )


@pytest.mark.parametrize("operation,with_path", [("stroke", False), ("click", True)])
def test_adapter_refuses_missing_or_contradictory_pointer_operation(operation, with_path):
    gui = RasterGui()
    frame = Frame(gui.image.copy())
    obs = Observation("fresh", frame, ())
    pointer = Contract(goal="Draw", pointer_inputs=[stroke(frame)]).pointer_inputs[0]
    action = ActionCandidate(
        id="invalid",
        operation=operation,
        observation_id=obs.id,
        description="invalid",
        pointer=pointer if with_path else None,
    )
    result = DesktopAction(gui=gui).execute(action, obs, Event())
    assert not result.ok and gui.presses == 0


@pytest.mark.parametrize("boundary", ["candidate", "adapter"])
def test_pointer_cannot_leave_captured_foreground_bounds(boundary):
    gui = RasterGui()
    frame = Frame(gui.image.copy(), foreground_window=123, foreground_bounds=(0, 0, 40, 100))
    obs = Observation("fresh", frame, ())
    contract = Contract(goal="Draw", pointer_inputs=[stroke(frame)])
    if boundary == "candidate":
        assert not CandidateBuilder().build(obs, contract)
    else:
        action = ActionCandidate(
            id="invalid",
            operation="stroke",
            observation_id=obs.id,
            description="outside window",
            pointer=contract.pointer_inputs[0],
        )
        assert not DesktopAction(gui=gui).execute(action, obs, Event()).ok
        assert gui.presses == 0


def test_runtime_rejects_pointer_if_even_unrelated_pixels_changed_before_input():
    class ChangedCapture(RasterDesktop):
        captures = 0

        def capture(self):
            self.captures += 1
            image = self.image.copy()
            if self.captures > 1:
                image.putpixel((99, 99), (0, 0, 0))
            return Frame(image)

    desktop = ChangedCapture()
    initial = Frame(desktop.image.copy())
    executor = SessionRuntime(
        desktop, desktop, desktop, DesktopAction(gui=desktop), Config(settle_seconds=0)
    )
    session = Session(Contract(goal="Draw", max_steps=4, pointer_inputs=[stroke(initial)]))
    result = executor.execute(session)
    assert result["status"] == "NEEDS_REPLAN"
    assert session.steps == desktop.presses == 0 and not desktop.held


def test_pointer_contract_offers_only_supplied_paths_with_coordinates_in_model_state():
    frame = Frame(Image.new("RGB", (100, 100), "white"))
    button = UIObject(
        id="other",
        label="Unrelated settings",
        actions=frozenset({"click"}),
        bbox=BoundingBox(x1=0.9, y1=0.9, x2=1, y2=1),
    )
    observation = Observation("fresh", frame, (button,))
    contract = Contract(goal="Draw", pointer_inputs=[stroke(frame)])
    actions = CandidateBuilder().build(observation, contract)
    assert len(actions) == 1 and actions[0].pointer is not None
    payload = decision_request(observation, contract, actions, [])
    assert payload["state"]["allowed_candidates"][0]["pointer"]["points"][1] == {"x": 0.5, "y": 0.4}


def test_pointer_action_history_does_not_claim_parser_detected_a_target():
    desktop = RasterDesktop()
    executor = SessionRuntime(
        desktop, desktop, desktop, DesktopAction(gui=desktop), Config(settle_seconds=0)
    )
    session = Session(
        Contract(
            goal="Draw",
            max_steps=4,
            pointer_inputs=[stroke(desktop.capture())],
        )
    )
    assert executor.execute(session)["status"] == "COMPLETED"
    delivered = next(row for row in session.history if row.get("execution_ok"))
    assert delivered["actionability"]["visible"] == "PLANNER_SUPPLIED_PIXELS"
    assert session.action_history[0]["pointer"]["points"][1] == {"x": 0.5, "y": 0.4}


@pytest.mark.parametrize(
    "changes",
    [
        {"points": [{"x": 0.05, "y": 0.4}, {"x": 0.8, "y": 0.4}]},
        {"points": [{"x": float("nan"), "y": 0.4}, {"x": 0.8, "y": 0.4}]},
        {"points": [{"x": 0.5, "y": 0.4}] * 129},
        {"points": [{"x": 0.5, "y": 0.4}]},
        {"duration": 6},
        {"duration": float("inf")},
        {"label": " "},
    ],
)
def test_pointer_schema_bounds_and_rejects_invalid_payload(changes):
    frame = Frame(Image.new("RGB", (100, 100), "white"))
    with pytest.raises(ValidationError):
        Contract(goal="Draw", pointer_inputs=[stroke(frame, **changes)])


@pytest.mark.parametrize(
    "changes",
    [
        {"origin": (10, 0)},
        {"logical_size": (200, 100)},
        {"foreground_window": 456},
        {"foreground_bounds": (0, 0, 100, 99)},
    ],
)
def test_identical_pixels_do_not_authorize_changed_coordinate_metadata(changes):
    gui = RasterGui()
    frame = Frame(gui.image.copy())
    contract = Contract(goal="Draw", pointer_inputs=[stroke(frame)])
    changed = Observation("fresh", replace(frame, **changes), ())
    assert not CandidateBuilder().build(changed, contract)
    action = ActionCandidate(
        id="old",
        operation="stroke",
        observation_id=changed.id,
        description="Old plan",
        pointer=contract.pointer_inputs[0],
    )
    assert not DesktopAction(gui=gui).execute(action, changed, Event()).ok
    assert gui.presses == 0


@pytest.mark.parametrize("interrupt", ["cancel", "failure"])
def test_stroke_interrupt_releases_held_button_and_keeps_failsafe(interrupt):
    cancelled = Event()

    class InterruptedGui(RasterGui):
        def moveTo(self, x, y, **kwargs):
            super().moveTo(x, y, **kwargs)
            if self.held:
                if interrupt == "failure":
                    raise RuntimeError("unit device interrupted")
                cancelled.set()

    gui = InterruptedGui()
    frame = Frame(gui.image.copy())
    obs = Observation("fresh", frame, ())
    contract = Contract(goal="Draw", pointer_inputs=[stroke(frame)])
    action = CandidateBuilder().build(obs, contract)[0]
    backend = DesktopAction(gui=gui)
    if interrupt == "failure":
        with pytest.raises(RuntimeError, match="unit device interrupted"):
            backend.execute(action, obs, cancelled)
    else:
        assert not backend.execute(action, obs, cancelled).ok
    assert not gui.held and not backend.buttons and gui.FAILSAFE


def test_pixel_click_maps_normalized_points_to_negative_origin_and_scaled_dimensions():
    gui = RasterGui()
    frame = Frame(gui.image.copy(), origin=(-200, 10), logical_size=(200, 300))
    pointer = stroke(frame, operation="click", points=[{"x": 0.5, "y": 0.4}])
    obs = Observation("fresh", frame, ())
    contract = Contract(goal="Click canvas", pointer_inputs=[pointer])
    action = CandidateBuilder().build(obs, contract)[0]
    assert DesktopAction(gui=gui).execute(action, obs, Event()).ok
    assert gui.position == (-100, 130) and gui.presses == 1 and not gui.held


@pytest.mark.parametrize("boundary", ["candidate", "adapter"])
def test_device_pixel_quantization_cannot_cross_into_sensitive_surface(boundary):
    gui = RasterGui(size=(200, 200))
    frame = Frame(gui.image.copy(), logical_size=(100, 100))
    sensitive = UIObject(
        id="secret",
        sensitive=True,
        bbox=BoundingBox(x1=0.49, y1=0.3, x2=0.495, y2=0.5),
    )
    observation = Observation("fresh", frame, (sensitive,))
    supplied = stroke(
        frame,
        operation="click",
        points=[{"x": 0.498, "y": 0.4}],
        surface={"x1": 0.496, "y1": 0.3, "x2": 0.499, "y2": 0.5},
    )
    contract = Contract(goal="Click inspected pixels", pointer_inputs=[supplied])
    if boundary == "candidate":
        assert not CandidateBuilder().build(observation, contract)
    else:
        candidate = ActionCandidate(
            id="supplied",
            operation="click",
            observation_id=observation.id,
            description="Inspected click",
            pointer=contract.pointer_inputs[0],
        )
        assert not DesktopAction(gui).execute(candidate, observation, Event()).ok
        assert gui.presses == 0


@pytest.mark.parametrize("case", ["containment", "coverage"])
def test_quantized_containment_and_sensitive_pixel_coverage_have_independent_guards(case):
    frame = Frame(Image.new("RGB", (200, 200), "white"), logical_size=(100, 100))
    objects = ()
    if case == "containment":
        surface = {"x1": 0.496, "y1": 0.3, "x2": 0.499, "y2": 0.5}
        point = {"x": 0.498, "y": 0.4}
    else:
        surface = {"x1": 0.5, "y1": 0.3, "x2": 0.507, "y2": 0.5}
        point = {"x": 0.503, "y": 0.4}
        objects = (
            UIObject(
                id="secret",
                sensitive=True,
                bbox=BoundingBox(x1=0.508, y1=0.3, x2=0.515, y2=0.5),
            ),
        )
    supplied = stroke(frame, operation="click", points=[point], surface=surface)
    contract = Contract(goal="Click inspected pixels", pointer_inputs=[supplied])
    observation = Observation("fresh", frame, objects)
    assert not CandidateBuilder().build(observation, contract)
