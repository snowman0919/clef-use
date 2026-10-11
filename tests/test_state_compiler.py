import time

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


def test_geometry_does_not_promote_uncertain_grounding_to_verified_coordinates():
    frame = observation().frame
    target = UIObject(
        id="candidate", bbox=BoundingBox(x1=0.1, y1=0.1, x2=0.2, y2=0.2), confidence=0.4
    )
    state = StateCompiler().compile(Observation("uncertain", frame, (target,)))
    assert state.fact("target_geometry").uncertainty == 0.6
