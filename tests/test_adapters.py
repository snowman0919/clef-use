import io
import queue
import sys
from threading import Event
from types import SimpleNamespace

import pytest
from PIL import Image

from clef_use.backends import DesktopAction, DesktopCapture, JsonWorker
from clef_use.config import Config
from clef_use.schema import ActionCandidate, Frame, Observation, PointerPoint


@pytest.mark.parametrize(
    "platform,image_size,input_size,origin,expected",
    [
        ("linux", (800, 600), (1600, 600), (0, 0), (320, 300)),
        ("linux", (800, 600), (1600, 600), (-800, 30), (-480, 330)),
        ("darwin", (1600, 1200), (800, 600), (0, 0), (320, 300)),
    ],
)
def test_capture_maps_points_with_monitor_extent_and_preserves_retina(
    monkeypatch, platform, image_size, input_size, origin, expected
):
    import clef_use.backends as backends

    image = Image.new("RGB", image_size)

    class Screen:
        monitors = [None, {"left": origin[0], "top": origin[1]}]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def grab(self, _):
            return SimpleNamespace(size=image.size, rgb=image.tobytes())

    monkeypatch.setattr(backends, "sys", SimpleNamespace(platform=platform))
    monkeypatch.setitem(sys.modules, "mss", SimpleNamespace(MSS=Screen))
    monkeypatch.setitem(sys.modules, "pyautogui", SimpleNamespace(size=lambda: input_size))
    monkeypatch.setattr(DesktopCapture, "_x11_context", staticmethod(lambda: (None, None)))
    frame = DesktopCapture().capture()
    assert frame.pointer_point(PointerPoint(x=0.4, y=0.5)) == expected


def test_capture_latency_cannot_renew_the_native_context(monkeypatch):
    import clef_use.backends as backends
    from clef_use.state import FactValidity, StateCompiler

    clock = [1000.0]
    image = Image.new("RGB", (100, 80))

    class Screen:
        monitors = [None, {"left": 0, "top": 0}]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def grab(self, _):
            clock[0] += 2
            return SimpleNamespace(size=image.size, rgb=image.tobytes())

    monkeypatch.setattr(backends.time, "time", lambda: clock[0])
    monkeypatch.setattr(backends, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setitem(sys.modules, "mss", SimpleNamespace(MSS=Screen))
    monkeypatch.setattr(DesktopCapture, "_x11_context", staticmethod(lambda: (42, (0, 0, 100, 80))))
    frame = DesktopCapture().capture()
    state = StateCompiler().compile(Observation("slow-capture", frame, ()))
    assert frame.captured_at == 1000.0
    assert state.fact("target_geometry").validity == FactValidity.STALE
    assert state.fact("window").validity == FactValidity.STALE
    assert state.fact("foreground").validity == FactValidity.STALE


class FailingGui:
    FAILSAFE = True

    def __init__(self, fail):
        self.fail = fail
        self.held = {fail} if fail else set()
        self.released = []
        self.platformModule = SimpleNamespace(keyboardMapping={"a": 65, "A": 0x141, "@": 0x640})

    def moveTo(self, *_):
        pass

    def mouseDown(self, **_):
        raise RuntimeError("failed without native acknowledgement")

    def mouseUp(self, button):
        assert not self.FAILSAFE
        self.released.append(button)
        self.held.discard(button)

    def keyDown(self, key):
        if key == self.fail:
            raise RuntimeError("failed without native acknowledgement")
        self.held.add(key)

    def keyUp(self, key):
        assert not self.FAILSAFE
        self.released.append(key)
        self.held.discard(key)

    def isShiftCharacter(self, key):
        return key.isupper() or key in "@!"

    def press(self, key):
        self.keyDown(key)
        self.keyUp(key)

    def write(self, key):
        self.press(key)


@pytest.mark.parametrize("operation,value", [("press", "enter"), ("type", "a")])
def test_plain_key_failure_preserves_unacknowledged_existing_input(monkeypatch, operation, value):
    gui = FailingGui(value)
    monkeypatch.setitem(sys.modules, "pyautogui", gui)
    action = DesktopAction(gui=gui)
    observation = Observation("epoch", Frame(Image.new("RGB", (20, 20))), [])
    candidate = ActionCandidate(
        id="a0", operation=operation, value=value, description="input", observation_id="epoch"
    )
    with pytest.raises(RuntimeError):
        action.execute(candidate, observation, Event())
    assert gui.held == {value}
    assert not action.keys and gui.FAILSAFE


@pytest.mark.parametrize(
    "platform,key",
    [
        ("darwin", "A"),
        ("linux", "A"),
        ("win32", "@"),
    ],
)
def test_failed_implicit_key_is_not_adopted_as_owned(monkeypatch, platform, key):
    import clef_use.backends as backends

    monkeypatch.setattr(backends, "sys", SimpleNamespace(platform=platform))
    gui, action = FailingGui(key), DesktopAction()
    with pytest.raises(RuntimeError):
        action._hotkey(gui, (key,), Event())
    assert gui.held == {key}
    assert not action.keys and gui.FAILSAFE


def test_cleanup_attempts_every_input_and_retains_failed_release_for_retry():
    class ReleaseFailure(FailingGui):
        def keyUp(self, key):
            if key == "ctrl" and self.fail:
                self.fail = None
                raise RuntimeError("release failed")
            super().keyUp(key)

    gui, action = ReleaseFailure("ctrl"), DesktopAction()
    action.keys.update({"ctrl", "a"})
    action.buttons.add("left")
    with pytest.raises(RuntimeError):
        action._release_with(gui)
    assert set(gui.released) == {"a", "left"}
    assert action.keys == {"ctrl"} and not action.buttons and gui.FAILSAFE
    action._release_with(gui)
    assert not action.keys and gui.FAILSAFE


def test_cancelled_hotkey_releases_first_key_and_never_presses_second():
    cancelled = Event()

    class CancelAfterPress(FailingGui):
        def keyDown(self, key):
            assert key == "ctrl"
            cancelled.set()

    action, gui = DesktopAction(), CancelAfterPress(None)
    action._hotkey(gui, ("ctrl", "a"), cancelled)
    assert gui.released == ["ctrl"]
    assert not action.keys and gui.FAILSAFE


def test_mouse_exception_preserves_unacknowledged_input_and_restores_failsafe():
    action, gui = DesktopAction(), FailingGui("left")
    with pytest.raises(RuntimeError):
        action._click(gui, 100, 200, 1, Event())
    assert gui.held == {"left"}
    assert not action.buttons and gui.FAILSAFE


def test_hotkey_exception_releases_all_pressed_keys():
    action, gui = DesktopAction(), FailingGui("a")
    with pytest.raises(RuntimeError):
        action._hotkey(gui, ("ctrl", "a"), Event())
    assert gui.held == {"a"}
    assert not action.keys and gui.FAILSAFE


def test_old_worker_eof_cannot_poison_new_worker_queue():
    worker = JsonWorker(None, "omni", Config())
    old_queue = queue.Queue()
    worker.replies = queue.Queue()
    worker._reader(SimpleNamespace(stdout=io.StringIO('{"old":true}\n')), old_queue)
    assert old_queue.get_nowait() == {"old": True}
    assert old_queue.get_nowait() == {"error": "worker disconnected"}
    assert worker.replies.empty()
