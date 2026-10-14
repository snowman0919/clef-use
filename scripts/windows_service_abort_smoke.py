"""Observe installed CLI/HTTP abort of an owned Windows input lease.

This component explicitly registers a real Session with a real SessionManager.
It does not run SessionRuntime.execute, a model, a full GestureInput, or a
Blender operation. The same runtime.action acquires native Shift/middle input;
the injector then blocks independently of the HTTP/CLI abort path.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path
from threading import Event, Thread

from windows_gui_support import restore_foreground, widget_point

from clef_use import __version__
from clef_use.backends import DesktopAction, DesktopCapture
from clef_use.input_ir import InputContext, InputInterrupted, KeyInput, PointerInput
from clef_use.runtime import Session, SessionRuntime
from clef_use.schema import Contract, Status
from clef_use.service import SessionManager, make_server
from clef_use.windows_input import Point, WindowsInput

LEASE_SECONDS = 25
INJECTOR_BLOCK_SECONDS = 20
CLI_SECONDS = 10
READBACK_SECONDS = 5


class Rectangle(ctypes.Structure):
    _fields_ = [(name, ctypes.c_long) for name in ("left", "top", "right", "bottom")]


class GuiThreadInfo(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        *[
            (name, ctypes.c_void_p)
            for name in ("active", "focus", "capture", "menu_owner", "move_size", "caret")
        ],
        ("caret_rect", Rectangle),
    ]


def held(gui):
    gui.user.GetAsyncKeyState.argtypes = [ctypes.c_int]
    gui.user.GetAsyncKeyState.restype = ctypes.c_short
    return [vk for vk in range(1, 256) if gui.user.GetAsyncKeyState(vk) & 0x8000]


def main(output):
    if sys.platform != "win32":
        raise RuntimeError("Requires an interactive Windows desktop")
    if output.exists():
        raise RuntimeError("Output already exists; attempts must be preserved")
    state = output.with_suffix(".state")
    state.mkdir(exist_ok=False)
    os.environ["CLEF_USE_STATE_DIR"] = str(state)
    os.environ["CLEF_USE_CONFIG"] = str(state / "absent.toml")
    gui, action, capture = WindowsInput(), DesktopAction(), DesktopCapture()
    root = owned = server = server_thread = injector = child = None
    ready, unblock = Event(), Event()
    endpoint_bytes = None
    previous, pointer = gui.foreground(), Point()
    with gui.physical_coordinates():
        pointer_known = bool(gui.user.GetCursorPos(ctypes.byref(pointer)))
    report = {
        "status": "FAILED",
        "mode": "REAL_WINDOWS_CLI_HTTP_ABORT_COMPONENT",
        "runtime_version": __version__,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "Explicit session setup; held Shift/middle lease; no models or full gesture",
        "budgets_seconds": {
            "lease": LEASE_SECONDS,
            "injector_block": INJECTOR_BLOCK_SECONDS,
            "cli": CLI_SECONDS,
            "readback": READBACK_SECONDS,
        },
    }
    session = Session(Contract(goal="Release this owned input lease through CLI abort"))
    worker = {}
    events = []

    def observe(predicate, seconds=READBACK_SECONDS):
        deadline = time.monotonic() + seconds
        while True:
            root.update()
            if predicate():
                return
            if time.monotonic() >= deadline:
                raise RuntimeError("Owned component observation exceeded its declared bound")
            time.sleep(0.005)

    try:
        report["desktop"] = gui.desktop_status()
        gui.user.IsWindow.argtypes = [ctypes.c_void_p]
        gui.user.IsWindow.restype = ctypes.c_int
        if not pointer_known or not previous or not gui.user.IsWindow(previous):
            raise RuntimeError("Original pointer/foreground restoration target unavailable")
        if held(gui):
            raise RuntimeError("External input is held; component refused")
        root = tk.Tk()
        root.title("clef-use owned service abort component")
        root.geometry("720x480+500+250")
        canvas = tk.Canvas(root, bg="white", takefocus=True)
        canvas.pack(fill="both", expand=True)

        def receive(phase, event):
            events.append(
                {
                    "phase": phase,
                    "key": getattr(event, "keysym", None),
                    "button": getattr(event, "num", None),
                    "at_ns": time.monotonic_ns(),
                }
            )

        canvas.bind("<KeyPress>", lambda event: receive("key_down", event))
        canvas.bind("<KeyRelease>", lambda event: receive("key_up", event))
        canvas.bind("<ButtonPress>", lambda event: receive("button_down", event))
        canvas.bind("<ButtonRelease>", lambda event: receive("button_up", event))
        root.update()
        canvas.focus_force()
        gui.user.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        gui.user.GetAncestor.restype = ctypes.c_void_p
        owned = gui.user.GetAncestor(root.winfo_id(), 2)
        gui.user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        if not gui.user.SetForegroundWindow(owned):
            raise RuntimeError("Owned foreground request was refused")
        root.update()
        canvas_hwnd = canvas.winfo_id()
        imm = ctypes.WinDLL("imm32", use_last_error=True)
        imm.ImmAssociateContextEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
        imm.ImmAssociateContextEx.restype = ctypes.c_int
        imm.ImmGetContext.argtypes = [ctypes.c_void_p]
        imm.ImmGetContext.restype = ctypes.c_void_p
        imm.ImmReleaseContext.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        imm.ImmReleaseContext.restype = ctypes.c_int
        if not imm.ImmAssociateContextEx(owned, None, 1):
            raise RuntimeError("Owned non-text canvas IMC disable was refused")
        gui.user.GetGUIThreadInfo.argtypes = [ctypes.c_uint, ctypes.POINTER(GuiThreadInfo)]
        gui.user.GetGUIThreadInfo.restype = ctypes.c_int

        def native_focus():
            info = GuiThreadInfo()
            info.size = ctypes.sizeof(info)
            native_thread = gui.user.GetWindowThreadProcessId(owned, None)
            if not native_thread or not gui.user.GetGUIThreadInfo(
                native_thread, ctypes.byref(info)
            ):
                raise RuntimeError("Owned native keyboard focus could not be read")
            if not info.focus or gui.user.GetAncestor(info.focus, 2) != owned:
                raise RuntimeError("Native keyboard focus is outside the owned window")
            return info.focus

        # Tk logical widget focus and Win32 HWND focus are different identities.
        # Bind the observed native HWND; do not assume it is the canvas HWND.
        bound_native_focus = native_focus()

        def guard():
            if gui.foreground() != owned or not gui.user.IsWindow(canvas_hwnd):
                raise RuntimeError("Owned canvas foreground changed")
            if gui.user.GetAncestor(canvas_hwnd, 2) != owned:
                raise RuntimeError("Owned canvas identity changed")
            if native_focus() != bound_native_focus:
                raise RuntimeError("Observed native keyboard focus changed")
            context = imm.ImmGetContext(canvas_hwnd)
            if context:
                imm.ImmReleaseContext(canvas_hwnd, context)
                raise RuntimeError("Owned canvas IMC absence is no longer observed")

        guard()
        if root.focus_get() is not canvas:
            raise RuntimeError("Owned non-text canvas keyboard focus was not observed")
        report["admission"] = {
            "owned_foreground": True,
            "nontext_canvas_focused": True,
            "native_focus_in_owned_window": True,
            "owned_canvas_imc_absent": True,
            "ime_scope": "Only this disposable canvas; not general IME discovery",
        }
        runtime = SessionRuntime(capture, None, None, action)
        manager = SessionManager()
        with manager.lock:
            manager.runtime = runtime
            manager.sessions[session.id] = session
            manager.active = session.id
            manager.busy = True
        report["session_setup"] = {
            "explicit_registration": True,
            "initial_status": session.status.value,
            "runtime_execute_called": False,
            "perception_and_decision_unused": True,
        }
        token = secrets.token_hex(32)
        server = make_server(manager, token)
        endpoint_bytes = json.dumps(
            {"port": server.server_port, "token": token, "pid": os.getpid()}
        ).encode("utf-8")
        (state / "endpoint.json").write_bytes(endpoint_bytes)
        server_thread = Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        frame = capture.capture()
        if frame.foreground_window != owned:
            raise RuntimeError("Capture did not bind the owned foreground")
        point = widget_point(gui, canvas, frame, 100, 200, owned)
        deadline = time.monotonic() + LEASE_SECONDS
        context = InputContext(text_focus=False, ime_composing=False)

        def inject():
            try:
                with runtime.desktop_lock:
                    for command in (
                        KeyInput(key="shift", phase="down"),
                        PointerInput(point=point, button="middle", phase="down"),
                    ):
                        result = runtime.action.execute_input(
                            command,
                            frame,
                            session.cancelled,
                            deadline=deadline,
                            context=context,
                            context_guard=guard,
                        )
                        if not result.ok:
                            raise RuntimeError(result.reason)
                    ready.set()
                    if not unblock.wait(INJECTOR_BLOCK_SECONDS):
                        raise RuntimeError("Owned injector was not unblocked within its budget")
                    try:
                        result = runtime.action.execute_input(
                            KeyInput(key="a"),
                            frame,
                            session.cancelled,
                            deadline=deadline,
                            context=context,
                            context_guard=guard,
                        )
                    except InputInterrupted as exc:
                        if not session.cancelled.is_set():
                            raise
                        worker.update(
                            after_abort_refused=True,
                            refusal_type=type(exc).__name__,
                            refusal_reason=str(exc),
                        )
                    else:
                        worker.update(
                            after_abort_refused=not result.ok,
                            refusal_type="ActionResult",
                            refusal_reason=result.reason,
                        )
            except Exception as exc:
                worker["error"] = type(exc).__name__ + ": " + str(exc)
            finally:
                with manager.lock:
                    manager.busy = False
                ready.set()

        injector = Thread(target=inject, daemon=True)
        injector.start()
        observe(ready.is_set)
        if worker.get("error"):
            raise RuntimeError(worker["error"])
        observe(lambda: any(e["phase"] == "button_down" and e["button"] == 2 for e in events))
        before = held(gui)
        if not ({4, 16, 160} <= set(before)) or not injector.is_alive():
            raise RuntimeError("Native Shift/middle held lease was not observed")
        guard()
        if session.cancelled.is_set():
            raise RuntimeError("Session was cancelled before the CLI request")
        started_ns = time.monotonic_ns()
        with (
            output.with_suffix(".cli.stdout").open("w", encoding="utf-8") as stdout,
            output.with_suffix(".cli.stderr").open("w", encoding="utf-8") as stderr,
        ):
            child = subprocess.Popen(
                [sys.executable, "-m", "clef_use.cli", "abort", "--session-id", session.id],
                stdout=stdout,
                stderr=stderr,
                env=os.environ.copy(),
            )
            observe(lambda: child.poll() is not None, CLI_SECONDS)
        reply = json.loads(output.with_suffix(".cli.stdout").read_text(encoding="utf-8"))
        if child.returncode != 0 or reply.get("session_id") != session.id:
            raise RuntimeError("Actual installed CLI abort did not return the owned session")
        if reply.get("status") != "ABORTED" or session.status != Status.ABORTED:
            raise RuntimeError("Canonical abort did not establish ABORTED")
        observe(lambda: not held(gui))
        observe(lambda: any(e["phase"] == "button_up" and e["button"] == 2 for e in events))
        guard()
        if time.monotonic() >= deadline or not injector.is_alive() or unblock.is_set():
            raise RuntimeError("Release was not observed while the injector remained blocked")
        releases = [e for e in events if e["phase"] in {"key_up", "button_up"}]
        if not any(e["phase"] == "key_up" and e["key"] == "Shift_L" for e in releases):
            raise RuntimeError("Owned Shift release was not received by the native widget")
        if any(e["at_ns"] < started_ns for e in releases):
            raise RuntimeError("Input was released before the CLI request")
        report["abort"] = {
            "cli_exit_code": child.returncode,
            "session_status": reply["status"],
            "session_cancelled": session.cancelled.is_set(),
            "held_before": before,
            "held_after": held(gui),
            "injector_still_blocked": injector.is_alive(),
            "service_busy_while_injector_blocked": manager.busy,
            "explicit_parent_release_before_observation": False,
            "lease_deadline_not_reached": True,
            "receiver_events": list(events),
        }
        unblock.set()
        observe(lambda: not injector.is_alive())
        if worker.get("error") or worker.get("after_abort_refused") is not True:
            raise RuntimeError("Cancelled injector did not refuse its subsequent command")
        if held(gui) or any(e["phase"] == "key_down" and e["key"] == "a" for e in events):
            raise RuntimeError("Cancelled injector reacquired or delivered native input")
        report["no_reacquisition"] = True
        report["status"] = "PASSED"
    except Exception as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        cleanup = {"errors": []}
        session.cancelled.set()
        unblock.set()
        try:
            if child is not None and child.poll() is None:
                child.terminate()
                child.wait(3)
                cleanup["owned_cli_terminated"] = True
        except Exception as exc:
            cleanup["errors"].append(type(exc).__name__ + ": " + str(exc))
        cleanup["owned_cli_exited"] = child is None or child.poll() is not None
        try:
            action.release()
        except Exception as exc:
            cleanup["errors"].append(type(exc).__name__ + ": " + str(exc))
        try:
            if injector is not None:
                injector.join(3)
                if injector.is_alive():
                    raise RuntimeError("Owned injector remains alive")
            cleanup["owned_injector_exited"] = True
        except Exception as exc:
            cleanup["errors"].append(type(exc).__name__ + ": " + str(exc))
        try:
            executor = action.input_executor
            if executor is not None and executor.guardian is not None:
                executor.guardian.stdin.close()
                executor.guardian.wait(3)
                cleanup["owned_guardian_exited"] = True
        except Exception as exc:
            cleanup["errors"].append(type(exc).__name__ + ": " + str(exc))
        try:
            cleanup["held_after"] = held(gui)
            if cleanup["held_after"]:
                raise RuntimeError("Native held input remains")
        except Exception as exc:
            cleanup["errors"].append(type(exc).__name__ + ": " + str(exc))
        try:
            if server is not None:
                if server_thread is not None:
                    server.shutdown()
                server.server_close()
            if server_thread is not None:
                server_thread.join(3)
                if server_thread.is_alive():
                    raise RuntimeError("Owned HTTP service thread remains alive")
            cleanup["owned_http_service_closed"] = True
            endpoint = state / "endpoint.json"
            if endpoint.exists():
                if endpoint.read_bytes() != endpoint_bytes:
                    raise RuntimeError("Owned endpoint changed; removal refused")
                endpoint.unlink()
            cleanup["owned_endpoint_removed"] = not endpoint.exists()
        except Exception as exc:
            cleanup["errors"].append(type(exc).__name__ + ": " + str(exc))
        if owned and gui.foreground() == owned:
            try:
                if not pointer_known:
                    raise RuntimeError("Original pointer was not observed")
                gui.FAILSAFE = False
                with gui.physical_coordinates():
                    gui.moveTo(pointer.x, pointer.y)
                cleanup["pointer_restored"] = True
            except Exception as exc:
                cleanup["errors"].append(type(exc).__name__ + ": " + str(exc))
        elif owned:
            cleanup["errors"].append("Owned foreground changed; pointer restoration refused")
        if owned and gui.foreground() == owned:
            try:
                cleanup.update(restore_foreground(root, gui, previous, owned))
                if not cleanup["foreground_restored"]:
                    raise RuntimeError("Original foreground restoration was not confirmed")
            except Exception as exc:
                cleanup["errors"].append(type(exc).__name__ + ": " + str(exc))
        elif owned:
            cleanup["errors"].append("Owned foreground changed; focus restoration refused")
        try:
            if root is not None:
                root.destroy()
            cleanup["owned_window_closed"] = True
        except Exception as exc:
            cleanup["errors"].append(type(exc).__name__ + ": " + str(exc))
        report["cleanup"] = cleanup
        report["injector_result"] = dict(worker)
        if cleanup["errors"]:
            report["status"] = "FAILED"
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"mode": report["mode"], "status": report["status"]}))
    return 0 if report["status"] == "PASSED" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.output))
