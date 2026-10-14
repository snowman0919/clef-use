"""Typed busy evidence through the collector/compiler; native proof is separate."""

import json
import os
import sys
from types import SimpleNamespace

import pytest
from PIL import Image

from clef_use.blender_snapshot import SnapshotUnavailable, collect_snapshot
from clef_use.blender_state import compile_snapshot
from clef_use.schema import Frame, Observation
from clef_use.state import FactValidity, StateCompiler, StateSource

MISSING = object()


def native_manager(locked=MISSING, pointer=10):
    objects = type("Objects", (list,), {"active": None})()
    layer = SimpleNamespace(name="ViewLayer", objects=objects, as_pointer=lambda: pointer + 3)
    workspace = SimpleNamespace(tools=[], as_pointer=lambda: pointer + 2)
    scene = SimpleNamespace(
        name_full="Scene",
        as_pointer=lambda: pointer + 4,
        unit_settings=SimpleNamespace(
            system="NONE", length_unit="ADAPTIVE", system_rotation="RADIANS", scale_length=1
        ),
        transform_orientation_slots=[],
        tool_settings=SimpleNamespace(transform_pivot_point="MEDIAN_POINT"),
    )
    window = SimpleNamespace(
        as_pointer=lambda: pointer + 1,
        workspace=workspace,
        scene=scene,
        view_layer=layer,
        width=100,
        height=80,
        screen=SimpleNamespace(areas=[]),
        modal_operators=[],
    )
    manager = SimpleNamespace(as_pointer=lambda: pointer, windows=[window])
    if locked is not MISSING:
        manager.is_interface_locked = locked
    return manager


def collect(monkeypatch, managers, context_manager=None):
    manager = context_manager or managers[0]
    window = manager.windows[0]
    monkeypatch.setitem(
        sys.modules,
        "bpy",
        SimpleNamespace(
            data=SimpleNamespace(window_managers=managers),
            app=SimpleNamespace(version=(5, 2, 0)),
            context=SimpleNamespace(
                window=window,
                window_manager=manager,
                workspace=window.workspace,
                view_layer=window.view_layer,
                mode="OBJECT",
            ),
        ),
    )
    monkeypatch.setattr("clef_use.blender_snapshot.time.time", lambda: 1000.0)
    return json.loads(json.dumps(collect_snapshot()))


def compile_document(document, **changes):
    frame = Frame(
        Image.new("RGB", (100, 80)), foreground_window=42, foreground_bounds=(0, 0, 100, 80)
    )
    arguments = dict(
        pid=os.getpid(), frame=frame, version=1, started_at=999.99, completed_at=1000.01
    )
    arguments.update(changes)
    facts = compile_snapshot(document, **arguments)
    return StateCompiler().compile(Observation("busy", frame, ()), facts)


def test_native_interface_lock_establishes_positive_busy_with_bound_provenance(monkeypatch):
    document = collect(monkeypatch, [native_manager(True)])
    state = compile_document(document)
    fact = state.fact("loading")
    assert state.require("loading") is True
    assert fact.source == StateSource.APP_TELEMETRY
    assert fact.observed_at == document["sampled_at"]
    assert fact.state_version == state.version
    for name in ("popup", "text_focus", "ime_composing", "keymap", "editor", "modal"):
        assert state.fact(name).validity == FactValidity.UNKNOWN


@pytest.mark.parametrize("locked", [False, None, MISSING])
def test_unlocked_or_unavailable_native_property_never_establishes_global_idle(monkeypatch, locked):
    document = collect(monkeypatch, [native_manager(locked)])
    assert document["windows"][0]["interface_locked"] is (None if locked is MISSING else locked)
    assert compile_document(document).fact("loading").validity == FactValidity.UNKNOWN


@pytest.mark.parametrize("locked", [0, 1, "true", "false", {}, []])
def test_malformed_native_interface_lock_refuses_collection(monkeypatch, locked):
    with pytest.raises(SnapshotUnavailable):
        collect(monkeypatch, [native_manager(locked)])


@pytest.mark.parametrize("own_lock,foreign_lock", [(True, False), (False, True)])
def test_busy_comes_from_owning_manager_without_context_manager_fallback(
    monkeypatch, own_lock, foreign_lock
):
    document = collect(
        monkeypatch, [native_manager(own_lock)], context_manager=native_manager(foreign_lock, 20)
    )
    state = compile_document(document)
    if own_lock:
        assert state.require("loading") is True
    else:
        assert state.fact("loading").validity == FactValidity.UNKNOWN


@pytest.mark.parametrize("locked", [False, None, 0, 1, "true", "false", {}, []])
def test_compiler_accepts_only_exact_positive_boolean(monkeypatch, locked):
    document = collect(monkeypatch, [native_manager()])
    document["windows"][0]["interface_locked"] = locked
    assert compile_document(document).fact("loading").validity == FactValidity.UNKNOWN


@pytest.mark.parametrize("change", ["pid", "stale", "window", "geometry"])
def test_positive_lock_cannot_bypass_snapshot_binding_or_freshness(monkeypatch, change):
    document = collect(monkeypatch, [native_manager(True)])
    arguments = {}
    if change == "pid":
        document["pid"] += 1
    elif change == "stale":
        document["sampled_at"] -= 1
    elif change == "window":
        document["windows"].append(document["windows"][0])
    else:
        document["windows"][0]["width"] += 1
    with pytest.raises(ValueError):
        compile_document(document, **arguments)
