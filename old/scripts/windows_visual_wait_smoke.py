"""Validate screenshot readiness on an owned Windows GUI, without model inference."""

import argparse
import ctypes
import json
import platform
import time
import tkinter as tk
import traceback
from pathlib import Path
from threading import Event

from clef_use.backends import DesktopAction, DesktopCapture
from clef_use.schema import ActionCandidate, BoundingBox, Frame, Observation, UIObject
from clef_use.verification import VisualWaiter
from clef_use.windows_input import Point, WindowsInput


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    native, action = WindowsInput(), DesktopAction()
    previous_target, pointer = native.foreground(), Point()
    with native.physical_coordinates():
        native.user.GetCursorPos(ctypes.byref(pointer))
    report = {"kind": "REAL_WINDOWS_NATIVE_VISUAL_WAIT", "host": platform.platform(), "runs": []}
    root = None
    try:
        native.desktop_status()
        root = tk.Tk()
        root.title("clef-use disposable visual readiness validation")
        root.geometry("600x400+500+200")
        root.configure(bg="white")
        root.attributes("-topmost", True)
        label = tk.Label(root, text="Pending", bg="white", font=("Segoe UI", 24))
        label.place(x=40, y=200, width=350, height=90)
        blink = tk.Label(root, text="Unrelated activity", bg="white")
        blink.place(x=420, y=20)
        state = {"no_effect": False, "callbacks": 0, "rendered": None}

        def render():
            label.configure(text="Ready")
            state["rendered"] = time.monotonic()

        def clicked():
            state["callbacks"] += 1
            if not state["no_effect"]:
                root.after(500, render)

        button = tk.Button(root, text="Start transition", command=clicked)
        button.place(x=40, y=60, width=260, height=80)

        def animate():
            blink.configure(fg="black" if blink.cget("fg") != "black" else "white")
            root.after(70, animate)

        animate()
        root.update()
        native.user.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        native.user.GetAncestor.restype = ctypes.c_void_p
        native.user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        target = native.user.GetAncestor(root.winfo_id(), 2)
        native.user.SetForegroundWindow(target)
        root.update()
        native.ensure_target(target)
        with native.physical_coordinates():
            x, y, width, height = (
                root.winfo_rootx(),
                root.winfo_rooty(),
                root.winfo_width(),
                root.winfo_height(),
            )

        class Capture:
            def capture(self):
                root.update()
                frame = DesktopCapture().capture()
                native.ensure_target(target)
                return Frame(
                    frame.image.crop((x, y, x + width, y + height)),
                    (x, y),
                    (width, height),
                    target,
                    frame.foreground_bounds,
                )

        capture = Capture()
        roi = BoundingBox(x1=40 / width, y1=200 / height, x2=390 / width, y2=290 / height)
        obj = UIObject(
            id="owned-button",
            label="Start transition",
            role="button",
            actions=("click",),
            bbox=BoundingBox(x1=40 / width, y1=60 / height, x2=300 / width, y2=140 / height),
        )
        candidate = ActionCandidate(
            id="click",
            operation="click",
            target=obj.id,
            observation_id="initial",
            description="Click owned transition button",
        )
        for trial in range(6):
            state.update(no_effect=trial == 5, rendered=None)
            label.configure(text="Pending")
            before = capture.capture()
            candidate = candidate.model_copy(update={"observation_id": str(trial)})
            accepted = action.execute(candidate, Observation(str(trial), before, (obj,)), Event())
            assert accepted.ok, accepted.reason
            started = time.monotonic()
            waiter = VisualWaiter(timeout=1 if trial == 5 else 3)
            result = waiter.wait(capture, before, roi, Event())
            readback = label.cget("text")
            row = {
                "trial": trial,
                "no_effect": trial == 5,
                **result.metrics(),
                "visible_text": readback,
                "callbacks": state["callbacks"],
                "render_delay_ms": None
                if state["rendered"] is None
                else (state["rendered"] - started) * 1000,
            }
            report["runs"].append(row)
            if trial == 5:
                assert result.state == "NO_CHANGE" and readback == "Pending", row
            else:
                assert result.state == "STABLE" and readback == "Ready", row
                assert result.elapsed_ms >= row["render_delay_ms"], row
            assert state["callbacks"] == trial + 1, row
        report.update(
            status="PASSED",
            model_calls=0,
            native_actions=6,
            limitation="Known widget geometry; readiness only, no model or task benchmark",
        )
    except Exception:
        report.update(status="FAILED", traceback=traceback.format_exc())
    finally:
        action.release()
        if root:
            root.destroy()
        native.FAILSAFE = False
        with native.physical_coordinates():
            native.moveTo(pointer.x, pointer.y)
        native.user.SetForegroundWindow(previous_target)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
