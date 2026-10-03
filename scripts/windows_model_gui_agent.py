"""Private Windows GUI endpoint for the diagnostic SSH model smoke; not a backend."""

import argparse
import ctypes
import hmac
import json
import threading
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
    args = parser.parse_args()
    token = (args.root / "gui-token").read_text().strip()
    native, action = WindowsInput(), DesktopAction()
    previous_target, previous_pointer = native.foreground(), Point()
    native.user.GetCursorPos(ctypes.byref(previous_pointer))
    desktop = native.desktop_status()
    root = tk.Tk()
    root.title("clef-use real model GUI validation")
    root.geometry("900x600+500+200")
    root.configure(bg="white")
    root.attributes("-topmost", True)
    state = {"stage": 0, "clicks": []}
    tk.Label(root, text="Local test workspace", font=("Segoe UI", 26), bg="white").place(x=40, y=40)
    label = tk.Label(root, text="", font=("Segoe UI", 26), bg="white")
    label.place(x=40, y=200)

    def advance():
        state["clicks"].append(button.cget("text"))
        state["stage"] += 1
        if state["stage"] == 1:
            button.configure(text="Confirm")
        else:
            button.destroy()
            label.configure(text="Task complete")

    button = tk.Button(root, text="Continue", font=("Segoe UI", 22), command=advance)
    button.place(x=50, y=220, width=260, height=80)
    root.update()
    root.focus_force()
    root.update()
    with native.physical_coordinates():
        bounds = (
            root.winfo_rootx(),
            root.winfo_rooty(),
            root.winfo_rootx() + root.winfo_width(),
            root.winfo_rooty() + root.winfo_height(),
        )
    target = native.foreground()

    def capture():
        frame = DesktopCapture().capture()
        native.ensure_target(target)
        pixels = frame.image.crop(bounds)
        return Frame(pixels, bounds[:2], pixels.size, frame.foreground_window)

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
                    }
                elif self.path == "/action":
                    import base64
                    import io

                    frame = Frame(
                        Image.open(io.BytesIO(base64.b64decode(payload["image"]))).convert("RGB"),
                        tuple(payload["origin"]),
                        tuple(payload["size"]),
                        payload["foreground"],
                    )
                    observation = Observation(
                        payload["id"],
                        frame,
                        tuple(UIObject.model_validate(o) for o in payload["objects"]),
                    )
                    result = action.execute(
                        ActionCandidate.model_validate(payload["action"]), observation, Event()
                    ).model_dump()
                elif self.path == "/release":
                    action.release()
                    result = {"released": True}
                elif self.path == "/result":
                    frame = capture()
                    frame.image.save(args.root / "windows-model-gui.png")
                    result = {
                        "stage": state["stage"],
                        "clicks": list(state["clicks"]),
                        "visible_result": "Task complete"
                        if state["stage"] == 2
                        else button.cget("text"),
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
    root.after(540_000, root.quit)
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
