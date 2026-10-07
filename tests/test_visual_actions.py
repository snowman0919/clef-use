from threading import Event

import pytest
from PIL import Image, ImageDraw

from clef_use.backends import DesktopAction
from clef_use.candidates import CandidateBuilder
from clef_use.schema import BoundingBox, Contract, Frame, Observation, PointerInput, PointerPoint


class CanvasDevice:
    FAILSAFE = True

    def __init__(self):
        self.image = Image.new("RGB", (100, 100), "white")
        self.position = (0, 0)
        self.held = False

    def moveTo(self, x, y, **kwargs):
        if self.held:
            ImageDraw.Draw(self.image).line([self.position, (x, y)], fill="black", width=2)
        self.position = (x, y)

    def mouseDown(self, button):
        self.held = True

    def mouseUp(self, button):
        self.held = False


def candidate(frame, operation, points):
    pointer = PointerInput(
        operation=operation,
        label="canvas",
        reference=frame.reference(),
        surface=BoundingBox(x1=0.1, y1=0.1, x2=0.9, y2=0.9),
        points=tuple(PointerPoint(x=x, y=y) for x, y in points),
        duration=0.05,
    )
    observation = Observation("current", frame, ())
    action = CandidateBuilder().build(observation, Contract(goal="draw", pointer_inputs=[pointer]))[
        0
    ]
    return action, observation


def test_drag_changes_entire_segment_and_releases():
    device = CanvasDevice()
    action, obs = candidate(Frame(device.image.copy()), "drag", [(0.2, 0.4), (0.8, 0.4)])
    result = DesktopAction(gui=device).execute(action, obs, Event())
    assert result.ok
    assert device.image.getpixel((50, 40)) == (0, 0, 0)
    assert device.image.getpixel((50, 60)) == (255, 255, 255)
    assert not device.held


def test_move_preserves_canvas_and_never_holds_button():
    device = CanvasDevice()
    action, obs = candidate(Frame(device.image.copy()), "move", [(0.6, 0.4)])
    assert DesktopAction(gui=device).execute(action, obs, Event()).ok
    assert device.position == (60, 40)
    assert device.image.getpixel((30, 20)) == (255, 255, 255)
    assert not device.held


@pytest.mark.parametrize("operation", ["move", "drag"])
def test_unscoped_pointer_operation_is_refused(operation):
    from clef_use.schema import ActionCandidate

    device = CanvasDevice()
    obs = Observation("current", Frame(device.image.copy()), ())
    action = ActionCandidate(
        id="unscoped", operation=operation, observation_id=obs.id, description="unscoped"
    )
    assert not DesktopAction(gui=device).execute(action, obs, Event()).ok
    assert device.position == (0, 0)
