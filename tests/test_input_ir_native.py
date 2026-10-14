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
run(TextInput(text="b 2.50 ! A:@_+", method="clipboard"))
assert entry.get() == "Ab 2.50 ! A:@_+", repr(entry.get())
run(TextInput(text="한😀 e\u0301", method="clipboard"))
assert entry.get() == "Ab 2.50 ! A:@_+한😀 e\u0301", repr(entry.get())
results["exact_unicode"] = True

# Clipboard delivery is a native transfer acknowledgement, not a timed restore.
# Keep the target's real selection request delayed beyond the former 100ms wait.
clipboard_events = []
literal = "delayed 한😀 e\u0301"
def delayed_paste(event):
    clipboard_events.append(("ctrl_v", time.monotonic()))
    def consume():
        value = entry.selection_get(selection="CLIPBOARD", type="UTF8_STRING")
        entry.insert("end", value)
        clipboard_events.append(("consumed", time.monotonic(), value))
    root.after(150, consume)
    return "break"
entry.bind("<Control-v>", delayed_paste)
before = entry.get()
run(TextInput(text=literal, method="clipboard"))
assert entry.get() == before + literal
assert clipboard_events[-1][2] == literal
assert clipboard_events[-1][1] - clipboard_events[0][1] >= .15
results["delayed_clipboard_request_exact"] = True

# Cancel after actual Ctrl+V delivery but before the target requests bytes. Old
# clipboard data must not replace the still-queued paste's offered literal.
def cancel_before_request(event):
    clipboard_events.append(("cancel_after_ctrl_v", time.monotonic()))
    cancelled.set()
    return "break"
entry.bind("<Control-v>", cancel_before_request)
cancelled = UIEvent()
interrupted = adapter.execute_input(TextInput(text="queued after cancel", method="clipboard"),
                                    frame, cancelled)
assert not interrupted.ok and "unacknowledged" in interrupted.reason, interrupted
assert not adapter.keys and not adapter.buttons
assert entry.selection_get(selection="CLIPBOARD", type="UTF8_STRING") == "queued after cancel"
cancelled = UIEvent()
results["cancel_retains_queued_literal_until_transfer"] = True

delivered_without_request = []
def omit_request(event):
    delivered_without_request.append(True)
    return "break"
entry.bind("<Control-v>", omit_request)
expired = adapter.execute_input(TextInput(text="queued after deadline", method="clipboard"),
                               frame, cancelled, deadline=time.monotonic()+1)
assert delivered_without_request and not expired.ok and "unacknowledged" in expired.reason, expired
assert entry.selection_get(selection="CLIPBOARD", type="UTF8_STRING") == "queued after deadline"
cancelled = UIEvent()
results["deadline_retains_queued_literal_until_transfer"] = True

# An eager clipboard reader on another native X client cannot acknowledge the
# target application's transfer or cause the old snapshot to be restored.
manager = None
manager_value = []
literal = "manager and target 한😀"
def eager_reader(event):
    global manager
    reader_code = "import pyperclip;print(pyperclip.paste(),end='')"
    manager = subprocess.Popen([sys.executable, "-c", reader_code],
                               stdout=subprocess.PIPE, text=True)
    def consume_after_reader():
        if manager.poll() is None:
            root.after(1, consume_after_reader)
            return
        manager_value.append(manager.stdout.read())
        entry.insert("end", entry.selection_get(selection="CLIPBOARD", type="UTF8_STRING"))
    root.after_idle(consume_after_reader)
    return "break"
entry.bind("<Control-v>", eager_reader)
before = entry.get()
run(TextInput(text=literal, method="clipboard"))
assert manager_value == [literal], manager_value
assert entry.get() == before + literal
results["foreign_clipboard_reader_cannot_ack_target"] = True

# Independent copies, including identical text, are preserved by owner identity.
literal = "same text copied independently"
def concurrent_copy(event):
    root.clipboard_clear()
    root.clipboard_append(literal)
    return "break"
entry.bind("<Control-v>", concurrent_copy)
changed = adapter.execute_input(TextInput(text=literal, method="clipboard"), frame, cancelled)
assert not changed.ok, changed
assert root.selection_get(selection="CLIPBOARD") == literal
results["concurrent_same_text_owner_preserved"] = True
entry.unbind("<Control-v>")

# Refuse rich/unknown prior formats before taking ownership or sending Ctrl+V.
root.selection_handle(lambda offset, size: "owned-rich-bytes",
                      selection="CLIPBOARD", type="image/png")
root.selection_own(selection="CLIPBOARD")
before = entry.get()
unsupported = adapter.execute_input(TextInput(text="must not replace rich", method="clipboard"),
                                   frame, cancelled)
assert not unsupported.ok and "restoration unsupported" in unsupported.reason, unsupported
assert entry.get() == before
assert root.selection_get(selection="CLIPBOARD", type="image/png") == "owned-rich-bytes"
results["unsupported_prior_format_preserved"] = True
# Release only the fixture-owned selection so remaining input tests start empty.
root.selection_clear(selection="CLIPBOARD")

# Provider EOF before a possible paste restores the snapshot with actual ACK.
from clef_use.x11_clipboard import X11ClipboardTransfer
display_name = adapter.gui.platformModule._display.get_display_name()
from Xlib import X, Xatom
native_reader = display.Display()
reader_window = native_reader.screen().root.create_window(
    0, 0, 1, 1, 0, X.CopyFromParent, event_mask=X.PropertyChangeMask)
clock_atom = native_reader.intern_atom("_CLEF_FIXTURE_CLOCK")
def native_clock():
    reader_window.change_property(clock_atom, Xatom.INTEGER, 32, [1])
    native_reader.flush()
    while True:
        event = native_reader.next_event()
        if event.type == X.PropertyNotify and event.atom == clock_atom:
            return event.time
before_acquisition = native_clock()
transfer = X11ClipboardTransfer("never injected", display_name,
                                time.monotonic()+2, cancelled, lambda: None)
# Read real SelectionNotify/properties on an independent native X client.
clip_atom = native_reader.intern_atom("CLIPBOARD")
reply_atom = native_reader.intern_atom("_CLEF_FIXTURE_SELECTION_REPLY")
def native_conversion(name):
    reader_window.convert_selection(clip_atom, native_reader.intern_atom(name),
                                    reply_atom, X.CurrentTime)
    native_reader.flush()
    while True:
        event = native_reader.next_event()
        if event.type == X.SelectionNotify:
            assert event.property == reply_atom
            return reader_window.get_property(reply_atom, X.AnyPropertyType, 0, 1024, delete=True)
advertised = native_conversion("TARGETS")
assert advertised.property_type == Xatom.ATOM and advertised.format == 32
assert native_reader.intern_atom("TIMESTAMP") in advertised.value
timestamp = native_conversion("TIMESTAMP")
assert timestamp.property_type == Xatom.INTEGER and timestamp.format == 32
acquired_at = timestamp.value[0]
after_acquisition = native_clock()
assert acquired_at != X.CurrentTime
elapsed = (after_acquisition-before_acquisition) & 0xffffffff
assert (acquired_at-before_acquisition) & 0xffffffff <= elapsed
atom_pair = native_reader.intern_atom("ATOM_PAIR")
multiple_atom = native_reader.intern_atom("MULTIPLE")
pair_time, pair_text, pair_failed, pair_nested = [native_reader.intern_atom(name) for name in
    ("_CLEF_PAIR_TIME", "_CLEF_PAIR_TEXT", "_CLEF_PAIR_FAILED", "_CLEF_PAIR_NESTED")]
unsupported_target = native_reader.intern_atom("_CLEF_UNSUPPORTED_TARGET")
reader_window.change_property(pair_failed, Xatom.STRING, 8, b"must remain unchanged")
reader_window.change_property(reply_atom, atom_pair, 32, [
    native_reader.intern_atom("TIMESTAMP"), pair_time,
    native_reader.intern_atom("UTF8_STRING"), pair_text,
    unsupported_target, pair_failed, multiple_atom, pair_nested])
converted = native_conversion("MULTIPLE")
assert converted.property_type == atom_pair and converted.format == 32
assert list(converted.value) == [native_reader.intern_atom("TIMESTAMP"), pair_time,
    native_reader.intern_atom("UTF8_STRING"), pair_text, X.NONE, pair_failed, X.NONE, pair_nested]
time_value = reader_window.get_property(pair_time, X.AnyPropertyType, 0, 1, delete=True)
assert time_value.property_type == Xatom.INTEGER and time_value.value[0] == acquired_at
unchanged_value = reader_window.get_property(pair_failed, X.AnyPropertyType, 0, 100)
unchanged_bytes = unchanged_value.value
if isinstance(unchanged_bytes, str):
    unchanged_bytes = unchanged_bytes.encode("utf-8")
assert bytes(unchanged_bytes) == b"must remain unchanged"
initial = reader_window.get_property(pair_text, X.AnyPropertyType, 0, 1024, delete=True)
assert initial.property_type == native_reader.intern_atom("INCR")
native_reader.flush()
received = []
while True:
    event = native_reader.next_event()
    assert event.type != X.SelectionNotify, "MULTIPLE emitted an extra SelectionNotify"
    if (event.type != X.PropertyNotify or event.atom != pair_text
            or event.state != X.PropertyNewValue):
        continue
    part = reader_window.get_property(pair_text, X.AnyPropertyType, 0, 1024, delete=True)
    native_reader.flush()
    if part is None:
        continue
    assert part.property_type == native_reader.intern_atom("UTF8_STRING") and part.format == 8
    value = part.value.encode("utf-8") if isinstance(part.value, str) else bytes(part.value)
    if not value:
        break
    received.append(value)
assert b"".join(received) == b"never injected"
reader_window.change_property(reply_atom, atom_pair, 32, [
    native_reader.intern_atom("TIMESTAMP"), 0x7ffffffe,
    native_reader.intern_atom("TIMESTAMP"), pair_time])
invalid_destination = native_conversion("MULTIPLE")
assert list(invalid_destination.value) == [X.NONE, 0x7ffffffe,
    native_reader.intern_atom("TIMESTAMP"), pair_time]
assert reader_window.get_property(pair_time, Xatom.INTEGER, 0, 1).value[0] == acquired_at
# A request beyond the declared pair resource bound fails as one request,
# without changing successful earlier snapshot/transfer state.
reader_window.change_property(reply_atom, atom_pair, 32,
    [native_reader.intern_atom("TIMESTAMP"), pair_time]*65)
reader_window.convert_selection(clip_atom,multiple_atom,reply_atom,X.CurrentTime)
native_reader.flush()
while True:
    event = native_reader.next_event()
    if event.type == X.SelectionNotify:
        assert event.property == X.NONE
        break
results["clipboard_multiple_independent_native_conversions"] = True
reader_window.destroy()
native_reader.close()
results["clipboard_timestamp_native_property"] = True
transfer.close()
assert transfer.restored
assert entry.selection_get(selection="CLIPBOARD", type="UTF8_STRING") == ""
results["clipboard_eof_before_arm_restores_snapshot"] = True

# Force an actual new native owner between the provider's last owner read and
# acquisition. A stale reply must not allow the earlier snapshot to overwrite
# the new copy. The timestamp predates the snapshot, not just the owner check.
import tempfile
from pathlib import Path
import clef_use.x11_clipboard as clipboard_module
with tempfile.TemporaryDirectory(prefix="clef-clipboard-acquire-") as directory:
    marker = Path(directory) / "stale-owner-read"
    copied = Path(directory) / "new-owner-ready"
    root.selection_clear(selection="CLIPBOARD")
    bootstrap = r"""
import runpy,time
from pathlib import Path
from Xlib import display
original=display.Display.get_selection_owner
reads=0
def stale_owner(self, selection):
    global reads
    value=original(self, selection)
    reads+=1
    if reads==2:
        Path(MARKER).write_text('read')
        until=time.monotonic()+3
        while not Path(COPIED).exists() and time.monotonic()<until:time.sleep(.001)
        assert Path(COPIED).exists()
    return value
display.Display.get_selection_owner=stale_owner
runpy.run_module('clef_use.x11_clipboard',run_name='__main__')
""".replace("MARKER", repr(str(marker))).replace("COPIED", repr(str(copied)))
    original_popen = clipboard_module.subprocess.Popen
    def race_provider(args, **kwargs):
        return original_popen([sys.executable, "-c", bootstrap], **kwargs)
    clipboard_module.subprocess.Popen = race_provider
    def copy_after_snapshot():
        if not marker.exists():
            root.after(1, copy_after_snapshot)
            return
        # Separate native timestamp milliseconds in this controlled fixture.
        def copy_now():
            root.clipboard_clear()
            root.clipboard_append("new native owner wins acquisition race")
            root.update_idletasks()
            copied.write_text("copied")
        root.after(5, copy_now)
    root.after_idle(copy_after_snapshot)
    try:
        X11ClipboardTransfer("must not replace new copy", display_name,
                             time.monotonic()+3, cancelled, root.update)
        raise AssertionError("stale acquisition overwrote a new clipboard owner")
    except clipboard_module.ClipboardTransferError as exc:
        assert "ownership refused" in str(exc), str(exc)
    finally:
        clipboard_module.subprocess.Popen = original_popen
    assert copied.exists()
    assert root.selection_get(selection="CLIPBOARD") == "new native owner wins acquisition race"
results["snapshot_acquisition_race_preserves_new_owner"] = True

# Inject an error only after actual native ownership and server synchronization.
# The parent independently observes that ownership before allowing the failure;
# the resulting lost snapshot must be reported unacknowledged, never restored.
with tempfile.TemporaryDirectory(prefix="clef-clipboard-sync-") as directory:
    marker = Path(directory) / "native-owner"
    observed = Path(directory) / "owner-observed"
    root.selection_clear(selection="CLIPBOARD")
    fault = r"""
import json,runpy,time
from pathlib import Path
from Xlib import display
from Xlib.xobject.drawable import Window
original_set=Window.set_selection_owner
original_sync=display.Display.sync
owned=None
def mark_set(self, selection, time, onerror=None):
    global owned
    value=original_set(self,selection,time,onerror)
    owned=self.id
    return value
def fail_after_sync(self):
    value=original_sync(self)
    if owned:
        actual=self.get_selection_owner(self.intern_atom('CLIPBOARD'))
        assert actual.id==owned
        Path(MARKER).write_text(json.dumps({'owner':actual.id}))
        until=time.monotonic()+3
        while not Path(OBSERVED).exists() and time.monotonic()<until:time.sleep(.001)
        assert Path(OBSERVED).exists()
        raise RuntimeError('native query failed after actual takeover')
    return value
Window.set_selection_owner=mark_set
display.Display.sync=fail_after_sync
runpy.run_module('clef_use.x11_clipboard',run_name='__main__')
""".replace("MARKER", repr(str(marker))).replace("OBSERVED", repr(str(observed)))
    def failing_provider(args, **kwargs):
        return original_popen([sys.executable, "-c", fault], **kwargs)
    clipboard_module.subprocess.Popen = failing_provider
    seen_native_owner = []
    def observe_native_owner():
        root.update()
        if marker.exists() and not observed.exists():
            expected = json.loads(marker.read_text())["owner"]
            native = display.Display()
            assert native.get_selection_owner(native.intern_atom("CLIPBOARD")).id == expected
            native.close()
            seen_native_owner.append(expected)
            observed.write_text("observed")
    try:
        X11ClipboardTransfer("acknowledged then failed", display_name,
                             time.monotonic()+3, cancelled, observe_native_owner)
        raise AssertionError("post-takeover query fault unexpectedly succeeded")
    except clipboard_module.ClipboardTransferError as exc:
        assert seen_native_owner and "restoration unacknowledged" in str(exc), str(exc)
    finally:
        clipboard_module.subprocess.Popen = original_popen
    native = display.Display()
    assert native.get_selection_owner(native.intern_atom("CLIPBOARD")) == X.NONE
    native.close()
results["native_query_fault_after_takeover_reports_unacknowledged"] = True

# A child can own the selection before its ready status reaches the caller.
# Cancel in that gap: report unresolved restoration until native ACK, then
# verify EOF restores the previous bytes and a new owner terminates the child.
with tempfile.TemporaryDirectory(prefix="clef-clipboard-ready-") as directory:
    marker = Path(directory) / "owned-not-ready"
    resume = Path(directory) / "resume"
    root.selection_clear(selection="CLIPBOARD")
    startup = r"""
import builtins,json,runpy,time
from pathlib import Path
original=builtins.print
def delayed_ready(*args, **kwargs):
    if args and isinstance(args[0],str):
        try:message=json.loads(args[0])
        except ValueError:message={}
        if message.get('event')=='ready':
            Path(MARKER).write_text('owned')
            until=time.monotonic()+3
            while not Path(RESUME).exists() and time.monotonic()<until:time.sleep(.001)
    return original(*args, **kwargs)
builtins.print=delayed_ready
runpy.run_module('clef_use.x11_clipboard',run_name='__main__')
""".replace("MARKER", repr(str(marker))).replace("RESUME", repr(str(resume)))
    children = []
    def startup_provider(args, **kwargs):
        process = original_popen([sys.executable, "-c", startup], **kwargs)
        children.append(process)
        return process
    clipboard_module.subprocess.Popen = startup_provider
    gap_cancelled = UIEvent()
    def cancel_owned_gap():
        root.update()
        if marker.exists():
            gap_cancelled.set()
    startup_transfer = object.__new__(X11ClipboardTransfer)
    try:
        startup_transfer.__init__("never armed startup payload", display_name,
                                  time.monotonic()+.3, gap_cancelled, cancel_owned_gap)
        raise AssertionError("cancelled startup unexpectedly succeeded")
    except clipboard_module.ClipboardTransferError as exc:
        assert marker.exists() and "restoration unacknowledged" in str(exc), str(exc)
    finally:
        clipboard_module.subprocess.Popen = original_popen
        resume.write_text("resume")
    # The cancelled constructor reported restoration as unresolved. Observe the
    # provider's real later restoration ACK before asserting the old bytes.
    while startup_transfer.events.get(timeout=2)["event"] != "restored":
        pass
    assert entry.selection_get(selection="CLIPBOARD", type="UTF8_STRING") == ""
    root.clipboard_clear()
    root.clipboard_append("owner replacing restored provider")
    root.update()
    assert children[0].wait(timeout=2) == 0
    root.selection_clear(selection="CLIPBOARD")
results["owned_startup_gap_reports_unacknowledged_then_restores"] = True

# Actual injector process death after OS Ctrl+V delivery cannot make a queued
# target request consume old data. The independent provider remains available.
with tempfile.TemporaryDirectory(prefix="clef-clipboard-eof-") as directory:
    marker = Path(directory) / "delivered"
    def deferred_after_crash(event):
        marker.write_text("delivered")
        return "break"
    entry.bind("<Control-v>", deferred_after_crash)
    dying_injector = r"""
import os,time
from pathlib import Path
from threading import Event,Thread
from clef_use.backends import DesktopAction,DesktopCapture
from clef_use.input_ir import TextInput
frame=DesktopCapture().capture()
command=TextInput(text='queued after parent death',method='clipboard')
marker=Path(MARKER)
def inject():
    result=DesktopAction().execute_input(command,frame,Event())
    marker.with_suffix('.result').write_text(str(result))
Thread(target=inject,daemon=True).start()
until=time.monotonic()+4
while not marker.exists() and time.monotonic()<until:time.sleep(.001)
detail=marker.with_suffix('.result')
assert marker.exists(), detail.read_text() if detail.exists() else 'no input result'
os._exit(19)
""".replace("MARKER", repr(str(marker)))
    injector = subprocess.Popen([sys.executable, "-c", dying_injector], stdout=subprocess.DEVNULL)
    until = time.monotonic()+5
    while injector.poll() is None and time.monotonic()<until:
        root.update()
        time.sleep(.001)
    assert injector.wait(timeout=1) == 19
    assert marker.exists()
    after_death = entry.selection_get(selection="CLIPBOARD", type="UTF8_STRING")
    assert after_death == "queued after parent death"
    entry.unbind("<Control-v>")
results["injector_death_retains_queued_clipboard_literal"] = True

unchanged = entry.get()
unavailable = adapter.execute_input(TextInput(text="abc", method="unicode"), frame, cancelled)
assert not unavailable.ok and entry.get() == unchanged
results["x11_unicode_keyboard_substitution_refused"] = True

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

# Receipt construction can fail after the OS has acknowledged a real keydown.
# Cleanup must already own that physical key, even without a completed receipt.
import clef_use.schema as schema
from clef_use.input_ir import InputInterrupted
original_delivery = schema.InputDelivery
def refused_delivery(**kwargs):
    raise InputInterrupted("receipt construction refused after native acknowledgement")
try:
    schema.InputDelivery = refused_delivery
    failed_receipt = adapter.execute_input(KeyInput(key="shift", phase="down"), frame, cancelled,
                                          deadline=time.monotonic() + 1)
    assert not failed_receipt.ok and failed_receipt.delivery is None, failed_receipt
    assert not held(), "receipt failure orphaned an acknowledged physical key"
    assert not adapter.keys and not adapter.input_executor.owned
finally:
    schema.InputDelivery = original_delivery
results["receipt_failure_releases_acknowledged_key"] = True

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

# The reused query connection must still read fresh geometry and pointer state.
run(KeyInput(key="shift", phase="down"), deadline=time.monotonic() + 2)
root.geometry("610x450+30+40")
root.update()
assert cancelled.wait(.7)
assert not held()
root.geometry("600x450+30+40")
root.update()
cancelled = UIEvent()
results["resize_watchdog_release"] = True

run(KeyInput(key="shift", phase="down"), deadline=time.monotonic() + 2)
adapter.gui.mouseDown(button="right", _pause=False)
assert cancelled.wait(.7)
assert not held()
from Xlib import X
assert connection.screen().root.query_pointer().mask & X.Button3Mask
adapter.gui.mouseUp(button="right", _pause=False)
cancelled = UIEvent()
results["pointer_intervention_preserves_unowned"] = True

# A native keymap change after connection creation cannot use its old keysym cache.
letter_code = adapter.gui.platformModule.keyboardMapping["a"]
original_mapping = connection.get_keyboard_mapping(letter_code, 1)
changed_mapping = [list(original_mapping[0])]
changed_mapping[0][0] = ord("b")
before_text = entry.get()
try:
    connection.change_keyboard_mapping(letter_code, changed_mapping)
    connection.sync()
    key_refusal = adapter.execute_input(KeyInput(key="a"), frame, cancelled)
    assert not key_refusal.ok and "logical key binding changed" in key_refusal.reason, key_refusal
    root.update()
    assert entry.get() == before_text
finally:
    connection.change_keyboard_mapping(letter_code, original_mapping)
    connection.sync()
run(KeyInput(key="escape"))
results["fresh_keymap_refuses_wrong_logical_key"] = True

# Layout drift during an acknowledged held lease is detected by the independent
# watchdog, which must release that exact original physical code.
run(KeyInput(key="a", phase="down"), deadline=time.monotonic() + 2)
try:
    connection.change_keyboard_mapping(letter_code, changed_mapping)
    connection.sync()
    assert cancelled.wait(.7)
    bitmap = connection.query_keymap()
    assert not bitmap[letter_code // 8] & (1 << (letter_code % 8))
finally:
    connection.change_keyboard_mapping(letter_code, original_mapping)
    connection.sync()
cancelled = UIEvent()
results["held_binding_drift_releases_original_code"] = True

# The recovery process may initialize its own logical map after the injector's
# map changed. Its recovery authority is the acknowledged code in the protocol,
# never a reconstruction from its different logical map.
from Xlib.ext.xtest import fake_input
other_letter_code = connection.keysym_to_keycode(ord("b"))
other_letter_mapping = connection.get_keyboard_mapping(other_letter_code, 1)
recovery = None
try:
    fake_input(connection, X.KeyPress, letter_code)
    connection.sync()
    connection.change_keyboard_mapping(letter_code, other_letter_mapping)
    connection.change_keyboard_mapping(other_letter_code, original_mapping)
    connection.sync()
    recovery = subprocess.Popen([sys.executable, "-m", "clef_use.input_ir", "--guardian"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    for line in recovery.stdout:
        if line.strip() == "ready": break
    recovery.stdin.write(json.dumps({"owned": [["key", "a"]], "x11_keys": {"a": letter_code},
                                    "deadline": time.monotonic() + 1}) + "\n")
    recovery.stdin.close()
    assert recovery.wait(timeout=5) == 0
    bitmap = connection.query_keymap()
    assert not bitmap[letter_code // 8] & (1 << (letter_code % 8))
finally:
    fake_input(connection, X.KeyRelease, letter_code)
    fake_input(connection, X.KeyRelease, other_letter_code)
    connection.change_keyboard_mapping(letter_code, original_mapping)
    connection.change_keyboard_mapping(other_letter_code, other_letter_mapping)
    connection.sync()
    if recovery is not None and recovery.poll() is None:
        recovery.terminate();recovery.wait(timeout=5)
results["guardian_uses_acknowledged_code_after_layout_change"] = True

# A fork cannot send through its parent's query stream, and rejecting it must
# not close the parent's copy of that connection.
query = adapter.input_executor.x11_state
child_pid = os.fork()
if child_pid == 0:
    try:
        with query.query():
            os._exit(31)
    except RuntimeError:
        os._exit(0)
_, child_status = os.waitpid(child_pid, 0)
assert os.waitstatus_to_exitcode(child_status) == 0
run(KeyInput(key="escape"))
results["forked_query_refused_parent_usable"] = True

# Environment rebinding must refuse rather than silently inspect a different
# display while injection still points at the original PyAutoGUI connection.
before_text = entry.get()
previous_display = os.environ["DISPLAY"]
try:
    os.environ["DISPLAY"] = ":65530"
    try:
        adapter.execute_input(KeyInput(key="a"), frame, cancelled)
    except RuntimeError as error:
        assert "display changed" in str(error)
    else:
        raise AssertionError("query display rebinding was accepted")
finally:
    os.environ["DISPLAY"] = previous_display
root.update()
assert entry.get() == before_text
adapter.release()
adapter = DesktopAction()
run(KeyInput(key="escape"))
results["display_rebinding_refused"] = True

# Losing the query socket is a refusal, never cached success or an implicit
# reconnect. Recovery releases do not depend on this query connection.
adapter.input_executor.x11_state.connection.display.socket.close()
try:
    adapter.execute_input(KeyInput(key="a"), frame, cancelled)
except RuntimeError:
    pass
else:
    raise AssertionError("dead native query connection was accepted")
root.update()
assert entry.get() == before_text
adapter.release()
adapter = DesktopAction()
run(KeyInput(key="escape"))
results["query_connection_loss_refused"] = True

# Query refusal cannot prevent an explicit release of acknowledged ownership.
run(KeyInput(key="shift", phase="down"), deadline=time.monotonic() + 2)
try:
    os.environ["DISPLAY"] = ":65530"
    release_result = adapter.execute_input(KeyInput(key="shift", phase="up"), frame, cancelled)
    assert release_result.ok, release_result
    assert not held()
finally:
    os.environ["DISPLAY"] = previous_display
cancelled = UIEvent()
results["release_independent_of_query_binding"] = True

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

CLIPBOARD_PROGRAM = r"""
import json, os, select, time, tkinter as tk
from threading import Event, Thread
from Xlib import X, Xatom, display, protocol
from clef_use.x11_clipboard import X11ClipboardTransfer

root = tk.Tk()
entry = tk.Entry(root)
entry.pack()
root.update()
entry.focus_force()
root.update()
results = {}
def raw(value):
    return value.encode("utf-8") if isinstance(value, str) else bytes(value)

def previous_owner(data, name):
    ready, finished = Event(), Event()
    def serve():
        connection = display.Display()
        window = connection.screen().root.create_window(
            0,0,1,1,0,X.CopyFromParent,event_mask=X.PropertyChangeMask)
        clip, target, targets, incr = [connection.intern_atom(n) for n in
            ("CLIPBOARD", name, "TARGETS", "INCR")]
        window.set_selection_owner(clip, X.CurrentTime)
        connection.sync()
        ready.set()
        transfers = {}
        try:
            while True:
                event = connection.next_event()
                if event.type == X.SelectionClear:
                    return
                if event.type == X.SelectionRequest:
                    prop = event.property or event.target
                    if event.target == targets:
                        event.requestor.change_property(prop, Xatom.ATOM,32,[targets,target])
                    elif event.target == target:
                        if len(data) > 16384:
                            event.requestor.change_attributes(event_mask=X.PropertyChangeMask)
                            event.requestor.change_property(prop,incr,32,[len(data)])
                            transfers[(event.requestor.id,prop)] = [event.requestor,0]
                        else:
                            event.requestor.change_property(prop,target,8,data)
                    else:
                        prop = X.NONE
                    event.requestor.send_event(protocol.event.SelectionNotify(
                        time=event.time,requestor=event.requestor,selection=event.selection,
                        target=event.target,property=prop),propagate=False)
                    connection.flush()
                elif event.type == X.PropertyNotify and event.state == X.PropertyDelete:
                    key = (event.window.id,event.atom)
                    if key not in transfers:
                        continue
                    requestor, offset = transfers[key]
                    chunk = data[offset:offset+16384]
                    requestor.change_property(event.atom,target,8,chunk)
                    connection.flush()
                    transfers[key][1] += len(chunk)
                    if not chunk:
                        del transfers[key]
        finally:
            connection.close()
            finished.set()
    Thread(target=serve,daemon=True).start()
    assert ready.wait(2)
    return finished

def new_reader(name):
    connection = display.Display()
    window = connection.screen().root.create_window(
        0,0,1,1,0,X.CopyFromParent,event_mask=X.PropertyChangeMask)
    target, prop, clip = [connection.intern_atom(n) for n in
        (name,"_CLEF_RAW_RESTORED","CLIPBOARD")]
    window.convert_selection(clip,target,prop,X.CurrentTime)
    connection.flush()
    return connection, window, target, prop

def next_event(connection):
    until = time.monotonic()+3
    while not connection.pending_events():
        remaining = until-time.monotonic()
        assert remaining > 0, "native clipboard response absent"
        assert select.select([connection],[],[],remaining)[0], "native clipboard response absent"
    return connection.next_event()

def initial_reply(reader):
    connection, window, target, prop = reader
    while True:
        event = next_event(connection)
        if event.type == X.SelectionNotify:
            assert event.property == prop
            value = window.get_property(prop,X.AnyPropertyType,0,1024*1024//4,delete=False)
            assert value is not None and not value.bytes_after
            return value

def consume(reader, initial):
    connection, window, target, prop = reader
    if initial.property_type != connection.intern_atom("INCR"):
        assert initial.property_type == target and initial.format == 8
        return raw(initial.value)
    window.delete_property(prop)
    connection.flush()
    chunks = []
    while True:
        event = next_event(connection)
        if (event.type != X.PropertyNotify or event.atom != prop
                or event.state != X.PropertyNewValue):
            continue
        value = window.get_property(prop,X.AnyPropertyType,0,16384//4+1,delete=True)
        connection.flush()
        if value is None:
            continue
        assert not value.bytes_after and value.property_type == target and value.format == 8
        chunk = raw(value.value)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)

for name, data in (("UTF8_STRING","한😀 e\u0301".encode()),
                   ("UTF8_STRING",("한😀 e\u0301"*40000).encode()),
                   ("STRING",b"\xff"*(400*1024))):
    prior_finished = previous_owner(data,name)
    transfer = X11ClipboardTransfer("temporary literal",os.environ["DISPLAY"],
                                    time.monotonic()+10,Event(),root.update)
    assert prior_finished.wait(2)
    transfer.arm()
    assert entry.selection_get(selection="CLIPBOARD",type="UTF8_STRING") == "temporary literal"
    transfer.wait_consumed()
    transfer.close()
    reader = new_reader(name)
    initial = initial_reply(reader)
    restored = consume(reader,initial)
    assert restored == data, (name,len(data),len(restored))
    reader[1].destroy()
    reader[0].sync()
    reader[0].close()
    root.clipboard_clear()
    root.clipboard_append("replacement owner")
    root.update()
    assert transfer.process.wait(timeout=2) == 0
    results[f"restored_{name}_{len(data)}_exact_native_bytes"] = True
root.selection_clear(selection="CLIPBOARD")

for destroy in (False, True):
    transfer = X11ClipboardTransfer("foreign live transfer "*2000,os.environ["DISPLAY"],
                                    time.monotonic()+5,Event(),root.update)
    transfer.arm()
    reader = new_reader("UTF8_STRING")
    initial = initial_reply(reader)
    assert initial.property_type == reader[0].intern_atom("INCR")
    if destroy:
        reader[1].destroy()
        reader[0].sync()
        reader[0].close()
    root.clipboard_clear()
    root.clipboard_append("new copy must win")
    root.update()
    transfer.close()
    assert root.selection_get(selection="CLIPBOARD") == "new copy must win"
    if not destroy:
        assert consume(reader,initial) == ("foreign live transfer "*2000).encode()
        reader[1].destroy()
        reader[0].sync()
        reader[0].close()
    assert transfer.process.wait(timeout=2) == 0
    results["destroyed_reader_reaps_provider" if destroy else
            "live_transfer_finishes_after_selection_clear"] = True
    root.selection_clear(selection="CLIPBOARD")

# Freeze only this owned provider so server ordering deterministically delivers
# SelectionRequest after its requestor has already been destroyed.
import signal
for target_name in ("UTF8_STRING", "MULTIPLE"):
    root.update()
    previous = "previous native snapshot 한😀".encode()
    prior_finished = previous_owner(previous,"UTF8_STRING")
    transfer = X11ClipboardTransfer("owned offered literal",os.environ["DISPLAY"],
                                    time.monotonic()+5,Event(),root.update)
    assert prior_finished.wait(2)
    transfer.arm()
    os.kill(transfer.process.pid,signal.SIGSTOP)
    stopped_pid, status = os.waitpid(transfer.process.pid,os.WUNTRACED)
    assert stopped_pid == transfer.process.pid and os.WIFSTOPPED(status)
    try:
        native = display.Display()
        window = native.screen().root.create_window(0,0,1,1,0,X.CopyFromParent)
        clip, target, prop = [native.intern_atom(name) for name in
            ("CLIPBOARD",target_name,"_CLEF_DESTROYED_REQUEST")]
        if target_name == "MULTIPLE":
            window.change_property(prop,native.intern_atom("ATOM_PAIR"),32,
                [native.intern_atom("TIMESTAMP"),native.intern_atom("_CLEF_STALE_RESULT")])
        window.convert_selection(clip,target,prop,X.CurrentTime)
        window.destroy()
        native.sync()
        native.close()
    finally:
        os.kill(transfer.process.pid,signal.SIGCONT)
    if target_name == "MULTIPLE":
        # A valid request queued behind the stale one proves the provider
        # survived it. Then verify the prior snapshot still restores exactly.
        offered_value = entry.selection_get(selection="CLIPBOARD",type="UTF8_STRING")
        assert offered_value == "owned offered literal"
        transfer.wait_consumed()
        reader = new_reader("UTF8_STRING")
        assert consume(reader,initial_reply(reader)) == previous
        reader[1].destroy()
        reader[0].sync()
        reader[0].close()
    root.clipboard_clear()
    root.clipboard_append("new copy after stale request")
    root.update()
    transfer.close()
    assert root.selection_get(selection="CLIPBOARD") == "new copy after stale request"
    assert transfer.process.wait(timeout=2) == 0
    results[f"destroyed_before_{target_name}_request_preserves_lifecycle"] = True
    root.selection_clear(selection="CLIPBOARD")

# Cancel only after the real prior owner receives TARGETS and deliberately
# withholds its reply. Cleanup must not wait for the three-second input lease.
stop_bound_seconds = .25
root.update()
unresponsive = display.Display()
unresponsive_window = unresponsive.screen().root.create_window(0,0,1,1,0,X.CopyFromParent)
clipboard_atom = unresponsive.intern_atom("CLIPBOARD")
unresponsive_window.set_selection_owner(clipboard_atom,X.CurrentTime)
unresponsive.sync()
assert unresponsive.get_selection_owner(clipboard_atom).id == unresponsive_window.id
cancelled = Event()
cancelled_at = []
keys_before = bytes(unresponsive.query_keymap())
def cancel_pending_snapshot():
    root.update()
    while unresponsive.pending_events():
        event = unresponsive.next_event()
        if event.type == X.SelectionRequest:
            assert event.target == unresponsive.intern_atom("TARGETS")
            cancelled_at.append(time.monotonic())
            cancelled.set()
transfer = object.__new__(X11ClipboardTransfer)
try:
    transfer.__init__("must never take ownership",os.environ["DISPLAY"],
                      time.monotonic()+3,cancelled,cancel_pending_snapshot)
    raise AssertionError("cancelled unresponsive snapshot succeeded")
except RuntimeError as exc:
    assert cancelled_at and "unacknowledged" not in str(exc), str(exc)
elapsed = time.monotonic()-cancelled_at[0]
assert elapsed < stop_bound_seconds, elapsed
assert not transfer.offered and not transfer.unresolved
assert unresponsive.get_selection_owner(clipboard_atom).id == unresponsive_window.id
assert bytes(unresponsive.query_keymap()) == keys_before
assert transfer.process.wait(timeout=1) == 0
results["pending_snapshot_cancel_native_owner_preserved"] = True
results["pending_snapshot_cancel_seconds"] = elapsed
results["pending_snapshot_cancel_predeclared_bound_seconds"] = stop_bound_seconds
unresponsive_window.destroy()
unresponsive.close()
root.destroy()
print(json.dumps(results))
"""


PRETRIGGER_CANCEL_PROGRAM = r"""
import json, os, signal, threading, time, tkinter as tk
import pyperclip
from Xlib import X, display
from clef_use.x11_clipboard import ClipboardTransferError, X11ClipboardTransfer

root = tk.Tk()
root.overrideredirect(True)
root.geometry("400x300+0+0")
root.update()
connection = display.Display()
connection.set_input_focus(root.winfo_id(), X.RevertToParent, X.CurrentTime)
connection.sync()
clip = connection.intern_atom("CLIPBOARD")
key_events = []
root.bind("<KeyPress>", lambda event: key_events.append(event.keysym))
results = {}
transfers = []
previous = "previous supported text 한😀"
literal = "aborted owned literal"

def create_transfer(*, fail_arm=None):
    pyperclip.copy(previous)
    root.update()
    cancelled = threading.Event()
    stage = ["setup"]
    current = []
    def check():
        root.update()
        if stage[0] != "arming" or fail_arm is None:
            return
        transfer = current[0]
        with transfer.events.mutex:
            acknowledged = any(item.get("event") == "armed"
                               for item in transfer.events.queue)
        if acknowledged:
            if fail_arm == "cancel":
                cancelled.set()
            else:
                # Wait for this actual input deadline after a native armed ACK;
                # recovery uses its own explicit, bounded deadline below.
                cancelled.wait(max(0, transfer.deadline - time.monotonic()))
    transfer = X11ClipboardTransfer(literal, connection.get_display_name(),
                                    time.monotonic()+.5, cancelled, check)
    transfers.append(transfer)
    current.append(transfer)
    stage[0] = "arming"
    return transfer, cancelled

def replace_and_reap(transfer):
    root.clipboard_clear()
    root.clipboard_append("owned cleanup selection")
    root.update()
    transfer.close()
    transfer.process.wait(timeout=3)

try:
    for failure in ("cancel", "deadline"):
        transfer, cancelled = create_transfer(fail_arm=failure)
        try:
            transfer.arm()
        except ClipboardTransferError as error:
            assert "cancelled or deadline expired" in str(error), error
        else:
            raise AssertionError("native armed receipt must precede pre-trigger failure")
        transfer.cancel_before_trigger(deadline=time.monotonic()+.5)
        assert transfer.restored and not transfer.armed and not transfer.unresolved
        assert transfer.closed
        assert root.selection_get(selection="CLIPBOARD", type="UTF8_STRING") == previous
        results[f"armed_{failure}_before_trigger_restores_exact_snapshot"] = True
        replace_and_reap(transfer)

    for copied in ("independent user copy", literal):
        transfer, cancelled = create_transfer()
        transfer.arm()
        cancelled.set()
        root.clipboard_clear()
        root.clipboard_append(copied)
        root.update()
        user_owner = connection.get_selection_owner(clip).id
        transfer.cancel_before_trigger(deadline=time.monotonic()+.5)
        assert transfer.owner_changed and not transfer.restored
        assert not transfer.armed and not transfer.unresolved
        assert connection.get_selection_owner(clip).id == user_owner
        assert root.selection_get(selection="CLIPBOARD", type="UTF8_STRING") == copied
        copy_kind = "identical" if copied == literal else "distinct"
        results[f"concurrent_{copy_kind}_owner_preserved"] = True
        transfer.process.wait(timeout=3)

    # A genuine stopped provider cannot acknowledge recovery. Do not report
    # success from sending a command or EOF; a later native ACK is separate.
    transfer, cancelled = create_transfer()
    transfer.arm()
    cancelled.set()
    provider_owner = connection.get_selection_owner(clip).id
    os.kill(transfer.process.pid, signal.SIGSTOP)
    stopped_pid, stopped_status = os.waitpid(transfer.process.pid, os.WUNTRACED)
    assert stopped_pid == transfer.process.pid and os.WIFSTOPPED(stopped_status)
    try:
        try:
            transfer.cancel_before_trigger(deadline=time.monotonic()+.05)
        except ClipboardTransferError as error:
            assert "acknowledgement deadline expired" in str(error), error
        else:
            raise AssertionError("stopped native provider falsely acknowledged restoration")
        assert transfer.armed and transfer.unresolved and not transfer.restored
        assert connection.get_selection_owner(clip).id == provider_owner
    finally:
        os.kill(transfer.process.pid, signal.SIGCONT)
    end = time.monotonic()+2
    while True:
        event = transfer.events.get(timeout=max(.001, end-time.monotonic()))["event"]
        if event == "restored":
            break
        assert time.monotonic() < end, "late native restoration ACK absent"
    assert root.selection_get(selection="CLIPBOARD", type="UTF8_STRING") == previous
    results["missing_native_recovery_ack_stays_unresolved"] = True
    replace_and_reap(transfer)

    # Without positive knowledge that no trigger was attempted, ordinary close
    # must retain the offered literal even after cancellation/parent pipe EOF.
    transfer, cancelled = create_transfer()
    transfer.arm()
    cancelled.set()
    transfer.close()
    assert transfer.unresolved and transfer.armed and not transfer.restored
    assert root.selection_get(selection="CLIPBOARD", type="UTF8_STRING") == literal
    end = time.monotonic()+2
    while True:
        event = transfer.events.get(timeout=max(.001, end-time.monotonic()))["event"]
        if event == "consumed":
            break
        assert time.monotonic() < end, "actual native consumption ACK absent"
    assert root.selection_get(selection="CLIPBOARD", type="UTF8_STRING") == previous
    results["unknown_possible_trigger_retains_literal_until_native_consumption"] = True
    replace_and_reap(transfer)
    assert not key_events, key_events
    results["direct_transfer_paste_key_attempts"] = 0

    # Exercise the canonical caller with real arm acknowledgement and native
    # Ctrl delivery, then cancel before it can attempt the paste trigger.
    import clef_use.x11_clipboard as clipboard_module
    from clef_use.backends import DesktopAction, DesktopCapture
    from clef_use.input_ir import InputInterrupted, TextInput
    original_transfer = clipboard_module.X11ClipboardTransfer
    adapter = DesktopAction()
    root.focus_force()
    root.update()
    def owned_frame():
        assert root.focus_get() == root, "owned Tk keyboard event target unknown"
        focused = connection.get_input_focus().focus
        ancestry = []
        while hasattr(focused, "id") and focused.id != connection.screen().root.id:
            ancestry.append(focused.id)
            focused = focused.query_tree().parent
        assert root.winfo_id() in ancestry, "native keyboard focus outside owned Tk client"
        # The real clipboard provider independently verifies this focus's
        # X-Resource client identity before acquiring the selection.
        return DesktopCapture().capture()
    try:
        for arm_error in (False, True):
            class CancelAfterNativeArm(original_transfer):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    transfers.append(self)
                def arm(self):
                    super().arm()
                    self.cancelled.set()
                    if arm_error:
                        raise ClipboardTransferError("controlled failure after native armed ACK")
            clipboard_module.X11ClipboardTransfer = CancelAfterNativeArm
            pyperclip.copy(previous)
            key_events.clear()
            cancelled = threading.Event()
            result = adapter.execute_input(TextInput(text=literal, method="clipboard"),
                                           owned_frame(), cancelled)
            root.update()
            transfer = transfers[-1]
            assert not result.ok and "unresolved" not in result.reason, result
            assert transfer.restored and not transfer.unresolved and not transfer.armed
            assert root.selection_get(selection="CLIPBOARD", type="UTF8_STRING") == previous
            assert "Control_L" in key_events, key_events
            assert not any(k.lower() == "v" for k in key_events), key_events
            assert not adapter.keys and not adapter.input_executor.owned
            assert not any(connection.query_keymap()), "native Ctrl was left held"
            failure_kind = "arm_error" if arm_error else "cancel"
            results[f"canonical_caller_{failure_kind}_before_v_restores"] = True
            results[f"canonical_caller_{failure_kind}_v_key_events"] = sum(
                key.lower() == "v" for key in key_events)
            replace_and_reap(transfer)

        # An actual acknowledged V request followed by a controlled OS error
        # must not use the known-pretrigger restoration authority.
        class RecordNativeTransfer(original_transfer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                transfers.append(self)
        clipboard_module.X11ClipboardTransfer = RecordNativeTransfer
        original_down = adapter.input_executor._key_down
        def fail_after_native_v(key, frame, acknowledged=None):
            original_down(key, frame, acknowledged)
            if key == "v":
                raise InputInterrupted("controlled OS error after acknowledged V")
        adapter.input_executor._key_down = fail_after_native_v
        pyperclip.copy(previous)
        key_events.clear()
        try:
            result = adapter.execute_input(TextInput(text=literal, method="clipboard"),
                                           owned_frame(), threading.Event())
        finally:
            adapter.input_executor._key_down = original_down
        root.update()
        transfer = transfers[-1]
        assert not result.ok and "unresolved" in result.reason, result
        assert transfer.armed and transfer.unresolved and not transfer.restored
        assert any(k.lower() == "v" for k in key_events), key_events
        results["canonical_caller_possible_v_error_v_key_events"] = sum(
            key.lower() == "v" for key in key_events)
        assert not adapter.keys and not adapter.input_executor.owned
        assert not any(connection.query_keymap()), "native paste keys were left held"
        assert root.selection_get(selection="CLIPBOARD", type="UTF8_STRING") == literal
        end = time.monotonic()+2
        while True:
            event = transfer.events.get(timeout=max(.001, end-time.monotonic()))["event"]
            if event == "consumed":
                break
            assert time.monotonic() < end, "actual native consumption ACK absent"
        assert root.selection_get(selection="CLIPBOARD", type="UTF8_STRING") == previous
        results["canonical_caller_possible_v_error_retains_until_native_consumption"] = True
        replace_and_reap(transfer)
    finally:
        clipboard_module.X11ClipboardTransfer = original_transfer
        adapter.release()
        if adapter.input_executor is not None and adapter.input_executor.guardian is not None:
            guardian = adapter.input_executor.guardian
            guardian.stdin.close()
            assert guardian.wait(timeout=3) == 0
            results["canonical_caller_guardian_reaped"] = True

    results["all_private_providers_reaped"] = all(t.process.poll() is not None for t in transfers)
    assert results["all_private_providers_reaped"]
    print(json.dumps(results))
finally:
    root.clipboard_clear()
    root.clipboard_append("owned final cleanup selection")
    root.update()
    for transfer in transfers:
        transfer.close()
        transfer.process.wait(timeout=3)
    connection.close()
    root.destroy()
"""


@pytest.mark.skipif(
    not shutil.which("Xvfb") or not shutil.which("xsel"),
    reason="native X11 fixture requires Xvfb and xsel",
)
@pytest.mark.parametrize(
    "program",
    [NATIVE_PROGRAM, CLIPBOARD_PROGRAM, PRETRIGGER_CANCEL_PROGRAM],
    ids=["input", "clipboard", "pretrigger-cancel"],
)
def test_native_widget_effects_and_independent_recovery(tmp_path, program):
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
            [sys.executable, "-c", program],
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=Path(__file__).resolve().parents[1],
        )
        assert result.returncode == 0, result.stdout + result.stderr
        evidence = json.loads(result.stdout.strip().splitlines()[-1])
        report = tmp_path / "native-input-evidence.json"
        report.write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps(evidence))
        print(f"Raw evidence: {report}")
    finally:
        process.terminate()
        process.wait(timeout=5)
