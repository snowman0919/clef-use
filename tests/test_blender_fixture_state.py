import ast
import runpy
from collections import namedtuple
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

Vector = namedtuple("Vector", "x y z")


def fixture_state(system, length_unit, scale, rotation_unit):
    """Execute the real embedded reader without its UI/socket setup side effects."""
    script = Path(__file__).resolve().parents[1] / "scripts/blender_operations_fixture.py"
    startup = runpy.run_path(str(script))["STARTUP"]
    definition = next(
        node
        for node in ast.parse(startup).body
        if isinstance(node, ast.FunctionDef) and node.name == "state"
    )
    cube = NS(
        name="Cube",
        session_uid=42,
        mode="OBJECT",
        parent=None,
        location=Vector(2.0, -3.0, 0.5),
        rotation_euler=Vector(0.1, 0.0, 0.0),
        scale=Vector(1.5, 1.0, 1.0),
        delta_location=Vector(0, 0, 0),
        delta_rotation_euler=Vector(0, 0, 0),
        delta_scale=Vector(1, 1, 1),
        data=NS(polygons=[NS(use_smooth=False)]),
        select_get=lambda: True,
    )
    units = NS(
        system=system, length_unit=length_unit, scale_length=scale, system_rotation=rotation_unit
    )
    scene = NS(
        unit_settings=units,
        as_pointer=lambda: 1,
        transform_orientation_slots=[NS(type="GLOBAL")],
        tool_settings=NS(transform_pivot_point="MEDIAN_POINT"),
    )
    window = NS(
        scene=scene, view_layer=NS(objects=[cube]), width=800, height=600, screen=NS(areas=[])
    )
    manager = NS(keyconfigs=NS(default=NS(keymaps=[])), operators=[])
    view = NS(
        spaces=NS(
            active=NS(
                region_3d=NS(view_location=[0, 0, 0], view_rotation=[1, 0, 0, 0], view_distance=10)
            )
        )
    )
    import math
    import os

    namespace = {
        "bpy": NS(app=NS(version_string="test"), context=NS(window_manager=manager)),
        "win": window,
        "view": view,
        "cube": cube,
        "binding": lambda *args: None,
        "math": math,
        "os": os,
    }
    exec(compile(ast.Module(body=[definition], type_ignores=[]), str(script), "exec"), namespace)
    return namespace["state"]()


@pytest.mark.parametrize(
    "system,unit,scale,expected",
    [
        ("NONE", "CENTIMETERS", 100.0, (2.0, -3.0, 0.5)),
        ("METRIC", "METERS", 0.01, (0.02, -0.03, 0.005)),
        ("METRIC", "METERS", 1.0, (2.0, -3.0, 0.5)),
        ("METRIC", "METERS", 100.0, (200.0, -300.0, 50.0)),
        ("METRIC", "CENTIMETERS", 1.0, (200.0, -300.0, 50.0)),
    ],
)
def test_fixture_distance_readback_uses_declared_supported_unit(system, unit, scale, expected):
    state = fixture_state(system, unit, scale, "DEGREES")
    values = state["transform_values"]["Cube"]
    assert tuple(values["translate"][axis] for axis in "XYZ") == pytest.approx(expected)
    assert state["unit"]["translate"] == ("NONE" if system == "NONE" else unit)
    assert state["transform_preview"] == state["transform_values"]
    assert state["properties"]["Cube"] == {"location_x": 2.0, "scale_x": 1.5, "shading": "FLAT"}
    assert values["scale"] == {"X": 1.5, "Y": 1.0, "Z": 1.0}


@pytest.mark.parametrize("unit,expected", [("DEGREES", 5.729577951308233), ("RADIANS", 0.1)])
def test_fixture_angular_readback_matches_declared_unit_without_changing_properties(unit, expected):
    state = fixture_state("NONE", "ADAPTIVE", 1.0, unit)
    assert state["unit"]["rotate"] == unit
    assert state["transform_values"]["Cube"]["rotate"] == pytest.approx(
        {"X": expected, "Y": 0.0, "Z": 0.0}
    )
    assert state["properties"]["Cube"]["location_x"] == 2.0


def test_unsupported_distance_unit_preserves_other_channels_without_admitting_translation():
    from clef_use.operations import parse_operation_request

    state = fixture_state("METRIC", "ADAPTIVE", 100.0, "RADIANS")
    assert state["transform_values"]["Cube"]["translate"] == {"X": 2.0, "Y": -3.0, "Z": 0.5}
    with pytest.raises(ValueError):
        parse_operation_request(
            dict(
                family="numeric_transform",
                target_id="Cube",
                operation="translate",
                axis="X",
                space="GLOBAL",
                unit=state["unit"]["translate"],
                amount=2,
                keymap_version="fixture",
            )
        )
