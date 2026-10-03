"""Exercise the canonical native adapter against a disposable Windows Tk window."""

from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
import tkinter as tk
import traceback
from pathlib import Path
from threading import Event

from clef_use.backends import DesktopAction, DesktopCapture
from clef_use.schema import ActionCandidate, BoundingBox, Observation, UIObject
from clef_use.windows_input import Point, WindowsInput


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"mode": "REAL_WINDOWS_GUI_NATIVE_ADAPTER", "native_input": True}
    root, gui, action = None, WindowsInput(), DesktopAction()
    previous_target, previous_pointer = gui.foreground(), Point()
    gui.user.GetCursorPos(ctypes.byref(previous_pointer))
    try:
        result["desktop"] = gui.desktop_status()
        root = tk.Tk()
        root.title("clef-use disposable input validation")
        root.geometry("640x400+500+250")
        root.attributes("-topmost", True)
        tk.Label(root, text="Disposable native input validation", font=("Segoe UI", 18)).pack(
            pady=20
        )
        entry = tk.Entry(root, font=("Segoe UI", 18))
        entry.pack(pady=15)
        clicks, scrolls = [], []
        button = tk.Button(root, text="Count click", command=lambda: clicks.append(1))
        button.pack(pady=20)
        root.bind("<MouseWheel>", lambda event: scrolls.append(event.delta))
        root.update()
        entry.focus_force()
        root.update()
        time.sleep(0.3)

        def snapshot():
            root.update()
            frame = DesktopCapture().capture()
            objects = []
            for name, widget in [("entry", entry), ("button", button)]:
                x, y = widget.winfo_rootx(), widget.winfo_rooty()
                w, h = widget.winfo_width(), widget.winfo_height()
                width, height = frame.image.size
                objects.append(
                    UIObject(
                        id=name,
                        label=name,
                        role="input" if name == "entry" else "button",
                        bbox=BoundingBox(
                            x1=(x - frame.origin[0]) / width,
                            y1=(y - frame.origin[1]) / height,
                            x2=(x + w - frame.origin[0]) / width,
                            y2=(y + h - frame.origin[1]) / height,
                        ),
                        actions=("click", "double_click", "focus", "type"),
                    )
                )
            return Observation(str(time.monotonic_ns()), frame, tuple(objects))

        def execute(operation, value=None, target=None, cancelled=None, observation=None):
            obs = observation or snapshot()
            candidate = ActionCandidate(
                id="test",
                operation=operation,
                value=value,
                target=target,
                description="disposable validation",
                observation_id=obs.id,
            )
            outcome = action.execute(candidate, obs, cancelled or Event())
            root.update()
            time.sleep(0.1)
            root.update()
            return outcome

        import pyperclip

        clipboard = pyperclip.paste()
        try:
            pyperclip.copy("clef-use clipboard invariant")
            text = "Windows 한글 테스트 😀"
            assert execute("type", text, "entry").ok
            assert entry.get() == text, repr(entry.get())
            assert pyperclip.paste() == "clef-use clipboard invariant"
            result["unicode_readback"] = entry.get()
            result["clipboard_preserved"] = True
        finally:
            pyperclip.copy(clipboard)
        assert execute("hotkey", "ctrl+a").ok
        assert execute("press", "backspace").ok
        assert entry.get() == ""
        result["shortcut_readback"] = entry.get()
        assert execute("click", target="button").ok and len(clicks) == 1
        assert execute("double_click", target="button").ok and len(clicks) == 3
        result["click_readback"] = len(clicks)
        assert execute("scroll", "down").ok and scrolls[-1] < 0
        result["wheel_readback"] = scrolls
        cancelled = Event()
        cancelled.set()
        assert not execute("type", "must not appear", "entry", cancelled).ok
        assert entry.get() == ""
        result["cancelled_before_input"] = True
        assert not execute("type", "line\nsubmit", "entry").ok and entry.get() == ""
        result["control_characters_refused"] = True
        old = snapshot()
        other = tk.Toplevel(root)
        other.title("Disposable foreground change")
        other.geometry("300x100+800+600")
        other.update()
        other.focus_force()
        root.update()
        time.sleep(0.2)
        try:
            execute("press", "enter", observation=old)
            raise AssertionError("stale foreground input accepted")
        except RuntimeError as exc:
            assert "foreground changed" in str(exc), str(exc)
            result["foreground_change_refused"] = str(exc)
        finally:
            other.destroy()
        entry.focus_force()
        root.update()
        action.release()
        gui.user.GetAsyncKeyState.argtypes = [ctypes.c_int]
        gui.user.GetAsyncKeyState.restype = ctypes.c_short
        result["held_inputs_after_release"] = [
            vk for vk in (1, 16, 17, 18, 65, 76) if gui.user.GetAsyncKeyState(vk) & 0x8000
        ]
        assert result["held_inputs_after_release"] == []
        frame = DesktopCapture().capture()
        assert frame.logical_size == frame.image.size
        result["capture_pixels"] = frame.image.size
        result["physical_coordinates"] = True
        with gui.physical_coordinates():
            bounds = (
                root.winfo_rootx(),
                root.winfo_rooty(),
                root.winfo_rootx() + root.winfo_width(),
                root.winfo_rooty() + root.winfo_height(),
            )
        frame.image.crop(bounds).save(args.output.with_suffix(".png"))
        result["status"] = "PASSED"
    except Exception:
        result.update(status="FAILED", traceback=traceback.format_exc())
    finally:
        action.release()
        if root:
            root.destroy()
        gui.FAILSAFE = False
        with gui.physical_coordinates():
            gui.moveTo(previous_pointer.x, previous_pointer.y)
        gui.user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        gui.user.SetForegroundWindow(previous_target)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASSED" else 1


if __name__ == "__main__":
    if sys.platform != "win32":
        raise SystemExit("Requires an interactive Windows desktop")
    raise SystemExit(main())
