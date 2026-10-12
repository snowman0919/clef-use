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
