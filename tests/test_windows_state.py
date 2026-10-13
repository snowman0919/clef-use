import time

import pytest
from PIL import Image

from clef_use.schema import Frame, Observation
from clef_use.state import FactValidity, StateCompiler
from clef_use.windows_state import WindowsStateProvider, focus_evidence


def native_sample(composing=False):
    now = time.time()
    identity = {"hwnd": 123, "pid": 456, "tid": 789, "bounds": [0, 0, 100, 100]}
    observation = Observation(
        "owned",
        Frame(
            Image.new("RGB", (100, 100)),
            captured_at=now,
            foreground_window=123,
            foreground_bounds=(0, 0, 100, 100),
        ),
        (),
    )
    sample = {
        "status": "VALID",
        "cleanup_errors": [],
        "observed_at": now,
        "acquisition_seconds": 0.01,
        "native_before": identity.copy(),
        "native_after": identity.copy(),
        "pattern_supported": True,
        "text_focus": True,
        "ime_composing": composing,
        "composition": {"hresult": "0x00000000", "range_present": composing},
    }
    return observation, sample


@pytest.mark.parametrize("composing", [False, True])
def test_bound_supported_composition_compiles_without_inventing_other_app_facts(composing):
    observation, sample = native_sample(composing)
    state = StateCompiler().compile(observation, focus_evidence(observation, 1, sample))
    assert state.require("text_focus") is True
    assert state.require("ime_composing") is composing
    assert state.access_level == "ACCESSIBILITY_ASSISTED"
    for name in ("popup", "modal", "loading", "keymap", "editor", "unit", "menus"):
        assert state.fact(name).validity == FactValidity.UNKNOWN


@pytest.mark.parametrize(
    "change",
    [
        "stale",
        "future",
        "slow",
        "wrong_window",
        "changed_focus_window",
        "wrong_bounds",
        "unsupported",
        "cleanup",
        "unknown_focus",
    ],
)
def test_unbound_or_unavailable_focus_cannot_establish_ime_absence(change):
    observation, sample = native_sample()
    if change == "stale":
        sample["observed_at"] -= 1
    elif change == "future":
        sample["observed_at"] += 1
    elif change == "slow":
        sample["acquisition_seconds"] = 0.501
    elif change == "wrong_window":
        sample["native_before"]["hwnd"] = sample["native_after"]["hwnd"] = 999
    elif change == "changed_focus_window":
        sample["native_after"]["tid"] += 1
    elif change == "wrong_bounds":
        sample["native_before"]["bounds"] = sample["native_after"]["bounds"] = [0, 0, 99, 100]
    elif change == "unsupported":
        sample["pattern_supported"] = False
    elif change == "cleanup":
        sample["cleanup_errors"] = [{"operation": "VariantClear"}]
    elif change == "unknown_focus":
        sample["text_focus"] = None
    state = StateCompiler().compile(observation, focus_evidence(observation, 1, sample))
    assert state.fact("ime_composing").validity == FactValidity.UNKNOWN
    assert state.fact("text_focus").validity == FactValidity.UNKNOWN


@pytest.mark.parametrize(
    "status,hr,range_present",
    [
        ("PARTIAL", "0x80040204", False),
        ("VALID", "0x00000001", False),
        ("VALID", "0x00000000", True),
        ("VALID", "0x00000000", None),
    ],
)
def test_unsupported_error_or_inconsistent_composition_never_becomes_false(
    status, hr, range_present
):
    observation, sample = native_sample()
    sample["status"] = status
    sample["composition"] = {"hresult": hr, "range_present": range_present}
    state = StateCompiler().compile(observation, focus_evidence(observation, 1, sample))
    assert state.require("text_focus") is True
    assert state.fact("ime_composing").validity == FactValidity.UNKNOWN


def test_non_windows_provider_does_not_launch_a_worker_or_invent_state():
    import sys

    if sys.platform == "win32":
        pytest.skip("non-Windows admission boundary")
    observation, _ = native_sample()
    provider = WindowsStateProvider()
    try:
        state = StateCompiler().compile(observation, provider(observation, 1))
        assert state.fact("ime_composing").validity == FactValidity.UNKNOWN
        assert provider.process is None
        assert provider.status["status"] == "UNAVAILABLE"
    finally:
        provider.close()
