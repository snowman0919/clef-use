import copy
import json
import os
import socket
import struct
import sys
import threading
import time

import pytest
from PIL import Image

from clef_use.blender_observer import SnapshotServer, peer_credentials, read_message
from clef_use.blender_state import _view_pose_revision, compile_snapshot
from clef_use.schema import Frame, Observation
from clef_use.state import FactValidity, StateCompiler


def snapshot():
    now = time.time()
    return {
        "schema_version": 1,
        "source": "BLENDER_PUBLIC_RNA",
        "pid": 123,
        "sampled_at": now,
        "completed_at": now,
        "windows": [
            {
                "width": 100,
                "height": 80,
                "selection": ["Cube"],
                "active_object_mode": "OBJECT",
                "objects": {"Cube": {"properties": {"location_x": 2.5, "shading": "FLAT"}}},
                "positive_modal_operators": [],
                "areas": [],
            }
        ],
    }


def compile_document(document):
    frame = Frame(
        Image.new("RGB", (100, 80)), foreground_window=42, foreground_bounds=(0, 0, 100, 80)
    )
    facts = compile_snapshot(
        document,
        pid=123,
        frame=frame,
        version=1,
        started_at=document["sampled_at"] - 0.01,
        completed_at=document["sampled_at"] + 0.01,
    )
    return StateCompiler().compile(Observation("scene", frame, ()), facts)


def test_partial_scene_evidence_preserves_numbers_without_inventing_input_context():
    state = compile_document(snapshot())
    assert state.require("selection") == ["Cube"]
    assert state.require("properties")["Cube"]["location_x"] == 2.5
    assert state.require("mode") == "OBJECT"
    assert state.access_level == "APP_TELEMETRY_ASSISTED"
    assert state.fact("selection_identities").validity == FactValidity.UNKNOWN
    for name in ("modal", "popup", "text_focus", "ime_composing", "keymap", "loading", "unit"):
        assert state.fact(name).validity == FactValidity.UNKNOWN


def test_selection_identity_tracks_same_name_object_replacement():
    document = snapshot()
    obj = document["windows"][0]["objects"]["Cube"]
    obj["id"] = "123:OBJECT:11"
    assert compile_document(document).require("selection_identities") == {"Cube": "123:OBJECT:11"}
    obj["id"] = "123:OBJECT:12"
    assert compile_document(document).require("selection_identities") == {"Cube": "123:OBJECT:12"}


def test_scene_units_preserve_bound_scale_without_inventing_field_or_modal_context():
    document = snapshot()
    window = document["windows"][0]
    window["scene_identity"] = "123:88"
    window["unit_settings"] = {
        "system": "METRIC",
        "length_unit": "CENTIMETERS",
        "scale_length": 0.01,
        "system_rotation": "DEGREES",
    }
    state = compile_document(document)
    assert state.require("scene_units") == {
        "scene_identity": "123:88",
        "system": "METRIC",
        "length_unit": "CENTIMETERS",
        "scale_length": 0.01,
    }
    for name in ("focused_property", "text_focus", "unit", "space"):
        assert state.fact(name).validity == FactValidity.UNKNOWN
    window["scene_identity"] = "123:89"
    assert compile_document(document).require("scene_units")["scene_identity"] == "123:89"


@pytest.mark.parametrize(
    "change",
    [
        {"scene_identity": "124:88"},
        {"scene_identity": "123:0"},
        {"scene_identity": "123:x"},
        {"scene_identity": None},
        {"unit_settings": None},
        {"unit_settings": {"system": "METRIC", "length_unit": "CENTIMETERS", "scale_length": True}},
        {"unit_settings": {"system": "METRIC", "length_unit": "CENTIMETERS", "scale_length": 0}},
        {"unit_settings": {"system": "METRIC", "length_unit": "CENTIMETERS", "scale_length": -1}},
        {"unit_settings": {"system": "METRIC", "length_unit": "UNKNOWN", "scale_length": 1}},
        {"unit_settings": {"system": "UNKNOWN", "length_unit": "CENTIMETERS", "scale_length": 1}},
    ],
)
def test_invalid_scene_length_settings_remain_unknown(change):
    document = snapshot()
    document["windows"][0].update(
        {
            "scene_identity": "123:88",
            "unit_settings": {
                "system": "METRIC",
                "length_unit": "CENTIMETERS",
                "scale_length": 1.0,
            },
            **change,
        }
    )
    state = compile_document(document)
    assert state.fact("scene_units").validity == FactValidity.UNKNOWN
    assert state.require("properties")["Cube"]["location_x"] == 2.5


@pytest.mark.parametrize(
    "identity",
    [
        None,
        True,
        11,
        "",
        "999:OBJECT:11",
        "123:11",
        "123:OBJECT:0",
        "123:OBJECT:-1",
        "123:OBJECT:01",
        "123:OBJECT:１２",
        "123:OBJECT:1.0",
    ],
)
def test_invalid_or_unavailable_object_identity_does_not_authorize_continuity(identity):
    document = snapshot()
    document["windows"][0]["objects"]["Cube"]["id"] = identity
    assert compile_document(document).fact("selection_identities").validity == FactValidity.UNKNOWN


@pytest.mark.parametrize(
    "change", ["duplicate_id", "missing_object", "extra_object", "duplicate_name"]
)
def test_partial_or_ambiguous_identity_map_is_unknown(change):
    document = snapshot()
    window = document["windows"][0]
    window["objects"]["Cube"]["id"] = "123:OBJECT:11"
    if change in ("duplicate_id", "extra_object"):
        window["objects"]["Other"] = copy.deepcopy(window["objects"]["Cube"])
        if change == "duplicate_id":
            window["selection"].append("Other")
    elif change == "missing_object":
        window["selection"].append("Other")
    else:
        window["selection"].append("Cube")
    assert compile_document(document).fact("selection_identities").validity == FactValidity.UNKNOWN


def test_empty_selection_has_verified_empty_identity_map():
    document = snapshot()
    document["windows"][0].update(selection=[], objects={})
    assert compile_document(document).require("selection_identities") == {}


def test_object_rename_preserves_identity_value():
    document = snapshot()
    window = document["windows"][0]
    obj = window["objects"].pop("Cube")
    obj["id"] = "123:OBJECT:11"
    window["objects"]["Renamed"] = obj
    window["selection"] = ["Renamed"]
    assert compile_document(document).require("selection_identities") == {
        "Renamed": "123:OBJECT:11"
    }


@pytest.mark.parametrize("change", ["pid", "stale", "future", "windows", "size", "source"])
def test_wrong_process_age_or_ambiguous_window_refuses_scene_evidence(change):
    document = snapshot()
    frame = Frame(
        Image.new("RGB", (100, 80)), foreground_window=42, foreground_bounds=(0, 0, 100, 80)
    )
    start, end = document["sampled_at"] - 0.01, document["sampled_at"] + 0.01
    if change == "pid":
        document["pid"] = 999
    elif change == "stale":
        end += 1
    elif change == "future":
        document["sampled_at"] = end + 1
    elif change == "windows":
        document["windows"].append(copy.deepcopy(document["windows"][0]))
    elif change == "size":
        document["windows"][0]["width"] = 101
    elif change == "source":
        document["source"] = "CALLER_FACTS"
    with pytest.raises(ValueError):
        compile_snapshot(
            document, pid=123, frame=frame, version=1, started_at=start, completed_at=end
        )


def test_positive_modal_never_becomes_absence():
    document = snapshot()
    operators = [{"id": "123:44", "rna": "TRANSFORM_OT_translate", "name": "Move"}]
    document["windows"][0]["positive_modal_operators"] = operators
    assert compile_document(document).require("modal") == {"positive_operators": operators}


def area_geometry(x, y, width, height, *, identity="area", kind="VIEW_3D", regions=()):
    return {
        "id": identity,
        "type": kind,
        "geometry_window_pixels_bottom_left": dict(x=x, y=y, width=width, height=height),
        "regions": list(regions),
    }


def viewport_document():
    document = snapshot()
    area = area_geometry(
        0,
        0,
        100,
        80,
        regions=[area_geometry(0, 0, 100, 80, identity="region", kind="WINDOW")],
    )
    area["viewport"] = {
        "id": "viewport",
        "view_location": [0.0, 0.0, 0.0],
        "view_rotation": [1.0, 0.0, 0.0, 0.0],
        "view_distance": 10.0,
        "view_perspective": "PERSP",
        "view_matrix": [[float(row == column) for column in range(4)] for row in range(4)],
        "window_matrix": [[1.0]],
        "revision": "producer-projection-revision",
    }
    area["quad_views"] = []
    document["windows"][0]["areas"] = [area]
    return document


def test_view_revision_ignores_layout_ids_and_projection_changes():
    document = viewport_document()
    original = compile_document(document).require("view_revision")
    area = document["windows"][0]["areas"][0]
    area["id"] = "new-area"
    area["regions"][0]["id"] = "new-region"
    area["regions"][0]["geometry_window_pixels_bottom_left"]["width"] = 70
    area["viewport"]["id"] = "new-viewport"
    area["viewport"]["window_matrix"] = [[2.0]]
    area["viewport"]["revision"] = "changed-projection-revision"
    assert compile_document(document).require("view_revision") == original


@pytest.mark.parametrize(
    "field,value",
    [
        ("view_location", [1.0, 0.0, 0.0]),
        ("view_rotation", [0.0, 1.0, 0.0, 0.0]),
        ("view_distance", 9.0),
        ("view_perspective", "ORTHO"),
    ],
)
def test_effective_view_change_changes_revision(field, value):
    document = viewport_document()
    original = compile_document(document).require("view_revision")
    document["windows"][0]["areas"][0]["viewport"][field] = value
    if field != "view_perspective":
        document["windows"][0]["areas"][0]["viewport"]["view_matrix"][0][3] = 2.0
    assert compile_document(document).require("view_revision") != original


def test_pending_pose_and_quaternion_sign_do_not_invent_effective_view_change():
    document = viewport_document()
    original = compile_document(document).require("view_revision")
    pose = document["windows"][0]["areas"][0]["viewport"]
    pose["view_rotation"] = [-1.0, 0.0, 0.0, 0.0]
    pose["view_matrix"][0][1] = -0.0
    assert compile_document(document).require("view_revision") == original
    pose["view_location"] = [1.0, 2.0, 3.0]
    pose["view_distance"] = 12.0
    assert compile_document(document).require("view_revision") == original


def test_viewport_operation_cannot_report_layout_only_change_as_success():
    from threading import Event

    from test_operations import Desktop

    from clef_use.operations import OperationRunner, parse_operation_request
    from clef_use.schema import ActionResult

    document = viewport_document()
    desktop = Desktop(
        target_geometry={"editor_surface": [0, 0, 1, 1]},
        keymap={"orbit": {"button": "middle", "modifiers": []}},
        view_revision=compile_document(document).require("view_revision"),
    )

    def execute(command, state, cancelled):
        desktop.inputs.append(command)
        document["windows"][0]["areas"][0]["regions"][0]["id"] = "new-layout-region"
        desktop.values["view_revision"] = compile_document(document).require("view_revision")
        return ActionResult(ok=True)

    request = parse_operation_request(
        dict(
            family="viewport_gesture",
            gesture="orbit",
            keymap_version="test-1",
            surface=(0, 0, 1, 1),
            points=((0.4, 0.4), (0.5, 0.5)),
        )
    )
    report = OperationRunner(desktop.observe, execute).run(request, Event())
    assert report.status == "FAILED"
    assert report.reason == "viewport readback did not change"
    assert report.input_count == 1
    assert "view_change_verified" not in report.transitions


@pytest.mark.parametrize(
    "field,value",
    [
        ("view_location", None),
        ("view_location", [0, 0]),
        ("view_location", [0, True, 0]),
        ("view_location", [0, float("inf"), 0]),
        ("view_rotation", [1, 0, 0]),
        ("view_rotation", [1, 0, float("nan"), 0]),
        ("view_distance", None),
        ("view_distance", True),
        ("view_distance", float("inf")),
        ("view_perspective", None),
        ("view_perspective", "UNKNOWN"),
        ("view_matrix", None),
        ("view_matrix", [[1.0] * 4] * 3),
        ("view_matrix", [[True] * 4] * 4),
        ("view_matrix", [[float("inf")] * 4] * 4),
    ],
)
def test_incomplete_or_invalid_view_pose_never_establishes_revision(field, value):
    document = viewport_document()
    document["windows"][0]["areas"][0]["viewport"][field] = value
    assert _view_pose_revision(document["windows"][0]["areas"]) is None
    if "Infinity" in json.dumps(document) or "NaN" in json.dumps(document):
        with pytest.raises(ValueError, match="finite number"):
            compile_document(document)
    else:
        assert compile_document(document).fact("view_revision").validity == FactValidity.UNKNOWN


@pytest.mark.parametrize("change", ["missing_pose", "missing_quad_inventory", "quad", "multiple"])
def test_ambiguous_or_missing_view_never_establishes_revision(change):
    document = viewport_document()
    areas = document["windows"][0]["areas"]
    if change == "missing_pose":
        areas[0]["viewport"] = None
    elif change == "missing_quad_inventory":
        del areas[0]["quad_views"]
    elif change == "quad":
        areas[0]["quad_views"] = [copy.deepcopy(areas[0]["viewport"])]
    else:
        areas.append(copy.deepcopy(areas[0]))
    assert compile_document(document).fact("view_revision").validity == FactValidity.UNKNOWN


def layout_state(areas, *, origin=(-200, 40), client=(-180, 60, -80, 140)):
    document = snapshot()
    document["windows"][0]["areas"] = areas
    frame = Frame(
        Image.new("RGB", (200, 160)), origin=origin, foreground_window=42, foreground_bounds=client
    )
    facts = compile_snapshot(
        document,
        pid=123,
        frame=frame,
        version=1,
        started_at=document["sampled_at"] - 0.01,
        completed_at=document["sampled_at"] + 0.01,
    )
    return StateCompiler().compile(Observation("layout", frame, ()), facts)


def test_editor_layout_maps_bottom_left_to_capture_and_keeps_separate_regions():
    regions = [
        area_geometry(10, 20, 30, 40, identity="region-a", kind="WINDOW"),
        area_geometry(40, 20, 30, 40, identity="region-b", kind="WINDOW"),
    ]
    state = layout_state([area_geometry(0, 0, 100, 80, regions=regions)])
    layout = state.require("editor_layout")
    assert layout["client_bounds_screen_pixels"] == [-180, 60, -80, 140]
    mapped = layout["areas"][0]
    assert mapped["bounds_screen_pixels"] == [-180, 60, -80, 140]
    assert mapped["bounds_capture_normalized"] == [0.1, 0.125, 0.6, 0.625]
    assert mapped["regions"][0] == {
        "id": "region-a",
        "type": "WINDOW",
        "bounds_screen_pixels": [-170, 80, -140, 120],
        "bounds_capture_normalized": [0.15, 0.25, 0.3, 0.5],
    }
    assert mapped["regions"][1]["id"] == "region-b"
    assert mapped["regions"][1]["bounds_capture_normalized"] == [0.3, 0.25, 0.45, 0.5]
    assert layout["focused_editor"] == "UNKNOWN"
    for name in ("editor", "keymap", "keymap_version"):
        assert state.fact(name).validity == FactValidity.UNKNOWN
    assert "editor_surface" not in state.require("target_geometry")


@pytest.mark.parametrize("geometry", [(0, 0, 0, 40), (-1, 0, 100, 80), (0, 0, 101, 80)])
def test_hidden_or_clipped_regions_never_gain_clamped_actionable_bounds(geometry):
    state = layout_state([area_geometry(*geometry)])
    assert state.require("editor_layout")["areas"][0]["bounds_capture_normalized"] is None


def test_client_partly_outside_capture_keeps_actual_bounds_without_clamping():
    state = layout_state([area_geometry(0, 0, 100, 80)], client=(-220, 60, -120, 140))
    area = state.require("editor_layout")["areas"][0]
    assert area["bounds_screen_pixels"] == [-220, 60, -120, 140]
    assert area["bounds_capture_normalized"] is None


def test_inconsistent_capture_and_native_coordinate_spaces_refuse_layout():
    document = snapshot()
    frame = Frame(
        Image.new("RGB", (100, 80)),
        logical_size=(200, 80),
        foreground_window=42,
        foreground_bounds=(0, 0, 100, 80),
    )
    with pytest.raises(ValueError, match="Blender capture coordinate scale mismatch"):
        compile_snapshot(
            document,
            pid=123,
            frame=frame,
            version=1,
            started_at=document["sampled_at"] - 0.01,
            completed_at=document["sampled_at"] + 0.01,
        )


@pytest.mark.parametrize("geometry", [(True, 0, 100, 80), (0, 0, -1, 80), (0, 0, 100, 1.5)])
def test_invalid_rna_geometry_refuses_state_instead_of_coercing(geometry):
    with pytest.raises(ValueError, match="invalid Blender editor geometry"):
        layout_state([area_geometry(*geometry)])


def test_raw_inventory_is_observed_without_effective_keymap_authority():
    document = snapshot()
    inventory = {
        "source": "KEYCONFIGS_USER",
        "effective_dispatch": "UNKNOWN",
        "maps": [],
        "content_sha256": "raw-content-only",
    }
    document["windows"][0]["keymap_inventory"] = inventory
    state = compile_document(document)
    assert state.require("keymap_inventory") == inventory
    for name in ("keymap", "keymap_version", "popup", "text_focus", "ime_composing"):
        assert state.fact(name).validity == FactValidity.UNKNOWN
    document["windows"][0]["keymap_inventory"] = None
    assert compile_document(document).fact("keymap_inventory").validity == FactValidity.UNKNOWN


def test_xres_pid_wire_byte_length_yields_one_real_pid():
    from clef_use.blender_state import _query_ids

    # XRes 1.2 LocalClientPid reply: one ID, four value bytes, one uint32 PID.
    wire = struct.pack("=BBHII20xIIII", 1, 0, 1, 4, 1, 42, 2, 4, 12345)
    reply, remaining = _query_ids()._reply.parse_binary(wire, None)
    assert reply.ids[0].value == [12345]
    assert remaining == b""


@pytest.mark.skipif(sys.platform != "linux", reason="Linux peer credentials required")
def test_real_socket_requires_fixed_request_and_samples_only_on_pump(tmp_path):
    calls = []
    server = SnapshotServer(
        tmp_path / "observer",
        lambda: calls.append(threading.get_ident()) or {"selection": ["Cube"]},
    )
    assert not server.path.exists()
    server.start()
    responses = []

    def client():
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(1)
            connection.connect(str(server.path))
            assert peer_credentials(connection)[:2] == (os.getpid(), os.getuid())
            connection.sendall(
                json.dumps({"request": "snapshot", "nonce": "a" * 32}).encode() + b"\n"
            )
            responses.append(read_message(connection, 4096))

    worker = threading.Thread(target=client)
    worker.start()
    try:
        deadline = time.monotonic() + 1
        while server.requests.empty() and time.monotonic() < deadline:
            time.sleep(0.001)
        assert calls == []
        server.pump()
        worker.join(timeout=2)
        assert responses == [{"nonce": "a" * 32, "snapshot": {"selection": ["Cube"]}}]
        assert calls == [threading.get_ident()]
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(1)
            connection.connect(str(server.path))
            connection.sendall(
                b'{"request":"execute","nonce":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}\n'
            )
            assert connection.recv(1) == b""
        server.pump()
        assert calls == [threading.get_ident()]
    finally:
        server.close()
        worker.join(timeout=2)
    assert not server.path.exists()


@pytest.mark.skipif(sys.platform != "linux", reason="Linux peer credentials required")
def test_observer_refuses_reuse_of_existing_directory(tmp_path):
    private = tmp_path / "existing"
    private.mkdir(mode=0o700)
    (private / "user.txt").write_text("preserve")
    with pytest.raises(FileExistsError):
        SnapshotServer(private, lambda: {})
    assert (private / "user.txt").read_text() == "preserve"


def test_slow_perception_cannot_publish_new_scene_state_as_matching_old_pixels(monkeypatch):
    import clef_use.state as state_module
    from clef_use.benchmark import FixtureDesktop
    from clef_use.config import Config
    from clef_use.runtime import SessionRuntime
    from clef_use.state import StateFact, StateSource

    clock = [100.0]
    mode = ["OBJECT"]

    class DelayedParser(FixtureDesktop):
        def parse(self, image):
            clock[0] += 2
            mode[0] = "EDIT"
            return super().parse(image)

    def provide(observation, version):
        return {
            "mode": StateFact(
                value=mode[0],
                source=StateSource.APP_TELEMETRY,
                observed_at=clock[0],
                state_version=version,
                validity=FactValidity.VALID,
                uncertainty=0,
            )
        }

    monkeypatch.setattr(state_module.time, "time", lambda: clock[0])
    desktop = DelayedParser()
    runtime = SessionRuntime(
        desktop, desktop, desktop, desktop, Config(activity_overlay=False), state_provider=provide
    )
    result = runtime.observe()
    state = result["compiled_state"]
    assert state["observation_id"] != result["observation_id"]
    assert state["facts"]["mode"]["value"] == "OBJECT"
    assert state["facts"]["mode"]["validity"] == "STALE"
    assert result["observation_fresh"] is True
    assert desktop.stage == 0
