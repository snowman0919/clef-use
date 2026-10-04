"""Private Windows GUI endpoint for the diagnostic SSH model smoke; not a backend."""

import argparse
import ctypes
import hmac
import json
import subprocess
import sys
import threading
import time
import tkinter as tk
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event

from PIL import Image

from clef_use.backends import DesktopAction, DesktopCapture, encode_image
from clef_use.schema import ActionCandidate, Frame, Observation, UIObject
from clef_use.windows_input import Point, WindowsInput


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=37943)
    parser.add_argument("--run-cli", action="store_true")
    args = parser.parse_args()
    token = (args.root / "gui-token").read_text().strip()
    native, action = WindowsInput(), DesktopAction()
    previous_target, previous_pointer = native.foreground(), Point()
    with native.physical_coordinates():
        native.user.GetCursorPos(ctypes.byref(previous_pointer))
    desktop = native.desktop_status()
    root = tk.Tk()
    root.title("clef-use real model GUI validation")
    root.geometry("900x600+500+200")
    root.configure(bg="white")
    root.attributes("-topmost", True)
    if args.run_cli:
        root.attributes("-fullscreen", True)
    state = {
        "stage": 0,
        "clicks": [],
        "input_attempts": [],
        "render_delay_ms": 0,
        "no_effect": False,
        "render_pending": False,
    }
    tk.Label(root, text="Local test workspace", font=("Segoe UI", 26), bg="white").place(x=40, y=40)
    label = tk.Label(root, text="", font=("Segoe UI", 26), bg="white")
    label.place(x=40, y=200)

    def advance():
        state["clicks"].append(button.cget("text"))
        if state["no_effect"]:
            return
        state["stage"] += 1
        state["render_pending"] = True

        def render():
            state["render_pending"] = False
            if state["stage"] == 1:
                button.configure(text="Confirm", state="normal")
            else:
                button.place_forget()
                label.configure(text="Task complete")

        if state["render_delay_ms"]:
            root.after(state["render_delay_ms"], render)
        else:
            render()

    button = tk.Button(root, text="Continue", font=("Segoe UI", 22), command=advance)
    button.place(x=50, y=220, width=260, height=80)
    if args.run_cli:
        button.configure(font=("Segoe UI", 42))
        button.place(x=50, y=220, width=420, height=120)
        label.configure(font=("Segoe UI", 42))
        state["render_delay_ms"] = 500
    root.update()
    root.focus_force()
    root.update()
    native.user.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    native.user.GetAncestor.restype = ctypes.c_void_p
    native.user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    owned_target = native.user.GetAncestor(root.winfo_id(), 2)
    native.user.SetForegroundWindow(owned_target)
    root.update()
    if native.foreground() != owned_target:
        raise RuntimeError("owned test window did not become foreground")
    with native.physical_coordinates():
        bounds = (
            root.winfo_rootx(),
            root.winfo_rooty(),
            root.winfo_rootx() + root.winfo_width(),
            root.winfo_rooty() + root.winfo_height(),
        )
    target = native.foreground()

    def on_ui(callback):
        done = Event()
        reply = {}

        def invoke():
            try:
                reply["value"] = callback()
            except Exception as exc:
                reply["error"] = exc
            finally:
                done.set()

        root.after(0, invoke)
        if not done.wait(10):
            raise TimeoutError("owned GUI did not answer")
        if "error" in reply:
            raise reply["error"]
        return reply.get("value")

    def reset(payload):
        state.update(
            stage=0,
            render_pending=False,
            clicks=[],
            input_attempts=[],
            render_delay_ms=int(payload.get("delay_ms", 0)),
            no_effect=bool(payload.get("no_effect", False)),
        )
        label.configure(text="")
        button.configure(text="Continue", state="normal")
        button.place(x=50, y=220, width=260, height=80)
        root.focus_force()
        root.update_idletasks()
        return {"reset": True, "stage": 0}

    def capture():
        frame = DesktopCapture().capture()
        native.ensure_target(target)
        pixels = frame.image.crop(bounds)
        return Frame(
            pixels, bounds[:2], pixels.size, frame.foreground_window, frame.foreground_bounds
        )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            if not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + token):
                self.send_error(403)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8_000_000:
                    raise ValueError("bounded request required")
                payload = json.loads(self.rfile.read(length))
                if self.path == "/capture":
                    frame = capture()
                    result = {
                        "image": encode_image(frame.image),
                        "origin": frame.origin,
                        "size": frame.image.size,
                        "foreground": frame.foreground_window,
                        "foreground_bounds": frame.foreground_bounds,
                        "render_pending": state["render_pending"],
                    }
                elif self.path == "/action":
                    import base64
                    import io

                    frame = Frame(
                        Image.open(io.BytesIO(base64.b64decode(payload["image"]))).convert("RGB"),
                        tuple(payload["origin"]),
                        tuple(payload["size"]),
                        payload["foreground"],
                        tuple(payload["foreground_bounds"]),
                    )
                    observation = Observation(
                        payload["id"],
                        frame,
                        tuple(UIObject.model_validate(o) for o in payload["objects"]),
                    )
                    expected_label = next(
                        (
                            o.label
                            for o in observation.objects
                            if o.id == payload["action"].get("target")
                        ),
                        None,
                    )
                    visible_label = on_ui(
                        lambda: button.cget("text") if state["stage"] < 2 else "Task complete"
                    )
                    state["input_attempts"].append(
                        {
                            "target_label": expected_label,
                            "visible_label": visible_label,
                            "correct": bool(
                                expected_label and visible_label.lower() in expected_label.lower()
                            ),
                        }
                    )
                    result = action.execute(
                        ActionCandidate.model_validate(payload["action"]), observation, Event()
                    ).model_dump()
                elif self.path == "/reset":
                    result = on_ui(lambda: reset(payload))
                elif self.path == "/release":
                    action.release()
                    result = {"released": True}
                elif self.path == "/result":
                    frame = capture()
                    frame.image.save(args.root / "windows-model-gui.png")
                    result = {
                        "stage": state["stage"],
                        "clicks": list(state["clicks"]),
                        "input_attempts": list(state["input_attempts"]),
                        "render_delay_ms": state["render_delay_ms"],
                        "no_effect": state["no_effect"],
                        "visible_result": on_ui(
                            lambda: (
                                label.cget("text") if state["stage"] == 2 else button.cget("text")
                            )
                        ),
                        "render_pending": state["render_pending"],
                        "desktop": desktop,
                        "native_input": True,
                    }
                    (args.root / "windows-model-readback.json").write_text(
                        json.dumps(result), encoding="utf-8"
                    )
                elif self.path == "/finish":
                    action.release()
                    root.after(100, root.quit)
                    result = {"closing_owned_window": True}
                else:
                    raise ValueError("unknown diagnostic operation")
                body = json.dumps(result).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:
                body = json.dumps({"error": str(exc), "kind": type(exc).__name__}).encode()
                self.send_response(500)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    (args.root / "windows-model-agent-ready.json").write_text(
        json.dumps({"session_id": desktop["session_id"], "port": args.port}), encoding="utf-8"
    )
    if args.run_cli:

        def cli_run():
            from clef_use.client import RuntimeClient
            from clef_use.config import state_dir

            report = {"mode": "REAL_WINDOWS_CANONICAL_CLI", "uses_action_bridge": False}
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "clef_use.cli",
                        "run",
                        "Make Task complete visible using Continue then Confirm.",
                        "--success",
                        "Task complete is visible",
                        "--max-steps",
                        "8",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=600,
                )
                (args.root / "cli.stdout.txt").write_text(result.stdout, encoding="utf-8")
                (args.root / "cli.stderr.txt").write_text(result.stderr, encoding="utf-8")
                report["exit_code"] = result.returncode
                report["runtime"] = json.loads(result.stdout)
                report["independent_gui_readback"] = on_ui(
                    lambda: {
                        "stage": state["stage"],
                        "clicks": list(state["clicks"]),
                        "visible_result": label.cget("text"),
                        "render_pending": state["render_pending"],
                    }
                )
            except Exception as exc:
                report["error"] = type(exc).__name__
            finally:
                client = RuntimeClient(start=False)
                try:
                    if (state_dir() / "endpoint.json").exists():
                        if client._send("health", {}).get("busy"):
                            client._send("abort", {})
                        client._send("shutdown_idle", {})
                    for _ in range(100):
                        if not (state_dir() / "endpoint.json").exists():
                            break
                        time.sleep(0.1)
                    report["endpoint_removed"] = not (state_dir() / "endpoint.json").exists()
                except Exception as exc:
                    report["cleanup_error"] = type(exc).__name__
                (args.root / "canonical-cli-result.json").write_text(
                    json.dumps(report), encoding="utf-8"
                )
                root.after(0, root.quit)

        threading.Thread(target=cli_run, daemon=True).start()
    root.after(2_700_000, root.quit)
    try:
        root.mainloop()
    finally:
        server.shutdown()
        server.server_close()
        action.release()
        root.destroy()
        native.FAILSAFE = False
        with native.physical_coordinates():
            native.moveTo(previous_pointer.x, previous_pointer.y)
        native.user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        native.user.SetForegroundWindow(previous_target)


if __name__ == "__main__":
    main()
