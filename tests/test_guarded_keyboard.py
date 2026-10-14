import time
from threading import Event

import pytest
from PIL import Image

from clef_use.backends import DesktopAction
from clef_use.runtime import SessionRuntime
from clef_use.schema import ActionCandidate, BoundingBox, Frame, Observation, UIObject
from clef_use.state import FactValidity, StateFact, StateSource


class Editor:
    FAILSAFE = True

    def __init__(self):
        self.text = ""
        self.held = set()
        self.clicked = False
        self.selected = False
        self.submits = 0
        self.after_submit = lambda: None
        self.native_identity = (200, 300)
        self.after_character = lambda: None
        self.focus = {
            "runtime_id": [42, 7],
            "bounds": [10, 10, 90, 70],
            "window": 100,
            "process": 200,
            "thread": 300,
        }
        self.ime = False
        self.writable = True

    def type_text(self, text, cancelled, target, before_input):
        for character in text:
            before_input()
            self.text = character if self.selected else self.text + character
            self.selected = False
            self.after_character()

    def keyDown(self, key, **kwargs):
        self.held.add(key)
        if key == "a" and "ctrl" in self.held:
            self.selected = True
        elif key == "backspace":
            self.text = "" if self.selected else self.text[:-1]
            self.selected = False
        elif key == "enter":
            self.submits += 1
            self.after_submit()

    def keyUp(self, key, **kwargs):
        self.held.discard(key)

    def moveTo(self, *args, **kwargs):
        self.clicked = True

    def mouseDown(self, *args, **kwargs):
        self.clicked = True

    def mouseUp(self, *args, **kwargs):
        pass


class GuardedAction(DesktopAction):
    @property
    def requires_keyboard_context(self):
        return True

    def input_recipient_matches(self, frame, control):
        return frame.foreground_window == control["window"] and self.gui.native_identity == (
            control["process"],
            control["thread"],
        )


def editor_runtime():
    editor = Editor()

    class Capture:
        def capture(self):
            return Frame(
                Image.new("RGB", (100, 100)),
                foreground_window=100,
                foreground_bounds=(0, 0, 100, 100),
            )

    missing = set()

    def provider(observation, version):
        values = {
            "focused_control": editor.focus,
            "text_focus": True,
            "ime_composing": editor.ime,
            "text_editable": editor.writable,
        }
        return {
            name: StateFact(
                value=value,
                source=StateSource.ACCESSIBILITY,
                state_version=version,
                observed_at=time.time(),
                validity=FactValidity.VALID,
                uncertainty=0,
            )
            for name, value in values.items()
            if name not in missing
        }

    runtime = SessionRuntime(Capture(), None, None, GuardedAction(editor), state_provider=provider)
    target = UIObject(
        id="field",
        bbox=BoundingBox(x1=0.1, y1=0.1, x2=0.9, y2=0.7),
        actions=frozenset({"type", "hotkey", "press"}),
    )
    observation = Observation("owned", runtime.capture.capture(), (target,))

    def execute(operation, value, target_id="field"):
        command = ActionCandidate(
            id="input",
            observation_id=observation.id,
            operation=operation,
            value=value,
            target=target_id,
            description="Owned editor action",
        )
        return runtime._execute_selected(command, observation, Event())

    return editor, missing, execute, runtime


def test_compiled_writable_focus_inserts_exact_unicode_without_an_implicit_click():
    editor, _, execute, runtime = editor_runtime()
    try:
        assert execute("type", "Hi 한😀").ok
        assert editor.text == "Hi 한😀" and not editor.clicked
        assert execute("hotkey", "ctrl+a", None).ok and editor.selected
        assert execute("press", "backspace", None).ok and editor.text == ""
        assert execute("press", "enter", None).ok and editor.submits == 1
        assert not editor.held
    finally:
        runtime.action.release()


@pytest.mark.parametrize(
    "fact", ["focused_control", "text_focus", "ime_composing", "text_editable"]
)
def test_unknown_keyboard_state_never_authorizes_typing(fact):
    editor, missing, execute, _ = editor_runtime()
    missing.add(fact)
    assert not execute("type", "Z").ok
    assert editor.text == "" and not editor.clicked


@pytest.mark.parametrize("unsafe", ["ime", "readonly", "different_field", "invalid_literal"])
def test_known_unsafe_text_is_refused_before_click_or_prefix(unsafe):
    editor, _, execute, _ = editor_runtime()
    value = "Z"
    if unsafe == "ime":
        editor.ime = True
    elif unsafe == "readonly":
        editor.writable = False
    elif unsafe == "different_field":
        editor.focus["bounds"] = [70, 70, 95, 95]
    else:
        value = "valid prefix\nsubmit"
    assert not execute("type", value).ok
    assert editor.text == "" and not editor.clicked


@pytest.mark.parametrize("change", ["focus", "ime", "readonly", "unknown"])
def test_changed_state_stops_later_characters_without_releasing_human_input(change):
    editor, missing, execute, runtime = editor_runtime()

    def transition():
        if change == "focus":
            editor.focus = {**editor.focus, "runtime_id": [42, 8]}
        elif change == "ime":
            editor.ime = True
        elif change == "readonly":
            editor.writable = False
        else:
            missing.add("focused_control")

    editor.after_character = transition
    try:
        assert not execute("type", "AB").ok
        assert editor.text == "A" and not editor.clicked and not editor.held
    finally:
        runtime.action.release()


def test_unknown_composition_still_allows_an_explicit_escape_cancellation():
    editor, missing, execute, runtime = editor_runtime()
    missing.update({"focused_control", "ime_composing", "text_focus", "text_editable"})
    try:
        assert execute("press", "escape", None).ok
        assert editor.text == "" and not editor.held
    finally:
        runtime.action.release()


def test_acknowledged_submit_can_move_focus_without_a_false_input_refusal():
    editor, missing, execute, runtime = editor_runtime()

    def submit():
        editor.focus = {**editor.focus, "runtime_id": [42, 8], "bounds": [70, 70, 95, 95]}
        missing.update({"text_editable", "ime_composing", "text_focus"})

    editor.after_submit = submit
    try:
        result = execute("press", "enter", None)
        assert result.ok and result.delivery is not None
        assert editor.submits == 1 and not editor.held
        assert not execute("type", "must not appear").ok and editor.text == ""
    finally:
        runtime.action.release()


def test_submit_delivery_remains_acknowledged_when_native_recipient_changes():
    editor, _, execute, runtime = editor_runtime()
    editor.after_submit = lambda: setattr(editor, "native_identity", (201, 300))
    try:
        result = execute("press", "enter", None)
        assert not result.ok and result.delivery is not None
        assert editor.submits == 1 and not editor.held
    finally:
        runtime.action.release()


def test_model_loop_counts_an_acknowledged_unverified_submit_without_retry_or_completion():
    from clef_use.runtime import Session
    from clef_use.schema import Contract, Decision

    editor, _, _, runtime = editor_runtime()
    field = UIObject(
        id="field",
        role="input",
        label="Owned input",
        confidence=1,
        bbox=BoundingBox(x1=0.1, y1=0.1, x2=0.9, y2=0.7),
        actions=frozenset({"type", "press"}),
        focused=True,
        editable=True,
        visible=True,
        enabled=True,
    )

    class Perception:
        def parse(self, image):
            return (field,)

    class Planner:
        def decide(self, observation, contract, candidates, history):
            selected = next(
                item for item in candidates if item.operation == "press" and item.value == "enter"
            )
            return Decision(action=selected.id, confidence=0.99)

    runtime.perception, runtime.decision = Perception(), Planner()
    editor.after_submit = lambda: setattr(editor, "native_identity", (201, 300))
    session = Session(Contract(goal="Submit once", execution_mode="STRUCTURED", max_steps=2))
    result = runtime.execute(session)
    assert result["status"] == "NEEDS_REPLAN"
    assert result["steps"] == 1 and editor.submits == 1 and not editor.held
    assert session.action_history[-1]["failure_kind"] == "DELIVERED_UNVERIFIED"
    assert any(row.get("input_delivery") for row in session.history)
