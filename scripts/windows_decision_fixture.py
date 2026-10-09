"""Collect three real Windows Tk client-area fixtures, without sending OS input.

Run with an existing Pillow/Tk interpreter in the user's interactive session:
    python windows_decision_fixture.py --output <fresh-directory>

A service/SSH session, a locked desktop, lost foreground, or blank pixels fail
closed. Button.invoke() constructs fixtures; it is not live desktop task E2E.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import sys
import threading
import time
from pathlib import Path

TIMEOUT_SECONDS = 25


class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int32), ("y", ctypes.c_int32)]


class Rect(ctypes.Structure):
    _fields_ = [(name, ctypes.c_int32) for name in ("left", "top", "right", "bottom")]


class NativeWindows:
    """Only owned-window capture/focus and read-only desktop/geometry queries."""

    def __init__(self):
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        handle, uint, boolean = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int
        signatures = {
            "GetForegroundWindow": ([], handle),
            "SetForegroundWindow": ([handle], boolean),
            "GetAncestor": ([handle, uint], handle),
            "IsWindow": ([handle], boolean),
            "IsWindowVisible": ([handle], boolean),
            "GetWindowThreadProcessId": ([handle, ctypes.POINTER(uint)], uint),
            "GetClientRect": ([handle, ctypes.POINTER(Rect)], boolean),
            "GetWindowRect": ([handle, ctypes.POINTER(Rect)], boolean),
            "ClientToScreen": ([handle, ctypes.POINTER(Point)], boolean),
            "GetCursorPos": ([ctypes.POINTER(Point)], boolean),
            "GetDpiForWindow": ([handle], uint),
            "SetThreadDpiAwarenessContext": ([handle], handle),
            "OpenInputDesktop": ([uint, boolean, uint], handle),
            "CloseDesktop": ([handle], boolean),
            "GetUserObjectInformationW": (
                [handle, ctypes.c_int, handle, uint, ctypes.POINTER(uint)],
                boolean,
            ),
            "PostMessageW": ([handle, uint, ctypes.c_size_t, ctypes.c_ssize_t], boolean),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.user, name)
            function.argtypes, function.restype = arguments, result
        self.kernel.ProcessIdToSessionId.argtypes = [uint, ctypes.POINTER(uint)]
        self.kernel.ProcessIdToSessionId.restype = boolean

    def desktop(self):
        session = ctypes.c_uint32()
        if not self.kernel.ProcessIdToSessionId(os.getpid(), ctypes.byref(session)):
            raise RuntimeError("Windows session identification failed")
        if session.value == 0:
            raise RuntimeError("Session 0 is not an interactive GUI owner session")
        desktop = self.user.OpenInputDesktop(0, False, 1)
        if not desktop:
            raise RuntimeError("Interactive input desktop is unavailable or locked")
        try:
            name, size = ctypes.create_unicode_buffer(256), ctypes.c_uint32()
            if not self.user.GetUserObjectInformationW(
                desktop, 2, name, ctypes.sizeof(name), ctypes.byref(size)
            ):
                raise RuntimeError("Input desktop identification failed")
            if name.value.lower() != "default":
                raise RuntimeError("Secure/non-default desktop refused")
        finally:
            self.user.CloseDesktop(desktop)
        return {"session_id": session.value, "desktop": name.value}

    def owner_pid(self, hwnd):
        pid = ctypes.c_uint32()
        if not self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid)):
            raise RuntimeError("Window owner PID unavailable")
        return pid.value

    def ensure_owned(self, hwnd):
        self.desktop()
        if not self.user.IsWindow(hwnd) or self.owner_pid(hwnd) != os.getpid():
            raise RuntimeError("Fixture HWND is not owned by this collector")
        if self.user.GetForegroundWindow() != hwnd:
            raise RuntimeError("Owned fixture is no longer the native foreground window")

    def cursor(self):
        point = Point()
        if not self.user.GetCursorPos(ctypes.byref(point)):
            raise RuntimeError("Pointer readback failed")
        return [point.x, point.y]

    def client(self, hwnd):
        rect, origin = Rect(), Point()
        if not self.user.GetClientRect(hwnd, ctypes.byref(rect)):
            raise RuntimeError("Owned client rectangle unavailable")
        if not self.user.ClientToScreen(hwnd, ctypes.byref(origin)):
            raise RuntimeError("Owned client origin unavailable")
        return [origin.x, origin.y], [rect.right - rect.left, rect.bottom - rect.top]

    def widget_rectangle(self, hwnd, origin):
        if self.owner_pid(hwnd) != os.getpid():
            raise RuntimeError("Widget HWND belongs to a different process")
        rect = Rect()
        if not self.user.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise RuntimeError("Widget native rectangle unavailable")
        return {
            "x": rect.left - origin[0],
            "y": rect.top - origin[1],
            "width": rect.right - rect.left,
            "height": rect.bottom - rect.top,
        }


def write_json(path, value):
    # Every evidence file, not just the directory, refuses overwrite.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def collect(output):
    import tkinter as tk
    import winreg

    import PIL
    from PIL import Image, ImageGrab, ImageStat

    started = time.monotonic()
    native = NativeWindows()
    desktop = native.desktop()
    previous = native.user.GetForegroundWindow()
    if not previous:
        raise RuntimeError("No previous foreground HWND; restoration cannot be guaranteed")
    previous_pointer = None
    old_dpi = native.user.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    if not old_dpi:
        raise RuntimeError("Per-monitor-v2 physical coordinate context was refused")
    root, owned, client_hwnd = None, None, None
    finished = threading.Event()
    cleanup: dict = {"pointer_input_sent": False, "keyboard_input_sent": False}
    records, callbacks, errors = [], [], []

    def restore_foreground():
        current = native.user.GetForegroundWindow()
        if current == previous:
            return True
        if owned and current == owned and native.user.IsWindow(previous):
            native.user.SetForegroundWindow(previous)
        return native.user.GetForegroundWindow() == previous

    def deadline():
        if finished.wait(TIMEOUT_SECONDS):
            return
        # WM_CLOSE is sent only to our verified HWND, never another application's.
        if owned and native.user.IsWindow(owned) and native.owner_pid(owned) == os.getpid():
            native.user.PostMessageW(owned, 0x0010, 0, 0)
        if finished.wait(2):
            return
        restored = restore_foreground()
        write_json(
            output / "deadline-failure.json",
            {
                "status": "BLOCKED",
                "exit_code": 3,
                "error": "Owned fixture exceeded the 25-second collection deadline",
                "foreground_restored": restored,
                "native_input": False,
            },
        )
        # Process termination removes only this process's windows. This emergency
        # path is not reported as successful finally-cleanup or successful capture.
        os._exit(3)

    threading.Thread(target=deadline, daemon=True).start()
    try:
        # Both pointer samples must use the same physical DPI context. Sampling
        # before this context would falsely report a move on a scaled desktop.
        previous_pointer = native.cursor()
        root = tk.Tk()
        tk_version = str(root.tk.call("package", "provide", "Tk"))
        root.withdraw()
        root.title("Owned Windows decision fixture")
        root.geometry("640x360+240+180")
        root.resizable(False, False)
        root.configure(background="white")
        widgets = {}

        def label(name, text, y, size):
            widget = tk.Label(
                root,
                name=name,
                text=text,
                anchor="w",
                background="white",
                foreground="black",
                font=("Segoe UI", -size),
            )
            widget.place(x=32, y=y, width=576, height=38)
            widgets[name] = widget
            return widget

        label("heading", "Local test workspace", 28, 24)
        stage_label = label("stage_label", "Continue", 88, 20)
        instruction = label("instruction", "Continue to the confirmation step.", 134, 14)
        final_label = label("final_label", "", 272, 22)

        def advance():
            title = str(button.cget("text"))
            callbacks.append(title)
            if title == "Continue" and len(callbacks) == 1:
                stage_label.configure(text="Confirm")
                instruction.configure(text="Confirm the local test action.")
                button.configure(text="Confirm")
            elif title == "Confirm" and len(callbacks) == 2:
                stage_label.configure(text="Complete")
                instruction.configure(text="The owned fixture reached its final stage.")
                button.configure(state="disabled")
                button.place_forget()
                final_label.configure(text="Task complete")
            else:
                raise RuntimeError("Unexpected owned native-toolkit callback")

        button = tk.Button(
            root, name="button", text="Continue", font=("Segoe UI", -18), command=advance
        )
        button.place(x=32, y=202, width=170, height=48)
        widgets["button"] = button
        root.report_callback_exception = lambda kind, value, tb: errors.append(str(value))
        root.protocol("WM_DELETE_WINDOW", root.quit)
        root.deiconify()
        root.attributes("-topmost", True)
        root.update()
        client_hwnd = root.winfo_id()
        owned = native.user.GetAncestor(client_hwnd, 2)
        if not owned or native.owner_pid(owned) != os.getpid():
            raise RuntimeError("Tk toplevel native ownership could not be established")
        root.focus_force()
        native.user.SetForegroundWindow(owned)
        root.update()
        native.ensure_owned(owned)

        def readback(origin, size):
            # Query Tcl widget properties and Win32 HWND geometry afresh. No
            # stage counter/expected label supplies the ground truth.
            actual = {str(w): w for w in root.winfo_children()}
            rectangles = {}
            for name, widget in widgets.items():
                if actual.get(str(widget)) is not widget:
                    raise RuntimeError("Owned native widget hierarchy changed")
                rect = native.widget_rectangle(widget.winfo_id(), origin)
                hidden = not bool(native.user.IsWindowVisible(widget.winfo_id()))
                if not hidden and not (
                    0 <= rect["x"] < rect["x"] + rect["width"] <= size[0]
                    and 0 <= rect["y"] < rect["y"] + rect["height"] <= size[1]
                ):
                    raise RuntimeError("Visible widget lies outside the captured client area")
                rectangles[name] = {"pixels": rect, "hidden": hidden}

            def text(widget):
                return str(root.tk.call(str(widget), "cget", "-text"))

            return {
                "stage": text(stage_label),
                "heading": text(widgets["heading"]),
                "instruction": text(instruction),
                "button_title": text(button),
                "button_hidden": rectangles["button"]["hidden"],
                "button_enabled": str(button.cget("state")) == "normal",
                "final_label": text(final_label),
                "final_label_hidden": rectangles["final_label"]["hidden"],
                "widget_rectangles": rectangles,
            }

        def capture():
            try:
                if time.monotonic() - started >= TIMEOUT_SECONDS:
                    raise TimeoutError("Collection deadline reached")
                root.update_idletasks()
                native.ensure_owned(owned)
                origin, size = native.client(client_hwnd)
                before = readback(origin, size)
                # Pillow's HWND path uses GetDC(hwnd)/GetClientRect/BitBlt, not
                # whole-desktop capture. The frame excludes decorations/other apps.
                image = ImageGrab.grab(window=client_hwnd)
                native.ensure_owned(owned)
                if native.client(client_hwnd) != (origin, size) or before != readback(origin, size):
                    raise RuntimeError("Owned widget or client geometry changed during capture")
                if list(image.size) != size:
                    raise RuntimeError("Pillow pixels do not match physical client dimensions")
                extrema, stat = image.getextrema(), ImageStat.Stat(image)
                if all(low == high for low, high in extrema) or max(stat.mean) <= 2:
                    raise RuntimeError("Uniform/black capture refused; no fixture synthesized")
                index = len(records)
                if before["stage"] != ("Continue", "Confirm", "Complete")[index]:
                    raise RuntimeError("Native widget readback did not reach the required stage")
                if before["button_hidden"] != (index == 2) or len(callbacks) != index:
                    raise RuntimeError("Native callback count/button visibility mismatch")
                if before["final_label"] != ("Task complete" if index == 2 else ""):
                    raise RuntimeError("Native completion label mismatch")
                filename = f"stage-{index}.png"
                path = output / filename
                with path.open("xb") as stream:
                    image.save(stream, format="PNG")
                with Image.open(path) as saved:
                    saved.load()
                    if saved.size != image.size or saved.tobytes() != image.tobytes():
                        raise RuntimeError("PNG independent file readback mismatch")
                records.append(
                    {
                        "index": index,
                        "stage": before["stage"],
                        "filename": filename,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "pixel_width": image.width,
                        "pixel_height": image.height,
                        "client_origin_screen_pixels": origin,
                        "foreground_hwnd": owned,
                        "foreground_owner_pid": os.getpid(),
                        "capture_hwnd": client_hwnd,
                        "capture_owner_pid": native.owner_pid(client_hwnd),
                        "window_dpi": native.user.GetDpiForWindow(client_hwnd),
                        "native_action_callback_count": len(callbacks),
                        "trigger": "initial native rendering"
                        if index == 0
                        else "Tk Button.invoke()",
                        "pixel_extrema": extrema,
                        "pixel_mean": stat.mean,
                        "readback": before,
                    }
                )
                if index == 2:
                    root.quit()
                else:
                    button.invoke()
                    if errors:
                        raise RuntimeError(errors[-1])
                    root.after(200, capture)
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
                root.quit()

        root.after(200, capture)
        root.after(TIMEOUT_SECONDS * 1000, root.quit)
        root.mainloop()
        if errors or len(records) != 3:
            raise RuntimeError(errors[-1] if errors else "Owned app exited before three captures")
        if len({record["sha256"] for record in records}) != 3:
            raise RuntimeError("Stage captures are identical; transition pixels were not verified")
    finally:
        try:
            cleanup["foreground_restored"] = restore_foreground()
            cleanup["previous_foreground_hwnd"] = previous
            cleanup["foreground_readback_hwnd"] = native.user.GetForegroundWindow()
            cleanup["pointer_before"] = previous_pointer
            cleanup["pointer_after"] = native.cursor()
            cleanup["pointer_unchanged"] = cleanup["pointer_after"] == previous_pointer
        finally:
            if root is not None:
                root.destroy()
            cleanup["owned_window_destroyed"] = not owned or not bool(native.user.IsWindow(owned))
            cleanup["foreground_readback_hwnd"] = native.user.GetForegroundWindow()
            cleanup["foreground_restored"] = cleanup["foreground_readback_hwnd"] == previous
            cleanup["dpi_context_restored"] = bool(
                native.user.SetThreadDpiAwarenessContext(old_dpi)
            )
            finished.set()
        write_json(output / "cleanup.json", cleanup)
    if not all(
        cleanup[key]
        for key in ("foreground_restored", "owned_window_destroyed", "dpi_context_restored")
    ):
        raise RuntimeError("Owned app cleanup/restoration failed; evidence retained")
    registry_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as key:
        build = str(winreg.QueryValueEx(key, "CurrentBuild")[0])
        revision = int(winreg.QueryValueEx(key, "UBR")[0])
        display_version = str(winreg.QueryValueEx(key, "DisplayVersion")[0])
    manifest = {
        "schema_version": 1,
        "platform": "Windows",
        "fixture_kind": "owned_native_gui",
        "os_name": platform.win32_edition(),
        "os_version": platform.version(),
        "os_build": f"{build}.{revision}",
        "os_display_version": display_version,
        "architecture": platform.machine(),
        "process_architecture": platform.architecture()[0],
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "pillow_version": PIL.__version__,
        "tk_version": tk_version,
        "collector_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "capture_method": (
            "PIL.ImageGrab.grab(window=owned Tk client HWND); Win32 GetDC/GetClientRect/BitBlt"
        ),
        "capture_scope": "owned client area only; no title bar or desktop pixels",
        "readback_method": (
            "fresh Tcl widget cget/hierarchy plus Win32 widget HWND geometry/visibility"
        ),
        "transition_method": "owned Tk Button.invoke() -> native-toolkit command callbacks",
        "native_rendering": True,
        "native_input": False,
        "os_screenshot": True,
        "desktop_e2e": False,
        "task_e2e": False,
        "model_inference": False,
        "scope": "fixture-only/not live E2E",
        "desktop": desktop,
        "coordinate_convention": {
            "image": "physical client pixels; top-left origin; x right, y down",
            "widget_rectangles": (
                "Win32 GetWindowRect minus ClientToScreen(client HWND, (0,0)); x/y/width/height"
            ),
            "screen": "physical virtual-screen pixels; per-monitor-v2 thread DPI context",
        },
        "collector_timeout_seconds": TIMEOUT_SECONDS,
        "elapsed_seconds": time.monotonic() - started,
        "stage_count": len(records),
        "stages": records,
        "callbacks": callbacks,
        "cleanup": cleanup,
        "status": "PASSED",
        "exit_code": 0,
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Windows is required; no cross-platform fixture synthesis is supported")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    try:
        manifest = collect(output)
    except Exception as exc:
        write_json(
            output / "failure.json",
            {
                "status": "BLOCKED",
                "exit_code": 2,
                "native_input": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        print(f"BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": "PASSED",
                "output": str(output),
                "stage_count": manifest["stage_count"],
                "exit_code": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
