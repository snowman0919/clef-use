"""Observe guardian deadline recovery while an owned Windows worker is stopped.

DebugActiveProcess plus its uncontinued attach breakpoint suspends all worker
threads. Only the owned worker PID is debugged, never its guardian.
https://learn.microsoft.com/en-us/windows/win32/api/debugapi/nf-debugapi-debugactiveprocess
https://learn.microsoft.com/en-us/windows/win32/debug/debugging-events

This is a native input component, not service, model, full gesture or Blender
operation admission. No privileges are enabled and no debug API failure is
repaired. DebugSetProcessKillOnExit(False) makes debugger exit detach instead
of killing this one owned debuggee.
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

from windows_gui_support import restore_foreground

from clef_use import __version__
from clef_use.backends import DesktopAction, DesktopCapture
from clef_use.input_ir import InputContext, InputInterrupted, KeyInput, PointerInput
from clef_use.windows_input import Point, Rect, WindowsInput

LEASE_SECONDS = 6
OBSERVATION_SECONDS = 5
RECOVERY_GRACE_SECONDS = 2
U32, PTR, HANDLE = ctypes.c_uint32, ctypes.c_size_t, ctypes.c_void_p


class ProcessEntry(ctypes.Structure):
    _fields_ = [
        ("size", U32),
        ("usage", U32),
        ("pid", U32),
        ("heap", PTR),
        ("module", U32),
        ("threads", U32),
        ("parent", U32),
        ("priority", ctypes.c_int32),
        ("flags", U32),
        ("exe", ctypes.c_wchar * 260),
    ]


class GuiThreadInfo(ctypes.Structure):
    _fields_ = [
        ("size", U32),
        ("flags", U32),
        *[(name, HANDLE) for name in ("active", "focus", "capture", "menu", "move", "caret")],
        ("rect", Rect),
    ]


class ExceptionRecord(ctypes.Structure):
    _fields_ = [
        ("code", U32),
        ("flags", U32),
        ("record", HANDLE),
        ("address", HANDLE),
        ("parameters", U32),
        ("information", PTR * 15),
    ]


class ExceptionInfo(ctypes.Structure):
    _fields_ = [("record", ExceptionRecord), ("first_chance", U32)]


class CreateProcessInfo(ctypes.Structure):
    _fields_ = [
        ("file", HANDLE),
        ("process", HANDLE),
        ("thread", HANDLE),
        ("base", HANDLE),
        ("debug_offset", U32),
        ("debug_size", U32),
        ("thread_local", HANDLE),
        ("start", HANDLE),
        ("image_name", HANDLE),
        ("unicode", ctypes.c_uint16),
    ]


class LoadDllInfo(ctypes.Structure):
    _fields_ = [
        ("file", HANDLE),
        ("base", HANDLE),
        ("debug_offset", U32),
        ("debug_size", U32),
        ("image_name", HANDLE),
        ("unicode", ctypes.c_uint16),
    ]


class DebugData(ctypes.Union):
    # EXCEPTION_DEBUG_INFO is the largest DEBUG_EVENT union member on both
    # Windows pointer widths. Only the first create-process member is consumed.
    _fields_ = [("exception", ExceptionInfo), ("create", CreateProcessInfo), ("dll", LoadDllInfo)]


class DebugEvent(ctypes.Structure):
    _fields_ = [("code", U32), ("pid", U32), ("tid", U32), ("data", DebugData)]


def bind_kernel(kernel):
    signatures = {
        "CreateToolhelp32Snapshot": ([U32, U32], HANDLE),
        "Process32FirstW": ([HANDLE, ctypes.POINTER(ProcessEntry)], ctypes.c_int),
        "Process32NextW": ([HANDLE, ctypes.POINTER(ProcessEntry)], ctypes.c_int),
        "OpenProcess": ([U32, ctypes.c_int, U32], HANDLE),
        "CloseHandle": ([HANDLE], ctypes.c_int),
        "WaitForSingleObject": ([HANDLE, U32], U32),
        "TerminateProcess": ([HANDLE, U32], ctypes.c_int),
        "DebugActiveProcess": ([U32], ctypes.c_int),
        "DebugActiveProcessStop": ([U32], ctypes.c_int),
        "DebugSetProcessKillOnExit": ([ctypes.c_int], ctypes.c_int),
        "WaitForDebugEvent": ([ctypes.POINTER(DebugEvent), U32], ctypes.c_int),
        "ContinueDebugEvent": ([U32, U32, U32], ctypes.c_int),
    }
    for name, (args, result) in signatures.items():
        function = getattr(kernel, name)
        function.argtypes, function.restype = args, result


def require(ok, operation):
    if not ok:
        raise OSError(ctypes.get_last_error(), operation)


def parents(kernel):
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot")
    try:
        entry = ProcessEntry()
        entry.size = ctypes.sizeof(entry)
        require(kernel.Process32FirstW(snapshot, ctypes.byref(entry)), "Process32FirstW")
        result = {}
        while True:
            result[entry.pid] = entry.parent
            if not kernel.Process32NextW(snapshot, ctypes.byref(entry)):
                if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
                    raise OSError(ctypes.get_last_error(), "Process32NextW")
                return result
    finally:
        require(kernel.CloseHandle(snapshot), "CloseHandle(process snapshot)")


def belongs(pid, ancestor, tree):
    seen = set()
    while pid and pid not in seen and len(seen) < 128:
        if pid == ancestor:
            return True
        seen.add(pid)
        pid = tree.get(pid, 0)
    return False


def held(gui):
    gui.user.GetAsyncKeyState.argtypes = [ctypes.c_int]
    gui.user.GetAsyncKeyState.restype = ctypes.c_short
    return [vk for vk in range(1, 256) if gui.user.GetAsyncKeyState(vk) & 0x8000]


def publish(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def worker(args):
    """Own the real input executor and heartbeat; never suspend the guardian."""
    action, capture, cancelled, stop = DesktopAction(), DesktopCapture(), Event(), Event()
    result = {"pid": os.getpid(), "nonce": args.nonce, "status": "FAILED"}
    publish(args.output, result)
    heartbeat_thread = None
    try:
        owner = json.loads((args.output.parent / "owner.json").read_text(encoding="utf-8"))
        gui = WindowsInput()
        bind_kernel(gui.kernel)
        if (
            owner["nonce"] != args.nonce
            or owner["window"] != args.target
            or not belongs(os.getpid(), owner["pid"], parents(gui.kernel))
        ):
            raise RuntimeError("Worker is not a child of this owned receiver fixture")

        def guard():
            if gui.foreground() != args.target:
                raise RuntimeError("Owned receiver foreground changed")
            pid = U32()
            gui.user.GetWindowThreadProcessId(args.target, ctypes.byref(pid))
            if pid.value != owner["pid"]:
                raise RuntimeError("Owned receiver process identity changed")

        guard()
        frame = capture.capture()
        if frame.foreground_window != args.target:
            raise RuntimeError("Owned receiver foreground was not observed by the child")

        deadline = time.monotonic() + LEASE_SECONDS
        context = InputContext(text_focus=False, ime_composing=False)
        for command in (
            KeyInput(key="shift", phase="down"),
            PointerInput(point=tuple(args.point), button="middle", phase="down"),
        ):
            outcome = action.execute_input(
                command, frame, cancelled, deadline=deadline, context=context, context_guard=guard
            )
            if not outcome.ok:
                raise RuntimeError(outcome.reason)

        def heartbeat():
            with args.heartbeat.open("a", encoding="ascii", buffering=1) as stream:
                while not stop.is_set():
                    stream.write(str(time.monotonic_ns()) + "\n")
                    stop.wait(0.05)

        heartbeat_thread = Thread(target=heartbeat, daemon=True)
        heartbeat_thread.start()
        result.update(
            status="HOLDING",
            guardian_pid=action.input_executor.guardian.pid,
            guardian_pid_kind="Popen PID; may be a venv launcher",
            deadline=deadline,
        )
        publish(args.output, result)
        end = time.monotonic() + 20
        while not args.resume.exists():
            if time.monotonic() >= end:
                raise RuntimeError("Owned child resume observation exceeded its budget")
            stop.wait(0.01)
        if time.monotonic() < deadline:
            raise RuntimeError("Parent resumed the child before its lease deadline")
        if not cancelled.wait(2):
            raise RuntimeError("Real worker watchdog cancellation was not observed after resume")
        result["cancelled_observed"] = True
        try:
            outcome = action.execute_input(
                KeyInput(key="a"),
                frame,
                cancelled,
                deadline=deadline,
                context=context,
                context_guard=guard,
            )
        except InputInterrupted as exc:
            result.update(refused_after_deadline=True, refusal_type=type(exc).__name__)
        else:
            result.update(refused_after_deadline=not outcome.ok, refusal_type="ActionResult")
        if not result["refused_after_deadline"]:
            raise RuntimeError("Expired worker delivered subsequent input")
        result["status"] = "PASSED"
    except Exception as exc:
        result["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        stop.set()
        cleanup = {"errors": []}
        if heartbeat_thread is not None:
            heartbeat_thread.join(2)
            cleanup["heartbeat_stopped"] = not heartbeat_thread.is_alive()
        try:
            action.release()
        except Exception as exc:
            cleanup["errors"].append(type(exc).__name__ + ": " + str(exc))
        try:
            executor = action.input_executor
            if executor is not None and executor.guardian is not None:
                executor.guardian.stdin.close()
                executor.guardian.wait(3)
                cleanup["guardian_exited"] = True
        except Exception as exc:
            cleanup["errors"].append(type(exc).__name__ + ": " + str(exc))
        result["cleanup"] = cleanup
        if cleanup["errors"]:
            result["status"] = "FAILED"
        publish(args.output, result)
    return 0 if result["status"] == "PASSED" else 1


def main(output):
    if output.exists():
        raise RuntimeError("Output exists; prior attempts must be preserved")
    folder = output.with_suffix(".owned")
    folder.mkdir(exist_ok=False)
    gui = WindowsInput()
    bind_kernel(gui.kernel)
    root = owned = child = actual_pid = None
    worker_handle = None
    guardian_handles = {}
    attached = detach_attempted = False
    previous, pointer = gui.foreground(), Point()
    with gui.physical_coordinates():
        pointer_known = bool(gui.user.GetCursorPos(ctypes.byref(pointer)))
    report = {
        "status": "FAILED",
        "mode": "REAL_WINDOWS_SUSPENDED_WORKER_DEADLINE",
        "runtime_version": __version__,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "Native input component; no HTTP/service/models/full gesture/Blender operation",
        "lease_seconds": LEASE_SECONDS,
        "recovery_grace_seconds": RECOVERY_GRACE_SECONDS,
        "suspended_deadline_proof": "NOT_RUN",
    }
    child_report, heartbeat, resume = (
        folder / name for name in ("child.json", "heartbeat", "resume")
    )
    nonce = secrets.token_hex(16)
    events = []

    def observe(predicate, seconds=OBSERVATION_SECONDS):
        until = time.monotonic() + seconds
        while True:
            root.update()
            if predicate():
                return
            if time.monotonic() >= until:
                raise RuntimeError("Owned native observation exceeded its budget")
            time.sleep(0.005)

    try:
        report["desktop"] = gui.desktop_status()
        gui.user.IsWindow.argtypes, gui.user.IsWindow.restype = [HANDLE], ctypes.c_int
        if not pointer_known or not previous or not gui.user.IsWindow(previous) or held(gui):
            raise RuntimeError("Original restoration target unavailable or human input held")
        root = tk.Tk()
        root.title("clef-use owned suspended worker component")
        root.geometry("720x480+500+250")
        canvas = tk.Canvas(root, bg="white", takefocus=True)
        canvas.pack(fill="both", expand=True)

        def receive(phase, event):
            events.append(
                {
                    "phase": phase,
                    "key": getattr(event, "keysym", None),
                    "button": getattr(event, "num", None),
                    "at": time.monotonic(),
                }
            )

        canvas.bind("<KeyPress>", lambda event: receive("key_down", event))
        canvas.bind("<KeyRelease>", lambda event: receive("key_up", event))
        canvas.bind("<ButtonPress>", lambda event: receive("button_down", event))
        canvas.bind("<ButtonRelease>", lambda event: receive("button_up", event))
        root.update()
        canvas.focus_force()
        gui.user.GetAncestor.argtypes, gui.user.GetAncestor.restype = [HANDLE, U32], HANDLE
        owned = gui.user.GetAncestor(root.winfo_id(), 2)
        gui.user.SetForegroundWindow.argtypes = [HANDLE]
        require(gui.user.SetForegroundWindow(owned), "SetForegroundWindow(owned)")
        root.update()
        canvas_hwnd = canvas.winfo_id()
        imm = ctypes.WinDLL("imm32", use_last_error=True)
        imm.ImmAssociateContextEx.argtypes = [HANDLE, HANDLE, U32]
        imm.ImmAssociateContextEx.restype = ctypes.c_int
        imm.ImmGetContext.argtypes, imm.ImmGetContext.restype = [HANDLE], HANDLE
        imm.ImmReleaseContext.argtypes, imm.ImmReleaseContext.restype = (
            [HANDLE, HANDLE],
            ctypes.c_int,
        )
        require(imm.ImmAssociateContextEx(owned, None, 1), "ImmAssociateContextEx(owned)")
        gui.user.GetGUIThreadInfo.argtypes = [U32, ctypes.POINTER(GuiThreadInfo)]
        gui.user.GetGUIThreadInfo.restype = ctypes.c_int

        def admission():
            if gui.foreground() != owned or root.focus_get() is not canvas:
                raise RuntimeError("Owned non-text receiver focus changed")
            info = GuiThreadInfo()
            info.size = ctypes.sizeof(info)
            tid = gui.user.GetWindowThreadProcessId(owned, None)
            require(tid and gui.user.GetGUIThreadInfo(tid, ctypes.byref(info)), "GetGUIThreadInfo")
            if not info.focus or gui.user.GetAncestor(info.focus, 2) != owned:
                raise RuntimeError("Native keyboard focus outside owned receiver")
            context = imm.ImmGetContext(canvas_hwnd)
            if context:
                imm.ImmReleaseContext(canvas_hwnd, context)
                raise RuntimeError("Owned receiver IMC absence was not observed")

        admission()
        report["admission"] = {
            "owned_foreground": True,
            "nontext_canvas_focused": True,
            "owned_imc_disabled_and_absent": True,
            "ime_scope": "Own disposable receiver only; not general IME discovery",
        }
        frame = DesktopCapture().capture()
        point = (
            (canvas.winfo_rootx() + 100 - frame.origin[0]) / frame.image.width,
            (canvas.winfo_rooty() + 200 - frame.origin[1]) / frame.image.height,
        )
        publish(folder / "owner.json", {"pid": os.getpid(), "window": owned, "nonce": nonce})
        with (
            (folder / "child.stdout").open("w", encoding="utf-8") as stdout,
            (folder / "child.stderr").open("w", encoding="utf-8") as stderr,
        ):
            child = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--worker",
                    "--output",
                    str(child_report),
                    "--target",
                    str(owned),
                    "--point",
                    *(str(x) for x in point),
                    "--nonce",
                    nonce,
                    "--heartbeat",
                    str(heartbeat),
                    "--resume",
                    str(resume),
                ],
                stdout=stdout,
                stderr=stderr,
            )
        observe(lambda: child_report.exists() or child.poll() is not None)
        identity = json.loads(child_report.read_text(encoding="utf-8"))
        actual_pid = identity["pid"]
        tree = parents(gui.kernel)
        if type(actual_pid) is not int or not belongs(actual_pid, child.pid, tree):
            raise RuntimeError("Reported actual worker PID is not the owned launcher descendant")
        if identity.get("nonce") != nonce:
            raise RuntimeError("Owned child receipt identity changed")
        worker_handle = gui.kernel.OpenProcess(0x100000 | 0x1000 | 1, False, actual_pid)
        require(worker_handle, "OpenProcess(owned actual worker)")

        def holding():
            identity.update(json.loads(child_report.read_text(encoding="utf-8")))
            if identity["status"] == "FAILED" and identity.get("error"):
                raise RuntimeError(identity["error"])
            return identity["status"] == "HOLDING" and heartbeat.exists()

        observe(holding)
        observe(lambda: len(heartbeat.read_bytes().splitlines()) >= 2)
        observe(lambda: any(e["phase"] == "button_down" and e["button"] == 2 for e in events))
        admission()
        before = held(gui)
        if not {4, 16, 160} <= set(before):
            raise RuntimeError("Native owned Shift/middle lease was not observed")
        deadline = identity["deadline"]
        if deadline - time.monotonic() < 0.5:
            raise RuntimeError("Insufficient unexpired lease for debugger admission")
        guardian_pid = identity["guardian_pid"]
        tree = parents(gui.kernel)
        if (
            type(guardian_pid) is not int
            or guardian_pid == actual_pid
            or not belongs(guardian_pid, actual_pid, tree)
        ):
            raise RuntimeError("Guardian is not a distinct owned worker descendant")
        for pid in tree:
            if belongs(pid, guardian_pid, tree):
                handle = gui.kernel.OpenProcess(0x100000 | 0x1000, False, pid)
                require(handle, "OpenProcess(owned guardian family)")
                guardian_handles[pid] = handle
        require(gui.kernel.DebugActiveProcess(actual_pid), "DebugActiveProcess(owned worker)")
        attached = True
        require(gui.kernel.DebugSetProcessKillOnExit(False), "DebugSetProcessKillOnExit(False)")
        attach_end = time.monotonic() + 1
        initial_events = []
        while True:
            remaining = attach_end - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("Owned debugger attach event sequence exceeded one second")
            event = DebugEvent()
            require(
                gui.kernel.WaitForDebugEvent(ctypes.byref(event), max(1, int(remaining * 1000))),
                "WaitForDebugEvent",
            )
            if event.pid != actual_pid:
                raise RuntimeError("Debug event PID is not the exact owned worker")
            if not initial_events and event.code != 3:
                raise RuntimeError("Initial debug event is not CREATE_PROCESS")
            initial_events.append(event.code)
            if event.code == 1:
                if event.data.exception.record.code != 0x80000003 or not (
                    event.data.exception.first_chance == 1
                ):
                    raise RuntimeError("Unexpected exception during owned debugger attach")
                break
            if event.code not in {2, 3, 6}:
                raise RuntimeError("Unexpected event during owned debugger attach")
            file_handle = (
                event.data.create.file
                if event.code == 3
                else (event.data.dll.file if event.code == 6 else None)
            )
            if file_handle:
                require(gui.kernel.CloseHandle(file_handle), "CloseHandle(debug image file)")
            require(
                gui.kernel.ContinueDebugEvent(event.pid, event.tid, 0x00010002),
                "ContinueDebugEvent(attach enumeration)",
            )
        frozen_heartbeat = heartbeat.read_bytes()
        if not frozen_heartbeat or not held(gui):
            raise RuntimeError("Worker was not suspended before owned-input recovery")
        report["debugger"] = {
            "actual_worker_pid": actual_pid,
            "launcher_pid": child.pid,
            "guardian_launcher_pid": guardian_pid,
            "guardian_family_pids": list(guardian_handles),
            "event_pid": event.pid,
            "event_code": event.code,
            "attach_event_codes": initial_events,
            "event_left_uncontinued": True,
            "kill_on_debugger_exit": False,
        }
        report["suspended_deadline_proof"] = "RUNNING"
        while True:
            root.update()
            admission()
            if heartbeat.read_bytes() != frozen_heartbeat:
                raise RuntimeError("Worker heartbeat advanced while debug event was pending")
            if gui.kernel.WaitForSingleObject(worker_handle, 0) != 258:
                raise RuntimeError("Owned worker exited before suspended recovery observation")
            if any(gui.kernel.WaitForSingleObject(h, 0) != 258 for h in guardian_handles.values()):
                raise RuntimeError("Guardian family exited before recovery; EOF proof is excluded")
            if not held(gui):
                if time.monotonic() < deadline:
                    raise RuntimeError("Owned input was released before its lease deadline")
                break
            if time.monotonic() > deadline + RECOVERY_GRACE_SECONDS:
                raise RuntimeError("Guardian did not release native input at the bounded deadline")
            time.sleep(0.005)
        observe(lambda: any(e["phase"] == "button_up" and e["button"] == 2 for e in events))
        if not any(e["phase"] == "key_up" and e["key"] == "Shift_L" for e in events):
            raise RuntimeError("Native receiver did not observe the owned Shift release")
        if heartbeat.read_bytes() != frozen_heartbeat:
            raise RuntimeError("Worker resumed before native release evidence was complete")
        report["suspended_recovery"] = {
            "held_before": before,
            "held_after": held(gui),
            "heartbeat_unchanged": True,
            "pending_debug_event": True,
            "worker_alive": True,
            "guardian_family_alive": True,
            "explicit_release_or_eof_before_observation": False,
            "deadline": deadline,
            "release_observed_at": time.monotonic(),
            "receiver_events": list(events),
        }
        report["suspended_deadline_proof"] = "PASS"
        require(
            gui.kernel.ContinueDebugEvent(event.pid, event.tid, 0x00010002),
            "ContinueDebugEvent(owned attach breakpoint)",
        )
        detach_attempted = True
        require(
            gui.kernel.DebugActiveProcessStop(actual_pid), "DebugActiveProcessStop(owned worker)"
        )
        attached = False
        resume.write_text("resume after observed guardian deadline recovery", encoding="ascii")
        observe(lambda: gui.kernel.WaitForSingleObject(worker_handle, 0) == 0, 10)
        child.wait(3)
        result = json.loads(child_report.read_text(encoding="utf-8"))
        if (
            result["status"] != "PASSED"
            or not result.get("cancelled_observed")
            or not result.get("refused_after_deadline")
        ):
            raise RuntimeError("Resumed child did not establish cancellation and refusal")
        if held(gui) or any(e["phase"] == "key_down" and e["key"] == "a" for e in events):
            raise RuntimeError("Resumed expired worker reacquired or delivered input")
        report["resumed_child"] = {k: v for k, v in result.items() if k != "nonce"}
        report["status"] = "PASSED"
    except Exception as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)
        if report["suspended_deadline_proof"] == "RUNNING":
            report["suspended_deadline_proof"] = "FAIL"
    finally:
        cleanup = {"errors": [], "http_service_started": False}
        if attached and not detach_attempted:
            detach_attempted = True
            try:
                require(
                    gui.kernel.DebugActiveProcessStop(actual_pid), "DebugActiveProcessStop(cleanup)"
                )
                attached = False
            except Exception as exc:
                cleanup["errors"].append(str(exc))
        cleanup["debugger_detached"] = not attached
        if not attached:
            resume.write_text("owned cleanup", encoding="ascii")
        try:
            if worker_handle and gui.kernel.WaitForSingleObject(worker_handle, 5000) == 258:
                require(
                    gui.kernel.TerminateProcess(worker_handle, 19), "TerminateProcess(owned worker)"
                )
                require(
                    gui.kernel.WaitForSingleObject(worker_handle, 3000) == 0, "Owned worker exit"
                )
                cleanup["owned_worker_terminated"] = True
            if child is not None:
                child.wait(3)
            cleanup["owned_worker_exited"] = worker_handle is not None and (
                gui.kernel.WaitForSingleObject(worker_handle, 0) == 0
            )
        except Exception as exc:
            cleanup["errors"].append(type(exc).__name__ + ": " + str(exc))
        try:
            cleanup["guardian_family_exited"] = bool(guardian_handles) and all(
                gui.kernel.WaitForSingleObject(handle, 3000) == 0
                for handle in guardian_handles.values()
            )
            if guardian_handles and not cleanup["guardian_family_exited"]:
                raise RuntimeError("Owned guardian family remains alive")
            cleanup["held_after"] = held(gui)
            if cleanup["held_after"]:
                raise RuntimeError("Native held input remains; parent did not inject release")
        except Exception as exc:
            cleanup["errors"].append(type(exc).__name__ + ": " + str(exc))
        for handle in [worker_handle, *guardian_handles.values()]:
            if handle and not gui.kernel.CloseHandle(handle):
                cleanup["errors"].append("CloseHandle(owned component) failed")
        if owned and gui.foreground() == owned:
            try:
                if not pointer_known:
                    raise RuntimeError("Original pointer unavailable")
                gui.FAILSAFE = False
                with gui.physical_coordinates():
                    gui.moveTo(pointer.x, pointer.y)
                cleanup["pointer_restored"] = True
            except Exception as exc:
                cleanup["errors"].append(str(exc))
        elif owned:
            cleanup["errors"].append("Owned foreground changed; pointer restoration refused")
        if owned and gui.foreground() == owned:
            try:
                cleanup.update(restore_foreground(root, gui, previous, owned))
                if not cleanup["foreground_restored"]:
                    raise RuntimeError("Original foreground restoration not confirmed")
            except Exception as exc:
                cleanup["errors"].append(str(exc))
        elif owned:
            cleanup["errors"].append("Owned foreground changed; focus restoration refused")
        try:
            if root is not None:
                root.destroy()
            cleanup["owned_window_closed"] = True
        except Exception as exc:
            cleanup["errors"].append(str(exc))
        report["cleanup"] = cleanup
        if cleanup["errors"]:
            report["status"] = "FAILED"
        publish(output, report)
    print(json.dumps({"mode": report["mode"], "status": report["status"]}))
    return 0 if report["status"] == "PASSED" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--target", type=int)
    parser.add_argument("--point", type=float, nargs=2)
    parser.add_argument("--nonce")
    parser.add_argument("--heartbeat", type=Path)
    parser.add_argument("--resume", type=Path)
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Requires an interactive Windows desktop")
    raise SystemExit(worker(args) if args.worker else main(args.output))
