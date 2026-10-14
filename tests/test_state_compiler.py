import time

import pytest
from PIL import Image

from clef_use.schema import BoundingBox, Frame, Observation, UIObject
from clef_use.state import FactValidity, StateCompiler, StateFact, StateSource


def observation():
    return Observation("frame-1", Frame(Image.new("RGB", (100, 80))), ())


def test_pixels_do_not_fabricate_application_facts_and_unknown_differs_from_false():
    compiler = StateCompiler()
    state = compiler.compile(observation())
    assert state.fact("text_focus").value is None
    assert state.fact("text_focus").validity == FactValidity.UNKNOWN
    assert state.access_level == "PIXELS_ONLY"
    evidence = {
        "text_focus": StateFact(
            value=False,
            source=StateSource.APP_TELEMETRY,
            observed_at=time.time(),
            state_version=state.version + 1,
            validity=FactValidity.VALID,
            uncertainty=0,
        )
    }
    fresh = compiler.compile(observation(), evidence)
    assert fresh.require("text_focus") is False
    assert fresh.access_level == "APP_TELEMETRY_ASSISTED"


def test_old_or_wrong_version_evidence_cannot_become_current_truth():
    compiler = StateCompiler(max_age_seconds=1)
    stale = StateFact(
        value="OBJECT",
        source=StateSource.APP_TELEMETRY,
        observed_at=time.time() - 5,
        state_version=1,
        validity=FactValidity.VALID,
        uncertainty=0,
    )
    state = compiler.compile(observation(), {"mode": stale})
    assert state.fact("mode").validity == FactValidity.STALE
    assert state.fact("mode").observed_at == stale.observed_at
    assert state.fact("mode").state_version == 1
    wrong = stale.model_copy(update={"observed_at": time.time(), "state_version": 1})
    second = compiler.compile(observation(), {"mode": wrong})
    assert second.fact("mode").validity == FactValidity.STALE


def test_view_change_invalidates_geometry_until_new_observation():
    state = StateCompiler().compile(observation())
    invalid = state.invalidate_geometry()
    assert invalid.fact("target_geometry").validity == FactValidity.INVALIDATED
    assert state.fact("target_geometry").validity == FactValidity.VALID


def test_processing_delay_expires_state_without_promoting_unknown_facts(monkeypatch):
    import clef_use.state as module

    state = StateCompiler().compile(observation())
    monkeypatch.setattr(module.time, "time", lambda: state.compiled_at + 2)
    expired = state.expire(1)
    assert expired.fact("target_geometry").validity == FactValidity.STALE
    assert expired.fact("text_focus").validity == FactValidity.UNKNOWN
    assert state.fact("target_geometry").validity == FactValidity.VALID


def test_geometry_does_not_promote_uncertain_grounding_to_verified_coordinates():
    frame = observation().frame
    target = UIObject(
        id="candidate", bbox=BoundingBox(x1=0.1, y1=0.1, x2=0.2, y2=0.2), confidence=0.4
    )
    state = StateCompiler().compile(Observation("uncertain", frame, (target,)))
    assert state.fact("target_geometry").uncertainty == 0.6


@pytest.mark.parametrize("delay,valid", [(0, True), (1, True), (1.0001, False), (-0.001, False)])
def test_capture_facts_keep_their_age_across_compilation(monkeypatch, delay, valid):
    clock = [1000.0]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    frame = Frame(Image.new("RGB", (100, 80)), foreground_window=42)
    clock[0] += delay
    state = StateCompiler(max_age_seconds=1).compile(Observation("delayed", frame, ()))
    for name in ("target_geometry", "window", "foreground"):
        fact = state.fact(name)
        assert fact.observed_at == 1000.0
        assert fact.validity == (FactValidity.VALID if valid else FactValidity.STALE)
    assert state.fact("text_focus").validity == FactValidity.UNKNOWN


def test_current_provider_evidence_does_not_renew_an_older_capture(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    frame = Frame(Image.new("RGB", (100, 80)), foreground_window=42)
    clock[0] = 1002.0
    evidence = StateFact(
        value="OBJECT",
        source=StateSource.APP_TELEMETRY,
        observed_at=clock[0],
        state_version=1,
        validity=FactValidity.VALID,
        uncertainty=0,
    )
    state = StateCompiler().compile(Observation("delayed", frame, ()), {"mode": evidence})
    assert state.require("mode") == "OBJECT"
    assert state.fact("target_geometry").validity == FactValidity.STALE
    assert state.fact("foreground").validity == FactValidity.STALE
    assert state.fact("mode").observed_at == 1002.0
