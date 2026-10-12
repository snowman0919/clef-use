import time
from copy import deepcopy
from threading import Event

import pytest
from PIL import Image

from clef_use.operations import OperationRunner, parse_operation_request
from clef_use.schema import ActionResult, Frame, InputDelivery, Observation
from clef_use.state import FactValidity, StateCompiler, StateFact, StateSource


class Desktop:
    def __init__(self, **overrides):
        self.compiler = StateCompiler()
        self.values = dict(
            application="Blender",
            window="fixture",
            foreground=True,
            editor="VIEW_3D",
            mode="OBJECT",
            text_focus=False,
            ime_composing=False,
            keymap_version="test-1",
            selection=["Cube"],
            selection_identities={"Cube": "object-1"},
            unit={"translate": "NONE", "rotate": "DEGREES", "scale": "NONE"},
            scene_units={
                "scene_identity": "scene-1",
                "system": "NONE",
                "length_unit": "ADAPTIVE",
                "scale_length": 1.0,
            },
            space="GLOBAL",
            modal=None,
            popup=False,
            loading=False,
            keymap={
                "translate": ["g"],
                "rotate": ["r"],
                "axis_x": ["x"],
                "commit": ["enter"],
                "cancel": ["escape"],
                "search": ["f3"],
                "select_all": ["ctrl", "a"],
            },
            transform_values={
                "Cube": {
                    "translate": {"X": 0.0, "Y": 0.0, "Z": 0.0},
                    "rotate": {"X": 0.0, "Y": 0.0, "Z": 0.0},
                    "scale": {"X": 1.0, "Y": 1.0, "Z": 1.0},
                }
            },
            transform_context={
                "Cube": {"parent": None, "delta_identity": True, "pivot": "MEDIAN_POINT"}
            },
            menus=[],
            owned_inputs=[],
            view_revision="view-1",
        )
        self.values.update(overrides)
        self.inputs = []

    def observe(self):
        version = self.compiler.version + 1
        facts = {
            name: StateFact(
                value=value,
                source=StateSource.APP_TELEMETRY,
                observed_at=time.time(),
                state_version=version,
                validity=FactValidity.VALID,
                uncertainty=0,
            )
            for name, value in self.values.items()
        }
        return self.compiler.compile(
            Observation(str(version), Frame(Image.new("RGB", (64, 64))), ()), facts
        )

    def execute(self, command, state, cancelled):
        self.inputs.append(command)
        if getattr(command, "key", None) in {"g", "r"}:
            self.values["modal"] = {
                "id": "modal-1",
                "name": {"g": "translate", "r": "rotate"}[command.key],
            }
        if getattr(command, "text", None) and self.values["modal"] is not None:
            preview = deepcopy(self.values["transform_values"])
            preview["Cube"][self.values["modal"]["name"]]["X"] = float(command.text)
            self.values["transform_preview"] = preview
        if getattr(command, "key", None) == "enter":
            if "transform_preview" in self.values:
                self.values["transform_values"] = self.values["transform_preview"]
            self.values["modal"] = None
        if getattr(command, "key", None) == "escape":
            self.values["modal"] = None
        return ActionResult(ok=True)


def transform(**changes):
    return parse_operation_request(
        dict(
            family="numeric_transform",
            target_id="Cube",
            operation="translate",
            axis="X",
            space="GLOBAL",
            unit="NONE",
            amount=2,
            keymap_version="test-1",
            **changes,
        )
    )


def test_menu_inspection_handles_absent_wrong_and_duplicate_without_input():
    desktop = Desktop()
    runner = OperationRunner(desktop.observe, desktop.execute)
    request = parse_operation_request({"family": "menu_assess", "menu": "File"})
    assert runner.run(request, Event()).assessment == "ABSENT"
    desktop.values["menus"] = [{"name": "Edit", "open": True, "id": "a"}]
    assert runner.run(request, Event()).assessment == "WRONG_MENU"
    desktop.values["menus"] = [
        {"name": "File", "open": True, "id": "a"},
        {"name": "File", "open": True, "id": "b"},
    ]
    assert runner.run(request, Event()).assessment == "AMBIGUOUS"
    desktop.values["menus"] = [{"name": "File", "open": True, "id": "a"}]
    assert runner.run(request, Event()).assessment == "OPEN"
    assert desktop.inputs == []


@pytest.mark.parametrize(
    "changes",
    [
        dict(selection=["Other"]),
        dict(editor="TEXT_EDITOR"),
        dict(keymap_version="different"),
        dict(unit="METERS"),
        dict(text_focus=True),
        dict(modal={"id": "foreign", "name": "translate"}),
        dict(ime_composing=True),
    ],
)
def test_transform_guard_counterexamples_never_change_scene(changes):
    desktop = Desktop(**changes)
    report = OperationRunner(desktop.observe, desktop.execute).run(transform(), Event())
    assert report.status == "BLOCKED"
    assert desktop.inputs == []
    assert desktop.values["transform_values"]["Cube"]["translate"]["X"] == 0


def test_transform_requires_preview_and_committed_numeric_readback():
    desktop = Desktop()
    report = OperationRunner(desktop.observe, desktop.execute).run(transform(), Event())
    assert report.status == "SUCCEEDED"
    assert desktop.values["transform_values"]["Cube"]["translate"]["X"] == 2
    assert "preview_verified" in report.transitions
    assert "readback_verified" in report.transitions


@pytest.mark.parametrize(
    "units",
    [
        None,
        {},
        {"scale_length": 1.0},
        {
            "scene_identity": "scene-1",
            "system": "METRIC",
            "length_unit": "METERS",
            "scale_length": 0.0,
        },
        {
            "scene_identity": "scene-1",
            "system": "METRIC",
            "length_unit": "METERS",
            "scale_length": True,
        },
    ],
)
def test_translation_requires_complete_scene_conversion_before_entry(units):
    desktop = Desktop(scene_units=units)
    report = OperationRunner(desktop.observe, desktop.execute).run(transform(), Event())
    assert report.status == "BLOCKED"
    assert desktop.inputs == []
    assert desktop.values["modal"] is None


@pytest.mark.parametrize(
    "change",
    [
        {"scene_identity": "scene-2"},
        {"system": "IMPERIAL"},
        {"length_unit": "CENTIMETERS"},
        {"scale_length": 100.0},
    ],
)
def test_translation_same_unit_label_cannot_cross_changed_scene_before_entry(change):
    desktop = Desktop()
    calls = 0

    def observe():
        nonlocal calls
        calls += 1
        if calls == 2:
            desktop.values["scene_units"] = {**desktop.values["scene_units"], **change}
        return desktop.observe()

    report = OperationRunner(observe, desktop.execute).run(transform(), Event())
    assert report.status == "BLOCKED"
    assert desktop.inputs == []
    assert desktop.values["transform_values"]["Cube"]["translate"]["X"] == 0


@pytest.mark.parametrize("change_after,count", [("g", 1), ("x", 2), ("text", 3), ("enter", 4)])
def test_translation_scene_change_stops_later_input_or_success(change_after, count):
    desktop = Desktop()

    def execute(command, state, cancelled):
        result = desktop.execute(command, state, cancelled)
        stage = "text" if getattr(command, "text", None) else getattr(command, "key", None)
        if stage == change_after:
            desktop.values["scene_units"] = {**desktop.values["scene_units"], "scale_length": 100.0}
        return result

    report = OperationRunner(desktop.observe, execute).run(transform(), Event())
    assert report.status == "FAILED"
    assert report.input_count == count
    if count < 4:
        assert all(getattr(command, "key", None) != "enter" for command in desktop.inputs)


def test_rotation_angular_readback_does_not_require_scene_length_conversion():
    desktop = Desktop(scene_units=None)
    request = parse_operation_request(
        {**transform().model_dump(), "operation": "rotate", "unit": "DEGREES", "amount": 45}
    )
    report = OperationRunner(desktop.observe, desktop.execute).run(request, Event())
    assert report.status == "SUCCEEDED"
    assert desktop.values["transform_values"]["Cube"]["rotate"]["X"] == 45


def test_owned_translation_cancel_retains_original_scene_conversion_guard():
    desktop = Desktop()
    stop = Event()

    def execute(command, state, cancelled):
        result = desktop.execute(command, state, cancelled)
        if getattr(command, "text", None):
            stop.set()
        return result

    runner = OperationRunner(desktop.observe, execute)
    entered = runner.run(transform(), stop)
    assert entered.status == "ABORTED" and runner.owns_modal()
    desktop.values["scene_units"]["scale_length"] = 100.0
    report = runner.run(
        parse_operation_request({"family": "modal_cancel", "modal_id": "modal-1"}), Event()
    )
    assert report.status == "BLOCKED" and runner.owns_modal()
    assert desktop.values["modal"] == {"id": "modal-1", "name": "translate"}
    assert all(getattr(command, "key", None) != "escape" for command in desktop.inputs)


@pytest.mark.parametrize(
    "after_close_units",
    [
        None,
        {
            "scene_identity": "scene-1",
            "system": "NONE",
            "length_unit": "ADAPTIVE",
            "scale_length": 100.0,
        },
    ],
)
def test_closed_translation_cancel_cannot_verify_changed_scene_conversion(after_close_units):
    desktop = Desktop()
    stop = Event()

    def execute(command, state, cancelled):
        result = desktop.execute(command, state, cancelled)
        if getattr(command, "text", None):
            stop.set()
        if getattr(command, "key", None) == "escape":
            desktop.values["scene_units"] = after_close_units
        return result

    runner = OperationRunner(desktop.observe, execute)
    assert runner.run(transform(), stop).status == "ABORTED"
    assert runner.owns_modal()
    report = runner.run(
        parse_operation_request({"family": "modal_cancel", "modal_id": "modal-1"}), Event()
    )
    assert report.status == "FAILED" and report.input_count == 1
    assert desktop.values["modal"] is None and not runner.owns_modal()
    assert "unchanged_readback_verified" not in report.transitions


@pytest.mark.parametrize(
    "identities",
    [
        None,
        {},
        {"Other": "object-1"},
        {"Cube": ""},
        {"Cube": 1},
        {"Cube": "\x00"},
        {"Cube": "x" * 257},
        {"Cube": "object-1", "Other": "object-2"},
    ],
)
def test_missing_or_malformed_selection_identities_block_before_input(identities):
    desktop = Desktop(selection_identities=identities)
    report = OperationRunner(desktop.observe, desktop.execute).run(transform(), Event())
    assert report.status == "BLOCKED"
    assert report.input_count == 0 and desktop.inputs == []


def test_unknown_selection_identity_fact_blocks_before_input():
    desktop = Desktop()
    del desktop.values["selection_identities"]
    report = OperationRunner(desktop.observe, desktop.execute).run(transform(), Event())
    assert report.status == "BLOCKED"
    assert desktop.inputs == []


def test_selection_identity_at_length_limit_allows_verified_effect():
    desktop = Desktop(selection_identities={"Cube": "x" * 256})
    report = OperationRunner(desktop.observe, desktop.execute).run(transform(), Event())
    assert report.status == "SUCCEEDED"
    assert desktop.values["transform_values"]["Cube"]["translate"]["X"] == 2


def test_read_only_menu_assessment_needs_no_object_identity():
    desktop = Desktop()
    del desktop.values["selection_identities"]
    report = OperationRunner(desktop.observe, desktop.execute).run(
        parse_operation_request({"family": "menu_assess", "menu": "File"}), Event()
    )
    assert report.assessment == "ABSENT"
    assert desktop.inputs == []


@pytest.mark.parametrize(
    "selection,identities",
    [
        (["Cube", "Cube"], {"Cube": "object-1"}),
        (["Cube", "Other"], {"Cube": "object-1", "Other": "object-1"}),
    ],
)
def test_duplicate_selected_name_or_identity_blocks_viewport_before_input(selection, identities):
    desktop = Desktop(
        selection=selection,
        selection_identities=identities,
        keymap={"orbit": {"button": "middle", "modifiers": []}},
        target_geometry={"editor_surface": [0, 0, 1, 1]},
    )
    request = parse_operation_request(
        dict(
            family="viewport_gesture",
            gesture="orbit",
            keymap_version="test-1",
            surface=(0, 0, 1, 1),
            points=((0.4, 0.4), (0.5, 0.5)),
        )
    )
    report = OperationRunner(desktop.observe, desktop.execute).run(request, Event())
    assert report.status == "BLOCKED" and desktop.inputs == []


@pytest.mark.parametrize("after_key", ["g", "x", "enter"])
def test_same_name_replacement_never_succeeds_or_continues_input(after_key):
    desktop = Desktop(application_snapshot={"objects": {"Cube": {"type": "MESH"}}})

    def execute(command, state, cancelled):
        result = desktop.execute(command, state, cancelled)
        if getattr(command, "key", None) == after_key:
            desktop.values["selection_identities"] = {"Cube": "object-2"}
            desktop.values["application_snapshot"] = {"objects": {"Cube": {"type": "EMPTY"}}}
        return result

    report = OperationRunner(desktop.observe, execute).run(transform(), Event())
    assert report.status == "FAILED"
    assert "selection" in report.reason
    assert report.input_count == {"g": 1, "x": 2, "enter": 4}[after_key]
    if after_key != "enter":
        assert not any(getattr(command, "key", None) == "enter" for command in desktop.inputs)
        assert desktop.values["transform_values"]["Cube"]["translate"]["X"] == 0
    if after_key == "g":
        assert report.owned_modal_id is None


def test_owned_cancel_never_targets_same_name_replacement():
    desktop = Desktop()
    stop = Event()

    def execute(command, state, cancelled):
        result = desktop.execute(command, state, cancelled)
        if getattr(command, "key", None) == "g":
            stop.set()
        return result

    runner = OperationRunner(desktop.observe, execute)
    assert runner.run(transform(), stop).owned_modal_id == "modal-1"
    desktop.values["selection_identities"] = {"Cube": "object-2"}
    desktop.inputs.clear()
    report = runner.run(
        parse_operation_request({"family": "modal_cancel", "modal_id": "modal-1"}), Event()
    )
    assert report.status == "BLOCKED" and desktop.inputs == []
    assert desktop.values["modal"] == {"id": "modal-1", "name": "translate"}
    assert runner.owns_modal("modal-1")
    desktop.values["modal"] = None
    report = runner.run(
        parse_operation_request({"family": "modal_cancel", "modal_id": "modal-1"}), Event()
    )
    assert report.status == "BLOCKED" and desktop.inputs == []
    assert not runner.owns_modal()
    assert "owned_modal_closed_observed" in report.transitions
    assert "unchanged_readback_observed" not in report.transitions
    assert "changed_readback_observed" not in report.transitions


@pytest.mark.parametrize("group", ["translate", "rotate", "scale"])
@pytest.mark.parametrize("axis", [None, "X", "Y", "Z"])
def test_incomplete_transform_snapshot_blocks_before_any_input(group, axis):
    desktop = Desktop()
    values = desktop.values["transform_values"]["Cube"]
    if axis is None:
        del values[group]
    else:
        del values[group][axis]
    report = OperationRunner(desktop.observe, desktop.execute).run(transform(), Event())
    assert report.status == "BLOCKED"
    assert report.input_count == 0
    assert desktop.inputs == []


def test_rotation_enters_only_numeric_literal_in_the_observed_angular_unit():
    desktop = Desktop()
    request = parse_operation_request(
        dict(
            family="numeric_transform",
            target_id="Cube",
            operation="rotate",
            axis="X",
            space="GLOBAL",
            unit="DEGREES",
            amount=45,
            keymap_version="test-1",
        )
    )
    report = OperationRunner(desktop.observe, desktop.execute).run(request, Event())
    assert report.status == "SUCCEEDED"
    assert desktop.values["transform_values"]["Cube"]["rotate"]["X"] == 45


def test_foreign_modal_is_never_cancelled():
    desktop = Desktop(modal={"id": "foreign", "name": "translate"})
    report = OperationRunner(desktop.observe, desktop.execute).run(
        parse_operation_request({"family": "modal_cancel", "modal_id": "foreign"}), Event()
    )
    assert report.status == "BLOCKED"
    assert desktop.inputs == []


def test_search_rejects_nonregistered_command_before_input():
    with pytest.raises(ValueError):
        parse_operation_request(
            {"family": "command_search", "command": "python.exec", "keymap_version": "test-1"}
        )


def test_text_focus_change_between_guard_and_input_prevents_transform():
    desktop = Desktop()
    count = 0

    def observe():
        nonlocal count
        count += 1
        if count == 2:
            desktop.values["text_focus"] = True
        return desktop.observe()

    report = OperationRunner(observe, desktop.execute).run(transform(), Event())
    assert report.status == "BLOCKED"
    assert desktop.inputs == []


def test_changed_keymap_content_with_same_version_refuses_transform_before_input():
    desktop = Desktop()
    count = 0

    def observe():
        nonlocal count
        count += 1
        if count == 2:
            desktop.values["keymap"]["translate"] = ["r"]
        return desktop.observe()

    report = OperationRunner(observe, desktop.execute).run(transform(), Event())
    assert report.status == "BLOCKED"
    assert desktop.inputs == []
    assert desktop.values["modal"] is None


def test_viewport_region_change_before_dispatch_refuses_the_old_gesture():
    desktop = Desktop(
        target_geometry={"editor_surface": [0, 0, 1, 1]},
        keymap={"orbit": {"button": "middle", "modifiers": []}},
    )
    count = 0

    def observe():
        nonlocal count
        count += 1
        if count == 2:
            desktop.values["target_geometry"]["editor_surface"] = [0, 0, 0.3, 1]
        return desktop.observe()

    request = parse_operation_request(
        dict(
            family="viewport_gesture",
            gesture="orbit",
            keymap_version="test-1",
            surface=(0, 0, 1, 1),
            points=((0.4, 0.4), (0.5, 0.5)),
        )
    )
    report = OperationRunner(observe, desktop.execute).run(request, Event())
    assert report.status == "BLOCKED"
    assert desktop.inputs == []
    assert not report.geometry_invalidated


def test_preview_mismatch_can_only_cancel_the_modal_this_runner_entered():
    desktop = Desktop()
    execute = desktop.execute

    def wrong_preview(command, state, cancelled):
        result = execute(command, state, cancelled)
        if getattr(command, "text", None):
            desktop.values["transform_preview"]["Cube"]["translate"]["X"] = 99
        return result

    runner = OperationRunner(desktop.observe, wrong_preview)
    report = runner.run(transform(), Event())
    assert report.status == "FAILED"
    assert report.owned_modal_id == "modal-1"
    assert runner.owns_modal("modal-1")
    assert not runner.owns_modal("foreign")
    cancel = parse_operation_request({"family": "modal_cancel", "modal_id": "modal-1"})
    assert runner.run(cancel, Event()).status == "SUCCEEDED"
    assert not runner.owns_modal("modal-1")
    assert desktop.values["transform_values"]["Cube"]["translate"]["X"] == 0


def test_abort_after_delivered_numeric_input_counts_the_delivered_command():
    desktop = Desktop()
    cancelled = Event()

    def execute(command, state, stop):
        result = desktop.execute(command, state, stop)
        if getattr(command, "text", None):
            cancelled.set()
        return result

    report = OperationRunner(desktop.observe, execute).run(transform(), cancelled)
    assert report.status == "ABORTED"
    assert report.input_count == 3


def test_abort_after_acknowledged_enter_preserves_only_known_modal_cleanup():
    desktop = Desktop()
    cancelled = Event()

    def execute(command, state, stop):
        result = desktop.execute(command, state, stop)
        if getattr(command, "key", None) == "g":
            stop.set()
        return result

    runner = OperationRunner(desktop.observe, execute)
    report = runner.run(transform(), cancelled)
    assert report.status == "ABORTED"
    assert report.input_count == 1
    assert report.owned_modal_id == "modal-1"
    cancel = parse_operation_request({"family": "modal_cancel", "modal_id": "modal-1"})
    assert runner.run(cancel, Event()).status == "SUCCEEDED"
    assert desktop.values["transform_values"]["Cube"]["translate"]["X"] == 0


@pytest.mark.parametrize(
    "change",
    [
        {"selection": ["Other"]},
        {"window": "foreign-window"},
        {"modal": {"id": "foreign", "name": "rotate"}},
    ],
)
def test_abort_enter_never_claims_modal_after_context_changed(change):
    desktop = Desktop()

    def execute(command, state, stop):
        result = desktop.execute(command, state, stop)
        desktop.values.update(change)
        stop.set()
        return result

    runner = OperationRunner(desktop.observe, execute)
    report = runner.run(transform(), Event())
    assert report.status == "ABORTED"
    assert report.owned_modal_id is None
    assert not runner.owns_modal()
    desktop.inputs.clear()
    cancel = parse_operation_request({"family": "modal_cancel", "modal_id": "modal-1"})
    assert runner.run(cancel, Event()).status == "BLOCKED"
    assert desktop.inputs == []


def test_unacknowledged_enter_attempt_does_not_claim_observed_modal():
    desktop = Desktop()

    def execute(command, state, stop):
        desktop.execute(command, state, stop)
        stop.set()
        return ActionResult(ok=False, reason="no acknowledged delivery receipt")

    runner = OperationRunner(desktop.observe, execute)
    report = runner.run(transform(), Event())
    assert report.status == "ABORTED"
    assert report.owned_modal_id is None
    assert not runner.owns_modal()


@pytest.mark.parametrize(
    "keys,kind,fresh,owned",
    [
        (("g",), "key", True, True),
        (("r",), "key", True, False),
        (("g",), "chord", True, False),
        (("g",), "key", False, False),
    ],
)
def test_interrupted_enter_claims_only_matching_native_acknowledgement(keys, kind, fresh, owned):
    desktop = Desktop()

    def execute(command, state, stop):
        if getattr(command, "key", None) != "g":
            return desktop.execute(command, state, stop)
        desktop.execute(command, state, stop)
        stop.set()
        return ActionResult(
            ok=False,
            reason="interrupted after native trigger acknowledgement",
            delivery=InputDelivery(
                execution_id="native-1",
                kind=kind,
                keys=keys,
                acknowledged_at_ns=time.monotonic_ns() if fresh else 1,
            ),
        )

    runner = OperationRunner(desktop.observe, execute)
    report = runner.run(transform(), Event())
    assert report.status == "ABORTED"
    assert report.owned_modal_id == ("modal-1" if owned else None)
    assert report.input_count == int(owned)


@pytest.mark.parametrize("commit", [True, False])
def test_abort_after_acknowledged_modal_close_clears_recovery_authority(commit):
    desktop = Desktop()
    closing = "enter" if commit else "escape"

    def execute(command, state, stop):
        result = desktop.execute(command, state, stop)
        if getattr(command, "key", None) == closing:
            stop.set()
        return result

    runner = OperationRunner(desktop.observe, execute)
    report = runner.run(transform(commit=commit), Event())
    assert report.status == "ABORTED"
    assert report.input_count == 4
    assert desktop.values["modal"] is None
    assert report.owned_modal_id is None
    assert not runner.owns_modal()
    assert desktop.values["transform_values"]["Cube"]["translate"]["X"] == (2 if commit else 0)


def test_abort_after_known_cancel_ack_clears_closed_modal_without_claiming_success():
    desktop = Desktop()

    def execute(command, state, stop):
        result = desktop.execute(command, state, stop)
        if getattr(command, "text", None) or getattr(command, "key", None) == "escape":
            stop.set()
        return result

    runner = OperationRunner(desktop.observe, execute)
    pending = runner.run(transform(), Event())
    assert pending.owned_modal_id == "modal-1"
    report = runner.run(
        parse_operation_request({"family": "modal_cancel", "modal_id": "modal-1"}), Event()
    )
    assert report.status == "ABORTED"
    assert report.input_count == 1
    assert report.owned_modal_id is None
    assert not runner.owns_modal()
    assert desktop.values["transform_values"]["Cube"]["translate"]["X"] == 0


def test_property_delivery_without_exact_literal_readback_is_failure():
    desktop = Desktop(
        text_focus=True,
        focused_property={"target_id": "Cube", "field": "location_x"},
        properties={"Cube": {"location_x": 0}},
    )
    request = parse_operation_request(
        dict(
            family="property_edit",
            target_id="Cube",
            field="location_x",
            value=2,
            keymap_version="test-1",
        )
    )
    report = OperationRunner(desktop.observe, desktop.execute).run(request, Event())
    assert report.status == "FAILED"
    assert "readback" in report.reason


@pytest.mark.parametrize("changed_target", [None, "Cube", "Other"])
def test_property_edit_verifies_all_observed_fields_without_rejecting_unchanged_metadata(
    changed_target,
):
    desktop = Desktop(
        text_focus=True,
        focused_property={"target_id": "Cube", "field": "location_x"},
        properties={
            "Cube": {"location_x": 0.0, "location_y": 0.0, "locked": True, "label": "target"},
            "Other": {"location_x": 5.0, "enabled": False},
        },
    )
    request = parse_operation_request(
        dict(
            family="property_edit",
            target_id="Cube",
            field="location_x",
            value=2,
            keymap_version="test-1",
        )
    )

    def execute(command, current, cancelled):
        result = desktop.execute(command, current, cancelled)
        if getattr(command, "text", None):
            desktop.values["properties"]["Cube"]["location_x"] = float(command.text)
        if getattr(command, "key", None) == "enter":
            if changed_target == "Cube":
                desktop.values["properties"]["Cube"]["location_y"] = 3.0
            elif changed_target == "Other":
                desktop.values["properties"]["Other"]["location_x"] = 9.0
        return result

    report = OperationRunner(desktop.observe, execute).run(request, Event())
    assert report.status == ("SUCCEEDED" if changed_target is None else "FAILED")
    assert desktop.values["properties"]["Cube"]["location_x"] == 2.0
    assert desktop.values["properties"]["Cube"]["locked"] is True
    assert desktop.values["properties"]["Cube"]["label"] == "target"
    assert desktop.values["properties"]["Other"]["enabled"] is False


def property_request(field="location_x", value=2):
    return parse_operation_request(
        dict(
            family="property_edit",
            target_id="Cube",
            field=field,
            value=value,
            keymap_version="test-1",
        )
    )


@pytest.mark.parametrize(
    "units",
    [
        None,
        {},
        {"system": "METRIC"},
        {
            "scene_identity": "scene-1",
            "system": "METRIC",
            "length_unit": "CENTIMETERS",
            "scale_length": True,
        },
        {
            "scene_identity": "scene-1",
            "system": "METRIC",
            "length_unit": "CENTIMETERS",
            "scale_length": 0,
        },
        {
            "scene_identity": "scene-1",
            "system": "METRIC",
            "length_unit": "CENTIMETERS",
            "scale_length": -1,
        },
    ],
)
def test_location_field_without_complete_units_refuses_before_input(units):
    desktop = Desktop(
        text_focus=True,
        focused_property={"target_id": "Cube", "field": "location_x"},
        properties={"Cube": {"location_x": 0.0}},
        scene_units=units,
    )
    report = OperationRunner(desktop.observe, desktop.execute).run(property_request(), Event())
    assert report.status == "BLOCKED"
    assert desktop.inputs == []
    assert desktop.values["properties"]["Cube"]["location_x"] == 0.0


@pytest.mark.parametrize("system", ["METRIC", "IMPERIAL", "NONE"])
@pytest.mark.parametrize("scale", [0.01, 1.0, 100.0])
@pytest.mark.parametrize("value", [2.0, -0.12345678901234566])
def test_location_field_converts_raw_value_without_default_display_unit(system, scale, value):
    desktop = Desktop(
        text_focus=True,
        focused_property={"target_id": "Cube", "field": "location_x"},
        properties={"Cube": {"location_x": 0.0}},
        scene_units={
            "scene_identity": "scene-1",
            "system": system,
            "length_unit": "FEET" if system == "IMPERIAL" else "CENTIMETERS",
            "scale_length": scale,
        },
    )
    pending = [None]

    def execute(command, state, cancelled):
        result = desktop.execute(command, state, cancelled)
        if getattr(command, "text", None):
            text = command.text
            # Explicit consumer model: a bare value uses cm or feet in a unit-enabled
            # field; an explicit meter literal is divided by scene scale.
            pending[0] = (
                float(text[:-1]) / scale
                if text.endswith("m")
                else float(text)
                if system == "NONE"
                else float(text) * (0.3048 if system == "IMPERIAL" else 0.01) / scale
            )
        if getattr(command, "key", None) == "enter":
            desktop.values["properties"]["Cube"]["location_x"] = pending[0]
        return result

    report = OperationRunner(desktop.observe, execute).run(property_request(value=value), Event())
    assert report.status == "SUCCEEDED"
    assert desktop.values["properties"]["Cube"]["location_x"] == pytest.approx(value, abs=1e-12)


@pytest.mark.parametrize("change_after", ["select_all", "text", "commit"])
def test_changed_scene_units_stop_property_entry_or_success(change_after):
    desktop = Desktop(
        text_focus=True,
        focused_property={"target_id": "Cube", "field": "location_x"},
        properties={"Cube": {"location_x": 0.0}},
    )

    def execute(command, state, cancelled):
        result = desktop.execute(command, state, cancelled)
        stage = (
            "text"
            if getattr(command, "text", None)
            else "commit"
            if getattr(command, "key", None) == "enter"
            else "select_all"
        )
        if stage == "text":
            desktop.values["properties"]["Cube"]["location_x"] = float(command.text)
        if stage == change_after:
            desktop.values["scene_units"] = {**desktop.values["scene_units"], "scale_length": 100.0}
        return result

    report = OperationRunner(desktop.observe, execute).run(property_request(), Event())
    assert report.status == "FAILED"
    assert report.input_count == {"select_all": 1, "text": 2, "commit": 3}[change_after]


def test_scale_field_is_dimensionless_without_scene_unit_evidence():
    desktop = Desktop(
        text_focus=True,
        focused_property={"target_id": "Cube", "field": "scale_x"},
        properties={"Cube": {"scale_x": 1.0}},
        scene_units=None,
    )

    def execute(command, state, cancelled):
        result = desktop.execute(command, state, cancelled)
        if getattr(command, "text", None):
            desktop.values["properties"]["Cube"]["scale_x"] = float(command.text)
        return result

    report = OperationRunner(desktop.observe, execute).run(
        property_request(field="scale_x"), Event()
    )
    assert report.status == "SUCCEEDED"
    assert desktop.values["properties"]["Cube"]["scale_x"] == 2.0


@pytest.mark.parametrize("value, scale", [(100000.0, 1e308), (0.1, 5e-324)])
def test_location_conversion_overflow_or_underflow_refuses_before_input(value, scale):
    desktop = Desktop(
        text_focus=True,
        focused_property={"target_id": "Cube", "field": "location_x"},
        properties={"Cube": {"location_x": 0.0}},
        scene_units={
            "scene_identity": "scene-1",
            "system": "METRIC",
            "length_unit": "CENTIMETERS",
            "scale_length": scale,
        },
    )
    report = OperationRunner(desktop.observe, desktop.execute).run(
        property_request(value=value), Event()
    )
    assert report.status == "BLOCKED"
    assert desktop.inputs == []
    assert desktop.values["properties"]["Cube"]["location_x"] == 0.0


def test_viewport_cannot_use_a_caller_surface_outside_observed_editor():
    desktop = Desktop(
        target_geometry={"editor_surface": [0.1, 0.1, 0.8, 0.8]},
        keymap={"orbit": {"button": "middle", "modifiers": []}},
    )
    request = parse_operation_request(
        dict(
            family="viewport_gesture",
            gesture="orbit",
            keymap_version="test-1",
            surface=(0, 0, 1, 1),
            points=((0.4, 0.4), (0.5, 0.5)),
        )
    )
    report = OperationRunner(desktop.observe, desktop.execute).run(request, Event())
    assert report.status == "BLOCKED"
    assert desktop.inputs == []


def test_view_change_before_gesture_dispatch_cannot_count_as_its_effect():
    desktop = Desktop(
        target_geometry={"editor_surface": [0, 0, 1, 1]},
        keymap={"orbit": {"button": "middle", "modifiers": []}},
    )
    calls = 0

    def observe():
        nonlocal calls
        calls += 1
        if calls == 2:
            desktop.values["view_revision"] = "independent-before-gesture"
        return desktop.observe()

    request = parse_operation_request(
        dict(
            family="viewport_gesture",
            gesture="orbit",
            keymap_version="test-1",
            surface=(0, 0, 1, 1),
            points=((0.4, 0.4), (0.5, 0.5)),
        )
    )
    report = OperationRunner(observe, desktop.execute).run(request, Event())
    assert report.status == "BLOCKED"
    assert desktop.inputs == []
    assert "view_change_verified" not in report.transitions
    assert not report.geometry_invalidated


def test_view_change_rejects_reused_geometry_before_next_edit():
    desktop = Desktop(
        target_geometry={"editor_surface": [0, 0, 1, 1]},
        keymap={
            "orbit": {"button": "middle", "modifiers": []},
            "translate": ["g"],
            "axis_x": ["x"],
            "commit": ["enter"],
            "cancel": ["escape"],
        },
    )
    state = desktop.observe()

    def observe():
        return state

    def execute(command, current, cancelled):
        nonlocal state
        desktop.values["view_revision"] = "view-2"
        state = desktop.observe()
        return ActionResult(ok=True)

    runner = OperationRunner(observe, execute)
    request = parse_operation_request(
        dict(
            family="viewport_gesture",
            gesture="orbit",
            keymap_version="test-1",
            surface=(0, 0, 1, 1),
            points=((0.4, 0.4), (0.5, 0.5)),
        )
    )
    assert runner.run(request, Event()).geometry_invalidated
    report = runner.run(transform(), Event())
    assert report.status == "BLOCKED"
    assert "reacquire" in report.reason


def test_partially_delivered_interrupted_view_gesture_invalidates_old_geometry():
    desktop = Desktop(
        target_geometry={"editor_surface": [0, 0, 1, 1]},
        keymap={"orbit": {"button": "middle", "modifiers": []}},
    )
    state = desktop.observe()

    def partial_gesture(command, current, cancelled):
        desktop.values["view_revision"] = "view-after-partial-drag"
        cancelled.set()
        return ActionResult(ok=False, reason="interrupted after first drag point")

    runner = OperationRunner(lambda: state, partial_gesture)
    report = runner.run(
        parse_operation_request(
            dict(
                family="viewport_gesture",
                gesture="orbit",
                keymap_version="test-1",
                surface=(0, 0, 1, 1),
                points=((0.4, 0.4), (0.5, 0.5)),
            )
        ),
        Event(),
    )
    assert report.status == "ABORTED"
    assert report.geometry_invalidated
    assert runner.run(transform(), Event()).status == "BLOCKED"


@pytest.mark.parametrize("stage", ["preview", "commit"])
@pytest.mark.parametrize("target", ["Cube", "Other"])
def test_transform_readback_rejects_unintended_other_axis_or_target_changes(stage, target):
    desktop = Desktop()
    desktop.values["transform_values"]["Cube"]["translate"]["Y"] = 0.0
    desktop.values["transform_values"]["Other"] = deepcopy(
        desktop.values["transform_values"]["Cube"]
    )

    def execute(command, current, cancelled):
        result = desktop.execute(command, current, cancelled)
        if stage == "preview" and getattr(command, "text", None):
            desktop.values["transform_preview"][target]["translate"]["Y"] = 3.0
        if stage == "commit" and getattr(command, "key", None) == "enter":
            desktop.values["transform_values"][target]["translate"]["Y"] = 3.0
        return result

    report = OperationRunner(desktop.observe, execute).run(transform(), Event())
    assert report.status == "FAILED"
    assert ("preview" if stage == "preview" else "readback") in report.reason
    if stage == "preview":
        assert not any(getattr(command, "key", None) == "enter" for command in desktop.inputs)
        assert report.owned_modal_id == "modal-1"
    else:
        assert report.owned_modal_id is None


@pytest.mark.parametrize(
    "context",
    [
        {"parent": "Parent", "delta_identity": True, "pivot": "MEDIAN_POINT"},
        {"parent": None, "delta_identity": False, "pivot": "MEDIAN_POINT"},
        {"parent": None, "delta_identity": True, "pivot": "CURSOR"},
    ],
)
def test_transform_context_needing_matrix_readback_is_blocked_before_input(context):
    desktop = Desktop(transform_context={"Cube": context})
    report = OperationRunner(desktop.observe, desktop.execute).run(transform(), Event())
    assert report.status == "BLOCKED"
    assert report.input_count == 0
    assert desktop.inputs == []
