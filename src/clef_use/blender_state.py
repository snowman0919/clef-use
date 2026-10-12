"""Partial public-RNA evidence bound to a fresh foreground X11 client PID.

Unavailable popup, effective keymap, text/IME focus and global idle facts remain
UNKNOWN. A running-job interface lock is positive busy evidence only. This
provider never authorizes an operation by assuming an input owner's absence.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import socket
import stat
import time
import uuid
from functools import lru_cache
from pathlib import Path

from .blender_observer import MAX_RESPONSE_BYTES, peer_credentials, private_directory, read_message
from .blender_snapshot import MAX_WORKSPACE_TOOLS
from .state import BlenderSceneUnits, FactValidity, StateFact, StateSource


@lru_cache(maxsize=1)
def _query_ids():
    from Xlib.protocol import rq

    class IdByteLength(rq.LengthOf):
        def parse_value(self, value, display):
            # The native server sends byte length (4), not a four-PID array.
            if value not in (0, 4):
                raise ValueError("unsupported X-Resource client ID length")
            return value // 4

    # X-Resource 1.2 QueryClientIds, XResproto.h. Unlike _NET_WM_PID,
    # this PID is supplied by the server from the client's local credentials.
    class QueryIds(rq.ReplyRequest):
        _request = rq.Struct(
            rq.Card8("opcode"),
            rq.Opcode(4),
            rq.RequestLength(),
            rq.LengthOf("specs", 4),
            rq.List("specs", rq.Struct(rq.Card32("client"), rq.Card32("mask"))),
        )
        _reply = rq.Struct(
            rq.ReplyCode(),
            rq.Pad(1),
            rq.Card16("sequence_number"),
            rq.ReplyLength(),
            rq.LengthOf("ids", 4),
            rq.Pad(20),
            rq.List(
                "ids",
                rq.Struct(
                    rq.Card32("client"),
                    rq.Card32("mask"),
                    IdByteLength("value", 4),
                    rq.List("value", rq.Card32Obj),
                ),
            ),
        )

    return QueryIds


def window_pid(connection, window):
    extension = connection.query_extension("X-Resource")
    if not extension or not extension.present:
        raise ValueError("X-Resource local PID query unavailable")
    reply = _query_ids()(
        display=connection.display,
        opcode=extension.major_opcode,
        specs=[{"client": window, "mask": 2}],
    )
    values = [item.value[0] for item in reply.ids if item.mask == 2 and len(item.value) == 1]
    if len(values) != 1 or values[0] <= 0:
        raise ValueError("foreground client PID unavailable")
    return values[0]


def foreground_client(connection, expected_window, expected_bounds):
    """Bind the focused app client inside the captured root-child WM frame."""
    from Xlib import X

    root = connection.screen().root
    focus = connection.get_input_focus().focus
    if not hasattr(focus, "id") or focus.id == root.id:
        raise ValueError("native foreground client unavailable")
    pid = window_pid(connection, focus.id)
    client = focus
    current = focus
    for _ in range(32):
        if current.id == expected_window:
            geometry = client.get_geometry()
            if client.get_attributes().map_state != X.IsViewable:
                raise ValueError("foreground client is not viewable")
            position = root.translate_coords(client, 0, 0)
            bounds = (
                position.x,
                position.y,
                position.x + geometry.width,
                position.y + geometry.height,
            )
            left, top, right, bottom = expected_bounds
            if not (
                left <= bounds[0] < bounds[2] <= right and top <= bounds[1] < bounds[3] <= bottom
            ):
                raise ValueError("foreground client outside captured window")
            return pid, client.id, bounds
        parent = current.query_tree().parent
        if parent.id == root.id:
            break
        if window_pid(connection, parent.id) == pid:
            client = parent
        current = parent
    raise ValueError("foreground client association unavailable")


def editor_layout(window, client_bounds, frame):
    """Map raw RNA regions, without guessing editor focus or usable surfaces."""
    left, top, _, _ = client_bounds
    width, height = frame.image.size
    # This provider binds X11 native pixel coordinates. A frame with a different
    # input extent cannot safely associate those pixels with normalized input.
    if frame.logical_size not in (None, frame.image.size):
        raise ValueError("Blender capture coordinate scale mismatch")
    origin_x, origin_y = frame.origin

    def geometry(item):
        raw = item["geometry_window_pixels_bottom_left"]
        x, y, w, h = (raw[name] for name in ("x", "y", "width", "height"))
        if any(type(value) is not int for value in (x, y, w, h)) or w < 0 or h < 0:
            raise ValueError("invalid Blender editor geometry")
        bounds = [
            left + x,
            top + window["height"] - y - h,
            left + x + w,
            top + window["height"] - y,
        ]
        # Hidden, clipped or off-capture regions retain their raw geometry, but
        # never gain a normalized actionable rectangle by clamping the edges.
        contained = (
            0 <= x < x + w <= window["width"]
            and 0 <= y < y + h <= window["height"]
            and origin_x <= bounds[0] < bounds[2] <= origin_x + width
            and origin_y <= bounds[1] < bounds[3] <= origin_y + height
        )
        return {
            "id": item["id"],
            "type": item["type"],
            "bounds_screen_pixels": bounds,
            "bounds_capture_normalized": [
                (bounds[0] - origin_x) / width,
                (bounds[1] - origin_y) / height,
                (bounds[2] - origin_x) / width,
                (bounds[3] - origin_y) / height,
            ]
            if contained
            else None,
        }

    areas = []
    for area in window["areas"]:
        mapped = geometry(area)
        mapped["regions"] = [geometry(region) for region in area["regions"]]
        areas.append(mapped)
    return {
        "client_bounds_screen_pixels": list(client_bounds),
        "areas": areas,
        "focused_editor": "UNKNOWN",
    }


def _view_pose_revision(areas):
    """Fingerprint one effective view, never layout or projection metadata."""
    viewports = [area for area in areas if area["type"] == "VIEW_3D"]
    if len(viewports) != 1 or viewports[0].get("quad_views") != []:
        return None
    pose = viewports[0].get("viewport")
    if not isinstance(pose, dict):
        return None

    def finite(value):
        try:
            return type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            return False

    location, rotation = pose.get("view_location"), pose.get("view_rotation")
    if any(
        not isinstance(vector, (list, tuple))
        or len(vector) != length
        or not all(finite(value) for value in vector)
        for vector, length in ((location, 3), (rotation, 4))
    ):
        return None
    distance, perspective = pose.get("view_distance"), pose.get("view_perspective")
    if not finite(distance) or perspective not in ("PERSP", "ORTHO", "CAMERA"):
        return None
    matrix = pose.get("view_matrix")
    if (
        not isinstance(matrix, (list, tuple))
        or len(matrix) != 4
        or any(
            not isinstance(row, (list, tuple))
            or len(row) != 4
            or not all(finite(value) for value in row)
            for row in matrix
        )
    ):
        return None
    # Quaternion signs and pending RNA parameters can differ without changing
    # the effective view. Projection/aspect matrices are intentionally excluded.
    content = [[[float(value) if value else 0.0 for value in row] for row in matrix], perspective]
    return hashlib.sha256(json.dumps(content, separators=(",", ":")).encode()).hexdigest()


def _rna_identity_matches(value, pid):
    if not isinstance(value, str) or len(value) > 256:
        return False
    prefix = f"{pid}:"
    suffix = value.removeprefix(prefix)
    return (
        value.startswith(prefix)
        and suffix.isascii()
        and suffix.isdecimal()
        and not suffix.startswith("0")
    )


def _configured_view3d_tool(window, pid):
    """Resolve a workspace tool for the bound mode, without claiming UI focus."""
    workspace = window.get("workspace_identity")
    mode = window.get("tool_context_mode")
    tools = window.get("workspace_tools")

    def enum(value):
        return (
            isinstance(value, str)
            and len(value) <= 128
            and re.fullmatch(r"[A-Z][A-Z0-9_]*", value) is not None
        )

    if not (
        _rna_identity_matches(workspace, pid)
        and enum(mode)
        and isinstance(tools, list)
        and len(tools) <= MAX_WORKSPACE_TOOLS
    ):
        return None
    matching = []
    for tool in tools:
        if not (
            isinstance(tool, dict)
            and enum(tool.get("space_type"))
            and enum(tool.get("mode"))
            and isinstance(tool.get("idname"), str)
            and len(tool["idname"]) <= 256
            and "\x00" not in tool["idname"]
        ):
            return None
        if tool["space_type"] == "VIEW_3D" and tool["mode"] == mode:
            matching.append(tool)
    areas = [area["id"] for area in window["areas"] if area["type"] == "VIEW_3D"]
    if (
        len(matching) != 1
        or not matching[0]["idname"]
        or not areas
        or not all(_rna_identity_matches(identity, pid) for identity in areas)
        or len(set(areas)) != len(areas)
    ):
        return None
    return {
        "workspace_identity": workspace,
        "space_type": "VIEW_3D",
        "context_mode": mode,
        "idname": matching[0]["idname"],
        "area_ids": areas,
        "focused_editor": "UNKNOWN",
        "effective_dispatch": "UNKNOWN",
    }


def compile_snapshot(
    snapshot, *, pid, frame, version, started_at, completed_at, client_bounds=None
):
    """Convert only uniquely bound and fresh positive observations into facts."""
    if (
        snapshot.get("schema_version") != 1
        or snapshot.get("source") != "BLENDER_PUBLIC_RNA"
        or snapshot.get("pid") != pid
        or not started_at <= snapshot.get("sampled_at", -1) <= completed_at
        or not snapshot["sampled_at"] <= snapshot.get("completed_at", -1) <= completed_at
        or completed_at - started_at > 0.5
    ):
        raise ValueError("snapshot identity or freshness mismatch")
    windows = snapshot.get("windows", [])
    # RNA exposes no native OS window handle. A single native client and single
    # RNA window with matching dimensions is the only supported association.
    if len(windows) != 1 or frame.foreground_bounds is None:
        raise ValueError("ambiguous Blender window association")
    window = windows[0]
    left, top, right, bottom = client_bounds or frame.foreground_bounds
    if (window["width"], window["height"]) != (right - left, bottom - top):
        raise ValueError("Blender window geometry mismatch")

    def fact(value):
        return StateFact(
            value=value,
            source=StateSource.APP_TELEMETRY,
            observed_at=snapshot["sampled_at"],
            state_version=version,
            validity=FactValidity.VALID,
            uncertainty=0,
        )

    result = {
        "application": fact("Blender"),
        "selection": fact(window["selection"]),
        "application_snapshot": fact(window),
        "editor_layout": fact(editor_layout(window, (left, top, right, bottom), frame)),
    }
    # The public lock covers running jobs, not every loading/input-owning state.
    # An unlocked manager can still have a popup, modal or unobserved job.
    if window.get("interface_locked") is True:
        result["loading"] = fact(True)
    selection = window["selection"]
    objects = window["objects"]
    # Names can be reused while an operation is in flight. Only a complete
    # process-bound public datablock identity map can establish continuity.
    identities = {name: obj.get("id") for name, obj in objects.items()}
    prefix = f"{pid}:OBJECT:"
    if (
        isinstance(selection, list)
        and all(isinstance(name, str) for name in selection)
        and len(selection) == len(set(selection))
        and set(selection) == set(identities)
        and all(
            isinstance(identity, str)
            and identity.startswith(prefix)
            and identity[len(prefix) :].isascii()
            and identity[len(prefix) :].isdecimal()
            and not identity[len(prefix) :].startswith("0")
            for identity in identities.values()
        )
        and len(set(identities.values())) == len(identities)
    ):
        result["selection_identities"] = fact(identities)
    inventory = window.get("keymap_inventory")
    if inventory is not None:
        result["keymap_inventory"] = fact(inventory)
    tool = _configured_view3d_tool(window, pid)
    if tool is not None:
        result["active_tool"] = fact(tool)
    if window["active_object_mode"] is not None:
        result["mode"] = fact(window["active_object_mode"])
    try:
        settings = window["unit_settings"]
        scene_identity = window["scene_identity"]
        units = BlenderSceneUnits.model_validate(
            {
                "scene_identity": scene_identity,
                **{name: settings[name] for name in ("system", "length_unit", "scale_length")},
            }
        )
        if not _rna_identity_matches(scene_identity, pid):
            raise ValueError("scene identity is not bound to observer process")
    except (KeyError, TypeError, ValueError):
        pass  # Partial snapshots cannot establish the length conversion.
    else:
        result["scene_units"] = fact(units.model_dump())
    # Raw scene units do not prove focused field, effective modal units or space.
    result["properties"] = fact(
        {name: obj["properties"] for name, obj in window["objects"].items()}
    )
    modals = window["positive_modal_operators"]
    if modals:
        result["modal"] = fact({"positive_operators": modals})
    revision = _view_pose_revision(window["areas"])
    if revision is not None:
        result["view_revision"] = fact(revision)
    return result


class BlenderStateProvider:
    def __init__(self, path: Path):
        from .x11_input_state import X11InputState

        self.path = path
        self.query = X11InputState(os.environ.get("DISPLAY"))
        self.status = {"status": "NOT_PROBED", "provider": "BLENDER_PUBLIC_RNA"}

    def __call__(self, observation, version):
        from Xlib.error import ConnectionClosedError, DisplayConnectionError, XError

        stage = "socket_permissions"
        try:
            private_directory(self.path.parent)
            info = self.path.lstat()
            if (
                not stat.S_ISSOCK(info.st_mode)
                or info.st_uid != os.getuid()
                or info.st_mode & 0o077
            ):
                raise ValueError("observer socket ownership or permissions mismatch")
            query = self.query
            started = time.time()
            stage = "foreground_identity"
            with query.query() as connection:
                window, bounds = query.foreground()
                frame = observation.frame
                if window != frame.foreground_window or bounds != frame.foreground_bounds:
                    raise ValueError("foreground changed before state sample")
                native_pid, client_window, client_bounds = foreground_client(
                    connection, window, bounds
                )
                stage = "observer_peer"
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.settimeout(0.5)
                    client.connect(str(self.path))
                    pid, uid, _ = peer_credentials(client)
                    if pid != native_pid or uid != os.getuid():
                        raise ValueError("observer peer does not own foreground client")
                    nonce = uuid.uuid4().hex
                    stage = "snapshot_response"
                    client.sendall(
                        json.dumps({"request": "snapshot", "nonce": nonce}).encode() + b"\n"
                    )
                    message = read_message(client, MAX_RESPONSE_BYTES)
                if message.get("nonce") != nonce or "snapshot" not in message:
                    if (
                        message.get("nonce") == nonce
                        and message.get("error") == "snapshot unavailable"
                    ):
                        self.status = {
                            "status": "UNAVAILABLE",
                            "provider": "BLENDER_PUBLIC_RNA",
                            "failed_check": "producer_snapshot",
                            "error_type": message.get("error_type"),
                            "reason": message.get("failed_check", "Blender public RNA read failed"),
                        }
                        return {}
                    raise ValueError("observer response mismatch or unavailable")
                stage = "foreground_recheck"
                if query.foreground() != (window, bounds) or foreground_client(
                    connection, window, bounds
                ) != (pid, client_window, client_bounds):
                    raise ValueError("foreground changed during state sample")
                stage = "snapshot_binding"
                facts = compile_snapshot(
                    message["snapshot"],
                    pid=pid,
                    frame=frame,
                    version=version,
                    started_at=started,
                    completed_at=time.time(),
                    client_bounds=client_bounds,
                )
            self.status = {
                "status": "PARTIAL",
                "provider": "BLENDER_PUBLIC_RNA",
                "verified_facts": sorted(facts),
            }
            return facts
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            XError,
            ConnectionClosedError,
            DisplayConnectionError,
        ) as exc:
            # Failure is public and explicit; no path, scene or credentials leak.
            self.status = {
                "status": "UNAVAILABLE",
                "provider": "BLENDER_PUBLIC_RNA",
                "reason": "Native peer/window binding or fresh snapshot unavailable",
                "failed_check": stage,
                "error_type": type(exc).__name__,
                "errno": exc.errno if isinstance(exc, OSError) else None,
                "detail": str(exc)
                if str(exc)
                in {
                    "incomplete observer message",
                    "invalid observer framing",
                    "observer message exceeds limit",
                    "observer response mismatch or unavailable",
                    "foreground changed before state sample",
                    "foreground changed during state sample",
                    "observer peer does not own foreground client",
                    "snapshot identity or freshness mismatch",
                    "ambiguous Blender window association",
                    "Blender window geometry mismatch",
                }
                else None,
            }
            return {}
