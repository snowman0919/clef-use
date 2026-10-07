"""Real, isolated Blender GUI benchmark. --help does not import ML or GUI modules."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import platform
import secrets
import shutil
import socket
import statistics
import subprocess
import time
from pathlib import Path

CASES = {
    "properties_tiny_icon": (
        "Open Material Properties using its small icon",
        "Material Properties icon",
        "PROPERTIES",
    ),
    "outliner": (
        "Select the Face object in the Outliner",
        "Face object row in Outliner",
        "OUTLINER",
    ),
    "viewport_selection": (
        "Select the visible face mesh in the viewport",
        "cheek on the left side of the visible face mesh",
        "VIEW_3D",
    ),
    "drag": (
        "Drag the boundary between Outliner and Properties up to shrink Outliner",
        "horizontal boundary below Outliner",
        "OUTLINER",
    ),
    "material_property": (
        "Enable Thin Wall in the Face material Surface settings",
        "Thin Wall checkbox in Material Properties Surface",
        "PROPERTIES",
    ),
    "prior_splash_failure": (
        "Dismiss Blender splash and switch to Modeling workspace",
        "Modeling workspace tab",
        None,
    ),
}


def last_decision(history):
    return next(
        (
            row
            for row in reversed(history)
            if row.get("mode") is not None or row.get("candidate_count") is not None
        ),
        {},
    )


def focus_fixture_window():
    """Focus the sole visible Blender client on the newly owned Xvfb display."""
    from Xlib import X, display

    connection = display.Display()
    try:
        windows = []
        for window in connection.screen().root.query_tree().children:
            labels = window.get_wm_class() or ()
            if (
                any(label.casefold() == "blender" for label in labels)
                and window.get_attributes().map_state == X.IsViewable
            ):
                windows.append(window)
        if len(windows) != 1:
            raise RuntimeError("private fixture has no unique visible Blender window")
        window = windows[0]
        window.set_input_focus(X.RevertToParent, X.CurrentTime)
        connection.sync()
        focus = connection.get_input_focus().focus
        if not hasattr(focus, "id") or focus.id != window.id:
            raise RuntimeError("private Blender input focus was not established")
        return {
            "window": window.id,
            "wm_class": window.get_wm_class(),
            "method": "native X11 focus before all model trials; no coordinates",
        }
    finally:
        connection.close()


def trial_metrics(history, clef_requests):
    terminal = last_decision(history)
    executions = [
        entry
        for entry in history
        if "execution_ok" in entry or (entry.get("execution_ms", 0) or 0) > 0
    ]
    modes = sorted({entry["mode"] for entry in executions if entry.get("mode")})
    decision = last_decision(executions) if executions else terminal
    grounding_times = [
        entry["grounding_ms"] for entry in history if (entry.get("grounding_ms", 0) or 0) > 0
    ]
    return {
        "mode": modes[0] if len(modes) == 1 else "MIXED" if modes else terminal.get("mode"),
        "mode_basis": "execution_attempts" if executions else "last_route_no_input",
        "execution_modes": modes,
        "terminal_mode": terminal.get("mode"),
        "candidate_count": decision.get("candidate_count"),
        "raw_candidate_counts": [
            entry["candidate_count"]
            for entry in history
            if entry.get("candidate_count") is not None
        ],
        "clef_choice_counts": [entry["candidates"] for entry in clef_requests],
        "step_latencies_ms": [entry.get("step_latency_ms") for entry in history],
        "grounding_ms": sum(grounding_times) if grounding_times else None,
        "confidence": decision.get("confidence"),
        "clef_candidate_count": decision.get("clef_candidate_count"),
        "visual_confidence": decision.get("visual_confidence"),
        "coarse_roi": decision.get("coarse_roi"),
        "fine_target": decision.get("fine_target"),
    }


def fixture_ready(case, state):
    expected_active = (
        state["target_object"] if case in {"properties_tiny_icon", "material_property"} else None
    )
    return (
        state["workspace"] == "Layout"
        and state["active_object"] == expected_active
        and (case != "properties_tiny_icon" or state["properties_context"] == "OBJECT")
        and (case != "material_property" or state["properties_context"] == "MATERIAL")
        and (case != "material_property" or state["thin_wall"] is False)
        and (case not in {"outliner", "viewport_selection"} or state["target_visible"])
        and (case != "drag" or state["outliner_height"] > 4)
        and {"PROPERTIES", "OUTLINER", "VIEW_3D"}.issubset(
            {area["type"] for area in state["areas"]}
        )
    )


def case_region(case, areas, area_type):
    if case == "drag":
        editors = [area for area in areas if area["type"] in {"OUTLINER", "PROPERTIES"}]
        if len(editors) != 2:
            raise ValueError("drag fixture requires Outliner and Properties editors")
        return {
            "x1": min(area["x1"] for area in editors),
            "y1": min(area["y1"] for area in editors),
            "x2": max(area["x2"] for area in editors),
            "y2": max(area["y2"] for area in editors),
        }
    return next((area for area in areas if area["type"] == area_type), None)


def missing_trials(cases, repetitions, rows):
    attempted = {(row["case"], row["repetition"], row["variant"]) for row in rows}
    return [
        {"case": case, "repetition": repetition, "variant": variant, "status": "NOT_RUN"}
        for repetition in range(repetitions)
        for case in cases
        for variant in ("baseline", "hybrid")
        if (case, repetition, variant) not in attempted
    ]


def summarize(rows):
    """Include failures in counts; report success-only and all-run latency separately."""
    groups = {}
    for variant in sorted({row["variant"] for row in rows}):
        selected = [row for row in rows if row["variant"] == variant]

        def distribution(values):
            values = sorted(value for value in values if value is not None and math.isfinite(value))
            if not values:
                return None
            return {
                "count": len(values),
                "min": values[0],
                "max": values[-1],
                "p50": statistics.median(values),
                "p95": values[math.ceil(0.95 * len(values)) - 1],
            }

        groups[variant] = {
            "trials": len(selected),
            "successes": sum(row.get("success") is True for row in selected),
            "unverified_outcomes": sum(row.get("success") is None for row in selected),
            "confirmed_failures": sum(row.get("success") is False for row in selected),
            "escalations": sum(row.get("status") == "NEEDS_REPLAN" for row in selected),
            "success_rate": sum(row.get("success") is True for row in selected) / len(selected),
            "success_rate_basis": "confirmed successes / all persisted trials",
            "escalation_frequency": sum(row.get("status") == "NEEDS_REPLAN" for row in selected)
            / len(selected),
            "end_to_end_ms": distribution([row.get("end_to_end_ms") for row in selected]),
            "runtime_ms": distribution([row.get("runtime_ms") for row in selected]),
            "step_latency_ms": distribution(
                [value for row in selected for value in row.get("step_latencies_ms", [])]
            ),
            "successful_end_to_end_ms": distribution(
                [row.get("end_to_end_ms") for row in selected if row.get("success")]
            ),
            "grounding_ms": distribution([row.get("grounding_ms") for row in selected]),
            "grounding_error": distribution([row.get("grounding_error") for row in selected]),
            "grounding_error_methods": sorted(
                {
                    row["grounding_error_method"]
                    for row in selected
                    if row.get("grounding_error") is not None
                    and math.isfinite(row["grounding_error"])
                    and row.get("grounding_error_method") is not None
                }
            ),
            "structured_successes": sum(
                row.get("success") is True and row.get("mode") == "STRUCTURED" for row in selected
            ),
            "visual_successes": sum(
                row.get("success") is True and row.get("mode") in {"VISUAL", "CANVAS"}
                for row in selected
            ),
        }
        modes = {}
        for mode in sorted({str(row.get("mode")) for row in selected}):
            samples = [row for row in selected if str(row.get("mode")) == mode]
            successes = sum(row.get("success") is True for row in samples)
            modes[mode] = {
                "trials": len(samples),
                "successes": successes,
                "success_rate": successes / len(samples),
            }
        groups[variant]["by_mode"] = modes
        for field, label in (
            ("raw_candidate_counts", "raw_candidate_count_vs_success"),
            ("clef_choice_counts", "clef_choice_count_vs_success"),
        ):
            counts = sorted(
                {
                    value
                    for row in selected
                    for value in row.get(field, [])
                    if field != "clef_choice_counts" or value > 0
                }
            )
            breakdown = {}
            for count in counts:
                samples = [row for row in selected if count in row.get(field, [])]
                successes = sum(row.get("success") is True for row in samples)
                breakdown[str(count)] = {
                    "trials": len(samples),
                    "successes": successes,
                    "success_rate": successes / len(samples),
                    "calls": sum(row.get(field, []).count(count) for row in samples),
                }
            groups[variant][label] = breakdown
        groups[variant]["clef_zero_choice_calls"] = sum(
            row.get("clef_choice_counts", []).count(0) for row in selected
        )
    return groups


def outcome(case, before, after, input_attempts=None):
    if case in {"properties_tiny_icon", "material_property"}:
        return (
            after["properties_context"] == "MATERIAL"
            if case == "properties_tiny_icon"
            else after["thin_wall"] is True
        )
    if case in {"outliner", "viewport_selection"}:
        target = before["target_object"]
        if after["active_object"] != target or before["active_object"] == target:
            return False
        if input_attempts is None:
            return None
        area_type = "VIEW_3D" if case == "viewport_selection" else "OUTLINER"
        unknown = False
        for index, attempt in enumerate(input_attempts):
            if attempt.get("ok") is not True or attempt.get("delivery") != "completed":
                unknown = True
                continue
            if attempt.get("operation") not in {"click", "double_click"}:
                continue
            native_before = attempt.get("native_before")
            native_after = attempt.get("native_after")
            # A queued mouse event may be processed after the immediate readback.
            # Only the boundary before the very next input, or the final readback
            # for the last input, can extend this action's evidence window.
            boundary = (
                input_attempts[index + 1].get("native_before")
                if index + 1 < len(input_attempts)
                else after
            )
            if isinstance(boundary, dict) and "active_object" in boundary:
                native_after = boundary
            if (
                not isinstance(native_before, dict)
                or "active_object" not in native_before
                or not isinstance(native_after, dict)
                or "active_object" not in native_after
            ):
                unknown = True
                continue
            if native_before["active_object"] == target or native_after["active_object"] != target:
                continue
            areas = [
                area for area in native_before.get("areas", []) if area.get("type") == area_type
            ]
            points = attempt.get("points", [])
            if not areas or len(points) != 1:
                unknown = True
                continue
            x, y = points[0]
            if any(area["x1"] <= x < area["x2"] and area["y1"] <= y < area["y2"] for area in areas):
                return True
        return None if unknown else False
    if case == "drag":
        return after["outliner_height"] < before["outliner_height"] - 4
    if case == "prior_splash_failure":
        return after["workspace"] == "Modeling" and before["workspace"] != "Modeling"
    raise ValueError(case)


def region_error(point, region, size):
    """Pixel distance outside a known editor region; zero does not prove icon accuracy."""
    if point is None or region is None:
        return None
    x, y = point
    dx = max(region["x1"] - x, 0, x - region["x2"]) * size[0]
    dy = max(region["y1"] - y, 0, y - region["y2"]) * size[1]
    return math.hypot(dx, dy)


# This server only accepts fixed fixture/reset/readback operations, never arbitrary code.
# Socket handling and bpy calls occur on Blender's main thread in a nonblocking timer.
STARTUP = r"""
import bpy, hmac, json, socket
from pathlib import Path
root = Path(__ROOT__)
port = __PORT__
token = (root / "fixture-token").read_bytes()
server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("127.0.0.1", port))
server.listen(4)
server.setblocking(False)
clients = {}
win = bpy.context.window_manager.windows[0]
win.workspace = bpy.data.workspaces["Layout"]
outliner = next(a for a in win.screen.areas if a.type == "OUTLINER")
baseline_height = outliner.height
view = next(a for a in win.screen.areas if a.type == "VIEW_3D")
r3d = view.spaces.active.region_3d
view_baseline = (r3d.view_location.copy(), r3d.view_rotation.copy(),
                 r3d.view_distance, r3d.view_perspective)
target = next((o for o in bpy.data.objects if o.type == "MESH" and o.name.lower() == "face"), None)
if target is None:
    raise RuntimeError("VRM fixture must contain a mesh named Face")
material = target.active_material
if material is None:
    raise RuntimeError("Face fixture needs an existing active material")
shader = next((node for node in material.node_tree.nodes
               if node.type == 'BSDF_PRINCIPLED'), None)
thin_wall = shader.inputs.get("Thin Wall") if shader else None
if thin_wall is None:
    raise RuntimeError("material fixture requires a Principled Thin Wall input")
baseline_thin_wall = bool(thin_wall.default_value)
# Private, in-memory fixture binding: invoke the real operator in GUI event context.
# Both benchmark variants use this binding; never save it into user preferences.
fixture_keyconfig = bpy.context.window_manager.keyconfigs.addon
if fixture_keyconfig is None:
    raise RuntimeError("private fixture requires Blender addon key configuration")
fixture_keymap = fixture_keyconfig.keymaps.new(name="Window", space_type="EMPTY")
fixture_keymap.keymap_items.new("wm.splash", "F10", "PRESS",
                              ctrl=True, alt=True, shift=True, head=True)
def state():
    win = bpy.context.window_manager.windows[0]
    areas = list(win.screen.areas)
    props = next((a for a in areas if a.type == "PROPERTIES"), None)
    out = next((a for a in areas if a.type == "OUTLINER"), None)
    width, height = win.width, win.height
    return dict(workspace=win.workspace.name, target_object=target.name,
        window_size=[width, height],
        target_visible=target.visible_get(view_layer=win.view_layer),
        active_object=win.view_layer.objects.active.name if win.view_layer.objects.active else None,
        properties_context=props.spaces.active.context if props else None,
        outliner_height=out.height if out else None,
        thin_wall=bool(thin_wall.default_value),
        areas=[dict(type=a.type, x1=a.x/width, y1=1-(a.y+a.height)/height,
            x2=(a.x+a.width)/width, y2=1-a.y/height) for a in areas])
def reset(case):
    win = bpy.context.window_manager.windows[0]
    win.workspace = bpy.data.workspaces["Layout"]
    # The screen attached to a workspace changes on the next event-loop turn.
    # Prepare only after that change; property enums need another redraw afterward.
def prepare_reset(conn, case):
    try:
        win = bpy.context.window_manager.windows[0]
        with bpy.context.temp_override(window=win, scene=win.scene, view_layer=win.view_layer):
            prepare(case, win)
        callback = lambda c=conn, selected=case: finish_reset(c, selected)
        bpy.app.timers.register(callback, first_interval=.1)
    except Exception as exc:
        conn.setblocking(True)
        conn.sendall(json.dumps({"error":type(exc).__name__+": "+str(exc)}).encode()+b"\n")
        conn.close()
    return None
def prepare(case, win):
    if bpy.context.object is not None and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    out = next(a for a in win.screen.areas if a.type == "OUTLINER")
    if out.height != baseline_height:
        # Fixture setup only: restore the divider via actual editor geometry.
        with bpy.context.temp_override(window=win, area=out):
            result = bpy.ops.screen.area_move(x=out.x + out.width // 2,
                                             y=out.y,
                                             delta=out.height - baseline_height)
        if 'FINISHED' not in result:
            raise RuntimeError("could not restore fixture Outliner height")
    view = next(a for a in win.screen.areas if a.type == "VIEW_3D")
    r3d = view.spaces.active.region_3d
    r3d.view_location, r3d.view_rotation = view_baseline[:2]
    r3d.view_distance, r3d.view_perspective = view_baseline[2:]
    thin_wall.default_value = baseline_thin_wall
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    bpy.context.view_layer.objects.active = None
    target.hide_set(False)
    target.hide_viewport = False
    props = next(a for a in win.screen.areas if a.type == "PROPERTIES")
    if case in {"material_property", "properties_tiny_icon"}:
        target.select_set(True)
        bpy.context.view_layer.objects.active = target
    else:
        props.spaces.active.context = "SCENE"
    if case == "material_property":
        thin_wall.default_value = False
    if case in {"outliner", "drag"}:
        target.select_set(True)
        bpy.context.view_layer.objects.active = target
        region = next(r for r in out.regions if r.type == "WINDOW")
        with bpy.context.temp_override(window=win, area=out, region=region):
            bpy.ops.outliner.show_active()
        target.select_set(False)
        bpy.context.view_layer.objects.active = None
    if case == "viewport_selection":
        view = next(a for a in win.screen.areas if a.type == "VIEW_3D")
        target.select_set(True)
        bpy.context.view_layer.objects.active = target
        region = next(r for r in view.regions if r.type == "WINDOW")
        with bpy.context.temp_override(window=win, area=view, region=region):
            bpy.ops.view3d.view_selected(use_all_regions=False)
        target.select_set(False)
        bpy.context.view_layer.objects.active = None
    return state()
def finish_reset(conn, case):
    # Active-object changes rebuild Properties context enums on the next redraw.
    try:
        win = bpy.context.window_manager.windows[0]
        props = next(a for a in win.screen.areas if a.type == "PROPERTIES")
        if case in {"properties_tiny_icon", "material_property"}:
            with bpy.context.temp_override(window=win, area=props,
                                           scene=win.scene, view_layer=win.view_layer):
                props.spaces.active.context = (
                    "MATERIAL" if case == "material_property" else "OBJECT")
        for area in win.screen.areas:
            area.tag_redraw()
        with bpy.context.temp_override(window=win, area=props,
                                       scene=win.scene, view_layer=win.view_layer):
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        out = next(a for a in win.screen.areas if a.type == "OUTLINER")
        if abs(out.height - baseline_height) > 2:
            raise RuntimeError("could not restore fixture Outliner height after redraw")
        reply = state()
    except Exception as exc:
        reply = {"error":type(exc).__name__+": "+str(exc)}
    conn.setblocking(True)
    conn.sendall(json.dumps(reply).encode()+b"\n")
    conn.close()
    return None
def tick():
    try:
        while True:
            conn, _ = server.accept()
            conn.setblocking(False)
            clients[conn] = b""
    except BlockingIOError:
        pass
    for conn in list(clients):
        try:
            chunk = conn.recv(65536)
            if not chunk:
                conn.close(); del clients[conn]; continue
            clients[conn] += chunk
            if b"\n" not in clients[conn]: continue
            try:
                request = json.loads(clients[conn].split(b"\n",1)[0])
                supplied = request.get("token") if isinstance(request, dict) else None
                authorized = isinstance(supplied, str) and hmac.compare_digest(
                    supplied.encode("utf-8"), token
                )
                op = request.get("operation") if authorized else None
                if not authorized:
                    reply = {"error":"unauthorized fixture request"}
                elif op == "reset":
                    reset(request["case"])
                    del clients[conn]
                    callback = lambda c=conn, case=request["case"]: prepare_reset(c, case)
                    bpy.app.timers.register(callback, first_interval=.2)
                    continue
                elif op == "readback":
                    reply = state()
                else:
                    reply = {"error":"unknown operation"}
            except Exception as exc:
                reply = {"error":type(exc).__name__+": "+str(exc)}
            conn.setblocking(True)
            conn.sendall(json.dumps(reply).encode()+b"\n")
            conn.close(); del clients[conn]
        except BlockingIOError:
            pass
    return .05
bpy.app.timers.register(tick, first_interval=.5, persistent=True)
(root / "ready.json").write_text(json.dumps(state()))
"""


def request(port, operation, *, token, **payload):
    with socket.create_connection(("127.0.0.1", port), timeout=15) as conn:
        conn.sendall(
            json.dumps({"operation": operation, **payload, "token": token}).encode() + b"\n"
        )
        data = b""
        while not data.endswith(b"\n"):
            chunk = conn.recv(65536)
            if not chunk:
                raise RuntimeError("Blender readback connection closed")
            data += chunk
    reply = json.loads(data)
    if "error" in reply:
        raise RuntimeError(reply["error"])
    return reply


def show_splash(gui, state):
    """Invoke the real splash operator and reject unchanged/unstable fixture setup."""
    import threading

    from clef_use.backends import DesktopCapture
    from clef_use.schema import BoundingBox
    from clef_use.verification import VisualWaiter

    view = next(area for area in state["areas"] if area["type"] == "VIEW_3D")
    width, height = state["window_size"]
    gui.moveTo((view["x1"] + view["x2"]) * width / 2, (view["y1"] + view["y2"]) * height / 2)
    capture = DesktopCapture()
    cancelled = threading.Event()
    waiter = VisualWaiter(timeout=5, interval=0.1, stable_samples=3)
    region = BoundingBox(x1=0, y1=0, x2=1, y2=1)
    before = capture.capture()
    settled = waiter.wait(capture, before, region, cancelled, require_change=False)
    if settled.state not in {"STABLE", "ALREADY_TRUE"}:
        raise RuntimeError(f"splash fixture baseline did not settle: {settled.state}")
    gui.hotkey("ctrl", "alt", "shift", "f10")
    opened = waiter.wait(capture, settled.frame, region, cancelled)
    if opened.state != "STABLE" or not opened.changed:
        raise RuntimeError(f"splash fixture did not change and settle: {opened.state}")
    return opened.metrics()


def configure_exclusive_workers(workers):
    """Keep only the requested model resident in this single-threaded benchmark."""
    workers = tuple(workers)
    for worker in workers:
        original_request = worker.request

        def exclusive_request(payload, selected=worker, request=original_request):
            for other in workers:
                if other is not selected:
                    other.close()
            return request(payload)

        worker.request = exclusive_request


def instrument_worker_trace(workers, report, persist, output):
    """Persist real startup replies and replayable CLEF inputs before inference."""
    for name, worker in workers:
        original_start = worker._start

        def traced_start(start=original_start, kind=name):
            ready = start()
            event = {"worker": kind, "time": time.time(), "ready": ready}
            if report.get("in_flight"):
                event["trial"] = {
                    key: report["in_flight"][key] for key in ("case", "variant", "repetition")
                }
            report.setdefault("model_startups", []).append(event)
            persist()
            return ready

        worker._start = traced_start
        if name != "clef":
            continue
        original_request = worker.request

        def traced_request(payload, request=original_request):
            entries = report.setdefault("clef_requests", [])
            index = len(entries)
            prefix = f"clef-request-{index:04d}"
            archived = {"request": {key: value for key, value in payload.items() if key != "image"}}
            if payload.get("image"):
                encoded = base64.b64decode(payload["image"], validate=True)
                image_path = output / f"{prefix}.png"
                image_path.write_bytes(encoded)
                image_path.chmod(0o600)
                archived.update(
                    image_file=image_path.name, image_sha256=hashlib.sha256(encoded).hexdigest()
                )
            path = output / f"{prefix}.json"
            path.write_text(json.dumps(archived))
            path.chmod(0o600)
            state = payload.get("state", {})
            entry = {
                "request_file": path.name,
                "time": time.time(),
                "state_bytes": len(json.dumps(state).encode("utf-8")),
                "objects": len(state.get("objects", [])),
                "candidates": len(state.get("allowed_candidates", [])),
            }
            if report.get("in_flight"):
                entry["trial"] = {
                    key: report["in_flight"][key] for key in ("case", "variant", "repetition")
                }
            entries.append(entry)
            persist()
            try:
                reply = request(payload)
            except Exception as exc:
                entry["error"] = type(exc).__name__ + ": " + str(exc)
                persist()
                raise
            reply_path = output / f"{prefix}-reply.json"
            reply_path.write_text(json.dumps(reply))
            reply_path.chmod(0o600)
            entry.update(reply_file=reply_path.name, usage=reply.get("usage"))
            persist()
            return reply

        worker.request = traced_request


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, required=True, help="New private directory beneath /tmp"
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--display", default=":130")
    parser.add_argument("--port", type=int, default=19876)
    parser.add_argument(
        "--setup-smoke",
        action="store_true",
        help="Reset/read back each fixture twice; no inference or task actions",
    )
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument(
        "--exclusive-model-workers",
        action="store_true",
        help="Keep only the active model worker resident; reload on model stage changes",
    )
    parser.add_argument("--cases", nargs="+", choices=list(CASES), default=list(CASES))
    args = parser.parse_args(argv)
    if args.repetitions < 5:
        parser.error("at least five repetitions are required")
    output = args.output.resolve()
    if not output.is_relative_to(Path("/tmp")) or output == Path("/tmp"):
        parser.error("output must be a new directory below /tmp")
    if (
        not args.blend.is_file()
        or not args.display.startswith(":")
        or not args.display[1:].isdigit()
    ):
        parser.error("existing .blend and numeric local display required")
    if Path("/tmp/.X11-unix/X" + args.display[1:]).exists():
        parser.error("display already exists; choose a fresh isolated display")
    with socket.socket() as check:
        check.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        check.bind(("127.0.0.1", args.port))
    output.mkdir(mode=0o700)
    token = secrets.token_hex(32)
    token_path = output / "fixture-token"
    token_path.touch(mode=0o600)
    token_path.write_text(token)
    shutil.copy2(args.blend, output / "fixture.blend")
    script = STARTUP.replace("__ROOT__", repr(str(output))).replace("__PORT__", str(args.port))
    (output / "start.py").write_text(script)
    os.environ["DISPLAY"] = args.display
    authority = output / "Xauthority"
    authority.touch(mode=0o600)
    os.environ["XAUTHORITY"] = str(authority)
    os.environ["CLEF_USE_STATE_DIR"] = str(output / "state")
    processes = []
    streams = []
    report = {
        "kind": "REAL_ISOLATED_BLENDER_HYBRID",
        "repetitions": args.repetitions,
        "runs": [],
        "worker_policy": "exclusive" if args.exclusive_model_workers else "resident",
        "method": (
            "Alternating baseline STRUCTURED and hybrid AUTO (explicit CANVAS for viewport) "
            "on reset Blender fixture; baseline has no visual intent, region scope or "
            "grounder and retains the original candidate/object decision context; "
            "end_to_end_ms includes fixture preparation and runtime_ms excludes it; "
            "cold model loads included and recorded by trial order and worker liveness."
        ),
        "hardware": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
        },
        "limitations": [
            "Grounding error is editor containment; exact icon accuracy unmeasured.",
            "Blender state success and runtime completion/escalation reported separately.",
            "Alive workers do not prove warm inference; cold/warm timings cannot be pooled.",
            "Both variants share canonical verification fixes; baseline is the preserved "
            "structured path, not execution of an immutable historical checkout.",
            "Hybrid receives explicit landmark queries and editor regions; gains compare "
            "the complete hybrid contract, not the grounding head alone.",
        ],
    }
    if args.exclusive_model_workers:
        report["limitations"].append(
            "Both variants use exclusive worker residency. Model stage changes close other "
            "owned workers and include cold reloads; consecutive requests to one model stay warm."
        )

    def save():
        report["summary"] = summarize(report["runs"])
        temporary = output / "report.json.tmp"
        temporary.write_text(json.dumps(report, indent=2))
        temporary.replace(output / "report.json")

    try:
        for name, command in (
            (
                "xvfb",
                [
                    "Xvfb",
                    args.display,
                    "-screen",
                    "0",
                    "1280x900x24",
                    "-nolisten",
                    "tcp",
                    "-auth",
                    str(authority),
                ],
            ),
            (
                "blender",
                [
                    "flatpak",
                    "run",
                    "--env=DISPLAY=" + args.display,
                    "--env=XAUTHORITY=" + str(authority),
                    "--filesystem=" + str(output),
                    "org.blender.Blender",
                    "--factory-startup",
                    str(output / "fixture.blend"),
                    "--python",
                    str(output / "start.py"),
                ],
            ),
        ):
            stream = (output / (name + ".log")).open("w")
            streams.append(stream)
            processes.append(subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT))
            if name == "xvfb":
                deadline = time.monotonic() + 15
                while not Path("/tmp/.X11-unix/X" + args.display[1:]).exists():
                    if time.monotonic() > deadline or processes[-1].poll() is not None:
                        raise RuntimeError("isolated Xvfb failed; see xvfb.log")
                    time.sleep(0.1)
        deadline = time.monotonic() + 90
        while not (output / "ready.json").exists():
            if time.monotonic() > deadline or processes[-1].poll() is not None:
                raise RuntimeError("Blender fixture startup failed; see blender.log")
            time.sleep(0.2)
        import pyautogui

        from clef_use.backends import DesktopCapture

        report["fixture_focus"] = focus_fixture_window()
        report["fixture_foreground"] = (
            DesktopCapture().capture().reference().model_dump(mode="json")
        )
        if (
            report["fixture_foreground"]["foreground_window"] is None
            or report["fixture_foreground"]["foreground_bounds"] is None
        ):
            raise RuntimeError("private Blender capture has no established foreground context")
        save()

        if args.setup_smoke:
            report["kind"] = "BLENDER_FIXTURE_SETUP_SMOKE_NO_INFERENCE"
            report["setup_smoke"] = []
            for repetition in range(2):
                for case in args.cases:
                    pyautogui.press("esc")  # Reset any prior fixture popup on our display.
                    before = request(args.port, "reset", token=token, case=case)
                    if case == "prior_splash_failure":
                        show_splash(pyautogui, before)
                    time.sleep(0.5)
                    after = request(args.port, "readback", token=token)
                    screenshot = f"setup-{repetition}-{case}.png"
                    DesktopCapture().capture().image.save(output / screenshot)
                    ready = fixture_ready(case, before) and fixture_ready(case, after)
                    report["setup_smoke"].append(
                        {
                            "case": case,
                            "repetition": repetition,
                            "before": before,
                            "after": after,
                            "fixture_ready": ready,
                            "screenshot": screenshot,
                        }
                    )
                    save()
                    if not ready:
                        raise RuntimeError(f"fixture precondition failed for {case}")
            return 0
        import tomllib

        from clef_use.backends import (
            ClefBackend,
            DesktopAction,
            DesktopCapture,
            OmniParserBackend,
            VisualGroundingBackend,
        )
        from clef_use.config import Config
        from clef_use.models import MODEL_REVISIONS, OMNI_SOURCE_REVISION
        from clef_use.runtime import Session, SessionRuntime
        from clef_use.schema import BoundingBox, Contract, VisualIntent

        config = Config.model_validate(tomllib.loads(args.config.read_text()))
        config = config.model_copy(
            update={
                "visual_grounding": True,
                "visual_python": config.visual_python or config.clef_python,
                "visual_model": "google/siglip2-base-patch16-512",
                "visual_device": "cpu",
                "activity_overlay": False,
                "debug": True,
            }
        )
        report["models"] = dict(MODEL_REVISIONS)
        report["visual_model"] = config.visual_model
        report["visual_revision"] = config.visual_revision
        report["visual_head"] = (
            {
                "name": config.visual_head.name,
                "sha256": hashlib.sha256(config.visual_head.read_bytes()).hexdigest(),
            }
            if config.visual_head
            else None
        )
        report["execution_config"] = {
            key: getattr(config, key)
            for key in (
                "quantization",
                "ml_profile",
                "cpu_compute_dtype",
                "max_candidates",
                "structured_candidate_threshold",
                "native_confidence_threshold",
                "visual_confidence_threshold",
                "visual_refinement_retries",
                "visual_stale_retries",
                "clef_entropy_threshold",
                "backend_timeout",
                "no_progress_limit",
                "max_steps",
            )
        }
        report["thread_environment"] = {
            key: os.environ.get(key)
            for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")
        }
        report["omni_source_revision"] = OMNI_SOURCE_REVISION
        report["devices"] = {
            "clef": config.device,
            "parser": config.parser_device,
            "visual": config.visual_device,
        }
        report["environment_versions"] = {}
        version_probe = (
            "import importlib.metadata as m,json; "
            "print(json.dumps({p:m.version(p) for p in "
            "['torch','transformers','Pillow']}))"
        )
        for name, python in (
            ("clef", config.clef_python),
            ("omni", config.omni_python),
            ("visual", config.visual_python),
        ):
            try:
                probe = subprocess.run(
                    [str(python), "-c", version_probe],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                report["environment_versions"][name] = json.loads(probe.stdout)
            except Exception as exc:
                report["environment_versions"][name] = {"error": type(exc).__name__}
        perception, decision, grounder = (
            OmniParserBackend(config),
            ClefBackend(config),
            VisualGroundingBackend(config),
        )
        instrument_worker_trace(
            tuple(
                (name, backend.worker)
                for name, backend in (
                    ("parser", perception),
                    ("clef", decision),
                    ("visual", grounder),
                )
            ),
            report,
            save,
            output,
        )
        if args.exclusive_model_workers:
            configure_exclusive_workers(
                tuple(backend.worker for backend in (perception, decision, grounder))
            )

        class RecordingAction(DesktopAction):
            def __init__(self, persist=None, selection_readback=None):
                super().__init__()
                self.attempts = []
                self.persist = persist or (lambda: None)
                self.selection_readback = selection_readback

            def record_selection_state(self, attempt, field):
                if self.selection_readback is not None:
                    try:
                        attempt[field] = self.selection_readback()
                    except Exception as exc:
                        attempt[field + "_error"] = type(exc).__name__
                    self.persist()

            def execute(self, action, observation, cancelled):
                target = next((obj for obj in observation.objects if obj.id == action.target), None)
                frame = observation.frame
                coordinates = []
                if action.pointer is not None:
                    coordinates = [frame.pointer_point(point) for point in action.pointer.points]
                elif target is not None and action.operation in {
                    "click",
                    "double_click",
                    "focus",
                    "type",
                    "scroll",
                }:
                    coordinates = [frame.point(target.bbox)]
                width, height = frame.logical_size or frame.image.size
                points = [
                    ((x - frame.origin[0]) / width, (y - frame.origin[1]) / height)
                    for x, y in coordinates
                ]
                attempt = {
                    "operation": action.operation,
                    # Planned points are not proof that every input was delivered.
                    "points": points,
                    "size": observation.frame.image.size,
                    "ok": False,
                    "delivery": "partial_or_unknown",
                }
                self.attempts.append(attempt)
                self.persist()
                self.record_selection_state(attempt, "native_before")
                try:
                    result = super().execute(action, observation, cancelled)
                except Exception as exc:
                    attempt["error"] = type(exc).__name__
                    self.persist()
                    raise
                attempt.update(ok=result.ok, delivery="completed" if result.ok else "not_completed")
                self.persist()
                self.record_selection_state(attempt, "native_after")
                return result

        for repetition in range(args.repetitions):
            for case, (goal, query, area_type) in ((key, CASES[key]) for key in args.cases):
                variants = ("baseline", "hybrid") if repetition % 2 == 0 else ("hybrid", "baseline")
                for variant in variants:
                    row = {
                        "case": case,
                        "variant": variant,
                        "repetition": repetition,
                        "status": "ERROR",
                        "success": None,
                        "candidate_count": None,
                        "mode": None,
                        "confidence": None,
                        "grounding_ms": None,
                        "grounding_error": None,
                        "grounding_error_method": "editor region containment only",
                        "input_attempts": [],
                    }
                    started = time.perf_counter()
                    row["workers_alive_before"] = {
                        name: backend.worker.process is not None
                        and backend.worker.process.poll() is None
                        for name, backend in (
                            ("parser", perception),
                            ("clef", decision),
                            ("visual", grounder),
                        )
                    }
                    report["in_flight"] = row
                    save()
                    try:
                        pyautogui.press("esc")  # Fixture reset; outside measured runtime actions.
                        before = request(args.port, "reset", token=token, case=case)
                        row["before"] = before
                        if not fixture_ready(case, before):
                            raise RuntimeError("fixture precondition failed")
                        if case == "prior_splash_failure":
                            show_splash(pyautogui, before)
                        time.sleep(0.5)
                        capture = DesktopCapture()
                        prefix = f"{case}-{repetition}-{variant}"
                        before_frame = capture.capture()
                        before_frame.image.save(output / f"{prefix}-before.png")
                        row["before_screenshot"] = f"{prefix}-before.png"
                        region = case_region(case, before["areas"], area_type)
                        box = (
                            BoundingBox(**{key: region[key] for key in ("x1", "y1", "x2", "y2")})
                            if region
                            else None
                        )
                        intent = VisualIntent(
                            query=query,
                            coarse_strategy="overview" if case == "viewport_selection" else "tiled",
                            target_geometry="horizontal_line" if case == "drag" else "point",
                            operation="drag" if case == "drag" else "click",
                            end_query="Face object row in Outliner" if case == "drag" else None,
                            region=box,
                        )
                        session = Session(
                            Contract(
                                goal=goal,
                                execution_mode=(
                                    "STRUCTURED"
                                    if variant == "baseline"
                                    else "CANVAS"
                                    if case == "viewport_selection"
                                    else "AUTO"
                                ),
                                visual_intent=intent if variant == "hybrid" else None,
                                max_steps=config.max_steps,
                                success_conditions=[goal + " is visibly achieved"],
                            )
                        )
                        action = RecordingAction(
                            save,
                            selection_readback=(lambda: request(args.port, "readback", token=token))
                            if case in {"outliner", "viewport_selection"}
                            else None,
                        )
                        row["input_attempts"] = action.attempts
                        runtime = SessionRuntime(
                            capture,
                            perception,
                            decision,
                            action,
                            config,
                            grounder=grounder if variant == "hybrid" else None,
                            log_path=output / f"{case}-{repetition}-{variant}.jsonl",
                        )
                        action_started = time.perf_counter()
                        result = runtime.execute(session)
                        row["runtime_ms"] = (time.perf_counter() - action_started) * 1000
                        trial = {key: row[key] for key in ("case", "variant", "repetition")}
                        requests = [
                            entry
                            for entry in report.get("clef_requests", [])
                            if entry.get("trial") == trial
                        ]
                        row.update(
                            result=result,
                            status=result["status"],
                            history=session.history,
                            **trial_metrics(session.history, requests),
                        )
                        errors = [
                            region_error(point, region, attempt["size"])
                            for attempt in action.attempts
                            if attempt["ok"]
                            for point in attempt["points"]
                        ]
                        errors = [error for error in errors if error is not None]
                        row["grounding_error"] = max(errors) if errors else None
                        save()
                        capture.capture().image.save(output / f"{prefix}-after.png")
                        row["after_screenshot"] = f"{prefix}-after.png"
                        after = request(args.port, "readback", token=token)
                        row.update(
                            before=before,
                            after=after,
                            result=result,
                            status=result["status"],
                            success=outcome(case, before, after, input_attempts=action.attempts),
                            history=session.history,
                        )
                    except Exception as exc:
                        row["error"] = type(exc).__name__ + ": " + str(exc)
                        if "result" in row:
                            row["outcome_error"] = row["error"]
                    row["end_to_end_ms"] = (time.perf_counter() - started) * 1000
                    row["worker_ready"] = {
                        name: backend.worker.ready
                        for name, backend in (
                            ("parser", perception),
                            ("clef", decision),
                            ("visual", grounder),
                        )
                    }
                    report["runs"].append(row)
                    save()
                    report.pop("in_flight", None)
                    save()
                    if processes[-1].poll() is not None:
                        raise RuntimeError("isolated Blender exited; remaining trials NOT_RUN")
        return 0
    except Exception as exc:
        report["fatal_error"] = type(exc).__name__ + ": " + str(exc)
        if not args.setup_smoke:
            report["not_run"] = missing_trials(args.cases, args.repetitions, report["runs"])
        save()
        raise
    finally:
        for backend_name in ("perception", "decision", "grounder"):
            backend = locals().get(backend_name)
            worker = getattr(backend, "worker", None)
            close = getattr(worker, "close", None)
            if close:
                close()
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for stream in streams:
            stream.close()


if __name__ == "__main__":
    raise SystemExit(main())
