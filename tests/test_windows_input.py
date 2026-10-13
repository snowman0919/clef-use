import ctypes
from threading import Event, Thread, local
from types import SimpleNamespace

import pytest
from PIL import Image

from clef_use.backends import DesktopAction
from clef_use.schema import ActionCandidate, Contract, Frame, Observation
from clef_use.windows_input import (
    Input,
    WindowsDesktopUnavailable,
    WindowsForegroundChanged,
    WindowsInput,
    WindowsInputFailsafe,
)


class FakeAPI:
    def __init__(self):
        self.session = 1
        self.target = 100
        self.recipient = 100
        self.desktop = "Default"
        self.events = []
        self.refuse = None
        self.position = (5, 5)
        self.contexts = []
        self.after_input = lambda: None

    def ProcessIdToSessionId(self, _, pointer):
        pointer._obj.value = self.session
        return 1

    def OpenInputDesktop(self, *_):
        return 9

    def CloseDesktop(self, *_):
        return 1

    def GetUserObjectInformationW(self, _, __, name, *___):
        name.value = self.desktop
        return 1

    def GetForegroundWindow(self):
        return self.target

    def WindowFromPoint(self, point):
        return 301

    def GetAncestor(self, window, flag):
        return self.recipient

    def SendInput(self, count, events, size):
        assert count == 1 and size == ctypes.sizeof(Input)
        event = events[0]
        fields = (
            (event.keyboard.scan, event.keyboard.flags)
            if event.type == 1
            else (event.mouse.data, event.mouse.flags)
        )
        if fields == self.refuse:
            return 0
        self.events.append((event.type, *fields))
        self.after_input()
        return 1

    def GetWindowThreadProcessId(self, *_):
        return 9

    def GetKeyboardLayout(self, thread):
        assert thread == 9
        return 0x409

    def MapVirtualKeyExW(self, vk, mode, layout):
        assert layout == 0x409
        return self.MapVirtualKeyW(vk, mode)

    def MapVirtualKeyW(self, vk, _):
        return vk

    def SetThreadDpiAwarenessContext(self, value):
        self.contexts.append(value)
        return 42

    def GetSystemMetrics(self, index):
        return {0: 1000, 1: 800, 76: -100, 77: 0, 78: 1100, 79: 800}[index]

    def SetCursorPos(self, x, y):
        self.position = (x, y)
        return 1

    def GetCursorPos(self, pointer):
        pointer._obj.x, pointer._obj.y = self.position
        return 1


def native():
    api = FakeAPI()
    gui = WindowsInput(api, api)
    gui.FAILSAFE = False
    return api, gui


@pytest.mark.parametrize(
    "operation,value",
    [("type", "Z"), ("press", "backspace"), ("hotkey", "ctrl+a")],
)
def test_legacy_keyboard_cannot_bypass_observed_input_context(operation, value):
    api, gui = native()
    gui.window_rect = lambda _: (0, 0, 100, 100)
    observation = Observation(
        "owned",
        Frame(Image.new("RGB", (100, 100)), foreground_window=100),
        (),
    )
    command = ActionCandidate(
        id="keyboard",
        observation_id=observation.id,
        operation=operation,
        value=value,
        description="Owned keyboard input",
    )
    result = DesktopAction(gui).execute(command, observation, Event())
    assert not result.ok
    assert api.events == []


@pytest.mark.parametrize(
    "command",
    [
        {"kind": "text", "text": "Z"},
        {"kind": "key", "key": "a"},
        {"kind": "chord", "modifiers": ["ctrl"], "key": "a"},
        {
            "kind": "gesture",
            "button": "middle",
            "modifiers": ["shift"],
            "points": [[0.2, 0.2], [0.3, 0.3]],
            "surface": [0.1, 0.1, 0.9, 0.9],
            "duration": 0.05,
        },
    ],
)
@pytest.mark.parametrize("missing", ["context", "guard"])
def test_native_keyboard_refuses_missing_observation_authority(monkeypatch, command, missing):
    from clef_use.input_ir import InputContext, InputExecutor

    api, gui = native()
    gui.window_rect = lambda _: (0, 0, 100, 100)
    gui.unowned_input = lambda *_: False
    adapter = DesktopAction(gui)
    executor = adapter.input_executor = InputExecutor(gui, adapter.keys, adapter.buttons)
    monkeypatch.setattr(executor, "_arm", lambda *args: None)
    context = InputContext(text_focus=False, ime_composing=False)
    frame = Frame(Image.new("RGB", (100, 100)), foreground_window=100)
    result = adapter.execute_input(
        command,
        frame,
        Event(),
        context=None if missing == "context" else context,
        context_guard=None if missing == "guard" else lambda: True,
    )
    assert not result.ok
    assert api.events == []


def test_owned_keyboard_release_remains_independent_of_focus_and_context():
    from clef_use.input_ir import InputExecutor, KeyInput

    api, gui = native()
    gui.keyDown("shift", target=100)
    adapter = DesktopAction(gui)
    executor = adapter.input_executor = InputExecutor(gui, adapter.keys, adapter.buttons)
    adapter.keys.add("shift")
    executor.owned.append(("key", "shift"))
    api.target = 200
    frame = Frame(Image.new("RGB", (100, 100)), foreground_window=100)
    result = adapter.execute_input(KeyInput(key="shift", phase="up"), frame, Event())
    assert result.ok
    assert api.events[-1] == (1, 0x10, 0xA)
    assert not adapter.keys and not executor.owned


@pytest.mark.parametrize("text_focus", [None, False])
def test_native_literal_cannot_type_without_verified_text_focus(monkeypatch, text_focus):
    from clef_use.input_ir import InputContext, InputExecutor, TextInput

    api, gui = native()
    gui.window_rect = lambda _: (0, 0, 100, 100)
    gui.unowned_input = lambda *_: False
    adapter = DesktopAction(gui)
    executor = adapter.input_executor = InputExecutor(gui, adapter.keys, adapter.buttons)
    monkeypatch.setattr(executor, "_arm", lambda *args: None)
    frame = Frame(Image.new("RGB", (100, 100)), foreground_window=100)
    result = adapter.execute_input(
        TextInput(text="Z"),
        frame,
        Event(),
        context=InputContext(ime_composing=False, text_focus=text_focus),
        context_guard=lambda: True,
    )
    assert not result.ok
    assert api.events == []


@pytest.mark.parametrize("identity", [(222, 9), (223, 9), (222, 10), (0, 9), (222, 0)])
def test_post_submit_recipient_checks_original_native_process_and_thread(identity):
    api, gui = native()
    gui.window_rect = lambda _: (0, 0, 100, 100)

    def owner(window, output):
        assert window == 100
        output._obj.value = identity[0]
        return identity[1]

    api.GetWindowThreadProcessId = owner
    frame = Frame(
        Image.new("RGB", (100, 100)), foreground_window=100, foreground_bounds=(0, 0, 100, 100)
    )
    control = {"window": 100, "process": 222, "thread": 9}
    if 0 in identity:
        with pytest.raises(WindowsDesktopUnavailable, match="process identity unavailable"):
            DesktopAction(gui).input_recipient_matches(frame, control)
    else:
        assert DesktopAction(gui).input_recipient_matches(frame, control) is (identity == (222, 9))
    assert api.events == []


@pytest.mark.parametrize("point", [(0, 0), (999, 0), (0, 799), (999, 799)])
def test_native_corner_failsafe_refuses_input(point):
    api, gui = native()
    api.position, gui.FAILSAFE = point, True
    with pytest.raises(WindowsInputFailsafe):
        gui.keyDown("a", target=100)
    assert not api.events and not gui.key_events


def test_native_corner_failsafe_accepts_adjacent_pixel_and_fails_closed_on_unreadable_cursor():
    api, gui = native()
    api.position, gui.FAILSAFE = (1, 0), True
    gui.keyDown("a", target=100)
    gui.keyUp("a")
    assert len(api.events) == 2 and not gui.key_events
    api.events.clear()
    api.GetCursorPos = lambda pointer: 0
    with pytest.raises(WindowsDesktopUnavailable, match="cursor"):
        gui.keyDown("a", target=100)
    assert not api.events and not gui.key_events


def test_window_geometry_is_physical_on_a_fresh_watchdog_thread_and_restores_its_context():
    api, gui = native()
    dpi = local()

    def context(value):
        previous = getattr(dpi, "value", 42)
        dpi.value = value.value if isinstance(value, ctypes.c_void_p) else value
        return previous

    def rectangle(target, pointer):
        extent = 200 if getattr(dpi, "value", 42) == ctypes.c_void_p(-4).value else 100
        pointer._obj.left = pointer._obj.top = 0
        pointer._obj.right = pointer._obj.bottom = extent
        return 1

    api.SetThreadDpiAwarenessContext = context
    api.GetWindowRect = rectangle
    results = []

    def watchdog():
        results.append((gui.window_rect(100), getattr(dpi, "value", 42)))

    thread = Thread(target=watchdog)
    thread.start()
    thread.join(timeout=1)
    assert not thread.is_alive()
    assert results == [((0, 0, 200, 200), 42)]


@pytest.mark.parametrize("operation", ["left", "right", "middle", "wheel", "horizontal_wheel"])
def test_pointer_recipient_outside_bound_window_is_refused_before_os_input(operation):
    api, gui = native()
    api.recipient = 200  # Foreground still matches; recipient ownership differs.
    with pytest.raises(RuntimeError, match="pointer recipient"):
        if operation == "wheel":
            gui.scroll(1, target=100)
        elif operation == "horizontal_wheel":
            gui.hscroll(1, target=100)
        else:
            gui.mouseDown(operation, target=100)
    assert not api.events


def test_pointer_recovery_release_remains_available_outside_bound_window():
    api, gui = native()
    gui.mouseDown("middle", target=100)
    api.recipient = api.target = 200
    gui.mouseUp("middle")
    assert [flags for _, _, flags in api.events] == [32, 64]


def test_windows_input_abi_and_unicode_surrogate_pairs():
    assert ctypes.sizeof(Input) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
    api, gui = native()
    gui.type_text("한😀", Event())
    encoded = "한😀".encode("utf-16-le")
    units = [int.from_bytes(encoded[i : i + 2], "little") for i in range(0, len(encoded), 2)]
    assert api.events == [(1, unit, flag) for unit in units for flag in (4, 6)]
    assert gui.unicode_units == set()


@pytest.mark.parametrize(
    "session,desktop,reason", [(0, "Default", "session 0"), (1, "Winlogon", "secure")]
)
def test_service_and_secure_desktop_refuse_input(session, desktop, reason):
    api, gui = native()
    api.session, api.desktop = session, desktop
    with pytest.raises(RuntimeError, match=reason):
        gui.type_text("a", Event())
    assert api.events == []


def test_refused_sendinput_is_error_and_failed_unicode_release_can_retry():
    api, gui = native()
    api.refuse = (ord("a"), 4)
    with pytest.raises(RuntimeError, match="SendInput"):
        gui.type_text("a", Event())
    assert gui.unicode_units == set()
    api.refuse = (ord("b"), 6)
    with pytest.raises(RuntimeError, match="SendInput"):
        gui.type_text("b", Event())
    assert gui.unicode_units == {ord("b")}
    api.refuse = None
    gui.release_text()
    assert gui.unicode_units == set()


def test_cancel_or_focus_change_during_text_sends_no_later_character():
    for change_focus in (False, True):
        api, gui = native()
        cancelled = Event()

        def interrupt(change_focus=change_focus, api=api, cancelled=cancelled):
            if change_focus:
                api.target = 200
            else:
                cancelled.set()

        api.after_input = interrupt
        if change_focus:
            with pytest.raises(RuntimeError, match="foreground changed"):
                gui.type_text("ab", cancelled)
        else:
            gui.type_text("ab", cancelled)
        assert api.events == [(1, ord("a"), 4), (1, ord("a"), 6)]
        assert not gui.unicode_units


@pytest.mark.parametrize("change", ["context", "geometry", "human_input", "deadline"])
@pytest.mark.parametrize("text", ["abc", "한😀b"])
def test_typed_unicode_rechecks_each_native_unit_before_later_text(monkeypatch, change, text):
    from clef_use import input_ir
    from clef_use.input_ir import InputContext, InputExecutor, TextInput

    api, gui = native()
    now = [100.0]
    safe = [True]
    bounds = [0, 0, 100, 100]
    human_held = set()
    api.GetAsyncKeyState = lambda vk: 0x8000 if vk in human_held else 0
    gui.window_rect = lambda _: tuple(bounds)
    adapter = DesktopAction(gui)
    executor = adapter.input_executor = InputExecutor(gui, adapter.keys, adapter.buttons)
    # Event-boundary checks must work independently of watchdog polling.
    monkeypatch.setattr(executor, "_arm", lambda *args: None)
    monkeypatch.setattr(input_ir, "time", SimpleNamespace(monotonic=lambda: now[0]))
    first_unit = ord(text[0])

    def interrupt():
        if api.events[-1] != (1, first_unit, 4):
            return
        if change == "context":
            safe[0] = False
        elif change == "geometry":
            bounds[2] = 90
        elif change == "human_input":
            human_held.add(0x10)
        else:
            now[0] = 102.0

    api.after_input = interrupt
    frame = Frame(
        Image.new("RGB", (100, 100)), foreground_window=100, foreground_bounds=(0, 0, 100, 100)
    )
    result = adapter.execute_input(
        TextInput(text=text),
        frame,
        Event(),
        context_guard=lambda: safe[0],
        deadline=101.0,
        context=InputContext(text_focus=True, ime_composing=False),
    )
    units = [scan for kind, scan, flags in api.events if kind == 1 and flags == 4]
    assert not result.ok
    assert units == [first_unit]
    assert not gui.unicode_units and not adapter.keys and not adapter.buttons
    assert human_held == ({0x10} if change == "human_input" else set())


def test_invalid_unicode_is_rejected_before_any_prefix_is_inserted():
    api, gui = native()
    with pytest.raises(UnicodeEncodeError):
        gui.type_text("a\ud800", Event())
    assert api.events == [] and not gui.unicode_units


def test_snapshot_target_change_refuses_action_and_control_characters():
    api, gui = native()
    action = DesktopAction(gui)
    observation = Observation("epoch", Frame(Image.new("RGB", (20, 20)), foreground_window=99), ())
    candidate = ActionCandidate(
        id="a", operation="scroll", value="down", description="input", observation_id="epoch"
    )
    with pytest.raises(RuntimeError, match="foreground changed"):
        action.execute(candidate, observation, Event())
    with pytest.raises(ValueError, match="control characters"):
        gui.type_text("a\n", Event())
    assert not api.events
    assert len(api.contexts) == 2


def test_physical_coordinates_restore_after_failure_and_reject_outside_desktop():
    api, gui = native()
    with pytest.raises(ValueError):
        with gui.physical_coordinates():
            gui.moveTo(1000, 0)
    assert len(api.contexts) == 2 and api.contexts[-1] == 42
    gui.moveTo(-50, 20)
    assert api.position == (-50, 20)


def test_foreground_change_in_failsafe_check_is_caught_before_injection():
    api, gui = native()
    gui._failsafe = lambda: setattr(api, "target", 200)
    with pytest.raises(RuntimeError, match="foreground changed"):
        gui.keyDown("enter", target=100)
    assert api.events == []


def test_doctor_reports_session_zero_without_injecting(monkeypatch):
    from clef_use.doctor import windows_desktop_probe

    api, gui = native()
    api.session = 0
    monkeypatch.setattr("clef_use.windows_input.WindowsInput", lambda: gui)
    result = windows_desktop_probe()
    assert result["status"] == "UNAVAILABLE" and "session 0" in result["reason"]
    assert api.events == []


def test_key_release_uses_original_scan_even_after_layout_mapping_changes():
    api, gui = native()
    gui.keyDown("ctrl")
    original = api.events[-1]
    api.MapVirtualKeyW = lambda *_: 0xE030
    gui.keyUp("ctrl")
    assert api.events[-1] == (original[0], original[1], original[2] | 2)
    assert gui.key_events == {}


@pytest.mark.parametrize(
    "key,owned_vk,scan,human_vk,human_scan",
    [
        ("left", 0x25, 0xE04B, 0x64, 0x4B),
        ("right", 0x27, 0xE04D, 0x66, 0x4D),
        ("up", 0x26, 0xE048, 0x68, 0x48),
        ("down", 0x28, 0xE050, 0x62, 0x50),
        ("home", 0x24, 0xE047, 0x67, 0x47),
        ("end", 0x23, 0xE04F, 0x61, 0x4F),
        ("insert", 0x2D, 0xE052, 0x60, 0x52),
        ("delete", 0x2E, 0xE053, 0x6E, 0x53),
        ("shift", 0x10, 0x2A, 0xA1, 0x36),
        ("ctrl", 0x11, 0x1D, 0xA3, 0xE01D),
        ("alt", 0x12, 0x38, 0xA5, 0xE038),
    ],
)
def test_unowned_distinct_key_is_not_hidden_by_owned_scan_or_modifier_alias(
    key, owned_vk, scan, human_vk, human_scan
):
    api, gui = native()
    held = {owned_vk}
    api.GetAsyncKeyState = lambda vk: 0x8000 if vk in held else 0
    api.MapVirtualKeyExW = lambda vk, *_: {owned_vk: scan, human_vk: human_scan}.get(vk, vk)
    gui.keyDown(key)
    assert not gui.unowned_input({key}, set())
    held.add(human_vk)
    assert gui.unowned_input({key}, set())
    gui.keyUp(key)
    assert api.events == [
        (1, scan & 0xFF, 9 if scan & 0xFF00 else 8),
        (1, scan & 0xFF, 11 if scan & 0xFF00 else 10),
    ]


def test_unmapped_virtual_key_ownership_does_not_hide_other_unmapped_keys():
    api, gui = native()
    held = {ord("A")}
    api.GetAsyncKeyState = lambda vk: 0x8000 if vk in held else 0
    api.MapVirtualKeyExW = lambda *_: 0
    gui.keyDown("a")
    assert not gui.unowned_input({"a"}, set())
    held.add(ord("B"))
    assert gui.unowned_input({"a"}, set())
    gui.keyUp("a")


@pytest.mark.parametrize(
    "key,generic,left,scan",
    [("shift", 0x10, 0xA0, 0x2A), ("ctrl", 0x11, 0xA2, 0x1D), ("alt", 0x12, 0xA4, 0x38)],
)
def test_owned_modifier_generic_and_left_reports_are_one_acknowledged_hold(
    key, generic, left, scan
):
    api, gui = native()
    api.GetAsyncKeyState = lambda vk: 0x8000 if vk in {generic, left} else 0
    api.MapVirtualKeyExW = lambda vk, *_: scan if vk in {generic, left} else vk
    gui.keyDown(key)
    assert not gui.unowned_input({key}, set())
    assert gui.unowned_input(set(), set())
    gui.keyUp(key)


@pytest.mark.parametrize(
    "key,generic,left,right",
    [("shift", 0x10, 0xA0, 0xA1), ("ctrl", 0x11, 0xA2, 0xA3), ("alt", 0x12, 0xA4, 0xA5)],
)
def test_virtual_modifier_fallback_accepts_own_left_alias_but_refuses_right(
    key, generic, left, right
):
    api, gui = native()
    held = {generic, left}
    api.GetAsyncKeyState = lambda vk: 0x8000 if vk in held else 0
    api.MapVirtualKeyExW = lambda *_: 0
    gui.keyDown(key)
    assert not gui.unowned_input({key}, set())
    held.add(right)
    assert gui.unowned_input({key}, set())
    gui.keyUp(key)


@pytest.mark.parametrize("missing", ["thread", "layout"])
def test_held_input_with_unavailable_keyboard_layout_fails_closed(missing):
    api, gui = native()
    api.GetAsyncKeyState = lambda vk: 0x8000 if vk == ord("A") else 0
    if missing == "thread":
        api.GetWindowThreadProcessId = lambda *_: 0
    api.GetKeyboardLayout = lambda _: 0 if missing == "layout" else 0x409
    with pytest.raises(RuntimeError, match="keyboard layout unavailable"):
        gui.unowned_input(set(), set())
    assert api.events == []


@pytest.mark.parametrize("interrupt", [None, "cancel", "focus", "geometry"])
def test_native_stroke_rechecks_foreground_and_releases_input(interrupt):
    from clef_use.candidates import CandidateBuilder

    api, gui = native()
    bounds = [0, 0, 100, 100]
    gui.window_rect = lambda target: tuple(bounds)
    frame = Frame(
        Image.new("RGB", (100, 100), "white"),
        foreground_window=100,
        foreground_bounds=tuple(bounds),
    )
    observation = Observation("epoch", frame, ())
    contract = Contract(
        goal="Draw within the captured foreground",
        pointer_inputs=[
            {
                "operation": "stroke",
                "label": "Inspected canvas path",
                "reference": frame.reference().model_dump(mode="json"),
                "surface": {"x1": 0.1, "y1": 0.1, "x2": 0.9, "y2": 0.9},
                "points": [{"x": 0.2, "y": 0.4}, {"x": 0.5, "y": 0.4}, {"x": 0.8, "y": 0.4}],
                "duration": 0.05,
            }
        ],
    )
    candidate = CandidateBuilder().build(observation, contract)[0]
    cancelled = Event()

    def after_input():
        if interrupt == "cancel":
            cancelled.set()
        elif interrupt == "focus":
            api.target = 200
        elif interrupt == "geometry":
            bounds[2] = 90

    api.after_input = after_input
    adapter = DesktopAction(gui)
    if interrupt in {"focus", "geometry"}:
        with pytest.raises(RuntimeError, match="foreground"):
            adapter.execute(candidate, observation, cancelled)
    else:
        result = adapter.execute(candidate, observation, cancelled)
        assert result.ok == (interrupt is None)
    assert api.events == [(0, 0, 2), (0, 0, 4)]
    assert api.position == ((80, 40) if interrupt is None else (20, 40))
    assert not adapter.buttons and api.contexts[-1] == 42


def _native_pointer_action(operation):
    from clef_use.candidates import CandidateBuilder

    api, gui = native()
    bounds = [0, 0, 100, 100]
    gui.window_rect = lambda target: tuple(bounds)
    frame = Frame(
        Image.new("RGB", (100, 100), "white"),
        foreground_window=100,
        foreground_bounds=tuple(bounds),
    )
    observation = Observation("epoch", frame, ())
    points = [{"x": 0.2, "y": 0.4}]
    if operation == "stroke":
        points.append({"x": 0.8, "y": 0.4})
    contract = Contract(
        goal="Use the inspected foreground surface",
        pointer_inputs=[
            {
                "operation": operation,
                "label": "Inspected pointer input",
                "reference": frame.reference().model_dump(mode="json"),
                "surface": {"x1": 0.1, "y1": 0.1, "x2": 0.9, "y2": 0.9},
                "points": points,
                "duration": 0.05,
            }
        ],
    )
    candidate = CandidateBuilder().build(observation, contract)[0]
    return api, gui, bounds, observation, candidate


def test_native_double_click_refuses_second_press_after_foreground_switch():
    api, gui, _, observation, candidate = _native_pointer_action("double_click")
    adapter = DesktopAction(gui)
    pressed_windows = []

    def switch_after_first_press():
        if api.events[-1] == (0, 0, 2):
            pressed_windows.append(api.target)
            api.target = 101

    api.after_input = switch_after_first_press
    error = None
    try:
        adapter.execute(candidate, observation, Event())
    except WindowsForegroundChanged as exc:
        error = exc

    assert pressed_windows == [100]
    assert api.events == [(0, 0, 2), (0, 0, 4)]
    assert error is not None
    assert not adapter.buttons
    assert api.contexts[-1] == 42


@pytest.mark.parametrize("operation", ["click", "stroke"])
@pytest.mark.parametrize("interrupt", [None, "geometry", "focus", "cancel"])
def test_native_pointer_rechecks_after_initial_move(operation, interrupt):
    api, gui, bounds, observation, candidate = _native_pointer_action(operation)
    adapter = DesktopAction(gui)
    cancelled = Event()
    moves = []
    original_move = api.SetCursorPos

    def move(x, y):
        moves.append((x, y))
        result = original_move(x, y)
        if interrupt == "geometry":
            bounds[2] = 90
        elif interrupt == "focus":
            api.target = 200
        elif interrupt == "cancel":
            cancelled.set()
        return result

    api.SetCursorPos = move
    error = None
    result = None
    try:
        result = adapter.execute(candidate, observation, cancelled)
    except RuntimeError as exc:
        error = exc

    # A stable HWND is insufficient when moving the pointer changes its geometry.
    assert api.events == ([(0, 0, 2), (0, 0, 4)] if interrupt is None else [])
    if interrupt in {"geometry", "focus"}:
        assert error is not None and "foreground" in str(error)
    else:
        assert error is None and result.ok == (interrupt is None)
    if interrupt == "geometry":
        assert api.target == observation.frame.foreground_window == 100
    assert moves == (
        [(20, 40), (80, 40)] if operation == "stroke" and interrupt is None else [(20, 40)]
    )
    assert not adapter.buttons and api.contexts[-1] == 42


@pytest.mark.parametrize("operation", ["click", "stroke"])
@pytest.mark.parametrize("failure", ["down", "up"])
def test_native_pointer_sendinput_failure_preserves_cleanup(operation, failure):
    api, gui, _, observation, candidate = _native_pointer_action(operation)
    adapter = DesktopAction(gui)
    api.refuse = (0, 2 if failure == "down" else 4)
    with pytest.raises(RuntimeError, match="SendInput"):
        adapter.execute(candidate, observation, Event())
    assert api.events == ([] if failure == "down" else [(0, 0, 2)])
    assert adapter.buttons == (set() if failure == "down" else {"left"})
    assert api.contexts[-1] == 42
    api.refuse = None
    adapter.release()
    assert not adapter.buttons
    assert api.events == ([] if failure == "down" else [(0, 0, 2), (0, 0, 4)])
