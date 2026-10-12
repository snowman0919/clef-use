import time
from threading import Event

import pytest
from PIL import Image
from pydantic import ValidationError

from clef_use.backends import DesktopAction
from clef_use.schema import Frame


class EditorDevice:
    """A stateful editor device for deterministic guard/ownership regression tests."""

    FAILSAFE = True

    def __init__(self):
        self.held = set()
        self.buttons = set()
        self.text = ""
        self.position = (0, 0)
        self.strokes = []
        self.refuse = None
        self.selected = False
        self.submits = 0

    def keyDown(self, key, **kwargs):
        if key == self.refuse:
            raise RuntimeError("device refused key")
        self.held.add(key)
        if key == "a" and "ctrl" in self.held:
            self.selected = True
        if key == "enter":
            self.submits += 1
        if len(key) == 1 and "ctrl" not in self.held:
            self.text += key.upper() if "shift" in self.held else key

    def keyUp(self, key, **kwargs):
        self.held.discard(key)

    def moveTo(self, x, y, **kwargs):
        if self.buttons:
            self.strokes.append((self.position, (x, y), frozenset(self.held)))
        self.position = x, y

    def mouseDown(self, button, **kwargs):
        self.buttons.add(button)

    def mouseUp(self, button, **kwargs):
        self.buttons.discard(button)


def setup_input():
    return DesktopAction(EditorDevice()), Frame(Image.new("RGB", (100, 100))), Event()


def test_chord_applies_modifiers_then_releases_all_owned_input():
    from clef_use.input_ir import ChordInput

    adapter, frame, cancelled = setup_input()
    result = adapter.execute_input(ChordInput(modifiers=("shift",), key="a"), frame, cancelled)
    assert result.ok and adapter.gui.text == "A"
    assert adapter.gui.held == set() and adapter.keys == set()


def test_rejected_press_never_becomes_owned_or_releases_an_existing_human_key():
    from clef_use.input_ir import KeyInput

    adapter, frame, cancelled = setup_input()
    adapter.gui.held.add("a")
    adapter.gui.refuse = "a"
    with pytest.raises(RuntimeError, match="refused"):
        adapter.execute_input(KeyInput(key="a"), frame, cancelled)
    assert adapter.gui.held == {"a"} and adapter.keys == set()


def test_deadline_watchdog_releases_held_key_without_another_executor_call():
    from clef_use.input_ir import KeyInput

    adapter, frame, cancelled = setup_input()
    adapter.execute_input(
        KeyInput(key="shift", phase="down"), frame, cancelled, deadline=time.monotonic() + 0.05
    )
    assert adapter.gui.held == {"shift"}
    assert cancelled.wait(0.5)
    assert adapter.gui.held == set()


def test_independent_cancellation_releases_owned_button_during_worker_stall():
    from clef_use.input_ir import PointerInput

    adapter, frame, cancelled = setup_input()
    adapter.execute_input(
        PointerInput(phase="down", point=(0.4, 0.4), button="middle"),
        frame,
        cancelled,
        deadline=time.monotonic() + 1,
    )
    cancelled.set()
    for _ in range(50):
        if not adapter.gui.buttons:
            break
        time.sleep(0.01)
    assert adapter.gui.buttons == set() and adapter.buttons == set()


def test_tap_does_not_release_a_separately_owned_modifier_until_explicit_up():
    from clef_use.input_ir import KeyInput

    adapter, frame, cancelled = setup_input()
    adapter.execute_input(
        KeyInput(key="shift", phase="down"), frame, cancelled, deadline=time.monotonic() + 1
    )
    assert adapter.execute_input(KeyInput(key="a"), frame, cancelled).ok
    assert adapter.gui.text == "A" and adapter.gui.held == {"shift"}
    assert adapter.execute_input(KeyInput(key="shift", phase="up"), frame, cancelled).ok
    assert not adapter.gui.held


def test_owned_release_remains_available_after_focus_or_ime_context_becomes_invalid():
    from clef_use.input_ir import InputContext, KeyInput

    adapter, frame, cancelled = setup_input()
    adapter.execute_input(
        KeyInput(key="shift", phase="down"), frame, cancelled, deadline=time.monotonic() + 1
    )

    def stale():
        raise RuntimeError("foreground changed")

    result = adapter.execute_input(
        KeyInput(key="shift", phase="up"),
        frame,
        cancelled,
        context_guard=stale,
        context=InputContext(ime_composing=True, text_focus=True),
    )
    assert result.ok and not adapter.gui.held


def test_gesture_binds_surface_and_modifiers_and_cleans_up_on_guard_change():
    from clef_use.input_ir import GestureInput

    adapter, frame, cancelled = setup_input()
    state = {"valid": True}

    def guard():
        if not state["valid"]:
            raise RuntimeError("editor changed")

    command = GestureInput(
        points=((0.2, 0.2), (0.4, 0.4), (0.6, 0.6)),
        surface=(0.1, 0.1, 0.9, 0.9),
        modifiers=("shift",),
        button="middle",
        duration=0.02,
    )
    assert adapter.execute_input(command, frame, cancelled, context_guard=guard).ok
    assert adapter.gui.strokes == [
        ((20, 20), (40, 40), frozenset({"shift"})),
        ((40, 40), (60, 60), frozenset({"shift"})),
    ]
    assert not adapter.gui.held and not adapter.gui.buttons
    state["valid"] = False
    with pytest.raises(RuntimeError, match="editor changed"):
        adapter.execute_input(command, frame, cancelled, context_guard=guard)
    assert not adapter.gui.held and not adapter.gui.buttons


@pytest.mark.parametrize("phase", ["button_ack", "modifier_drift", "failed_button"])
def test_gesture_view_transition_requires_acknowledged_button_and_releases_modifiers(phase):
    from clef_use.input_ir import GestureInput, InputContext

    class ViewDevice(EditorDevice):
        view = "baseline"

        def keyDown(self, key, **kwargs):
            super().keyDown(key, **kwargs)
            if phase == "modifier_drift":
                self.view = "independent"

        def mouseDown(self, button, **kwargs):
            if phase == "failed_button":
                raise RuntimeError("button request refused")
            super().mouseDown(button, **kwargs)
            self.view = "owned-button"

    adapter, frame, cancelled = setup_input()
    adapter.gui = ViewDevice()
    command = GestureInput(
        points=((0.2, 0.2), (0.4, 0.4), (0.6, 0.6)),
        surface=(0, 0, 1, 1),
        modifiers=("shift",),
        duration=0.01,
    )
    arguments = dict(
        context=InputContext(text_focus=False, ime_composing=False),
        context_guard=lambda: adapter.gui.view == "baseline",
        after_input_guard=lambda: adapter.gui.view == "owned-button",
    )
    if phase == "button_ack":
        result = adapter.execute_input(command, frame, cancelled, **arguments)
        assert result.ok and result.delivery is None
        assert adapter.gui.strokes == [
            ((20, 20), (40, 40), frozenset({"shift"})),
            ((40, 40), (60, 60), frozenset({"shift"})),
        ]
    elif phase == "failed_button":
        with pytest.raises(RuntimeError, match="button request refused"):
            adapter.execute_input(command, frame, cancelled, **arguments)
        assert adapter.gui.view == "baseline" and adapter.gui.strokes == []
    else:
        result = adapter.execute_input(command, frame, cancelled, **arguments)
        assert not result.ok and adapter.gui.strokes == []
    assert not adapter.gui.held and not adapter.gui.buttons
    assert not adapter.keys and not adapter.buttons


def test_ime_unknown_and_text_focus_block_shortcuts_but_do_not_rewrite_text():
    from clef_use.input_ir import ChordInput, InputContext, TextInput

    adapter, frame, cancelled = setup_input()
    for context in (InputContext(), InputContext(ime_composing=False, text_focus=True)):
        result = adapter.execute_input(
            ChordInput(modifiers=("ctrl",), key="a"), frame, cancelled, context=context
        )
        assert not result.ok and not adapter.gui.held
    assert TextInput(text="한😀 e\u0301").text == "한😀 e\u0301"
    with pytest.raises(ValidationError):
        TextInput(text="literal\nsubmit")


def test_out_of_surface_gesture_and_unbounded_holds_refuse_before_input():
    from clef_use.input_ir import GestureInput, KeyInput

    adapter, frame, cancelled = setup_input()
    with pytest.raises(ValidationError):
        GestureInput(points=((0.2, 0.2), (0.95, 0.4)), surface=(0.1, 0.1, 0.9, 0.9), duration=0.1)
    result = adapter.execute_input(KeyInput(key="shift", phase="down"), frame, cancelled)
    assert not result.ok and not adapter.gui.held


def test_false_context_guard_refuses_key_before_editor_content_changes():
    from clef_use.input_ir import KeyInput

    adapter, frame, cancelled = setup_input()
    try:
        result = adapter.execute_input(
            KeyInput(key="a"), frame, cancelled, context_guard=lambda: False
        )
    except RuntimeError:
        pass
    else:
        assert not result.ok
    assert adapter.gui.text == "" and not adapter.gui.held


@pytest.mark.parametrize("interrupt", ["cancel", "deadline"])
def test_context_sampling_cannot_outlive_input_authorization(monkeypatch, interrupt):
    from types import SimpleNamespace

    from clef_use import input_ir
    from clef_use.input_ir import InputExecutor, KeyInput

    adapter, frame, cancelled = setup_input()
    executor = adapter.input_executor = InputExecutor(adapter.gui, adapter.keys, adapter.buttons)
    now = [100.0]
    calls = [0]
    monkeypatch.setattr(
        input_ir,
        "time",
        SimpleNamespace(monotonic=lambda: now[0], monotonic_ns=lambda: int(now[0] * 1e9)),
    )
    monkeypatch.setattr(executor, "_arm", lambda *args: None)

    def sample_context():
        calls[0] += 1
        if calls[0] == 2:
            if interrupt == "cancel":
                cancelled.set()
            else:
                now[0] = 102.0
        return True

    result = adapter.execute_input(
        KeyInput(key="a"), frame, cancelled, context_guard=sample_context, deadline=101.0
    )
    assert not result.ok
    assert adapter.gui.text == "" and not adapter.gui.held


def test_verified_text_controls_preserve_true_text_focus_and_reject_other_shortcuts():
    from clef_use.input_ir import ChordInput, InputContext, KeyInput

    adapter, frame, cancelled = setup_input()
    context = InputContext(text_focus=True, ime_composing=False, text_control="select_all")
    assert adapter.execute_input(
        ChordInput(modifiers=("ctrl",), key="a"), frame, cancelled, context=context
    ).ok
    assert adapter.gui.selected and not adapter.gui.held
    assert not adapter.execute_input(
        ChordInput(modifiers=("ctrl",), key="l"), frame, cancelled, context=context
    ).ok
    assert not adapter.execute_input(KeyInput(key="enter"), frame, cancelled, context=context).ok
    context = InputContext(text_focus=True, ime_composing=False, text_control="submit")
    assert adapter.execute_input(KeyInput(key="enter"), frame, cancelled, context=context).ok
    assert adapter.gui.submits == 1


def test_owned_submit_changes_guard_phase_only_after_successful_input():
    from clef_use.input_ir import InputContext, KeyInput

    adapter, frame, cancelled = setup_input()
    context = InputContext(text_focus=True, ime_composing=False, text_control="submit")
    result = adapter.execute_input(
        KeyInput(key="enter"),
        frame,
        cancelled,
        context=context,
        context_guard=lambda: adapter.gui.submits == 0,
        after_input_guard=lambda: adapter.gui.submits == 1,
    )
    assert result.ok and adapter.gui.submits == 1 and not adapter.gui.held
    try:
        result = adapter.execute_input(
            KeyInput(key="enter"),
            frame,
            cancelled,
            context=context,
            context_guard=lambda: False,
            after_input_guard=lambda: True,
        )
    except RuntimeError:
        pass
    else:
        assert not result.ok
    assert adapter.gui.submits == 1
    context = InputContext(text_focus=True, ime_composing=True, text_control="submit")
    assert not adapter.execute_input(KeyInput(key="enter"), frame, cancelled, context=context).ok
    assert adapter.gui.submits == 1


@pytest.mark.parametrize(
    ("command", "control"),
    [
        ({"kind": "key", "key": "enter"}, "submit"),
        ({"kind": "chord", "modifiers": ["ctrl"], "key": "a"}, "select_all"),
    ],
)
def test_exact_text_controls_refuse_previously_owned_modifiers(command, control):
    from clef_use.input_ir import InputContext, KeyInput

    adapter, frame, cancelled = setup_input()
    try:
        assert adapter.execute_input(
            KeyInput(key="shift", phase="down"),
            frame,
            cancelled,
            deadline=time.monotonic() + 1,
        ).ok
        result = adapter.execute_input(
            command,
            frame,
            cancelled,
            context=InputContext(text_focus=True, ime_composing=False, text_control=control),
        )
        assert not result.ok
        assert adapter.gui.submits == 0 and not adapter.gui.selected
        assert adapter.gui.held == {"shift"}
    finally:
        adapter.release()


@pytest.mark.parametrize(
    "command",
    [{"kind": "key", "key": "f3"}, {"kind": "chord", "modifiers": ["shift"], "key": "space"}],
)
def test_bounded_final_trigger_can_open_owned_popup_after_strict_precondition(command):
    from clef_use.input_ir import InputContext

    class PopupDevice(EditorDevice):
        popup = False

        def keyDown(self, key, **kwargs):
            super().keyDown(key, **kwargs)
            if key in {"f3", "space"}:
                self.popup = True

    adapter, frame, cancelled = setup_input()
    adapter.gui = PopupDevice()
    outcome = adapter.execute_input(
        command,
        frame,
        cancelled,
        context=InputContext(text_focus=False, ime_composing=False),
        context_guard=lambda: not adapter.gui.popup,
        after_input_guard=lambda: adapter.gui.popup,
    )
    assert outcome.ok and adapter.gui.popup and not adapter.gui.held
    assert outcome.delivery.kind == command["kind"]
    assert outcome.delivery.keys == tuple([*command.get("modifiers", []), command["key"]])


def test_delivery_survives_exception_after_actual_trigger_and_never_leaks_to_next_call():
    from clef_use.input_ir import InputDispatchError, KeyInput

    adapter, frame, cancelled = setup_input()
    # The real device acknowledges the press, then persistence to the independent
    # guardian fails. The consumer must still know that "a" was actually entered.
    first = adapter.execute_input(KeyInput(key="escape"), frame, cancelled)
    assert first.delivery is not None
    executor = adapter.input_executor
    original = executor._sync

    def unavailable():
        if adapter.gui.text:
            raise RuntimeError("guardian update failed")
        original()

    executor._sync = unavailable
    try:
        with pytest.raises(InputDispatchError, match="guardian update failed") as caught:
            adapter.execute_input(KeyInput(key="a"), frame, cancelled)
        assert adapter.gui.text == "a"
        assert caught.value.delivery.keys == ("a",)
        assert caught.value.delivery.execution_id != first.delivery.execution_id
    finally:
        executor._sync = original
        adapter.release()
    adapter.gui.refuse = "b"
    with pytest.raises(RuntimeError, match="device refused") as refused:
        adapter.execute_input(KeyInput(key="b"), frame, cancelled)
    assert not isinstance(refused.value, InputDispatchError)
    assert adapter.gui.text == "a"


@pytest.mark.parametrize(
    "command",
    [
        {"kind": "key", "key": "f3", "repeat": 2},
        {"kind": "key", "key": "f3", "hold_seconds": 0.01},
        {"kind": "key", "key": "f3", "phase": "down"},
        {"kind": "pointer", "point": (0.4, 0.4)},
    ],
)
def test_post_trigger_transition_cannot_authorize_unbounded_or_nonkey_input(command):
    from clef_use.input_ir import InputContext

    adapter, frame, cancelled = setup_input()
    outcome = adapter.execute_input(
        command,
        frame,
        cancelled,
        context=InputContext(text_focus=False, ime_composing=False),
        context_guard=lambda: True,
        after_input_guard=lambda: True,
        deadline=time.monotonic() + 1,
    )
    assert not outcome.ok and outcome.delivery is None
    assert not adapter.gui.held and not adapter.gui.buttons


def test_modifier_drift_cannot_activate_post_guard_before_final_trigger():
    from clef_use.input_ir import ChordInput, InputContext

    class MenuDevice(EditorDevice):
        menu = False
        committed = False

        def keyDown(self, key, **kwargs):
            super().keyDown(key, **kwargs)
            if key == "alt":
                self.menu = True
            elif key == "enter":
                self.committed = True

    adapter, frame, cancelled = setup_input()
    adapter.gui = MenuDevice()
    outcome = adapter.execute_input(
        ChordInput(modifiers=("alt",), key="enter"),
        frame,
        cancelled,
        context=InputContext(text_focus=False, ime_composing=False),
        context_guard=lambda: not adapter.gui.menu,
        after_input_guard=lambda: adapter.gui.menu,
    )
    assert not outcome.ok and outcome.delivery is None
    assert adapter.gui.menu and not adapter.gui.committed and not adapter.gui.held


def test_abort_after_acknowledged_trigger_returns_receipt_and_releases_input():
    from clef_use.input_ir import KeyInput

    adapter, frame, cancelled = setup_input()

    class AbortingDevice(EditorDevice):
        def keyDown(self, key, **kwargs):
            super().keyDown(key, **kwargs)
            cancelled.set()

    adapter.gui = AbortingDevice()
    outcome = adapter.execute_input(KeyInput(key="a"), frame, cancelled)
    assert not outcome.ok and outcome.delivery.keys == ("a",)
    assert adapter.gui.text == "a" and not adapter.gui.held


def test_gesture_allows_consumer_to_receive_motion_while_button_and_modifier_remain_held():
    from threading import current_thread, main_thread

    from clef_use.input_ir import GestureInput

    class QueuedDevice(EditorDevice):
        pending = None

        def moveTo(self, x, y, **kwargs):
            if self.position != (x, y):
                self.pending = self.position, (x, y)
                self.position = x, y

        def mouseUp(self, button, **kwargs):
            self.pending = None
            super().mouseUp(button, **kwargs)

    device = QueuedDevice()
    device.position = (40, 40)

    class ConsumerEvent(Event):
        def wait(self, timeout=None):
            if current_thread() is main_thread() and device.pending and device.buttons:
                device.strokes.append((*device.pending, frozenset(device.held)))
                device.pending = None
            return super().wait(timeout)

    outcome = DesktopAction(device).execute_input(
        GestureInput(
            points=((0.4, 0.4), (0.5, 0.5)),
            surface=(0.1, 0.1, 0.9, 0.9),
            modifiers=("shift",),
            button="middle",
            duration=0.01,
        ),
        Frame(Image.new("RGB", (100, 100))),
        ConsumerEvent(),
    )
    assert outcome.ok
    assert device.strokes == [((40, 40), (50, 50), frozenset({"shift"}))]
    assert not device.held and not device.buttons


def test_windows_rejected_key_does_not_release_human_key_and_all_buttons_release_on_focus_loss():
    from test_windows_input import native

    api, gui = native()
    api.refuse = (ord("A"), 8)
    with pytest.raises(RuntimeError, match="SendInput"):
        gui.keyDown("a")
    assert not gui.key_events
    for button in ("left", "right", "middle"):
        gui.mouseDown(button)
        api.target = 200
        gui.mouseUp(button)
    assert [event[2] for event in api.events] == [2, 4, 8, 16, 32, 64]
