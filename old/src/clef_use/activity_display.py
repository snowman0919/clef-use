from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def images(state):
    fonts = [
        Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts/malgun.ttf",
        Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    font = next(
        (ImageFont.truetype(str(p), 14) for p in fonts if p.exists()),
        ImageFont.load_default(size=14),
    )
    panel = Image.new("RGBA", (340, 84))
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle((0, 0, 339, 83), radius=12, fill="#101b2e", outline="#344766")
    draw.ellipse((16, 16, 24, 24), fill="#58d6d1")
    draw.text((34, 9), f"clef-use  |  {state['phase']}", font=font, fill="white")
    label = state.get("target") or "Working on your desktop"
    # Display labels, never action payloads or raw planner instructions.
    draw.text((16, 34), str(label).replace("\n", " ")[:42], font=font, fill="#d3dfef")
    draw.text(
        (16, 59),
        f"Actions: {state['steps']}   Decisions: {state['rounds']}",
        font=font,
        fill="#9fb1c8",
    )
    cursor = Image.new("RGBA", (48, 48))
    draw = ImageDraw.Draw(cursor)
    draw.ellipse((2, 2, 45, 45), outline="#58d6d1", width=3)
    draw.polygon(
        [(24, 24), (24, 43), (29, 37), (34, 47), (39, 44), (34, 34), (44, 34)],
        fill="#58d6d1",
        outline="white",
        width=2,
    )
    return panel, cursor


def main():
    if sys.platform == "darwin":
        from .activity_macos import Display
    elif sys.platform == "win32":
        from .activity_windows import Display
    else:
        from .activity_x11 import Display
    display = Display()
    events = queue.Queue()

    def reader():
        for line in sys.stdin:
            events.put(json.loads(line))
        events.put(None)

    threading.Thread(target=reader, daemon=True).start()
    print(
        json.dumps(
            {
                "ready": True,
                "windows": display.window_ids(),
                "capture_excluded": getattr(display, "capture_excluded", False),
            }
        ),
        flush=True,
    )
    hide_at = None
    previous = None
    rendered = None
    try:
        while True:
            display.pump()
            try:
                event = events.get(timeout=0.02)
            except queue.Empty:
                if hide_at is not None and time.monotonic() >= hide_at:
                    display.hide()
                    hide_at = None
                continue
            if event is None:
                break
            if event["op"] == "hide":
                display.hide()
                # Allow one compositor cycle before acknowledging clean capture.
                time.sleep(0.035)
            else:
                state = event["state"]
                signature = tuple(state.get(key) for key in ("phase", "steps", "rounds", "target"))
                if signature != previous:
                    rendered = images(state)
                    previous = signature
                panel, cursor = rendered
                display.show(panel, cursor, event["state"].get("point"))
                hide_at = time.monotonic() + 3 if event["state"].get("terminal") else None
            print(json.dumps({"seq": event["seq"]}), flush=True)
    finally:
        display.close()


if __name__ == "__main__":
    main()
