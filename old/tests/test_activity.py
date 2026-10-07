import contextlib
import json
import queue
from types import SimpleNamespace

import pytest

from clef_use.activity import ActivityOverlay
from clef_use.benchmark import fixture_runtime
from clef_use.runtime import Session
from clef_use.schema import Contract, SessionResult


class RecordingDisplay:
    def __init__(self):
        self.phases = []
        self.hidden = False
        self.captures = 0
        self.terminal = None

    def update(self, phase, session, point=None, target=None):
        self.phases.append((phase, point, target))

    @contextlib.contextmanager
    def capture(self, backend=None):
        assert not self.hidden
        self.hidden = True
        self.captures += 1
        try:
            yield
        finally:
            self.hidden = False

    def finish(self, session):
        self.terminal = session.status


def test_canonical_loop_reports_real_phases_and_excludes_display_from_every_capture():
    runtime = fixture_runtime()
    display = runtime.activity = RecordingDisplay()
    original = runtime.capture.capture

    def capture():
        assert display.hidden
        return original()

    runtime.capture.capture = capture
    session = Session(Contract(goal="Apply font size 16"))
    result = runtime.execute(session)
    assert result["status"] == "COMPLETED"
    phases = [phase for phase, _, _ in display.phases]
    for phase in (
        "Reading screen",
        "Finding controls",
        "Choosing next action",
        "Checking target",
        "Click",
        "Checking result",
    ):
        assert phase in phases
    actions = [(point, target) for phase, point, target in display.phases if phase == "Click"]
    assert len(actions) == session.steps == 2
    assert all(point is not None and target for point, target in actions)
    assert display.captures > session.rounds
    assert display.terminal == "COMPLETED"
    assert SessionResult.model_validate(result).activity.phase == "Completed"
    runtime.observe(session)
    assert not display.hidden


def test_capture_barrier_restores_display_when_capture_raises(monkeypatch):
    overlay = ActivityOverlay()
    messages = []
    monkeypatch.setattr(overlay, "_send", messages.append)
    with pytest.raises(RuntimeError, match="capture unavailable"), overlay.capture():
        assert messages == ["hide"]
        raise RuntimeError("capture unavailable")
    assert messages == ["hide", "show"]


def test_native_exclusion_preserves_visible_display_and_clears_on_failure(monkeypatch):
    overlay = ActivityOverlay()
    overlay.windows = [123, 456]
    overlay.capture_excluded = True
    messages = []
    monkeypatch.setattr(overlay, "_send", messages.append)

    class Capture:
        native_overlay_exclusion = True
        excluded = []

        @contextlib.contextmanager
        def excluding_windows(self, windows):
            self.excluded = windows
            try:
                yield
            finally:
                self.excluded = []

    capture = Capture()
    with pytest.raises(RuntimeError), overlay.capture(capture):
        assert capture.excluded == [123, 456]
        raise RuntimeError("capture failed")
    assert capture.excluded == []
    assert messages == []


def test_missing_ack_removes_display_before_capture(monkeypatch):
    overlay = ActivityOverlay()
    messages = []
    monkeypatch.setattr(overlay, "_start", lambda: None)
    overlay.process = SimpleNamespace(
        stdin=SimpleNamespace(
            write=lambda message: messages.append(json.loads(message)), flush=lambda: None
        )
    )

    def no_reply(*args, **kwargs):
        raise queue.Empty

    monkeypatch.setattr(overlay.responses, "get", no_reply)

    def stop():
        overlay.process = None
        overlay.enabled = False
        messages.append("removed")

    monkeypatch.setattr(overlay, "_stop", stop)
    with overlay.capture():
        assert messages[-1] == "removed"
        assert not overlay.enabled
    assert messages[0]["op"] == "hide"


def test_private_action_payload_does_not_enter_display_or_status():
    runtime = fixture_runtime()
    display = runtime.activity = RecordingDisplay()
    session = Session(Contract(goal="Apply size 16", text_inputs=[{"value": "private-secret"}]))
    runtime.execute(session)
    assert "private-secret" not in json.dumps(display.phases)
    assert "private-secret" not in json.dumps(session.snapshot())
