from copy import deepcopy
from threading import Event

import pytest
from test_operations import Desktop, transform

from clef_use.operations import OperationRunner, parse_operation_request


def observed_change(desktop, sample, change):
    calls = 0

    def observe():
        nonlocal calls
        calls += 1
        if calls == sample:
            change(desktop.values)
        return desktop.observe()

    return observe


@pytest.mark.parametrize("sample", [2, 7])
def test_transform_parent_change_stops_before_enter_or_commit(sample):
    desktop = Desktop()
    observer = observed_change(
        desktop, sample, lambda values: values["transform_context"]["Cube"].update(parent="Parent")
    )
    report = OperationRunner(observer, desktop.execute).run(transform(), Event())
    assert report.status == ("BLOCKED" if sample == 2 else "FAILED")
    assert not any(getattr(command, "key", None) == "enter" for command in desktop.inputs)
    assert desktop.values["transform_values"]["Cube"]["translate"]["X"] == 0
    if sample == 2:
        assert desktop.inputs == []


def test_baseline_change_before_transform_entry_never_dispatches_stale_amount():
    desktop = Desktop()
    observer = observed_change(
        desktop, 2, lambda values: values["transform_values"]["Cube"]["translate"].update(X=5.0)
    )
    report = OperationRunner(observer, desktop.execute).run(transform(), Event())
    assert report.status == "BLOCKED"
    assert desktop.inputs == []
    assert desktop.values["transform_values"]["Cube"]["translate"]["X"] == 5


def test_preview_changed_after_verification_is_not_committed():
    desktop = Desktop()
    before = deepcopy(desktop.values["transform_values"])
    observer = observed_change(
        desktop, 7, lambda values: values["transform_preview"]["Cube"]["translate"].update(X=99.0)
    )
    runner = OperationRunner(observer, desktop.execute)
    report = runner.run(transform(), Event())
    assert report.status == "FAILED"
    assert desktop.values["transform_values"] == before
    assert desktop.values["modal"] == {"id": "modal-1", "name": "translate"}
    assert report.owned_modal_id == "modal-1"
    assert not any(getattr(command, "key", None) == "enter" for command in desktop.inputs)


def test_owned_entry_preview_does_not_redefine_the_initial_baseline():
    desktop = Desktop()

    def execute(command, state, cancelled):
        result = desktop.execute(command, state, cancelled)
        if getattr(command, "key", None) == "g":
            desktop.values["transform_values"]["Cube"]["translate"]["X"] = 5.0
        return result

    report = OperationRunner(desktop.observe, execute).run(transform(), Event())
    assert report.status == "SUCCEEDED"
    assert desktop.values["transform_values"]["Cube"]["translate"]["X"] == 2


@pytest.mark.parametrize("family", ["numeric_transform", "property_edit"])
def test_numeric_literal_keeps_the_requested_float_with_a_strict_tolerance(family):
    amount = 0.12345678901234566
    desktop = Desktop()
    if family == "numeric_transform":
        request = parse_operation_request(
            dict(transform().model_dump(), amount=amount, tolerance=1e-20)
        )
    else:
        desktop.values.update(
            text_focus=True,
            focused_property={"target_id": "Cube", "field": "location_x"},
            properties={"Cube": {"location_x": 0.0}},
        )
        request = parse_operation_request(
            dict(
                family=family,
                target_id="Cube",
                field="location_x",
                value=amount,
                tolerance=1e-20,
                keymap_version="test-1",
            )
        )

    def execute(command, state, cancelled):
        result = desktop.execute(command, state, cancelled)
        if family == "property_edit" and getattr(command, "text", None):
            desktop.values["properties"]["Cube"]["location_x"] = float(command.text)
        return result

    report = OperationRunner(desktop.observe, execute).run(request, Event())
    assert report.status == "SUCCEEDED"
    value = (
        desktop.values["transform_values"]["Cube"]["translate"]["X"]
        if family == "numeric_transform"
        else desktop.values["properties"]["Cube"]["location_x"]
    )
    assert abs(value - amount) <= request.tolerance
