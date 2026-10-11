"""Exercise guarded operations on an owned, disposable Blender/Xvfb desktop.

The app oracle is read-only after factory scene setup. It never accepts Python,
shell, or caller-supplied operator names. No production scene or preferences are
opened. Reports distinguish application telemetry from pixel observations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import socket
import subprocess
import time
from pathlib import Path

STARTUP = r"""
import bpy, hmac, json, socket
from pathlib import Path
root = Path(__ROOT__)
token = (root / "fixture-token").read_text()
server = socket.socket()
server.bind(("127.0.0.1", __PORT__))
server.listen(4)
server.setblocking(False)
clients = {}
win = bpy.context.window_manager.windows[0]
view = next(a for a in win.screen.areas if a.type == "VIEW_3D")
cube = bpy.data.objects["Cube"]
bpy.context.preferences.view.show_splash = False
for obj in win.view_layer.objects:
    obj.select_set(obj == cube)
win.view_layer.objects.active = cube
def binding(operator, preferred, action=None):
    for config in (bpy.context.window_manager.keyconfigs.user,
                   bpy.context.window_manager.keyconfigs.default):
        for km in config.keymaps:
            for item in km.keymap_items:
                if item.active and item.idname == operator and item.type == preferred:
                    if action is not None and getattr(item.properties, "action", None) != action:
                        continue
                    modifiers = [key for key in ("ctrl", "shift", "alt", "oskey")
                                 if getattr(item, key)]
                    return ["command" if key == "oskey" else key for key in modifiers] + [
                        {"RET":"enter", "ESC":"escape"}.get(item.type, item.type.lower())]
    return None
def state():
    modal = []
    for operator in getattr(win, "modal_operators", []):
        modal.append(dict(id=str(operator.as_pointer()), name=operator.bl_idname,
                          rna=operator.bl_rna.identifier))
    r3d = view.spaces.active.region_3d
    transform = {cube.name: {
        "translate": dict(zip("XYZ", list(cube.location))),
        "rotate": dict(zip("XYZ", [v * 180 / 3.141592653589793 for v in cube.rotation_euler])),
        "scale": dict(zip("XYZ", list(cube.scale)))}}
    keymap = {name: binding(operator, key) for name, operator, key in (
        ("translate", "transform.translate", "G"), ("rotate", "transform.rotate", "R"),
        ("scale", "transform.resize", "S"), ("search", "wm.search_menu", "F3"))}
    for name, operator in (("orbit", "view3d.rotate"), ("pan", "view3d.move")):
        found = binding(operator, "MIDDLEMOUSE")
        if found:
            keymap[name] = dict(button="middle", modifiers=found[:-1])
    keymap["select_all"] = ["ctrl", "a"]
    keymap["deselect"] = binding("object.select_all", "A", "DESELECT")
    for km in bpy.context.window_manager.keyconfigs.default.keymaps:
        if km.name == "Transform Modal Map":
            for item in km.keymap_items:
                entry = {"AXIS_X":"axis_x", "AXIS_Y":"axis_y", "AXIS_Z":"axis_z",
                         "CONFIRM":"commit", "CANCEL":"cancel"}.get(item.propvalue)
                if entry and item.active and item.type in {"X", "Y", "Z", "RET", "ESC"}:
                    logical = {"RET":"enter", "ESC":"escape"}.get(item.type, item.type.lower())
                    keymap[entry] = [logical]
    return dict(version=bpy.app.version_string,
        application="Blender", mode=cube.mode,
        selection=[o.name for o in win.view_layer.objects if o.select_get()],
        modal_operators=modal, has_modal_api=hasattr(win, "modal_operators"),
        unit={"translate": ("NONE" if win.scene.unit_settings.system == "NONE"
              else win.scene.unit_settings.length_unit),
              "rotate":win.scene.unit_settings.system_rotation, "scale":"NONE"},
        space=win.scene.transform_orientation_slots[0].type, keymap=keymap,
        transform_values=transform, transform_preview=transform,
        transform_context={cube.name:dict(parent=cube.parent.name if cube.parent else None,
            delta_identity=(all(abs(v)<1e-8 for v in cube.delta_location)
                and all(abs(v)<1e-8 for v in cube.delta_rotation_euler)
                and all(abs(v-1)<1e-8 for v in cube.delta_scale)),
            pivot=win.scene.tool_settings.transform_pivot_point)},
        properties={cube.name: {"location_x":cube.location.x, "scale_x":cube.scale.x,
            "shading":"SMOOTH" if all(p.use_smooth for p in cube.data.polygons) else "FLAT"}},
        view_revision=[list(r3d.view_location), list(r3d.view_rotation), r3d.view_distance],
        areas=[dict(type=a.type, surface=[a.x/win.width, 1-(a.y+a.height)/win.height,
            (a.x+a.width)/win.width, 1-a.y/win.height]) for a in win.screen.areas],
        operator_history=[o.bl_idname for o in bpy.context.window_manager.operators])
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
            chunk = conn.recv(16384)
            if not chunk:
                conn.close(); del clients[conn]; continue
            clients[conn] += chunk
            if len(clients[conn]) > 16384:
                conn.close(); del clients[conn]; continue
            if b"\n" not in clients[conn]: continue
            request = json.loads(clients[conn].split(b"\n", 1)[0])
            supplied = request.get("token")
            authorized = isinstance(supplied, str) and hmac.compare_digest(supplied, token)
            reply = state() if authorized and request.get("operation") == "readback" else {
                "error":"unauthorized or unsupported request"}
            conn.setblocking(True)
            conn.sendall(json.dumps(reply).encode() + b"\n")
            conn.close(); del clients[conn]
        except BlockingIOError:
            pass
    return .01
bpy.app.timers.register(tick, first_interval=.2)
(root / "ready.json").write_text(json.dumps(state()))
"""


def request(port, token):
    with socket.create_connection(("127.0.0.1", port), timeout=10) as connection:
        connection.sendall(json.dumps({"operation": "readback", "token": token}).encode() + b"\n")
        data = b""
        while not data.endswith(b"\n"):
            chunk = connection.recv(65536)
            if not chunk:
                raise RuntimeError("Blender oracle closed its connection")
            data += chunk
    result = json.loads(data)
    if "error" in result:
        raise RuntimeError(result["error"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--display", default=":198")
    parser.add_argument("--port", type=int, default=39851)
    parser.add_argument("--inspect-only", action="store_true")
    parser.add_argument(
        "--runtime",
        action="store_true",
        help="Use the imported package's SessionRuntime/Contract operation path",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or Path("/tmp/.X11-unix/X" + args.display[1:]).exists():
        parser.error("output and display must both be newly owned")
    with socket.socket() as check:
        check.bind(("127.0.0.1", args.port))
    output.mkdir(mode=0o700, parents=True)
    token = secrets.token_hex(32)
    token_path = output / "fixture-token"
    token_path.touch(mode=0o600)
    token_path.write_text(token)
    authority = output / "Xauthority"
    authority.touch(mode=0o600)
    subprocess.run(
        ["xauth", "-f", str(authority), "add", args.display, ".", secrets.token_hex(16)],
        check=True,
        capture_output=True,
    )
    os.environ.update(DISPLAY=args.display, XAUTHORITY=str(authority))
    (output / "start.py").write_text(
        STARTUP.replace("__ROOT__", repr(str(output))).replace("__PORT__", str(args.port))
    )
    report = {
        "kind": "ISOLATED_BLENDER_OPERATIONS",
        "access_level": "APP_TELEMETRY_ASSISTED",
        "production_scene_touched": False,
        "runs": [],
    }
    processes, streams = [], []
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
                    "--env=BLENDER_USER_CONFIG=" + str(output / "config"),
                    "--env=XMODIFIERS=@im=none",
                    "org.blender.Blender",
                    "--factory-startup",
                    "--python",
                    str(output / "start.py"),
                ],
            ),
        ):
            stream = (output / (name + ".log")).open("w")
            streams.append(stream)
            processes.append(subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT))
            if name == "xvfb":
                deadline = time.monotonic() + 10
                while not Path("/tmp/.X11-unix/X" + args.display[1:]).exists():
                    if time.monotonic() > deadline or processes[-1].poll() is not None:
                        raise RuntimeError("owned Xvfb startup failed")
                    time.sleep(0.05)
        deadline = time.monotonic() + 60
        while not (output / "ready.json").exists():
            if time.monotonic() > deadline or processes[-1].poll() is not None:
                raise RuntimeError("owned Blender startup failed; inspect blender.log")
            time.sleep(0.1)
        import pyautogui
        from blender_hybrid_benchmark import focus_fixture_window

        from clef_use.backends import DesktopCapture

        report["focus"] = focus_fixture_window()
        report["initial_oracle"] = request(args.port, token)
        time.sleep(0.5)
        capture = DesktopCapture()
        frame = capture.capture()
        frame.image.save(output / "initial.png")
        if not args.inspect_only:
            report.update(exercise(args, token, capture, pyautogui, output))
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        (output / "report.json").write_text(json.dumps(report, indent=2))
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for stream in streams:
            stream.close()
    print(
        json.dumps(
            {
                "report": str(output / "report.json"),
                "error": report.get("error"),
                "runs": [
                    {
                        "name": row["name"],
                        "status": (row.get("service_entry_refusal") or row["report"])["status"],
                        "reason": (row.get("service_entry_refusal") or row["report"]).get("reason"),
                    }
                    for row in report["runs"]
                ],
            }
        )
    )
    return 1 if report.get("error") or report.get("fixture_passed") is False else 0


def exercise(args, token, capture, gui, output):
    from threading import Event

    from Xlib import display

    from clef_use.backends import DesktopAction
    from clef_use.input_ir import ChordInput, KeyInput, PointerInput, TextInput
    from clef_use.operations import OperationReport, OperationRunner, parse_operation_request
    from clef_use.schema import Observation
    from clef_use.state import FactValidity, StateCompiler, StateFact, StateSource

    compiler = StateCompiler()
    frames = {}
    control = {"popup": False, "text_focus": False, "focused_property": None}

    class FixtureAction(DesktopAction):
        """Real native backend with a private fixture-only completed-event trace."""

        def execute_input(self, command, frame, cancelled, **kwargs):
            self.dispatch_attempts += 1
            if isinstance(command, KeyInput) and command.key == "f3":
                control.pop("search_anchor", None)
                # Arm observation before injection so post-ACK guards see the
                # actual popup transition while native execution is in flight.
                control["search_probe"] = True
            result = super().execute_input(command, frame, cancelled, **kwargs)
            if result.ok and (
                (isinstance(command, TextInput) and control.pop("abort_after_text", False))
                or (
                    isinstance(command, KeyInput)
                    and command.key == "g"
                    and control.pop("abort_after_enter", False)
                )
            ):
                if args.runtime:
                    manager.dispatch("abort", {"session_id": manager.active})
                    control["abort_path"] = "SessionManager.dispatch(abort) -> SessionRuntime.abort"
                else:
                    cancelled.set()
                    control["abort_path"] = "independent cancellation event"
            if result.ok and isinstance(command, KeyInput):
                if command.key in {"enter", "escape"}:
                    control.update(
                        popup=False, text_focus=False, focused_property=None, search_probe=False
                    )
            time.sleep(0.05)
            return result

    action = FixtureAction(gui)
    action.dispatch_attempts = 0
    connection = display.Display()
    xim_atom = connection.intern_atom("_XIM_SERVERS", only_if_exists=True)
    xim = connection.screen().root.get_full_property(xim_atom, 0) if xim_atom else None
    if xim is not None and len(xim.value):
        raise RuntimeError("isolated fixture has an XIM server; composition state is unknown")
    connection.close()
    oracle = request(args.port, token)
    surface = next(a["surface"] for a in oracle["areas"] if a["type"] == "VIEW_3D")
    gui.moveTo(int((surface[0] + surface[2]) * 640), int((surface[1] + surface[3]) * 450))
    gui.PAUSE = 0
    screenshots = 0

    def ocr(image):
        nonlocal screenshots
        screenshots += 1
        path = output / f"observe-{screenshots}.png"
        image.save(path)
        result = subprocess.run(
            ["tesseract", str(path), "stdout", "--psm", "11"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def provide(observation, version):
        oracle = request(args.port, token)
        frame = observation.frame
        facts = {}
        for name in (
            "application",
            "mode",
            "selection",
            "unit",
            "space",
            "keymap",
            "transform_values",
            "transform_preview",
            "transform_context",
            "properties",
        ):
            facts[name] = StateFact(
                value=oracle[name],
                # UI text selection is a controlled fixture binding rather
                # than an RNA-discovered keymap item. Keep aggregate keymap
                # provenance API-assisted; all command-search bindings above
                # are still read from the current real application keymap.
                source=StateSource.API if name == "keymap" else StateSource.APP_TELEMETRY,
                observed_at=time.time(),
                state_version=version,
                validity=FactValidity.VALID,
                uncertainty=0,
            )
        keymap_version = hashlib.sha256(
            json.dumps(oracle["keymap"], sort_keys=True).encode()
        ).hexdigest()
        for name, value in (
            ("keymap_version", keymap_version),
            ("owned_inputs", sorted(action.keys) + ["button:" + b for b in sorted(action.buttons)]),
            ("view_revision", oracle["view_revision"]),
        ):
            facts[name] = StateFact(
                value=value,
                source=StateSource.NATIVE if name == "owned_inputs" else StateSource.APP_TELEMETRY,
                observed_at=time.time(),
                state_version=version,
                validity=FactValidity.VALID,
                uncertainty=0,
            )
        facts["target_geometry"] = StateFact(
            value={
                "editor_surface": next(
                    a["surface"] for a in oracle["areas"] if a["type"] == "VIEW_3D"
                )
            },
            source=StateSource.APP_TELEMETRY,
            observed_at=time.time(),
            state_version=version,
            validity=FactValidity.VALID,
            uncertainty=0,
        )
        x, y = gui.position()
        px, py = x / frame.image.width, y / frame.image.height
        editor = next(
            (
                a["type"]
                for a in oracle["areas"]
                if a["surface"][0] <= px <= a["surface"][2]
                and a["surface"][1] <= py <= a["surface"][3]
            ),
            None,
        )
        modals = [m for m in oracle["modal_operators"] if m["name"].startswith("TRANSFORM_OT_")]
        modal = None
        if modals:
            modal = {
                "id": modals[-1]["id"],
                "name": {
                    "TRANSFORM_OT_translate": "translate",
                    "TRANSFORM_OT_rotate": "rotate",
                    "TRANSFORM_OT_resize": "scale",
                }.get(modals[-1]["name"], modals[-1]["name"]),
            }
        for name, value in (
            ("editor", editor),
            ("modal", modal),
            ("loading", False),
            ("text_focus", control["text_focus"]),
            ("ime_composing", False),
            ("popup", control["popup"]),
            ("focused_property", control["focused_property"]),
        ):
            # These are scoped fixture invariants: private display, factory
            # startup, no XIM server, sole controller event trace, no external
            # input, and current native cursor/editor + real modal readback.
            # They are never exported as a general production Blender detector.
            facts[name] = StateFact(
                value=value,
                source=StateSource.API,
                observed_at=time.time(),
                state_version=version,
                validity=FactValidity.VALID,
                uncertainty=0,
            )
        if control.get("search_probe"):
            anchor = control.get("search_anchor")
            if anchor:
                box, digest = anchor
                is_search = hashlib.sha256(frame.image.crop(box).tobytes()).hexdigest() == digest
            else:
                text = ocr(frame.image)
                is_search = all(word in text for word in ("Armature", "Nurbs", "Empty Hair"))
                if is_search:
                    box = (x + 3, y + 4, x + 20, y + 21)
                    control["search_anchor"] = (
                        box,
                        hashlib.sha256(frame.image.crop(box).tobytes()).hexdigest(),
                    )
            if is_search:
                control.update(popup="COMMAND_SEARCH", text_focus=True)
                facts["popup"] = facts["popup"].model_copy(update={"value": "COMMAND_SEARCH"})
                facts["text_focus"] = facts["text_focus"].model_copy(update={"value": True})
            else:
                # The exact owned search chrome disappeared and a registered
                # search command really ran with its corresponding property
                # effect. This is a fixture-only closed-popup observation,
                # not an assumption that an attempted Enter closed anything.
                completed = {
                    "OBJECT_OT_shade_smooth": "SMOOTH",
                    "OBJECT_OT_shade_flat": "FLAT",
                }.get(oracle["operator_history"][-1] if oracle["operator_history"] else "")
                if anchor and completed == oracle["properties"]["Cube"]["shading"]:
                    facts["popup"] = facts["popup"].model_copy(update={"value": False})
                    facts["text_focus"] = facts["text_focus"].model_copy(update={"value": False})
                elif control["popup"] == "COMMAND_SEARCH":
                    facts["popup"] = facts["popup"].model_copy(
                        update={"validity": FactValidity.UNKNOWN}
                    )
        if control.get("menu"):
            text = ocr(frame.image)
            signature = {
                "File": ("Open", "Save", "Revert"),
                "Edit": ("Undo", "Undo History", "Preferences"),
            }[control["menu"]]
            menu_visible = all(word in text for word in signature)
            facts["menus"] = StateFact(
                value=[dict(name=control["menu"], open=True, id="pixel-popup")]
                if menu_visible
                else [],
                source=StateSource.PIXELS,
                observed_at=time.time(),
                state_version=version,
                validity=FactValidity.VALID,
                uncertainty=0.05,
            )
        else:
            facts["menus"] = StateFact(
                value=[],
                source=StateSource.API,
                observed_at=time.time(),
                state_version=version,
                validity=FactValidity.VALID,
                uncertainty=0,
            )
        history = oracle["operator_history"]
        command_result = {
            "OBJECT_OT_shade_smooth": "object.shade_smooth",
            "OBJECT_OT_shade_flat": "object.shade_flat",
        }.get(history[-1] if history else "")
        facts["command_result"] = StateFact(
            value=command_result,
            source=StateSource.APP_TELEMETRY,
            observed_at=time.time(),
            state_version=version,
            validity=FactValidity.VALID,
            uncertainty=0,
        )
        return facts

    def observe():
        frame = capture.capture()
        version = compiler.version + 1
        observation = Observation(str(version), frame, ())
        state = compiler.compile(observation, provide(observation, version))
        frames[state.observation_id] = frame
        return state

    def execute(command, state, cancelled):
        return action.execute_input(command, frames[state.observation_id], cancelled)

    state = observe()
    runner = OperationRunner(observe, execute, text_method="unicode")
    runtime = session = manager = None
    if args.runtime:
        from clef_use.config import Config
        from clef_use.runtime import SessionRuntime
        from clef_use.service import SessionManager

        runtime = SessionRuntime(
            capture,
            None,
            None,
            action,
            Config(),
            state_provider=provide,
            log_path=output / "runtime.jsonl",
        )
        manager = SessionManager(factory=lambda: runtime)
    version = state.require("keymap_version")
    runs = []
    modal_sessions = {}

    def run(name, values):
        nonlocal session
        before = request(args.port, token)
        input_attempts_before = action.dispatch_attempts
        runtime_result = None
        service_refusal = lease = None
        if args.runtime:
            operation = parse_operation_request(values).model_dump(mode="json")
            if values["family"] == "modal_cancel":
                started = manager.continue_session(
                    modal_sessions[values["modal_id"]],
                    "Cancel only the known owned modal without committing",
                    operation,
                )
            else:
                started = manager.run(
                    dict(goal="Exercise registered operation on owned fixture", operation=operation)
                )
            session = manager.get(started["session_id"])
            deadline = time.monotonic() + 30
            while manager.busy and time.monotonic() < deadline:
                time.sleep(0.01)
            if manager.busy:
                raise RuntimeError("installed service operation exceeded fixture deadline")
            runtime_result = session.snapshot()
            if runtime_result["status"] == "SAFETY_BLOCK" and runtime_result["blocker"] is None:
                report = None
                service_refusal = dict(
                    status="SAFETY_BLOCK",
                    reason=runtime_result["reason"],
                    operation_invoked=session.id in runtime.operation_runners,
                    input_count=0,
                    input_dispatch_attempts=action.dispatch_attempts - input_attempts_before,
                )
            else:
                report = OperationReport.model_validate(runtime_result["blocker"]["observed"])
                if report.owned_modal_id:
                    modal_sessions[report.owned_modal_id] = session.id
                if report.status == "ABORTED" and report.owned_modal_id:
                    lease = {"health": manager.dispatch("health", {})}
                    try:
                        manager.dispatch("shutdown_idle", {})
                    except RuntimeError as exc:
                        lease["shutdown_idle_refusal"] = str(exc)
                    else:
                        raise RuntimeError("shutdown_idle accepted while an owned modal was open")
                    lease["stopping_after_refusal"] = manager.stopping
                elif values["family"] == "modal_cancel" and report.status == "SUCCEEDED":
                    lease = {
                        "health_after_cleanup": manager.dispatch("health", {}),
                        "stopping_after_cleanup": manager.stopping,
                    }
        else:
            report = runner.run(parse_operation_request(values), Event())
        after = request(args.port, token)
        capture.capture().image.save(output / (name + ".png"))
        runs.append(
            dict(
                name=name,
                report=report.model_dump(mode="json") if report else None,
                service_entry_refusal=service_refusal,
                desktop_lease=lease,
                before=before,
                after=after,
                runtime_result=runtime_result,
                evidence="service_entry_refusal"
                if service_refusal
                else "live application oracle + real DesktopAction; controlled private fixture",
                expected_status=(
                    "SAFETY_BLOCK"
                    if args.runtime and name == "existing_modal_guard"
                    else "BLOCKED"
                    if name.endswith("_guard")
                    else "ABORTED"
                    if name.endswith("_abort")
                    else "SUCCEEDED"
                ),
            )
        )
        return report

    transform = dict(
        family="numeric_transform",
        target_id="Cube",
        operation="translate",
        axis="X",
        space="GLOBAL",
        unit=state.require("unit")["translate"],
        amount=2,
        keymap_version=version,
    )
    run("wrong_keymap_guard", dict(transform, keymap_version="unobserved-keymap-version"))
    run("wrong_unit_guard", dict(transform, unit="CENTIMETERS"))
    run("numeric_transform", transform)
    run("numeric_transform_cancel", dict(transform, commit=False))
    control["abort_after_enter"] = True
    entered = run("numeric_transform_enter_abort", transform)
    if entered.owned_modal_id:
        run(
            "known_modal_enter_cancel",
            dict(family="modal_cancel", modal_id=entered.owned_modal_id),
        )
    control["abort_after_text"] = True
    pending = run("numeric_transform_abort", transform)
    if pending.owned_modal_id:
        run("existing_modal_guard", transform)
        run("known_modal_cancel", dict(family="modal_cancel", modal_id=pending.owned_modal_id))
    run("scale_y", dict(transform, operation="scale", axis="Y", unit="NONE", amount=1.5))
    run("rotation_z", dict(transform, operation="rotate", axis="Z", unit="DEGREES", amount=45))
    run(
        "incompatible_global_scale_guard",
        dict(transform, operation="scale", axis="Y", unit="NONE", amount=1.5),
    )
    run(
        "viewport_orbit",
        dict(
            family="viewport_gesture",
            gesture="orbit",
            keymap_version=version,
            points=((0.4, 0.4), (0.45, 0.43)),
            surface=surface,
        ),
    )
    run(
        "viewport_pan",
        dict(
            family="viewport_gesture",
            gesture="pan",
            keymap_version=version,
            points=((0.4, 0.4), (0.44, 0.42)),
            surface=surface,
        ),
    )
    run(
        "command_search",
        dict(
            family="command_search",
            command="object.shade_smooth",
            target_id="Cube",
            keymap_version=version,
        ),
    )
    # Known checkpoint: only an owned search popup may remain after the search
    # family; cancel it by its observed UI before continuing setup, not by a
    # production blind-Escape recovery path.
    if control["popup"] == "COMMAND_SEARCH":
        frame = capture.capture()
        anchor = control.get("search_anchor")
        if (
            anchor
            and hashlib.sha256(frame.image.crop(anchor[0]).tobytes()).hexdigest() == anchor[1]
        ):
            action.execute_input(KeyInput(key="escape"), frame, Event())
        control.update(popup=False, text_focus=False)
        control.pop("search_anchor", None)
    run("menu_absent", dict(family="menu_assess", menu="File"))
    for menu, x in (("File", 42), ("Edit", 80)):
        action.execute_input(PointerInput(point=(x / 1280, 13 / 900)), capture.capture(), Event())
        control["menu"] = menu
        time.sleep(0.15)
        run("menu_" + menu.lower(), dict(family="menu_assess", menu="File"))
        action.execute_input(KeyInput(key="escape"), capture.capture(), Event())
        control.pop("menu")
    # The fixture uses one named object and the factory property layout. These
    # coordinates are setup only; the production operation requires a verified
    # exact focused field and does not click guessed property coordinates.
    for _ in range(2):
        action.execute_input(
            PointerInput(point=(1188 / 1280, 332 / 900)), capture.capture(), Event()
        )
        time.sleep(0.08)
    control.update(text_focus=True, focused_property={"target_id": "Cube", "field": "location_x"})
    focused = capture.capture()
    focused.image.save(output / "property-focused.png")
    field_pixels = focused.image.crop((1155, 318, 1230, 347)).convert("RGB")
    caret_pixels = sum(
        b > r * 1.4 and b > g * 1.1 and b > 120 for r, g, b in field_pixels.get_flattened_data()
    )
    if caret_pixels >= 10:
        # Moving the pointer does not commit the selected text field. Keep
        # the actual text edit active while the pointer selects VIEW_3D so
        # this counterexample isolates keyboard focus from editor mismatch.
        gui.moveTo(500, 400)
        run("text_focus_guard", transform)
        gui.moveTo(1188, 332)
        run(
            "property_edit",
            dict(
                family="property_edit",
                target_id="Cube",
                field="location_x",
                value=3,
                keymap_version=version,
            ),
        )
    else:
        runs.append(
            dict(
                name="property_edit",
                report=dict(
                    status="NOT_RUN",
                    reason="exact selected property pixel evidence unavailable",
                    caret_pixels=caret_pixels,
                ),
            )
        )
    gui.moveTo(500, 350)
    control.update(text_focus=False, focused_property=None)
    deselect = request(args.port, token)["keymap"]["deselect"]
    if not deselect:
        raise RuntimeError("observed keymap lacks an exact deselect binding")
    action.execute_input(
        ChordInput(modifiers=tuple(deselect[:-1]), key=deselect[-1])
        if len(deselect) > 1
        else KeyInput(key=deselect[0]),
        capture.capture(),
        Event(),
    )
    time.sleep(0.1)
    run("selection_changed_guard", transform)
    action.execute_input(PointerInput(point=(1160 / 1280, 128 / 900)), capture.capture(), Event())
    time.sleep(0.1)
    gui.moveTo(1180, 350)
    run("wrong_editor_guard", transform)
    for row in runs:
        outcome = row.get("service_entry_refusal") or row["report"]
        row["passed"] = outcome["status"] == row.get("expected_status", "SUCCEEDED")
        if outcome["status"] == "NOT_RUN":
            row["passed"] = False
            continue
        if args.runtime:
            expected_task_status = (
                "SAFETY_BLOCK"
                if row["name"] == "existing_modal_guard"
                else "BLOCKED"
                if row["name"].endswith("_guard") or row["name"] in {"menu_absent", "menu_edit"}
                else "ABORTED"
                if row["name"].endswith("_abort")
                else "NEEDS_REPLAN"
            )
            row["expected_task_status"] = expected_task_status
            row["passed"] &= row["runtime_result"]["status"] == expected_task_status
            if row["service_entry_refusal"]:
                row["passed"] &= (
                    row["report"] is None
                    and outcome["operation_invoked"] is False
                    and outcome["input_dispatch_attempts"] == 0
                )
            lease = row.get("desktop_lease")
            if outcome["status"] == "ABORTED" and outcome.get("owned_modal_id"):
                row["passed"] &= (
                    lease["health"]["busy"] is True
                    and "owns the desktop" in lease["shutdown_idle_refusal"]
                    and lease["stopping_after_refusal"] is False
                )
            elif lease and "health_after_cleanup" in lease:
                row["passed"] &= (
                    lease["health_after_cleanup"]["busy"] is False
                    and lease["stopping_after_cleanup"] is False
                )
        guard_reason = {
            "wrong_keymap_guard": "keymap_version",
            "wrong_unit_guard": "unit",
            "existing_modal_guard": "modal",
            "incompatible_global_scale_guard": "rotated",
            "text_focus_guard": "text_focus",
            "selection_changed_guard": "selection",
            "wrong_editor_guard": "editor",
        }.get(row["name"])
        if guard_reason:
            row["passed"] &= (
                guard_reason in outcome["reason"]
                and outcome["input_count"] == 0
                and row["before"]["transform_values"] == row["after"]["transform_values"]
            )
        expected_menu = {
            "menu_absent": "ABSENT",
            "menu_file": "OPEN",
            "menu_edit": "WRONG_MENU",
        }.get(row["name"])
        if expected_menu:
            row["passed"] &= row["report"].get("assessment") == expected_menu
    return {
        "access_level": "API_ASSISTED",
        "runs": runs,
        "fixture_passed": all(row["passed"] for row in runs),
        "execution_path": "SessionManager.run/continue_session -> SessionRuntime.execute"
        if args.runtime
        else "OperationRunner.run",
        "imported_package": str(Path(__import__("clef_use").__file__).resolve()),
        "runtime_source": str(
            Path(__import__("clef_use.runtime", fromlist=["__file__"]).__file__).resolve()
        ),
        "abort_path": control.get("abort_path"),
        "fixture_invariant_scope": "API_ASSISTED: private factory-startup Xvfb; no XIM server; "
        "sole controller event trace; actual cursor/editor and Blender modal/readback. "
        "This evidence provider is not installed into production runtime.",
        "not_run": {
            "original_model_assess": "Run canonical model separately over saved menu screenshots",
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
