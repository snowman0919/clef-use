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
