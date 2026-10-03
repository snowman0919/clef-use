import io
import queue
import sys
from threading import Event
from types import SimpleNamespace

import pytest
from PIL import Image

from clef_use.backends import DesktopAction, JsonWorker
from clef_use.config import Config
from clef_use.schema import ActionCandidate, Frame, Observation


class FailingGui:
    FAILSAFE = True

    def __init__(self, fail):
        self.fail = fail
        self.released = []
        self.platformModule = SimpleNamespace(keyboardMapping={"a": 65, "A": 0x141, "@": 0x640})

    def moveTo(self, *_):
        pass

    def mouseDown(self, **_):
        raise RuntimeError("failed after native press")

    def mouseUp(self, button):
        assert not self.FAILSAFE
        self.released.append(button)

    def keyDown(self, key):
        if key == self.fail:
            raise RuntimeError("failed after native press")

    def keyUp(self, key):
        assert not self.FAILSAFE
        self.released.append(key)

    def isShiftCharacter(self, key):
        return key.isupper() or key in "@!"

    def press(self, key):
        self.keyDown(key)
        self.keyUp(key)

    def write(self, key):
        self.press(key)


@pytest.mark.parametrize("operation,value", [("press", "enter"), ("type", "a")])
def test_plain_key_failure_releases_the_native_press(monkeypatch, operation, value):
    gui = FailingGui(value)
    monkeypatch.setitem(sys.modules, "pyautogui", gui)
    action = DesktopAction()
    observation = Observation("epoch", Frame(Image.new("RGB", (20, 20))), [])
    candidate = ActionCandidate(
        id="a0", operation=operation, value=value, description="input", observation_id="epoch"
    )
    with pytest.raises(RuntimeError):
        action.execute(candidate, observation, Event())
    assert value in gui.released
    assert not action.keys and gui.FAILSAFE


@pytest.mark.parametrize(
    "platform,key,expected",
    [
        ("darwin", "A", {"A", "shift"}),
        ("linux", "A", {"A", "shift"}),
        ("win32", "@", {"@", "shift", "ctrl", "alt"}),
    ],
)
def test_implicit_modifiers_are_released_after_native_failure(monkeypatch, platform, key, expected):
    import clef_use.backends as backends

    monkeypatch.setattr(backends, "sys", SimpleNamespace(platform=platform))
    gui, action = FailingGui(key), DesktopAction()
    with pytest.raises(RuntimeError):
        action._hotkey(gui, (key,), Event())
    assert set(gui.released) == expected
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


def test_mouse_exception_releases_owned_button_and_restores_failsafe():
    action, gui = DesktopAction(), FailingGui("left")
    with pytest.raises(RuntimeError):
        action._click(gui, 100, 200, 1, Event())
    assert gui.released == ["left"]
    assert not action.buttons and gui.FAILSAFE


def test_hotkey_exception_releases_all_pressed_keys():
    action, gui = DesktopAction(), FailingGui("a")
    with pytest.raises(RuntimeError):
        action._hotkey(gui, ("ctrl", "a"), Event())
    assert set(gui.released) == {"ctrl", "a"}
    assert not action.keys and gui.FAILSAFE


def test_old_worker_eof_cannot_poison_new_worker_queue():
    worker = JsonWorker(None, "omni", Config())
    old_queue = queue.Queue()
    worker.replies = queue.Queue()
    worker._reader(SimpleNamespace(stdout=io.StringIO('{"old":true}\n')), old_queue)
    assert old_queue.get_nowait() == {"old": True}
    assert old_queue.get_nowait() == {"error": "worker disconnected"}
    assert worker.replies.empty()
