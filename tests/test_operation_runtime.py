import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from PIL import Image

from clef_use.config import Config
from clef_use.runtime import Session, SessionRuntime
from clef_use.schema import Contract, Frame, Status
from clef_use.service import SessionManager
from clef_use.state import FactValidity, StateFact, StateSource


class OperationEditor:
    """An editor whose UI state changes during acknowledged native key events."""

    FAILSAFE = True

    def __init__(self):
        self.held = set()
        self.text = ""
        self.after_enter = None
        self.values = {
            "application": "Blender",
            "window": "fixture",
            "foreground": True,
            "editor": "VIEW_3D",
            "mode": "OBJECT",
            "selection": ["Cube"],
            "ime_composing": False,
            "text_focus": False,
            "popup": False,
            "loading": False,
            "modal": None,
            "owned_inputs": [],
            "keymap_version": "fixture-1",
            "keymap": {
                "search": ["f3"],
                "commit": ["enter"],
                "cancel": ["escape"],
                "translate": ["g"],
                "axis_x": ["x"],
            },
            "space": "GLOBAL",
            "unit": {"translate": "METERS", "rotate": "DEGREES", "scale": "NONE"},
            "properties": {"Cube": {"shading": "FLAT"}},
            "command_result": "",
            "transform_values": {
                "Cube": {
                    "translate": {"X": 0.0, "Y": 0.0, "Z": 0.0},
                    "rotate": {"X": 0.0, "Y": 0.0, "Z": 0.0},
                    "scale": {"X": 1.0, "Y": 1.0, "Z": 1.0},
                }
            },
            "transform_context": {
                "Cube": {"parent": None, "delta_identity": True, "pivot": "MEDIAN_POINT"}
            },
        }

    def keyDown(self, key, **kwargs):
        self.held.add(key)
        if key == "f3":
            self.values.update(popup="COMMAND_SEARCH", text_focus=True)
        elif key == "g" and not self.values["text_focus"]:
            self.values["modal"] = {"id": "owned-modal", "name": "translate"}
            if self.after_enter:
                self.after_enter()
        elif key == "enter" and self.text == "Shade Smooth":
            self.values.update(popup=False, text_focus=False, command_result="object.shade_smooth")
            self.values["properties"]["Cube"]["shading"] = "SMOOTH"
        elif key == "escape":
            self.values["modal"] = None
        elif len(key) == 1:
            self.text += key.upper() if "shift" in self.held else key
        elif key == "space":
            self.text += " "

    def keyUp(self, key, **kwargs):
        self.held.discard(key)

    def type_text(self, text, cancelled, target):
        if self.values["text_focus"] and not cancelled.is_set():
            self.text += text

    def provide(self, observation, version):
        return {
            name: StateFact(
                value=value,
                source=StateSource.API,
                observed_at=time.time(),
                state_version=version,
                validity=FactValidity.VALID,
                uncertainty=0,
            )
            for name, value in self.values.items()
        }

    def runtime(self):
        from clef_use.backends import DesktopAction

        return SessionRuntime(
            Screen(),
            NoModel(),
            NoModel(),
            DesktopAction(self),
            Config(),
            state_provider=self.provide,
        )


def test_search_accepts_only_its_acknowledged_popup_transition_and_reads_effect():
    editor = OperationEditor()
    runtime = editor.runtime()
    session = Session(
        Contract(
            goal="Shade Cube smooth",
            operation={
                "family": "command_search",
                "command": "object.shade_smooth",
                "target_id": "Cube",
                "keymap_version": "fixture-1",
            },
        )
    )
    result = runtime.execute(session)
    assert result["status"] == "NEEDS_REPLAN"
    assert editor.values["properties"]["Cube"]["shading"] == "SMOOTH"
    assert not editor.values["popup"] and not editor.held


@pytest.mark.parametrize(
    "change",
    [
        {"loading": True},
        {"keymap": {"translate": ["r"], "axis_x": ["y"]}},
        {"space": "LOCAL"},
        {"modal": {"id": "foreign", "name": "rotate"}},
        {"unit": {"translate": "CENTIMETERS", "rotate": "DEGREES", "scale": "NONE"}},
        {
            "transform_context": {
                "Cube": {"parent": "Parent", "delta_identity": True, "pivot": "MEDIAN_POINT"}
            }
        },
    ],
)
def test_numeric_event_refuses_changed_safety_facts_at_native_boundary(change):
    from threading import Event

    from clef_use.input_ir import KeyInput

    editor = OperationEditor()
    runtime = editor.runtime()
    state = runtime._operation_state()
    editor.values.update(change)
    with pytest.raises(RuntimeError, match="context changed"):
        runtime._operation_input(
            KeyInput(key="x"),
            state,
            Event(),
            {"family": "numeric_transform", "operation": "translate"},
        )
    assert editor.text == "" and not editor.held


def test_numeric_baseline_change_at_native_boundary_refuses_modal_entry():
    from threading import Event

    from clef_use.input_ir import KeyInput

    editor = OperationEditor()
    runtime = editor.runtime()
    state = runtime._operation_state()
    editor.values["transform_values"]["Cube"]["translate"]["X"] = 5.0
    with pytest.raises(RuntimeError, match="context changed"):
        runtime._operation_input(
            KeyInput(key="g"),
            state,
            Event(),
            {"family": "numeric_transform", "operation": "translate"},
        )
    assert editor.values["modal"] is None and not editor.held


def test_owned_cancel_rechecks_transform_context_at_native_boundary():
    from threading import Event

    from clef_use.input_ir import KeyInput

    editor = OperationEditor()
    editor.values["modal"] = {"id": "owned", "name": "translate"}
    runtime = editor.runtime()
    state = runtime._operation_state()
    editor.values["transform_context"]["Cube"]["parent"] = "Parent"
    with pytest.raises(RuntimeError, match="context changed"):
        runtime._operation_input(
            KeyInput(key="escape"), state, Event(), {"family": "modal_cancel", "modal_id": "owned"}
        )
    assert editor.values["modal"] == {"id": "owned", "name": "translate"}
    assert not editor.held


def test_numeric_preview_change_at_native_boundary_refuses_commit():
    from copy import deepcopy
    from threading import Event

    from clef_use.input_ir import KeyInput

    editor = OperationEditor()
    editor.values["modal"] = {"id": "owned", "name": "translate"}
    editor.values["transform_preview"] = deepcopy(editor.values["transform_values"])
    runtime = editor.runtime()
    state = runtime._operation_state()
    editor.values["transform_preview"]["Cube"]["translate"]["X"] = 99.0
    with pytest.raises(RuntimeError, match="context changed"):
        runtime._operation_input(
            KeyInput(key="enter"),
            state,
            Event(),
            {"family": "numeric_transform", "operation": "translate"},
        )
    assert editor.values["modal"] == {"id": "owned", "name": "translate"}
    assert not editor.held


def test_acknowledged_entry_can_preview_values_without_failing_the_context_guard():
    from threading import Event

    from clef_use.input_ir import KeyInput

    editor = OperationEditor()
    runtime = editor.runtime()
    state = runtime._operation_state()
    editor.after_enter = lambda: editor.values["transform_values"]["Cube"]["translate"].update(
        X=5.0
    )
    result = runtime._operation_input(
        KeyInput(key="g"), state, Event(), {"family": "numeric_transform", "operation": "translate"}
    )
    assert result.ok
    assert editor.values["modal"] == {"id": "owned-modal", "name": "translate"}
    assert editor.values["transform_values"]["Cube"]["translate"]["X"] == 5
    assert not editor.held


def test_viewport_region_change_at_native_boundary_refuses_pointer_movement():
    from threading import Event

    from clef_use.input_ir import GestureInput

    editor = OperationEditor()
    editor.values["target_geometry"] = {"editor_surface": [0, 0, 1, 1]}
    editor.values["keymap"] = {"orbit": {"button": "middle", "modifiers": []}}

    def move(*args, **kwargs):
        pytest.fail("stale viewport geometry must refuse before moving the pointer")

    editor.moveTo = move
    runtime = editor.runtime()
    state = runtime._operation_state()
    editor.values["target_geometry"]["editor_surface"] = [0, 0, 0.3, 1]
    with pytest.raises(RuntimeError, match="context changed"):
        runtime._operation_input(
            GestureInput(points=((0.4, 0.4), (0.5, 0.5)), surface=(0, 0, 1, 1), duration=0.05),
            state,
            Event(),
            {"family": "viewport_gesture", "gesture": "orbit"},
        )
    assert not editor.held


class Screen:
    def capture(self):
        return Frame(Image.new("RGB", (100, 100)))


class NoModel:
    def parse(self, image):
        pytest.fail("registered operation unexpectedly invoked full perception")

    def decide(self, *args):
        pytest.fail("registered operation unexpectedly invoked a decision model")


class NoInput:
    def release(self):
        pass

    def execute(self, *args):
        pytest.fail("read-only or unknown state sent input")


def test_typed_continuation_requires_explicit_operation_to_avoid_repeating_effect():
    manager = SessionManager()
    session = Session(
        Contract(goal="Assess File", operation={"family": "menu_assess", "menu": "File"})
    )
    session.status = Status.NEEDS_REPLAN
    manager.sessions[session.id] = session
    with pytest.raises(ValueError, match="explicit operation"):
        manager.continue_session(session.id, "Now verify the whole goal")
    assert session.status == Status.NEEDS_REPLAN


def test_pending_modal_recovery_blocks_replacement_and_other_goals_until_cancelled():
    editor = OperationEditor()
    runtime = editor.runtime()
    manager = SessionManager(factory=lambda: runtime)
    manager.runtime = runtime
    session = Session(
        Contract(
            goal="Move Cube",
            operation={
                "family": "numeric_transform",
                "target_id": "Cube",
                "operation": "translate",
                "axis": "X",
                "space": "GLOBAL",
                "unit": "METERS",
                "amount": 2,
                "keymap_version": "fixture-1",
            },
        )
    )
    manager.sessions[session.id] = session
    manager.active = session.id
    editor.after_enter = session.cancelled.set
    assert runtime.execute(session)["status"] == "ABORTED"
    assert runtime.operation_runners[session.id].owns_modal("owned-modal")
    assert manager.dispatch("health", {})["busy"] is True
    with pytest.raises(RuntimeError, match="owns the desktop"):
        manager.dispatch("shutdown_idle", {})
    assert not manager.stopping
    refused = manager.run({"goal": "Start an unrelated desktop task"})
    assert refused["status"] == "SAFETY_BLOCK"
    assert manager.active == session.id
    manager.continue_session(
        session.id, "Cancel my modal", {"family": "modal_cancel", "modal_id": "owned-modal"}
    )
    deadline = time.monotonic() + 3
    while manager.busy and time.monotonic() < deadline:
        time.sleep(0.001)
    assert not manager.busy and editor.values["modal"] is None
    assert manager.dispatch("health", {})["busy"] is False
    assert manager.dispatch("shutdown_idle", {}) == {"ok": True}


def test_concurrent_watchdog_observation_preserves_fact_and_frame_version():
    def provider(observation, version):
        time.sleep(0.001)
        return {
            "mode": StateFact(
                value="OBJECT",
                source=StateSource.APP_TELEMETRY,
                observed_at=time.time(),
                state_version=version,
                validity=FactValidity.VALID,
                uncertainty=0,
            )
        }

    runtime = SessionRuntime(
        Screen(), NoModel(), NoModel(), NoInput(), Config(), state_provider=provider
    )
    with ThreadPoolExecutor(max_workers=8) as pool:
        states = list(pool.map(lambda _: runtime._operation_state(), range(32)))
    assert {s.version for s in states} == set(range(1, 33))
    for state in states:
        assert state.require("mode") == "OBJECT"
        assert runtime._operation_frames[state.observation_id].image.size == (100, 100)


def test_unknown_local_state_blocks_operation_without_model_or_input():
    runtime = SessionRuntime(Screen(), NoModel(), NoModel(), NoInput(), Config())
    session = Session(
        Contract(
            goal="Assess the File menu",
            execution_mode="ASSESS",
            operation={"family": "menu_assess", "menu": "File"},
        )
    )
    result = runtime.execute(session)
    assert result["status"] == "BLOCKED"
    assert result["blocker"]["observed"]["assessment"] == "UNKNOWN"
    assert result["steps"] == 0
    assert session.history[-2]["terminal_event"] == "BLOCKED"


def test_mutating_operation_cannot_enter_assess_mode():
    with pytest.raises(ValueError, match="ASSESS"):
        Contract(
            goal="move",
            execution_mode="ASSESS",
            operation={
                "family": "numeric_transform",
                "target_id": "Cube",
                "operation": "translate",
                "axis": "X",
                "space": "GLOBAL",
                "unit": "NONE",
                "amount": 2,
                "keymap_version": "test",
            },
        )


def test_operation_effect_does_not_claim_unrelated_task_conditions():
    def provider(observation, version):
        return {
            "menus": StateFact(
                value=[{"id": "file-menu", "name": "File", "open": True}],
                source=StateSource.APP_TELEMETRY,
                observed_at=time.time(),
                state_version=version,
                validity=FactValidity.VALID,
                uncertainty=0,
            )
        }

    runtime = SessionRuntime(
        Screen(), NoModel(), NoModel(), NoInput(), Config(), state_provider=provider
    )
    session = Session(
        Contract(
            goal="Assess File and verify saved file",
            success_conditions=["A file is saved on disk"],
            operation={"family": "menu_assess", "menu": "File"},
        )
    )
    result = runtime.execute(session)
    assert result["status"] == "NEEDS_REPLAN"
    assert result["blocker"]["observed"]["assessment"] == "OPEN"


@pytest.mark.parametrize(
    "menus,assessment",
    [
        ([], "ABSENT"),
        ([{"id": "edit", "name": "Edit", "open": True}], "WRONG_MENU"),
        (
            [{"id": "a", "name": "File", "open": True}, {"id": "b", "name": "File", "open": True}],
            "AMBIGUOUS",
        ),
    ],
)
def test_absent_wrong_or_ambiguous_menu_never_completes_open_menu_goal(menus, assessment):
    def provider(observation, version):
        return {
            "menus": StateFact(
                value=menus,
                source=StateSource.APP_TELEMETRY,
                observed_at=time.time(),
                state_version=version,
                validity=FactValidity.VALID,
                uncertainty=0,
            )
        }

    runtime = SessionRuntime(
        Screen(), NoModel(), NoModel(), NoInput(), Config(), state_provider=provider
    )
    session = Session(
        Contract(
            goal="File menu is open",
            execution_mode="ASSESS",
            operation={"family": "menu_assess", "menu": "File"},
        )
    )
    result = runtime.execute(session)
    assert result["status"] == "BLOCKED"
    assert result["blocker"]["observed"]["assessment"] == assessment
    assert result["steps"] == 0


def test_insufficient_transform_budget_refuses_before_entering_modal():
    runtime = SessionRuntime(Screen(), NoModel(), NoModel(), NoInput(), Config())
    session = Session(
        Contract(
            goal="Move Cube 2 units on X",
            max_steps=3,
            operation={
                "family": "numeric_transform",
                "target_id": "Cube",
                "operation": "translate",
                "axis": "X",
                "space": "GLOBAL",
                "unit": "NONE",
                "amount": 2,
                "keymap_version": "observed-keymap",
            },
        )
    )
    result = runtime.execute(session)
    assert result["status"] == "BLOCKED"
    assert result["steps"] == 0
    assert "budget" in result["reason"]


def test_verified_operation_never_certifies_an_unassessed_natural_language_goal():
    def provider(observation, version):
        return {
            "menus": StateFact(
                value=[{"id": "file", "name": "File", "open": True}],
                source=StateSource.APP_TELEMETRY,
                observed_at=time.time(),
                state_version=version,
                validity=FactValidity.VALID,
                uncertainty=0,
            )
        }

    runtime = SessionRuntime(
        Screen(), NoModel(), NoModel(), NoInput(), Config(), state_provider=provider
    )
    session = Session(
        Contract(
            goal="The Edit menu is open",
            execution_mode="ASSESS",
            operation={"family": "menu_assess", "menu": "File"},
        )
    )
    result = runtime.execute(session)
    assert result["status"] == "NEEDS_REPLAN"
    assert result["blocker"]["observed"]["status"] == "SUCCEEDED"
    assert result["blocker"]["observed"]["assessment"] == "OPEN"
