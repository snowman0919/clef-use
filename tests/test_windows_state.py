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


def writable_sample():
    observation, sample = native_sample()

    def boolean(value):
        return {"hresult": "0x00000000", "vt": 11, "value": value}

    sample.update(
        focused_control={"runtime_id": [42, -7, 99], "bounds": [10, 10, 90, 90]},
        editable=True,
        editing={
            "enabled": boolean(True),
            "password": boolean(False),
            "text_pattern_hresult": "0x00000000",
            "text_pattern_present": True,
            "document_range_hresult": "0x00000000",
            "readonly": boolean(False),
        },
    )
    return observation, sample


def test_focused_writable_control_preserves_identity_and_exact_editability_evidence():
    observation, sample = writable_sample()
    facts = focus_evidence(observation, 1, sample)
    assert facts["focused_control"].value == {
        **sample["focused_control"],
        "window": 123,
        "process": 456,
        "thread": 789,
    }
    assert facts["text_editable"].value is True
    assert facts["ime_composing"].value is False
    state = StateCompiler().compile(observation, facts)
    assert state.require("focused_control") == facts["focused_control"].value
    assert state.require("text_editable") is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("runtime_id", []),
        ("runtime_id", [True]),
        ("runtime_id", [2**31]),
        ("runtime_id", list(range(65))),
        ("bounds", [0, 0, 101, 100]),
        ("bounds", [10, 10, 10, 20]),
        ("bounds", [10, 10, 90.0, 90]),
    ],
)
def test_unbound_focused_control_never_establishes_writability(field, value):
    observation, sample = writable_sample()
    sample["focused_control"][field] = value
    facts = focus_evidence(observation, 1, sample)
    assert "focused_control" not in facts and "text_editable" not in facts
    assert facts["ime_composing"].value is False


@pytest.mark.parametrize("change", ["unsupported", "mixed", "error", "missing", "contradictory"])
def test_unknown_editability_does_not_erase_valid_composition_evidence(change):
    observation, sample = writable_sample()
    if change == "unsupported":
        sample["editing"]["document_range_hresult"] = "0x80040200"
    elif change == "mixed":
        sample["editing"]["readonly"] = {"hresult": "0x00000000", "vt": 13}
    elif change == "error":
        sample["editing"]["readonly"]["hresult"] = "0x80004005"
    elif change == "missing":
        sample.pop("editing")
    else:
        sample["editing"]["readonly"]["value"] = True
    facts = focus_evidence(observation, 1, sample)
    assert "text_editable" not in facts
    assert facts["focused_control"].value == {
        **sample["focused_control"],
        "window": 123,
        "process": 456,
        "thread": 789,
    }
    assert facts["text_focus"].value is True and facts["ime_composing"].value is False


@pytest.mark.parametrize("blocked", ["readonly", "password", "enabled"])
def test_readonly_password_or_disabled_control_is_known_unwritable(blocked):
    observation, sample = writable_sample()
    sample["editing"][blocked]["value"] = blocked != "enabled"
    sample["editable"] = False
    facts = focus_evidence(observation, 1, sample)
    assert facts["text_editable"].value is False
    assert facts["ime_composing"].value is False


@pytest.mark.parametrize("change", ["stale", "focus_window", "cleanup"])
def test_stale_or_interrupted_acquisition_cannot_bind_focused_control(change):
    observation, sample = writable_sample()
    if change == "stale":
        sample["observed_at"] -= 1
    elif change == "focus_window":
        sample["native_after"]["tid"] += 1
    else:
        sample["cleanup_errors"] = [{"operation": "SafeArrayDestroy"}]
    assert focus_evidence(observation, 1, sample) == {}


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "hresult",
        "s_false",
        "null",
        "dimension",
        "type",
        "element_size",
        "lower",
        "upper",
        "empty",
        "large",
        "element",
        "cleanup",
    ],
)
def test_native_runtime_identity_decodes_only_bounded_integer_arrays_and_frees_them(
    monkeypatch, failure
):
    import ctypes as C
    from types import SimpleNamespace

    from clef_use import windows_uia as uia

    freed = []
    values = [42, -7, 99]

    def output(pointer, kind, value):
        C.cast(pointer, C.POINTER(kind)).contents.value = value
        return 0

    def get_identity(pointer):
        output(pointer, uia.HANDLE, 0 if failure == "null" else 1234)
        return -1 if failure == "hresult" else 1 if failure == "s_false" else 0

    def element(array, index, pointer):
        offset = C.cast(index, C.POINTER(C.c_int32)).contents.value - 2
        if failure == "element":
            return -1
        return output(pointer, C.c_int32, values[offset])

    def destroy(array):
        freed.append(array.value)
        return -1 if failure == "cleanup" else 0

    session = uia.Session.__new__(uia.Session)
    session.result = {"cleanup_errors": []}
    session.automation = SimpleNamespace(
        SafeArrayGetDim=lambda array: 2 if failure == "dimension" else 1,
        SafeArrayGetElemsize=lambda array: 8 if failure == "element_size" else 4,
        SafeArrayGetVartype=lambda array, pointer: output(
            pointer, C.c_uint16, 11 if failure == "type" else 3
        ),
        SafeArrayGetLBound=lambda array, dim, pointer: (
            -1 if failure == "lower" else output(pointer, C.c_int32, 2)
        ),
        SafeArrayGetUBound=lambda array, dim, pointer: (
            -1
            if failure == "upper"
            else output(
                pointer, C.c_int32, 1 if failure == "empty" else 66 if failure == "large" else 4
            )
        ),
        SafeArrayGetElement=element,
        SafeArrayDestroy=destroy,
    )
    monkeypatch.setattr(uia, "com_method", lambda *args: get_identity)
    if failure is None:
        assert session.runtime_id(88) == values
    else:
        with pytest.raises(uia.Unavailable):
            session.runtime_id(88)
    assert freed == ([] if failure == "null" else [1234])
    assert bool(session.result["cleanup_errors"]) is (failure == "cleanup")


@pytest.mark.parametrize(
    "enabled,password,readonly,vt,hr,document,expected",
    [
        (True, False, 0, 11, 0, 99, True),
        (True, False, -1, 11, 0, 99, False),
        (False, False, 0, 11, 0, 99, False),
        (True, True, 0, 11, 0, 99, False),
        (True, False, 0, 13, 0, 99, None),
        (True, False, 0, 11, -1, 99, None),
        (True, False, 2, 11, 0, 99, None),
        (None, False, 0, 11, 0, 99, None),
        (True, False, 0, 11, 0, None, None),
    ],
)
def test_native_editability_requires_explicit_boolean_readonly_evidence(
    monkeypatch, enabled, password, readonly, vt, hr, document, expected
):
    import ctypes as C
    from types import SimpleNamespace

    from clef_use import windows_uia as uia

    def attribute(identifier, pointer):
        value = C.cast(pointer, C.POINTER(uia.VARIANT)).contents
        value.tagged.vt, value.tagged.value.boolean = vt, readonly
        return hr

    session = uia.Session.__new__(uia.Session)
    session.result = {"cleanup_errors": []}
    session.automation = SimpleNamespace(VariantClear=lambda value: 0)
    session.property = lambda element, identifier, kind: {
        "hresult": "0x00000000",
        "vt": 11,
        "value": enabled if identifier == 30010 else password,
    }
    session.returned = lambda pattern, slot, *arguments: (0, 89) if slot == 14 else (0, document)
    monkeypatch.setattr(uia, "com_method", lambda *args: attribute)
    editing, editable = session.editing(88)
    assert editable is expected
    observation, sample = writable_sample()
    sample.update(editing=editing, editable=editable)
    facts = focus_evidence(observation, 1, sample)
    if expected is None:
        assert "text_editable" not in facts
    else:
        assert facts["text_editable"].value is expected


@pytest.mark.parametrize("hr,pointer", [(1, 89), (-1, 89), (0, None)])
def test_unavailable_registered_text_pattern_never_establishes_editability(
    monkeypatch, hr, pointer
):
    import ctypes as C
    from types import SimpleNamespace

    from clef_use import windows_uia as uia

    def attribute(identifier, output):
        value = C.cast(output, C.POINTER(uia.VARIANT)).contents
        value.tagged.vt, value.tagged.value.boolean = 11, 0
        return 0

    session = uia.Session.__new__(uia.Session)
    session.result = {"cleanup_errors": []}
    session.automation = SimpleNamespace(VariantClear=lambda value: 0)
    session.property = lambda element, identifier, kind: {
        "hresult": "0x00000000",
        "vt": 11,
        "value": identifier == 30010,
    }
    session.returned = lambda element, slot, *arguments: (hr, pointer) if slot == 14 else (0, 99)
    monkeypatch.setattr(uia, "com_method", lambda *args: attribute)
    editing, editable = session.editing(88)
    assert editable is None
    observation, sample = writable_sample()
    sample.update(editing=editing, editable=editable)
    facts = focus_evidence(observation, 1, sample)
    assert "text_editable" not in facts
    assert facts["ime_composing"].value is False


@pytest.mark.parametrize("change", ["missing", "s_false", "error", "null", "not_boolean"])
def test_registered_text_pattern_proof_is_required_for_writability(change):
    observation, sample = writable_sample()
    if change == "missing":
        sample["editing"].pop("text_pattern_hresult")
    elif change == "s_false":
        sample["editing"]["text_pattern_hresult"] = "0x00000001"
    elif change == "error":
        sample["editing"]["text_pattern_hresult"] = "0x80040201"
    elif change == "null":
        sample["editing"]["text_pattern_present"] = False
    else:
        sample["editing"]["text_pattern_present"] = 1
    facts = focus_evidence(observation, 1, sample)
    assert "text_editable" not in facts
    assert facts["text_focus"].value is True and facts["ime_composing"].value is False
