"""Read-only, bounded Blender public-RNA snapshots, without input authority.

Call ``collect_snapshot`` from Blender's UI thread. Importing this module does
not import bpy and needs only the standard library. Coordinates are unmodified
window pixels with Blender's bottom-left origin; rotations retain their native
representation (Euler values are radians). Window/area/region/operator IDs are
process-scoped RNA pointers, never OS window IDs.

``positive_modal_operators`` is positive-only evidence. None means unavailable;
an empty list does NOT establish absence of popups, text editing, modal UI
handlers, or other input owners. Popup, text-focus, IME, effective keymap, and
global busy/idle facts are intentionally absent. A caller must independently
bind the process/window and freshness before consuming even the observed facts.
``keymap_inventory`` reads the owning manager's merged user configuration, not
effective dispatch. Its digest identifies retained content, not input authority.

The document includes all windows (up to 8), all selected objects (64 across
windows), and all area regions (128 across windows), refusing overflow rather
than silently truncating. Mesh shading above 100000 polygons is unobserved.
No operators, context overrides, filesystem, network, or scene writes occur.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import re
import threading
import time
from collections.abc import Iterable
from typing import Any, Literal, TypedDict

MAX_WINDOWS = 8
MAX_SELECTED_OBJECTS = 64
MAX_VIEW_LAYER_OBJECTS = 4096
MAX_REGIONS = 128
MAX_MODAL_OPERATORS = 128
MAX_SHADING_POLYGONS = 100000
MAX_KEYMAPS = 512
MAX_SCANNED_KEYMAP_ITEMS = 16384
MAX_RETAINED_KEYMAP_ITEMS = 256
KEYMAP_OPERATORS = frozenset(
    {
        "transform.translate",
        "transform.rotate",
        "transform.resize",
        "wm.search_menu",
        "wm.search_operator",
        "view3d.rotate",
        "view3d.move",
        "object.shade_smooth",
        "object.shade_flat",
    }
)


class SnapshotUnavailable(ValueError):
    """The complete bounded snapshot cannot be safely represented."""


class Geometry(TypedDict):
    x: int
    y: int
    width: int
    height: int


class ObjectSnapshot(TypedDict):
    mode: str
    type: str
    location: list[float]
    rotation_mode: str
    rotation_euler_radians: list[float]
    rotation_quaternion: list[float]
    rotation_axis_angle: list[float]
    scale: list[float]
    parent: str | None
    parent_type: str
    matrix_parent_inverse: list[list[float]]
    delta_location: list[float]
    delta_rotation_euler_radians: list[float]
    delta_rotation_quaternion: list[float]
    delta_scale: list[float]
    properties: dict[str, float | str | bool | None]


class ViewportSnapshot(TypedDict):
    id: str
    view_location: list[float]
    view_rotation: list[float]
    view_distance: float
    view_perspective: str
    view_matrix: list[list[float]]
    perspective_matrix: list[list[float]]
    window_matrix: list[list[float]]
    revision: str


class RegionSnapshot(TypedDict):
    id: str
    type: str
    geometry_window_pixels_bottom_left: Geometry


class AreaSnapshot(TypedDict):
    id: str
    type: str
    geometry_window_pixels_bottom_left: Geometry
    regions: list[RegionSnapshot]
    viewport: ViewportSnapshot | None
    quad_views: list[ViewportSnapshot]


class ModalOperatorSnapshot(TypedDict):
    id: str
    name: str | None
    rna: str


class KeymapItemSnapshot(TypedDict):
    order: int
    id: int
    idname: str
    active: bool
    type: str
    value: str
    key_modifier: str
    repeat: bool
    map_type: str
    direction: str | None
    any: bool
    modifiers: dict[str, int | None]
    propvalue: str | None
    properties: dict[str, str | list[bool] | bool | None]


class KeymapSnapshot(TypedDict):
    order: int
    name: str
    space_type: str
    region_type: str
    is_modal: bool
    bl_owner_id: str
    items: list[KeymapItemSnapshot]


class KeymapInventory(TypedDict):
    source: Literal["KEYCONFIGS_USER"]
    user_config_name: str
    active_preset_name: str | None
    effective_dispatch: Literal["UNKNOWN"]
    maps: list[KeymapSnapshot]
    scanned_maps: int
    scanned_items: int
    content_sha256: str


class WindowSnapshot(TypedDict):
    id: str
    width: int
    height: int
    scene_id: str
    scene_identity: str
    view_layer: str
    active_object_id: str | None
    active_object_mode: str | None
    selection: list[str]
    objects: dict[str, ObjectSnapshot]
    unit_settings: dict[str, str | float]
    orientations: list[str]
    pivot: str
    areas: list[AreaSnapshot]
    positive_modal_operators: list[ModalOperatorSnapshot] | None
    keymap_inventory: KeymapInventory | None


class BlenderSnapshot(TypedDict):
    schema_version: Literal[1]
    source: Literal["BLENDER_PUBLIC_RNA"]
    pid: int
    blender_version: list[int]
    sampled_at: float
    monotonic_ns: int
    completed_at: float
    completed_monotonic_ns: int
    windows: list[WindowSnapshot]


def _integer(value: Any, *, minimum: int | None = 0) -> int:
    if type(value) is not int or (minimum is not None and value < minimum):
        raise SnapshotUnavailable("Invalid native integer")
    return value


def _identity(pid: int, pointer: int) -> str:
    return f"{_integer(pid, minimum=1)}:{_integer(pointer, minimum=1)}"


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SnapshotUnavailable("Invalid native numeric value")
    result = float(value)
    if not math.isfinite(result):
        raise SnapshotUnavailable("Nonfinite native numeric value")
    return result


def _bounded(values: Iterable[Any], maximum: int, label: str) -> list[Any]:
    result = list(itertools.islice(values, maximum + 1))
    if len(result) > maximum:
        raise SnapshotUnavailable(f"Snapshot {label} limit exceeded")
    return result


def _vector(values: Iterable[Any], size: int) -> list[float]:
    result = _bounded(values, size, "vector dimension")
    if len(result) != size:
        raise SnapshotUnavailable("Invalid native vector dimension")
    return [_number(value) for value in result]


def _matrix(values: Iterable[Any]) -> list[list[float]]:
    rows = _bounded(values, 4, "matrix dimension")
    if len(rows) != 4:
        raise SnapshotUnavailable("Invalid native matrix dimension")
    return [_vector(row, 4) for row in rows]


def _name(value: Any) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise SnapshotUnavailable("Invalid native name")
    return value


def _enum(value: Any) -> str:
    # Preserve future native enum identifiers; do not invent a fallback enum.
    if not isinstance(value, str) or re.fullmatch(r"[A-Z][A-Z0-9_]*", value) is None:
        raise SnapshotUnavailable("Invalid native enum identifier")
    return value


def _text(value: Any) -> str:
    if not isinstance(value, str) or "\x00" in value:
        raise SnapshotUnavailable("Invalid native text")
    return value


def _boolean(value: Any) -> bool:
    if type(value) is not bool:
        raise SnapshotUnavailable("Invalid native boolean")
    return value


def _modifier(value: Any) -> int:
    if type(value) is not int or value not in (-1, 0, 1):
        raise SnapshotUnavailable("Invalid native tri-state modifier")
    return value


def _keymap_properties(value: Any) -> dict[str, str | list[bool] | bool | None]:
    """Read only explicitly allowed operator settings, never arbitrary properties."""
    result = {}
    for name in ("orient_type", "constraint_axis", "release_confirm", "confirm_on_release"):
        observed = getattr(value, name, None)
        if observed is None:
            result[name] = None
        elif name == "orient_type":
            result[name] = _text(observed)
        elif name == "constraint_axis":
            axes = _bounded(observed, 3, "constraint axes")
            if len(axes) != 3:
                raise SnapshotUnavailable("Invalid native constraint axes")
            result[name] = [_boolean(axis) for axis in axes]
        else:
            result[name] = _boolean(observed)
    return result


def _keymap_item(item: Any, order: int, modal: bool) -> KeymapItemSnapshot:
    absent = object()
    hyper = getattr(item, "hyper", absent)
    direction = getattr(item, "direction", None)
    return {
        "order": order,
        "id": _integer(item.id, minimum=None),
        "idname": _text(item.idname),
        "active": _boolean(item.active),
        "type": _enum(item.type),
        "value": _enum(item.value),
        "key_modifier": _enum(item.key_modifier),
        "repeat": _boolean(item.repeat),
        "map_type": _enum(item.map_type),
        "direction": _enum(direction) if direction is not None else None,
        "any": _boolean(item.any),
        "modifiers": {
            **{name: _modifier(getattr(item, name)) for name in ("shift", "ctrl", "alt", "oskey")},
            "hyper": None if hyper is absent else _modifier(hyper),
        },
        "propvalue": _text(item.propvalue) if modal else None,
        "properties": _keymap_properties(item.properties),
    }


def _keymap_inventory(keyconfigs: Any) -> KeymapInventory | None:
    """Bounded raw user-keyconfig inventory; never resolves polling or dispatch.

    Caps apply to one owning manager's configuration: 512 scanned maps, 16384
    scanned items across all maps, and 256 retained items across matching maps.
    Original order, duplicate bindings and inactive items remain distinct. The
    hash covers configuration names and retained maps/items with canonical JSON;
    it excludes process-local pointers and unrelated map/item scan counts.
    """
    user = getattr(keyconfigs, "user", None)
    if user is None:
        return None
    active = getattr(keyconfigs, "active", None)
    maps: list[KeymapSnapshot] = []
    scanned_maps = scanned_items = retained_items = 0
    for map_order, keymap in enumerate(_bounded(user.keymaps, MAX_KEYMAPS, "keymaps")):
        scanned_maps += 1
        modal = _boolean(keymap.is_modal)
        retain_modal = modal and keymap.name == "Transform Modal Map"
        items: list[KeymapItemSnapshot] = []
        for item_order, item in enumerate(keymap.keymap_items):
            scanned_items += 1
            if scanned_items > MAX_SCANNED_KEYMAP_ITEMS:
                raise SnapshotUnavailable("Snapshot scanned keymap items limit exceeded")
            if retain_modal or item.idname in KEYMAP_OPERATORS:
                retained_items += 1
                if retained_items > MAX_RETAINED_KEYMAP_ITEMS:
                    raise SnapshotUnavailable("Snapshot retained keymap items limit exceeded")
                items.append(_keymap_item(item, item_order, modal))
        if items or retain_modal:
            maps.append(
                {
                    "order": map_order,
                    "name": _text(keymap.name),
                    "space_type": _enum(keymap.space_type),
                    "region_type": _enum(keymap.region_type),
                    "is_modal": modal,
                    "bl_owner_id": _text(keymap.bl_owner_id),
                    "items": items,
                }
            )
    content = {
        "user_config_name": _text(user.name),
        "active_preset_name": _text(active.name) if active is not None else None,
        "maps": maps,
    }
    digest = hashlib.sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
    ).hexdigest()
    return {
        "source": "KEYCONFIGS_USER",
        **content,
        "effective_dispatch": "UNKNOWN",
        "scanned_maps": scanned_maps,
        "scanned_items": scanned_items,
        "content_sha256": digest,
    }


def _selection_index(entries: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for name, value in entries:
        name = _name(name)
        if name in result:
            raise SnapshotUnavailable("Selected object names are not unique")
        result[name] = value
    return result


def _shading(values: Iterable[bool], count: int) -> tuple[str | None, bool]:
    count = _integer(count)
    if count == 0 or count > MAX_SHADING_POLYGONS:
        return None, False
    smooth = flat = False
    iterator = iter(values)
    for _ in range(count):
        value = next(iterator, None)
        if type(value) is not bool:
            raise SnapshotUnavailable("Incomplete or invalid native shading readback")
        smooth |= value
        flat |= not value
    return ("MIXED" if smooth and flat else "SMOOTH" if smooth else "FLAT"), True


def _geometry(value: Any) -> Geometry:
    # Hidden/non-window regions can legitimately have zero width or height.
    return {
        "x": _integer(value.x, minimum=None),
        "y": _integer(value.y, minimum=None),
        "width": _integer(value.width),
        "height": _integer(value.height),
    }


def _object(value: Any) -> ObjectSnapshot:
    location = _vector(value.location, 3)
    scale = _vector(value.scale, 3)
    object_type = _enum(value.type)
    shading, shading_observed = (None, False)
    if object_type == "MESH" and value.data is not None:
        polygons = value.data.polygons
        shading, shading_observed = _shading(
            (polygon.use_smooth for polygon in polygons), len(polygons)
        )
    return {
        "mode": _enum(value.mode),
        "type": object_type,
        "location": location,
        "rotation_mode": _enum(value.rotation_mode),
        "rotation_euler_radians": _vector(value.rotation_euler, 3),
        "rotation_quaternion": _vector(value.rotation_quaternion, 4),
        "rotation_axis_angle": _vector(value.rotation_axis_angle, 4),
        "scale": scale,
        "parent": _name(value.parent.name_full) if value.parent is not None else None,
        "parent_type": _enum(value.parent_type),
        "matrix_parent_inverse": _matrix(value.matrix_parent_inverse),
        "delta_location": _vector(value.delta_location, 3),
        "delta_rotation_euler_radians": _vector(value.delta_rotation_euler, 3),
        "delta_rotation_quaternion": _vector(value.delta_rotation_quaternion, 4),
        "delta_scale": _vector(value.delta_scale, 3),
        "properties": {
            "location_x": location[0],
            "scale_x": scale[0],
            "shading": shading,
            "shading_observed": shading_observed,
        },
    }


def _viewport(value: Any, pid: int) -> ViewportSnapshot:
    content = {
        "view_location": _vector(value.view_location, 3),
        "view_rotation": _vector(value.view_rotation, 4),
        "view_distance": _number(value.view_distance),
        "view_perspective": _enum(value.view_perspective),
        "view_matrix": _matrix(value.view_matrix),
        "perspective_matrix": _matrix(value.perspective_matrix),
        "window_matrix": _matrix(value.window_matrix),
    }
    revision = hashlib.sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
    ).hexdigest()
    return {"id": _identity(pid, value.as_pointer()), **content, "revision": revision}


def collect_snapshot() -> BlenderSnapshot:
    """Sample all Blender windows on the UI thread, or refuse incomplete bounds.

    Native references/enum values/geometry remain uninterpreted observations.
    This is not an authorization, OS-window binding, or absence detector. RNA
    collection exceptions propagate; no partial snapshot is returned on error.
    """
    if threading.current_thread() is not threading.main_thread():
        raise SnapshotUnavailable("Blender RNA collection requires the UI thread")
    import bpy

    pid = os.getpid()
    started_wall, started_monotonic = time.time(), time.monotonic_ns()
    native_windows = _bounded(
        ((manager, window) for manager in bpy.data.window_managers for window in manager.windows),
        MAX_WINDOWS,
        "windows",
    )
    windows: list[WindowSnapshot] = []
    window_ids: set[str] = set()
    keymaps: dict[str, KeymapInventory | None] = {}
    selected_count = region_count = modal_count = 0
    for manager, window in native_windows:
        window_id = _identity(pid, window.as_pointer())
        if window_id in window_ids:
            raise SnapshotUnavailable("Duplicate native window identity")
        window_ids.add(window_id)
        manager_id = _identity(pid, manager.as_pointer())
        if manager_id not in keymaps:
            keymaps[manager_id] = _keymap_inventory(getattr(manager, "keyconfigs", None))
        scene, layer = window.scene, window.view_layer
        layer_objects = _bounded(layer.objects, MAX_VIEW_LAYER_OBJECTS, "view layer objects")
        selected = _bounded(
            (obj for obj in layer_objects if obj.select_get(view_layer=layer)),
            MAX_SELECTED_OBJECTS - selected_count,
            "selected objects",
        )
        selected_count += len(selected)
        objects = _selection_index((_name(obj.name_full), _object(obj)) for obj in selected)
        active = layer.objects.active
        areas: list[AreaSnapshot] = []
        for area in _bounded(window.screen.areas, MAX_REGIONS, "areas"):
            native_regions = _bounded(area.regions, MAX_REGIONS - region_count, "regions")
            region_count += len(native_regions)
            regions: list[RegionSnapshot] = [
                {
                    "id": _identity(pid, region.as_pointer()),
                    "type": _enum(region.type),
                    "geometry_window_pixels_bottom_left": _geometry(region),
                }
                for region in native_regions
            ]
            viewport, quad_views = None, []
            if area.type == "VIEW_3D":
                space = area.spaces.active
                if space.region_3d is not None:
                    viewport = _viewport(space.region_3d, pid)
                # Do not guess a quad-view-to-region association from list order.
                quad_views = [
                    _viewport(view, pid)
                    for view in _bounded(space.region_quadviews, 4, "quad views")
                ]
            areas.append(
                {
                    "id": _identity(pid, area.as_pointer()),
                    "type": _enum(area.type),
                    "geometry_window_pixels_bottom_left": _geometry(area),
                    "regions": regions,
                    "viewport": viewport,
                    "quad_views": quad_views,
                }
            )
        native_modals = getattr(window, "modal_operators", None)
        modals = None
        if native_modals is not None:
            positive = _bounded(
                native_modals, MAX_MODAL_OPERATORS - modal_count, "positive modal operators"
            )
            modal_count += len(positive)
            modals = [
                {
                    "id": _identity(pid, operator.as_pointer()),
                    "name": _name(name) if (name := getattr(operator, "bl_idname", None)) else None,
                    "rna": _name(operator.bl_rna.identifier),
                }
                for operator in positive
            ]
        units = scene.unit_settings
        windows.append(
            {
                "id": window_id,
                "width": _integer(window.width, minimum=1),
                "height": _integer(window.height, minimum=1),
                "scene_id": _name(scene.name_full),
                "scene_identity": _identity(pid, scene.as_pointer()),
                "view_layer": _name(layer.name),
                "active_object_id": _name(active.name_full) if active is not None else None,
                "active_object_mode": _enum(active.mode) if active is not None else None,
                "selection": list(objects),
                "objects": objects,
                "unit_settings": {
                    "system": _enum(units.system),
                    "length_unit": _enum(units.length_unit),
                    "system_rotation": _enum(units.system_rotation),
                    "scale_length": _number(units.scale_length),
                },
                "orientations": [
                    # Custom orientation identifiers can contain user-defined text.
                    _name(slot.type)
                    for slot in _bounded(scene.transform_orientation_slots, 4, "orientation slots")
                ],
                "pivot": _enum(scene.tool_settings.transform_pivot_point),
                "areas": areas,
                "positive_modal_operators": modals,
                "keymap_inventory": keymaps[manager_id],
            }
        )
    return {
        "schema_version": 1,
        "source": "BLENDER_PUBLIC_RNA",
        "pid": pid,
        "blender_version": [_integer(value) for value in _bounded(bpy.app.version, 3, "version")],
        "sampled_at": started_wall,
        "monotonic_ns": started_monotonic,
        "completed_at": time.time(),
        "completed_monotonic_ns": time.monotonic_ns(),
        "windows": windows,
    }
