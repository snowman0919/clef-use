"""Observe installed typed pointer input and independent recovery on Windows."""

from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
import time
import tkinter as tk
import traceback
from pathlib import Path
from threading import Event, Thread

from windows_gui_support import restore_foreground, widget_point

from clef_use.backends import DesktopAction, DesktopCapture
from clef_use.input_ir import GestureInput, InputContext, KeyInput, PointerInput
from clef_use.windows_input import Point, WindowsInput


def held(gui):
    gui.user.GetAsyncKeyState.argtypes = [ctypes.c_int]
    gui.user.GetAsyncKeyState.restype = ctypes.c_short
    return [vk for vk in (1, 2, 4, 16, 160, 161) if gui.user.GetAsyncKeyState(vk) & 0x8000]


def hold_inputs(action, frame, cancel, point, deadline):
    context = InputContext(ime_composing=False, text_focus=False)
    for command in (
        KeyInput(phase="down", key="shift"),
        PointerInput(phase="down", point=point, button="middle"),
    ):
        outcome = action.execute_input(command, frame, cancel, deadline=deadline, context=context)
        if not outcome.ok:
            raise RuntimeError(outcome.reason)


def crash_worker(args):
    frame = DesktopCapture().capture()
    if frame.foreground_window != args.target:
        raise RuntimeError("owned receiver is no longer foreground")
    action = DesktopAction()
    hold_inputs(action, frame, Event(), tuple(args.point), time.monotonic() + 10)
    args.output.write_text(
        json.dumps({"holding": True, "guardian_pid": action.input_executor.guardian.pid}),
        encoding="utf-8",
    )
    # The parent terminates this owned process. There is deliberately no release
    # or finally here: only the separate guardian can recover after termination.
    Event().wait(30)
    raise RuntimeError("parent did not terminate the owned crash fixture")


def main(args):
    gui, action = WindowsInput(), DesktopAction()
    previous, pointer = gui.foreground(), Point()
    with gui.physical_coordinates():
        pointer_known = bool(gui.user.GetCursorPos(ctypes.byref(pointer)))
    root, owned, child, guardian_handle = None, None, None, None
    blocked, unblock, cancel = None, Event(), Event()
    report = {"mode": "REAL_WINDOWS_INSTALLED_TYPED_INPUT", "status": "FAILED"}
    try:
        report["desktop"] = gui.desktop_status()
        if held(gui):
            raise RuntimeError("external input is held; fixture refused")
        root = tk.Tk()
        root.title("clef-use owned typed input validation")
        root.geometry("720x480+500+250")
        root.attributes("-topmost", True)
        canvas = tk.Canvas(root, bg="white", takefocus=True)
        canvas.pack(fill="both", expand=True)
        events = []

        def receive(phase, event):
            events.append(
                {
                    "phase": phase,
                    "button": event.num,
                    "x": event.x,
                    "y": event.y,
                    "state": event.state,
                }
            )

        canvas.bind("<ButtonPress>", lambda event: receive("down", event))
        canvas.bind("<ButtonRelease>", lambda event: receive("up", event))
        canvas.bind("<Motion>", lambda event: receive("motion", event))
        root.update()
        canvas.focus_force()
        gui.user.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        gui.user.GetAncestor.restype = ctypes.c_void_p
        gui.user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        owned = gui.user.GetAncestor(root.winfo_id(), 2)
        gui.user.SetForegroundWindow(owned)
        root.update()
        if gui.foreground() != owned or root.focus_get() is not canvas:
            raise RuntimeError("owned canvas focus was not established")
        # Disable composition only on this disposable receiver, never globally.
        # No associated IMC proves this fixture cannot have active composition.
        imm = ctypes.WinDLL("imm32", use_last_error=True)
        imm.ImmAssociateContextEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
        imm.ImmAssociateContextEx.restype = ctypes.c_int
        imm.ImmGetContext.argtypes = [ctypes.c_void_p]
        imm.ImmGetContext.restype = ctypes.c_void_p
        if not imm.ImmAssociateContextEx(owned, None, 1) or imm.ImmGetContext(canvas.winfo_id()):
            raise RuntimeError("owned receiver IME disable/readback was not confirmed")
        report["ime_scope"] = (
            "Owned non-text canvas IMC disabled and absence read back; not general IME discovery"
        )

        def observe(predicate, seconds=3):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                root.update()
                if predicate():
                    return
                time.sleep(0.005)
            raise RuntimeError("owned fixture effect not observed within declared bound")

        def coordinates(frame, x, y):
            return widget_point(gui, canvas, frame, x, y, owned)

        def execute(command, frame, predicate):
            reply = {}

            def worker():
                try:
                    reply["outcome"] = action.execute_input(
                        command,
                        frame,
                        Event(),
                        context=InputContext(ime_composing=False, text_focus=False),
                    )
                except BaseException as exc:
                    reply["error"] = exc

            thread = Thread(target=worker)
            thread.start()
            try:
                observe(lambda: not thread.is_alive() and ("error" in reply or predicate()))
            finally:
                thread.join(4)
            if thread.is_alive():
                raise RuntimeError("owned typed input worker remains live")
            if "error" in reply:
                raise reply["error"]
            if not reply["outcome"].ok:
                raise RuntimeError(reply["outcome"].reason)
            if held(gui):
                raise RuntimeError("typed operation left native input held")

        report["buttons"] = []
        for button, number in (("left", 1), ("right", 3), ("middle", 2)):
            events.clear()
            frame = DesktopCapture().capture()
            point = coordinates(frame, 100, 100)
            execute(
                PointerInput(point=point, button=button),
                frame,
                lambda number=number: any(
                    e["phase"] == "up" and e["button"] == number for e in events
                ),
            )
            actual = [e for e in events if e["phase"] in {"down", "up"}]
            assert [(e["phase"], e["button"]) for e in actual] == [("down", number), ("up", number)]
            assert all(abs(e["x"] - 100) <= 1 and abs(e["y"] - 100) <= 1 for e in actual)
            report["buttons"].append({"button": button, "receiver_events": actual})

        report["gestures"] = []
        for button, number, modifiers in (
            ("left", 1, ("shift",)),
            ("middle", 2, ("shift",)),
            ("middle", 2, ()),
        ):
            events.clear()
            frame = DesktopCapture().capture()
            points = tuple(coordinates(frame, x, 200) for x in (100, 200, 300))
            surface = (*coordinates(frame, 20, 150), *coordinates(frame, 400, 250))
            execute(
                GestureInput(
                    points=points, surface=surface, button=button, modifiers=modifiers, duration=0.3
                ),
                frame,
                lambda number=number: any(
                    e["phase"] == "up" and e["button"] == number for e in events
                ),
            )
            actual = [e for e in events if e["phase"] in {"down", "up"}]
            assert [(e["phase"], e["button"]) for e in actual] == [("down", number), ("up", number)]
            down, up = actual
            assert abs(down["x"] - 100) <= 1 and abs(up["x"] - 300) <= 1
            motions = [e for e in events if e["phase"] == "motion" and e["x"] > 100]
            assert motions and any(abs(e["x"] - 300) <= 1 for e in motions)
            button_mask = 256 if button == "left" else 512
            assert all(e["state"] & button_mask for e in motions)
            assert all(20 <= e["x"] <= 400 and 150 <= e["y"] <= 250 for e in motions)
            assert all(bool(e["state"] & 1) == bool(modifiers) for e in [down, *motions, up])
            report["gestures"].append(
                {"button": button, "modifiers": modifiers, "receiver_events": [down, *motions, up]}
            )

        frame = DesktopCapture().capture()
        point = coordinates(frame, 100, 300)
        ready, errors = Event(), []

        def blocked_worker():
            try:
                hold_inputs(action, frame, cancel, point, time.monotonic() + 8)
                ready.set()
                unblock.wait(12)
            except BaseException as exc:
                errors.append(type(exc).__name__ + ": " + str(exc))
                ready.set()

        blocked = Thread(target=blocked_worker)
        blocked.start()
        observe(ready.is_set)
        assert not errors, errors
        before = held(gui)
        assert 4 in before and 16 in before
        cancel.set()
        observe(lambda: not held(gui))
        report["independent_cancel"] = {
            "held_before": before,
            "held_after": held(gui),
            "worker_still_blocked": blocked.is_alive(),
            "explicit_release_called": False,
        }
        assert blocked.is_alive()
        unblock.set()
        blocked.join(2)
        assert not blocked.is_alive()

        child_report = args.output.with_suffix(".child.json")
        with args.output.with_suffix(".child.stderr").open("w", encoding="utf-8") as stderr:
            child = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--crash-worker",
                    "--target",
                    str(owned),
                    "--point",
                    *(str(x) for x in point),
                    "--output",
                    str(child_report),
                ],
                stdout=subprocess.DEVNULL,
                stderr=stderr,
            )
        observe(lambda: child_report.exists() or child.poll() is not None, 5)
        assert child_report.exists(), "owned crash worker terminated before holding input"
        receipt = json.loads(child_report.read_text())
        before = held(gui)
        assert receipt["holding"] and child.poll() is None and 4 in before and 16 in before
        gui.kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        gui.kernel.OpenProcess.restype = ctypes.c_void_p
        gui.kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        gui.kernel.WaitForSingleObject.restype = ctypes.c_uint32
        gui.kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        gui.kernel.CloseHandle.restype = ctypes.c_int
        guardian_handle = gui.kernel.OpenProcess(0x100000, False, receipt["guardian_pid"])
        assert guardian_handle and gui.kernel.WaitForSingleObject(guardian_handle, 0) == 258
        child.terminate()
        child.wait(3)
        observe(lambda: not held(gui))
        guardian_exited = gui.kernel.WaitForSingleObject(guardian_handle, 3000) == 0
        assert guardian_exited
        report["independent_crash_recovery"] = {
            "held_before": before,
            "held_after": held(gui),
            "worker_terminated": child.poll() is not None,
            "guardian_exited": guardian_exited,
            "parent_release_called": False,
        }
        report["status"] = "PASSED"
    except Exception:
        report["traceback"] = traceback.format_exc()
    finally:
        cancel.set()
        unblock.set()
        if blocked is not None:
            blocked.join(2)
        if child is not None and child.poll() is None:
            child.terminate()
            child.wait(3)
        cleanup = {"errors": []}
        try:
            action.release()
            if action.input_executor and action.input_executor.guardian:
                action.input_executor.guardian.stdin.close()
                action.input_executor.guardian.wait(3)
                cleanup["own_guardian_exited"] = True
            # A terminated owned crash worker's lease expires independently.
            deadline = time.monotonic() + 11
            while held(gui) and time.monotonic() < deadline:
                if root:
                    root.update()
                time.sleep(0.01)
            cleanup["held_after"] = held(gui)
            assert not cleanup["held_after"]
        except Exception:
            cleanup["errors"].append(traceback.format_exc())
        if guardian_handle:
            gui.kernel.CloseHandle(guardian_handle)
        if owned and gui.foreground() == owned:
            try:
                if not pointer_known:
                    raise RuntimeError("original pointer unavailable")
                gui.FAILSAFE = False
                with gui.physical_coordinates():
                    gui.moveTo(pointer.x, pointer.y)
                cleanup["pointer_restored"] = True
            except Exception:
                cleanup["errors"].append(traceback.format_exc())
        else:
            cleanup["errors"].append("owned foreground changed; pointer restoration refused")
        if owned and gui.foreground() == owned:
            try:
                cleanup.update(restore_foreground(root, gui, previous, owned))
                assert cleanup["foreground_restored"]
            except Exception:
                cleanup["errors"].append(traceback.format_exc())
        else:
            cleanup["errors"].append("owned foreground changed; focus restoration refused")
        try:
            if root:
                root.destroy()
            cleanup["owned_window_closed"] = True
        except Exception:
            cleanup["errors"].append(traceback.format_exc())
        report["cleanup"] = cleanup
        if cleanup["errors"]:
            report["status"] = "FAILED"
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    return 0 if report["status"] == "PASSED" else 1


if __name__ == "__main__":
    if sys.platform != "win32":
        raise SystemExit("Requires an interactive Windows desktop")
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--crash-worker", action="store_true")
    parser.add_argument("--target", type=int)
    parser.add_argument("--point", type=float, nargs=2)
    arguments = parser.parse_args()
    if arguments.crash_worker:
        crash_worker(arguments)
    else:
        raise SystemExit(main(arguments))
