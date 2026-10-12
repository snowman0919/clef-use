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
    root, owned_target, gui, action = None, None, WindowsInput(), DesktopAction()
    previous_target, previous_pointer = gui.foreground(), Point()
    with gui.physical_coordinates():
        pointer_observed = bool(gui.user.GetCursorPos(ctypes.byref(previous_pointer)))
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
        gui.user.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        gui.user.GetAncestor.restype = ctypes.c_void_p
        gui.user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        owned_target = gui.user.GetAncestor(root.winfo_id(), 2)
        gui.user.SetForegroundWindow(owned_target)
        root.update()
        if gui.foreground() != owned_target:
            raise RuntimeError("owned test window did not become foreground")
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

        clipboard_sequence = gui.user.GetClipboardSequenceNumber()
        text = "Windows 한글 테스트 😀"
        assert execute("type", text, "entry").ok
        assert entry.get() == text, repr(entry.get())
        assert gui.user.GetClipboardSequenceNumber() == clipboard_sequence
        result["unicode_readback"] = entry.get()
        result["clipboard_preserved"] = True
        result["clipboard_verification"] = "sequence unchanged; no clipboard read/write"
        assert execute("hotkey", "ctrl+a").ok
        result["select_all_readback"] = {
            "text": entry.get(),
            "selection_present": bool(entry.selection_present()),
            "focused_widget": str(root.focus_get()),
        }
        if entry.selection_present():
            result["select_all_readback"]["selected_range"] = [
                entry.index(tk.SEL_FIRST),
                entry.index(tk.SEL_LAST),
            ]
        assert execute("press", "backspace").ok
        result["shortcut_readback"] = entry.get()
        assert result["shortcut_readback"] == ""
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
        cleanup = {"errors": []}
        try:
            action.release()
            cleanup["input_released"] = True
        except Exception:
            cleanup["errors"].append(traceback.format_exc())
        # Restore while the owned window still grants foreground input access.
        # Destroying the last Tk window first can leave no input target on Windows.
        if owned_target is not None and gui.foreground() == owned_target:
            try:
                if not pointer_observed:
                    raise RuntimeError("previous pointer was not observed; restoration refused")
                gui.FAILSAFE = False
                with gui.physical_coordinates():
                    gui.moveTo(previous_pointer.x, previous_pointer.y)
                cleanup["pointer_restored"] = True
            except Exception:
                cleanup["errors"].append(traceback.format_exc())
        else:
            cleanup["pointer_restoration_skipped"] = "owned foreground unavailable or changed"
            cleanup["errors"].append(cleanup["pointer_restoration_skipped"])
        # Pointer restoration can fail independently; still restore the prior
        # foreground if no other actor has taken it from our owned window.
        if owned_target is not None and gui.foreground() == owned_target:
            try:
                gui.user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
                admitted = gui.user.SetForegroundWindow(previous_target)
                cleanup["foreground_immediate"] = gui.foreground() == previous_target
                # Cross-thread foreground activation is asynchronous. Synchronize
                # its message queue once; do not replay focus or input requests.
                gui.user.SendMessageTimeoutW.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_uint,
                    ctypes.c_size_t,
                    ctypes.c_ssize_t,
                    ctypes.c_uint,
                    ctypes.c_uint,
                    ctypes.POINTER(ctypes.c_size_t),
                ]
                gui.user.SendMessageTimeoutW.restype = ctypes.c_ssize_t
                response = ctypes.c_size_t()
                acknowledged = admitted and gui.user.SendMessageTimeoutW(
                    previous_target, 0, 0, 0, 2, 1000, ctypes.byref(response)
                )
                cleanup["foreground_queue_synchronized"] = bool(acknowledged)
                cleanup["foreground_restored"] = bool(
                    acknowledged and gui.foreground() == previous_target
                )
                if not cleanup["foreground_restored"]:
                    raise RuntimeError("previous foreground restoration was not confirmed")
            except Exception:
                cleanup["errors"].append(traceback.format_exc())
        else:
            cleanup["foreground_restoration_skipped"] = "owned foreground unavailable or changed"
            cleanup["errors"].append(cleanup["foreground_restoration_skipped"])
        try:
            if root:
                root.destroy()
            cleanup["owned_window_closed"] = True
        except Exception:
            cleanup["errors"].append(traceback.format_exc())
        result["cleanup"] = cleanup
        if cleanup["errors"]:
            result["status"] = "FAILED"
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASSED" else 1


if __name__ == "__main__":
    if sys.platform != "win32":
        raise SystemExit("Requires an interactive Windows desktop")
    raise SystemExit(main())
