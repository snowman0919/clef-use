import ctypes
from threading import Event

import pytest
from PIL import Image

from clef_use.backends import DesktopAction
from clef_use.schema import ActionCandidate, Contract, Frame, Observation
from clef_use.windows_input import Input, WindowsForegroundChanged, WindowsInput


class FakeAPI:
    def __init__(self):
        self.session = 1
        self.target = 100
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
        return {76: -100, 77: 0, 78: 1100, 79: 800}[index]

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


def test_snapshot_target_change_refuses_action_and_control_characters():
    api, gui = native()
    action = DesktopAction(gui)
    observation = Observation("epoch", Frame(Image.new("RGB", (20, 20)), foreground_window=99), ())
    candidate = ActionCandidate(
        id="a", operation="press", value="enter", description="input", observation_id="epoch"
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
    assert api.events == ([(0, 0, 4)] if failure == "down" else [(0, 0, 2)])
    assert adapter.buttons == (set() if failure == "down" else {"left"})
    assert api.contexts[-1] == 42
    api.refuse = None
    adapter.release()
    assert not adapter.buttons
    assert api.events[-1] == (0, 0, 4)
