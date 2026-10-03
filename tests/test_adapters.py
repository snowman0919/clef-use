import io
import queue
from threading import Event
from types import SimpleNamespace

import pytest

from clef_use.backends import DesktopAction, JsonWorker
from clef_use.config import Config


class FailingGui:
    FAILSAFE = True

    def __init__(self, fail):
        self.fail = fail
        self.released = []

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
