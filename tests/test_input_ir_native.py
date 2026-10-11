"""Disposable X11 fixture: actual OS input, widget effects and process death recovery."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

NATIVE_PROGRAM = r'''
import json
import os
import signal
import subprocess
import sys
import time
import tkinter as tk
from threading import Event, current_thread, main_thread
from PIL import Image
from Xlib import display
from clef_use.backends import DesktopAction, DesktopCapture
from clef_use.input_ir import ChordInput, KeyInput, TextInput, PointerInput, GestureInput
from clef_use.schema import Frame

root = tk.Tk()
root.geometry("600x450+30+40")
entry = tk.Entry(root)
entry.pack(fill="x")
canvas = tk.Canvas(root, width=550, height=350)
canvas.pack()
root.update()
entry.focus_force()
root.update()
window, bounds = DesktopCapture._x11_context()
frame = Frame(Image.new("RGB", (800, 600)), foreground_window=window, foreground_bounds=bounds)
adapter = DesktopAction()
class UIEvent(Event):
    def wait(self, timeout=None):
        if current_thread() is main_thread():
            root.update()
        return super().wait(timeout)
cancelled = UIEvent()
results = {}
releases = []
entry.bind("<KeyRelease>", lambda event: releases.append(event.keysym))

def run(command, **kwargs):
    result = adapter.execute_input(command, frame, cancelled, **kwargs)
    assert result.ok, result
    root.update()

run(ChordInput(modifiers=("shift",), key="a"))
assert entry.get() == "A", repr(entry.get())
results["chord_literal"] = entry.get()
assert releases[-2:] == ["A", "Shift_L"], releases
run(TextInput(text="b 2.50 ! A:@_+", method="unicode"))
assert entry.get() == "Ab 2.50 ! A:@_+", repr(entry.get())
run(TextInput(text="한😀 e\u0301", method="clipboard"))
assert entry.get() == "Ab 2.50 ! A:@_+한😀 e\u0301", repr(entry.get())
results["exact_unicode"] = True

connection = display.Display()
code = adapter.gui.platformModule.keyboardMapping["shift"]
def held():
    bitmap = connection.query_keymap()
    return bool(bitmap[code // 8] & (1 << (code % 8)))
run(KeyInput(key="shift", phase="down"), deadline=time.monotonic() + 1)
assert held()
run(KeyInput(key="shift", phase="up"))
assert not held()
results["down_up"] = True

buttons = []
motions = []
for number in (1, 2, 3):
    canvas.bind(f"<ButtonPress-{number}>", lambda event: buttons.append(event.num))
canvas.bind("<B2-Motion>", lambda event: motions.append(event.state))
point = ((canvas.winfo_rootx() + 80) / 800, (canvas.winfo_rooty() + 80) / 600)
for button in ("left", "right", "middle"):
    run(PointerInput(button=button, point=point))
assert buttons == [1, 3, 2], buttons
motions.clear()
run(GestureInput(points=(point, (point[0] + .05, point[1] + .05)),
                 surface=(.01, .01, .9, .9), modifiers=("shift",), button="middle", duration=.04))
assert motions and motions[-1] & 1, motions
assert not adapter.keys and not adapter.buttons
results["buttons_and_modifier_gesture"] = True

run(KeyInput(key="shift", phase="down"), deadline=time.monotonic() + .08)
assert held()
assert cancelled.wait(.7)
assert not held()
results["deadline_release"] = True
cancelled = Event()
run(KeyInput(key="shift", phase="down"), deadline=time.monotonic() + 1)
cancelled.set()
for _ in range(100):
    if not held(): break
    time.sleep(.01)
assert not held()
results["cancel_release"] = True

# A key held by a different OS input source is never adopted or released.
cancelled = UIEvent()
adapter.gui.keyDown("ctrl", _pause=False)
try:
    try:
        adapter.execute_input(KeyInput(key="a"), frame, cancelled)
    except RuntimeError as error:
        assert "unowned input" in str(error)
    else:
        raise AssertionError("human-held key conflict was accepted")
    ctrl = adapter.gui.platformModule.keyboardMapping["ctrl"]
    bitmap = connection.query_keymap()
    assert bitmap[ctrl // 8] & (1 << (ctrl % 8))
finally:
    adapter.gui.keyUp("ctrl", _pause=False)
results["preexisting_input_preserved"] = True

# Independent watchdog observes a foreground change while the caller is idle.
run(KeyInput(key="shift", phase="down"), deadline=time.monotonic() + 2)
other = tk.Toplevel(root)
other.geometry("100x100+650+10")
other.update()
other.focus_force()
other.update()
assert cancelled.wait(.7)
assert not held()
other.destroy()
entry.focus_force()
root.update()
cancelled = UIEvent()
results["foreground_watchdog_release"] = True

# New unowned keypress is conservative user-intervention evidence on X11.
run(KeyInput(key="shift", phase="down"), deadline=time.monotonic() + 2)
adapter.gui.keyDown("ctrl", _pause=False)
assert cancelled.wait(.7)
assert not held()
bitmap = connection.query_keymap()
assert bitmap[ctrl // 8] & (1 << (ctrl % 8))
adapter.gui.keyUp("ctrl", _pause=False)
cancelled = UIEvent()
results["intervention_release_preserves_unowned"] = True

# Losing the recovery process while an input is held must cancel and clean up
# immediately; it must not orphan ownership by replacing the active watcher.
run(KeyInput(key="shift", phase="down"), deadline=time.monotonic() + 2)
guardian = adapter.input_executor.guardian
guardian.terminate()
guardian.wait(timeout=5)
try:
    adapter.execute_input(KeyInput(key="a"), frame, cancelled)
except RuntimeError:
    pass
except BrokenPipeError:
    pass
else:
    raise AssertionError("dead guardian was accepted")
assert not held(), "guardian failure orphaned a held key"
adapter = DesktopAction()
cancelled = UIEvent()
run(KeyInput(key="escape"))
results["guardian_failure_release"] = True

crash = r"""
import os,time
from threading import Event
from PIL import Image
from clef_use.backends import DesktopAction, DesktopCapture
from clef_use.input_ir import KeyInput
from clef_use.schema import Frame
window,bounds=DesktopCapture._x11_context()
frame=Frame(Image.new('RGB',(800,600)),foreground_window=window,foreground_bounds=bounds)
result=DesktopAction().execute_input(KeyInput(key='shift',phase='down'),frame,Event(),deadline=time.monotonic()+5)
assert result.ok,result
os._exit(19)
"""
child = subprocess.run([sys.executable, "-c", crash], timeout=10)
assert child.returncode == 19
for _ in range(100):
    if not held(): break
    time.sleep(.01)
assert not held()
results["process_crash_release"] = True

# SIGSTOP freezes the injector and all its threads. The guardian still has to
# enforce the lease deadline under the same desktop permissions.
stalled = crash.replace("os._exit(19)",
    "import signal;print('held',flush=True);os.kill(os.getpid(),signal.SIGSTOP);os._exit(20)")
stalled = stalled.replace("time.monotonic()+5", "time.monotonic()+.5")
child = subprocess.Popen([sys.executable, "-c", stalled], stdout=subprocess.PIPE, text=True)
try:
    for line in child.stdout:
        if line.strip() == "held":
            break
    assert held()
    for _ in range(150):
        if not held(): break
        time.sleep(.01)
    assert not held(), "guardian failed to release a SIGSTOP-frozen injector"
    os.kill(child.pid, signal.SIGCONT)
    assert child.wait(timeout=5) == 20
finally:
    if child.poll() is None:
        os.kill(child.pid, signal.SIGCONT)
        child.terminate()
        child.wait(timeout=5)
results["frozen_injector_deadline_release"] = True
adapter.release()
connection.close()
root.destroy()
print(json.dumps(results))
'''


@pytest.mark.skipif(
    not shutil.which("Xvfb") or not shutil.which("xsel"),
    reason="native X11 fixture requires Xvfb and xsel",
)
def test_native_widget_effects_and_independent_recovery(tmp_path):
    read_fd, write_fd = os.pipe()
    process = subprocess.Popen(
        [
            "Xvfb",
            "-displayfd",
            str(write_fd),
            "-screen",
            "0",
            "800x600x24",
            "-nolisten",
            "tcp",
            "-ac",
        ],
        pass_fds=(write_fd,),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    os.close(write_fd)
    try:
        with os.fdopen(read_fd) as stream:
            number = stream.readline().strip()
        assert number.isdigit(), "Xvfb did not allocate a disposable display"
        environment = dict(os.environ, DISPLAY=f":{number}")
        authority = tmp_path / "Xauthority"
        authority.touch()
        environment["XAUTHORITY"] = str(authority)
        result = subprocess.run(
            [sys.executable, "-c", NATIVE_PROGRAM],
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=Path(__file__).resolve().parents[1],
        )
        assert result.returncode == 0, result.stdout + result.stderr
        evidence = json.loads(result.stdout.strip().splitlines()[-1])
        assert evidence["process_crash_release"] is True
        report = tmp_path / "native-input-evidence.json"
        report.write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps(evidence))
        print(f"Raw evidence: {report}")
    finally:
        process.terminate()
        process.wait(timeout=5)
