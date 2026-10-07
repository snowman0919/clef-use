"""Native display/capture check. Windows uses only a disposable button window."""

from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from clef_use.activity import ActivityOverlay
from clef_use.backends import DesktopCapture


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    overlay = ActivityOverlay()
    result = {"platform": sys.platform, "real_models": False}
    root = None
    coordinates = None
    try:
        if sys.platform == "win32":
            import tkinter as tk
            from threading import Event

            from clef_use.backends import DesktopAction
            from clef_use.schema import ActionCandidate, BoundingBox, Observation, UIObject
            from clef_use.windows_input import Point, WindowsInput

            native = WindowsInput()
            coordinates = native.physical_coordinates()
            coordinates.__enter__()
            original = native.foreground()
            pointer = Point()
            native.user.GetCursorPos(ctypes.byref(pointer))
            root = tk.Tk()
            root.title("clef-use owned activity validation")
            root.geometry("640x320+450+250")
            clicks = []
            button = tk.Button(root, text="Overlay passthrough", command=lambda: clicks.append(1))
            button.pack(padx=30, pady=90)
            root.update()
            native.user.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            native.user.GetAncestor.restype = ctypes.c_void_p
            hwnd = native.user.GetAncestor(root.winfo_id(), 2)
            native.user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
            native.user.SetForegroundWindow(hwnd)
            root.update()
            point = (
                button.winfo_rootx() + button.winfo_width() // 2,
                button.winfo_rooty() + button.winfo_height() // 2,
            )
        else:
            point = (200, 180)
        capture = DesktopCapture()
        before = capture.capture()
        if sys.platform == "darwin":
            import AppKit

            workspace = AppKit.NSWorkspace.sharedWorkspace()
            foreground = workspace.frontmostApplication().processIdentifier()
        overlay.update("Click", SimpleNamespace(steps=0, rounds=1), point=point, target="Continue")
        assert overlay.enabled, "native display unavailable"
        result["window_ids"] = overlay.windows
        time.sleep(0.15)
        if sys.platform == "darwin":
            import AppKit
            import Quartz

            def visible():
                info = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll, 0)
                return {
                    int(i["kCGWindowNumber"]): bool(i.get("kCGWindowIsOnscreen"))
                    and float(i.get("kCGWindowAlpha", 1)) > 0.00001
                    for i in info
                }

            assert all(visible().get(w) for w in overlay.windows), "initial display not visible"
            with overlay.capture():
                assert all(not visible().get(w) for w in overlay.windows), "display not hidden"
                DesktopCapture().capture()
            deadline = time.monotonic() + 0.5
            while (
                not all(visible().get(w) for w in overlay.windows) and time.monotonic() < deadline
            ):
                time.sleep(0.01)
            assert all(visible().get(w) for w in overlay.windows), "display not restored"
            assert workspace.frontmostApplication().processIdentifier() == foreground
            result["window_server_hide_restore"] = "PASSED"
            with overlay.capture(capture):
                clean = capture.capture()
                assert all(visible().get(w) for w in overlay.windows)
            assert clean.image.size == before.image.size
            x, y = point
            scale = before.image.width / before.logical_size[0]
            region = tuple(int(v * scale) for v in (x - 24, y - 24, x + 24, y + 24))
            assert before.image.crop(region).tobytes() == clean.image.crop(region).tobytes()
            result["native_exclusion_without_hiding"] = "PASSED"

        else:
            with overlay.capture(capture):
                clean = capture.capture()
            # Only compare our stable marker region, not unrelated desktop animation.
            x, y = point
            region = (x - 24, y - 24, x + 24, y + 24)
            assert before.image.crop(region).tobytes() == clean.image.crop(region).tobytes()
            result["capture_marker_region_unchanged"] = "PASSED"
        if sys.platform == "win32":
            assert native.foreground() == hwnd
            current = Point()
            native.user.GetCursorPos(ctypes.byref(current))
            assert current.x == pointer.x and current.y == pointer.y
            frame = clean
            x, y = point
            w, h = frame.image.size
            obj = UIObject(
                id="button",
                label="Overlay passthrough",
                role="button",
                bbox=BoundingBox(x1=(x - 4) / w, y1=(y - 4) / h, x2=(x + 4) / w, y2=(y + 4) / h),
                actions=frozenset({"click"}),
            )
            observation = Observation("owned-display-test", frame, (obj,))
            action = DesktopAction()
            try:
                outcome = action.execute(
                    ActionCandidate(
                        id="a",
                        operation="click",
                        observation_id=observation.id,
                        target=obj.id,
                        description="Owned test button",
                    ),
                    observation,
                    Event(),
                )
                root.update()
                assert outcome.ok and len(clicks) == 1
                result["real_click_through"] = "PASSED"
            finally:
                action.release()
        result["status"] = "PASSED"
    except Exception as exc:
        result["status"] = "FAILED"
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        overlay.close()
        if root is not None:
            root.destroy()
            native.user.SetForegroundWindow(original)
            with native.physical_coordinates():
                native.user.SetCursorPos(pointer.x, pointer.y)
        if coordinates is not None:
            coordinates.__exit__(None, None, None)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result["status"] != "PASSED"


if __name__ == "__main__":
    raise SystemExit(main())
