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
            unit={"translate": "NONE", "rotate": "DEGREES", "scale": "NONE"},
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
                "Cube": {"translate": {"X": 0.0}, "rotate": {"X": 0.0, "Y": 0.0, "Z": 0.0}}
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
