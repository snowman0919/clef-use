"""Pure boundary checks; native bpy collection is exercised separately."""

import math
from types import SimpleNamespace

import pytest


def test_identity_is_process_scoped_and_rejects_null_or_boolean_pointers():
    from clef_use.blender_snapshot import SnapshotUnavailable, _identity

    assert _identity(31, 700) == "31:700"
    assert _identity(32, 700) == "32:700"
    for pid, pointer in [(0, 700), (31, 0), (True, 700), (31, True)]:
        with pytest.raises(SnapshotUnavailable):
            _identity(pid, pointer)


@pytest.fixture
def native_object():
    return SimpleNamespace(
        name_full="Owned",
        session_uid=77,
        mode="OBJECT",
        type="EMPTY",
        location=[-2, 0, 3.25],
        scale=[0.5, 2, 0],
        rotation_mode="XYZ",
        rotation_euler=[0.1, 0.2, 0.3],
        rotation_quaternion=[1, 0, 0, 0],
        rotation_axis_angle=[0, 0, 1, 0],
        parent=None,
        parent_type="OBJECT",
        matrix_parent_inverse=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        delta_location=[1, -1, 0],
        delta_rotation_euler=[0.3, 0.2, 0.1],
        delta_rotation_quaternion=[0, 1, 0, 0],
        delta_scale=[1, 2, 3],
    )


def test_object_identity_survives_rename_and_distinguishes_native_uid_and_process(native_object):
    from clef_use.blender_snapshot import _object

    before = _object(native_object, 31)
    native_object.name_full = "Renamed"
    assert _object(native_object, 31)["id"] == before["id"] == "31:OBJECT:77"
    native_object.session_uid = 78
    assert _object(native_object, 31)["id"] == "31:OBJECT:78"
    assert _object(native_object, 32)["id"] == "32:OBJECT:78"


def test_missing_public_uid_stays_unknown_without_rna_pointer_fallback(native_object):
    from clef_use.blender_snapshot import _object

    del native_object.session_uid

    def unsupported_pointer():
        raise AssertionError("RNA address cannot establish stable object identity")

    native_object.as_pointer = unsupported_pointer
    snapshot = _object(native_object, 31)
    assert snapshot["id"] is None
    assert snapshot["location"] == [-2.0, 0.0, 3.25]


@pytest.mark.parametrize("uid", [None, False, True, 0, -1, 1.0, "77"])
def test_present_invalid_public_uid_refuses_snapshot(native_object, uid):
    from clef_use.blender_snapshot import SnapshotUnavailable, _object

    native_object.session_uid = uid
    with pytest.raises(SnapshotUnavailable):
        _object(native_object, 31)


def test_object_axis_properties_and_complete_transform_baseline_are_preserved(native_object):
    from clef_use.blender_snapshot import _object

    snapshot = _object(native_object, 31)
    assert snapshot["properties"] == {
        "location_x": -2.0,
        "location_y": 0.0,
        "location_z": 3.25,
        "scale_x": 0.5,
        "scale_y": 2.0,
        "scale_z": 0.0,
        "shading": None,
        "shading_observed": False,
    }
    assert snapshot["location"] == [-2.0, 0.0, 3.25]
    assert snapshot["scale"] == [0.5, 2.0, 0.0]
    assert snapshot["rotation_mode"] == "XYZ"
    assert snapshot["rotation_euler_radians"] == [0.1, 0.2, 0.3]
    assert snapshot["rotation_quaternion"] == [1.0, 0.0, 0.0, 0.0]
    assert snapshot["rotation_axis_angle"] == [0.0, 0.0, 1.0, 0.0]
    assert snapshot["parent"] is None and snapshot["parent_type"] == "OBJECT"
    assert snapshot["matrix_parent_inverse"] == native_object.matrix_parent_inverse
    assert snapshot["delta_location"] == [1.0, -1.0, 0.0]
    assert snapshot["delta_rotation_euler_radians"] == [0.3, 0.2, 0.1]
    assert snapshot["delta_rotation_quaternion"] == [0.0, 1.0, 0.0, 0.0]
    assert snapshot["delta_scale"] == [1.0, 2.0, 3.0]


@pytest.mark.parametrize("values", [[1, math.nan, 3], [math.inf, 0, 0], [True, 0, 0], [1, 2]])
def test_transform_values_reject_nonfinite_boolean_and_wrong_dimension(values):
    from clef_use.blender_snapshot import SnapshotUnavailable, _vector

    with pytest.raises(SnapshotUnavailable):
        _vector(values, 3)


def test_vector_preserves_negative_and_zero_numeric_values():
    from clef_use.blender_snapshot import _vector

    assert _vector([-2, 0, 1.25], 3) == [-2.0, 0.0, 1.25]


def test_enum_validation_does_not_coerce_unknown_or_nonidentifier_values():
    from clef_use.blender_snapshot import SnapshotUnavailable, _enum

    assert _enum("AXIS_ANGLE") == "AXIS_ANGLE"
    assert _enum("FUTURE_NATIVE_ENUM") == "FUTURE_NATIVE_ENUM"
    for value in [None, False, "", "Object Mode", "object"]:
        with pytest.raises(SnapshotUnavailable):
            _enum(value)


def test_bounds_refuse_overflow_without_consuming_unbounded_collection():
    from clef_use.blender_snapshot import SnapshotUnavailable, _bounded

    assert _bounded(iter(range(8)), 8, "windows") == list(range(8))
    values = iter(range(1000))
    with pytest.raises(SnapshotUnavailable):
        _bounded(values, 8, "windows")
    assert next(values) == 9


def test_selection_cannot_silently_overwrite_duplicate_native_names():
    from clef_use.blender_snapshot import SnapshotUnavailable, _selection_index

    assert _selection_index([("Cube", {"mode": "OBJECT"})]) == {"Cube": {"mode": "OBJECT"}}
    with pytest.raises(SnapshotUnavailable):
        _selection_index([("Cube", {}), ("Cube", {})])
    with pytest.raises(SnapshotUnavailable):
        _selection_index([("", {})])


def test_shading_never_classifies_empty_or_partial_polygon_reads_as_smooth():
    from clef_use.blender_snapshot import _shading

    assert _shading(iter(()), 0) == (None, False)
    assert _shading(iter([True, True]), 2) == ("SMOOTH", True)
    assert _shading(iter([False, False]), 2) == ("FLAT", True)
    assert _shading(iter([True, False]), 2) == ("MIXED", True)
    assert _shading(iter([True]), 100001) == (None, False)


def test_shading_rejects_missing_or_nonboolean_native_values():
    from clef_use.blender_snapshot import SnapshotUnavailable, _shading

    for values, count in [([True], 2), ([1], 1)]:
        with pytest.raises(SnapshotUnavailable):
            _shading(iter(values), count)


def test_matrix_preserves_rows_and_rejects_ragged_or_nonfinite_geometry():
    from clef_use.blender_snapshot import SnapshotUnavailable, _matrix

    matrix = [[1, 0, 0, 2], [0, 1, 0, 3], [0, 0, 1, 4], [0, 0, 0, 1]]
    assert _matrix(matrix) == matrix
    for bad in [matrix[:3], [*matrix[:3], [0, 0, 1]], [*matrix[:3], [0, 0, math.nan, 1]]]:
        with pytest.raises(SnapshotUnavailable):
            _matrix(bad)


def test_geometry_preserves_clipped_positions_and_hidden_region_dimensions():
    from clef_use.blender_snapshot import SnapshotUnavailable, _geometry

    assert _geometry(SimpleNamespace(x=-1, y=5, width=0, height=20)) == {
        "x": -1,
        "y": 5,
        "width": 0,
        "height": 20,
    }
    for width in [-1, True, 3.5]:
        with pytest.raises(SnapshotUnavailable):
            _geometry(SimpleNamespace(x=0, y=0, width=width, height=20))


def test_viewport_revision_changes_on_quaternion_or_matrix_change():
    from clef_use.blender_snapshot import _viewport

    matrix = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    native = SimpleNamespace(
        as_pointer=lambda: 700,
        view_location=[0, 0, 0],
        view_rotation=[1, 0, 0, 0],
        view_distance=10,
        view_perspective="PERSP",
        view_matrix=matrix,
        perspective_matrix=matrix,
        window_matrix=matrix,
    )
    before = _viewport(native, 31)
    native.view_rotation = [0, 1, 0, 0]
    rotated = _viewport(native, 31)
    assert rotated["view_rotation"] == [0.0, 1.0, 0.0, 0.0]
    assert rotated["id"] == before["id"]
    assert rotated["revision"] != before["revision"]
    native.view_matrix = [[1, 0, 0, 2], *matrix[1:]]
    moved = _viewport(native, 31)
    assert moved["view_matrix"][0][3] == 2.0
    assert moved["revision"] != rotated["revision"]


def keymap_item(**changes):
    values = dict(
        id=7,
        idname="transform.translate",
        active=True,
        type="G",
        value="PRESS",
        key_modifier="NONE",
        repeat=False,
        map_type="KEYBOARD",
        direction="ANY",
        any=False,
        shift=-1,
        ctrl=0,
        alt=1,
        oskey=0,
        hyper=-1,
        propvalue="NONE",
        properties=SimpleNamespace(
            orient_type="GLOBAL", constraint_axis=(True, False, False), release_confirm=False
        ),
    )
    values.update(changes)
    return SimpleNamespace(**values)


def keymap(items, **changes):
    values = dict(
        name="3D View",
        space_type="VIEW_3D",
        region_type="WINDOW",
        is_modal=False,
        bl_owner_id="",
        keymap_items=items,
    )
    values.update(changes)
    return SimpleNamespace(**values)


def keyconfigs(maps):
    return SimpleNamespace(
        user=SimpleNamespace(name="Blender User", keymaps=maps),
        active=SimpleNamespace(name="Blender"),
    )


def test_inventory_keeps_tristate_modifiers_duplicates_and_original_binding_order():
    from clef_use.blender_snapshot import _keymap_inventory

    duplicate = keymap_item(id=8, active=False)
    excluded = keymap_item(idname="wm.open_mainfile")
    inventory = _keymap_inventory(keyconfigs([keymap([excluded, keymap_item(), duplicate])]))
    assert inventory["effective_dispatch"] == "UNKNOWN"
    assert inventory["active_preset_name"] == "Blender"
    bindings = inventory["maps"][0]["items"]
    assert [(item["order"], item["id"], item["active"]) for item in bindings] == [
        (1, 7, True),
        (2, 8, False),
    ]
    assert bindings[0]["modifiers"] == {"shift": -1, "ctrl": 0, "alt": 1, "oskey": 0, "hyper": -1}
    assert bindings[0]["properties"] == {
        "orient_type": "GLOBAL",
        "constraint_axis": [True, False, False],
        "release_confirm": False,
        "confirm_on_release": None,
    }
    assert bindings[0]["properties"]["release_confirm"] is False
    assert all(type(axis) is bool for axis in bindings[0]["properties"]["constraint_axis"])


def test_inventory_only_retains_whitelisted_operators_and_actual_transform_modal_map():
    from clef_use.blender_snapshot import _keymap_inventory

    inventory = _keymap_inventory(
        keyconfigs(
            [
                keymap([keymap_item(idname="wm.open_mainfile")]),
                keymap([keymap_item(idname="", propvalue="CONFIRM")], is_modal=True),
                keymap(
                    [keymap_item(idname="", propvalue="CANCEL")],
                    name="Transform Modal Map",
                    is_modal=True,
                ),
            ]
        )
    )
    assert [entry["order"] for entry in inventory["maps"]] == [2]
    assert inventory["maps"][0]["items"][0]["propvalue"] == "CANCEL"
    assert inventory["scanned_items"] == 3


def test_inventory_retains_each_allowed_operator_and_original_map_context():
    from clef_use.blender_snapshot import _keymap_inventory

    ids = [
        "transform.translate",
        "transform.rotate",
        "transform.resize",
        "wm.search_menu",
        "wm.search_operator",
        "view3d.rotate",
        "view3d.move",
        "object.shade_smooth",
        "object.shade_flat",
    ]
    maps = [
        keymap([], name="Unrelated Map"),
        keymap(
            [keymap_item(idname=identifier) for identifier in ids],
            name="Custom Context",
            space_type="EMPTY",
            region_type="HEADER",
            bl_owner_id="own_workspace",
        ),
    ]
    inventory = _keymap_inventory(keyconfigs(maps))
    retained = inventory["maps"][0]
    assert (
        retained["order"],
        retained["name"],
        retained["space_type"],
        retained["region_type"],
    ) == (
        1,
        "Custom Context",
        "EMPTY",
        "HEADER",
    )
    assert retained["bl_owner_id"] == "own_workspace"
    assert [item["idname"] for item in retained["items"]] == ids


@pytest.mark.parametrize(
    "properties",
    [
        SimpleNamespace(release_confirm=1),
        SimpleNamespace(confirm_on_release=0.0),
        SimpleNamespace(constraint_axis=(1, 0, 0)),
        SimpleNamespace(constraint_axis=(True, False)),
    ],
)
def test_inventory_property_booleans_and_axis_dimensions_cannot_be_coerced(properties):
    from clef_use.blender_snapshot import SnapshotUnavailable, _keymap_inventory

    with pytest.raises(SnapshotUnavailable):
        _keymap_inventory(keyconfigs([keymap([keymap_item(properties=properties)])]))


def test_inventory_content_digest_tracks_disabled_binding_and_preset_changes():
    from clef_use.blender_snapshot import _keymap_inventory

    configs = keyconfigs([keymap([keymap_item()])])
    original = _keymap_inventory(configs)["content_sha256"]
    configs.user.keymaps[0].keymap_items[0].active = False
    disabled = _keymap_inventory(configs)["content_sha256"]
    assert disabled != original
    configs.active.name = "Industry Compatible"
    assert _keymap_inventory(configs)["content_sha256"] != disabled


def test_inventory_does_not_read_arbitrary_operator_properties_or_pointer_identity():
    from clef_use.blender_snapshot import _keymap_inventory

    class Properties:
        orient_type = "LOCAL"

        @property
        def filepath(self):
            raise AssertionError("private property must not be accessed")

    item = keymap_item(properties=Properties())
    configs = keyconfigs([keymap([item])])
    before = _keymap_inventory(configs)
    item.as_pointer = lambda: 123456
    configs.user.as_pointer = lambda: 123456
    assert _keymap_inventory(configs)["content_sha256"] == before["content_sha256"]
    assert before["maps"][0]["items"][0]["properties"]["constraint_axis"] is None


def test_inventory_unavailable_config_and_missing_optional_hyper_stay_unknown():
    from clef_use.blender_snapshot import _keymap_inventory

    assert _keymap_inventory(None) is None
    assert _keymap_inventory(SimpleNamespace(user=None)) is None
    item = keymap_item()
    del item.hyper
    configs = keyconfigs([keymap([item])])
    configs.active = None
    inventory = _keymap_inventory(configs)
    assert inventory["active_preset_name"] is None
    assert inventory["maps"][0]["items"][0]["modifiers"]["hyper"] is None


@pytest.mark.parametrize("value", [True, -2, 2, None, "ANY"])
def test_inventory_refuses_invalid_modifiers_instead_of_coercing_to_boolean(value):
    from clef_use.blender_snapshot import SnapshotUnavailable, _keymap_inventory

    with pytest.raises(SnapshotUnavailable):
        _keymap_inventory(keyconfigs([keymap([keymap_item(shift=value)])]))


@pytest.mark.parametrize("boundary", ["maps", "scanned_items", "retained_items"])
def test_inventory_exact_caps_and_overflow_refuse_without_truncation(boundary):
    from clef_use.blender_snapshot import SnapshotUnavailable, _keymap_inventory

    excluded = keymap_item(idname="wm.open_mainfile")
    if boundary == "maps":
        maps = [keymap([]) for _ in range(512)]
        assert _keymap_inventory(keyconfigs(maps))["scanned_maps"] == 512
        maps.append(keymap([]))
    elif boundary == "scanned_items":
        maps = [keymap([excluded] * 8192), keymap([excluded] * 8192)]
        assert _keymap_inventory(keyconfigs(maps))["scanned_items"] == 16384
        maps[1].keymap_items.append(excluded)
    else:
        maps = [keymap([keymap_item()] * 128), keymap([keymap_item()] * 128)]
        assert sum(len(m["items"]) for m in _keymap_inventory(keyconfigs(maps))["maps"]) == 256
        maps[1].keymap_items.append(keymap_item())
    with pytest.raises(SnapshotUnavailable):
        _keymap_inventory(keyconfigs(maps))


def workspace_tool(idname="builtin.select_box", space_type="VIEW_3D", mode="OBJECT"):
    return SimpleNamespace(idname=idname, space_type=space_type, mode=mode)


def native_reference(pointer):
    return SimpleNamespace(as_pointer=lambda: pointer)


def tool_context():
    window = SimpleNamespace(
        as_pointer=lambda: 11,
        workspace=native_reference(22),
        view_layer=native_reference(33),
    )
    context = SimpleNamespace(
        window=native_reference(11),
        workspace=native_reference(22),
        view_layer=native_reference(33),
        mode="EDIT_MESH",
    )
    return context, window


def test_workspace_tools_preserve_mode_order_duplicates_and_uninitialized_identifiers():
    from clef_use.blender_snapshot import _workspace_tools

    observed = [
        workspace_tool(mode="EDIT_MESH"),
        workspace_tool(),
        workspace_tool("", mode="SCULPT"),
        workspace_tool("custom.select", mode="EDIT_MESH"),
        workspace_tool("custom.node", space_type="NODE_EDITOR", mode="DEFAULT"),
    ]
    assert _workspace_tools(observed) == [
        {"idname": "builtin.select_box", "space_type": "VIEW_3D", "mode": "EDIT_MESH"},
        {"idname": "builtin.select_box", "space_type": "VIEW_3D", "mode": "OBJECT"},
        {"idname": "", "space_type": "VIEW_3D", "mode": "SCULPT"},
        {"idname": "custom.select", "space_type": "VIEW_3D", "mode": "EDIT_MESH"},
        {"idname": "custom.node", "space_type": "NODE_EDITOR", "mode": "DEFAULT"},
    ]


@pytest.mark.parametrize(
    "tool",
    [
        workspace_tool(idname=None),
        workspace_tool(idname="custom.\x00tool"),
        workspace_tool(space_type="view3d"),
        workspace_tool(mode=None),
        workspace_tool(mode="Object Mode"),
    ],
)
def test_workspace_tools_refuse_malformed_native_text_and_enum(tool):
    from clef_use.blender_snapshot import SnapshotUnavailable, _workspace_tools

    with pytest.raises(SnapshotUnavailable):
        _workspace_tools([tool])


def test_workspace_tool_cap_accepts_exact_bound_and_refuses_overflow_without_truncation():
    from clef_use.blender_snapshot import SnapshotUnavailable, _workspace_tools

    tools = [workspace_tool(idname=f"custom.tool_{i}") for i in range(130)]
    assert _workspace_tools(tools[:128]) == [vars(tool) for tool in tools[:128]]
    unbounded = iter(tools)
    with pytest.raises(SnapshotUnavailable, match="workspace tools limit"):
        _workspace_tools(unbounded)
    assert next(unbounded).idname == "custom.tool_129"


def test_tool_context_mode_binds_native_pointers_not_python_wrapper_identity():
    from clef_use.blender_snapshot import _tool_context_mode

    context, window = tool_context()
    assert context.window is not window
    assert context.workspace is not window.workspace
    assert _tool_context_mode(context, window) == "EDIT_MESH"
    context.mode = "SCULPT"
    assert _tool_context_mode(context, window) == "SCULPT"


@pytest.mark.parametrize("name", ["window", "workspace", "view_layer"])
def test_tool_context_mode_requires_every_owning_window_context_binding(name):
    from clef_use.blender_snapshot import _tool_context_mode

    context, window = tool_context()
    setattr(context, name, native_reference(99))
    assert _tool_context_mode(context, window) is None


@pytest.mark.parametrize("name", ["window", "workspace", "view_layer", "mode"])
def test_missing_native_context_never_falls_back_to_object_mode(name):
    from clef_use.blender_snapshot import _tool_context_mode

    context, window = tool_context()
    window.view_layer.objects = SimpleNamespace(active=SimpleNamespace(mode="OBJECT"))
    delattr(context, name)
    assert _tool_context_mode(context, window) is None


def test_context_mode_does_not_read_mode_from_an_unbound_window():
    from clef_use.blender_snapshot import _tool_context_mode

    context, window = tool_context()

    class ForeignContext:
        window = native_reference(99)
        workspace = context.workspace
        view_layer = context.view_layer

        @property
        def mode(self):
            raise AssertionError("foreign context mode cannot establish this window's tool")

    assert _tool_context_mode(ForeignContext(), window) is None


def test_tool_context_mode_rejects_malformed_bound_native_enum():
    from clef_use.blender_snapshot import SnapshotUnavailable, _tool_context_mode

    context, window = tool_context()
    context.mode = "Edit Mesh"
    with pytest.raises(SnapshotUnavailable):
        _tool_context_mode(context, window)
