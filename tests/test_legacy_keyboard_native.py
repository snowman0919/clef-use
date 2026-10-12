"""Legacy keyboard input must honor live X11 bindings and physical ownership."""

import shutil
import sys

import pytest
import test_input_button_mapping_native as native_fixture

PROGRAM = r"""
import json, sys, threading, tkinter as tk
from Xlib import X, display
from Xlib.ext import xtest
import pyautogui
from clef_use.backends import DesktopAction, DesktopCapture
from clef_use.schema import ActionCandidate, Observation

root=tk.Tk();root.overrideredirect(True);root.geometry('800x600+0+0')
entry=tk.Entry(root);entry.pack(fill='both',expand=True)
events=[]
entry.bind('<KeyPress>',lambda e:events.append((e.keysym,e.char,e.keycode)))
root.update();entry.focus_force();root.update()
connection=display.Display()
connection.set_input_focus(root.winfo_id(),X.RevertToParent,X.CurrentTime)
connection.sync();root.update()
assert root.focus_get()==entry
focus=connection.get_input_focus().focus
ancestry=[]
while getattr(focus,'id',0):
    ancestry.append(focus.id)
    parent=focus.query_tree().parent
    if not getattr(parent,'id',0) or parent.id==focus.id:break
    focus=parent
assert root.winfo_id() in ancestry
pyautogui.moveTo(400,300)
frame=DesktopCapture().capture();assert frame.foreground_window is not None
observation=Observation('owned',frame,())
adapter=DesktopAction();cancelled=threading.Event();case=sys.argv[1]
operation,value,key={
    'type':('type','a','a'),
    'press':('press','enter','enter'),
    'hotkey':('hotkey','ctrl+a','a'),
    'shift':('type','A','A'),
    'release':('type','a','a'),
    'human':('type','a','a'),
    'human_shift':('type','a','a'),
    'human_ctrl':('type','a','a'),
}[case]
code=pyautogui.platformModule.keyboardMapping[key]
original=connection.get_keyboard_mapping(code,1)
original_cached=pyautogui.platformModule.keyboardMapping[key]
action=ActionCandidate(id='legacy',operation=operation,value=value,
    description='Owned input',observation_id=observation.id)
report={'case':case}
original_fake=xtest.fake_input
held_code=pyautogui.platformModule.keyboardMapping[{'human_shift':'shift','human_ctrl':'ctrl'}.get(case,key)]
try:
    if case in {'type','press','hotkey','shift'}:
        result=adapter.execute(action,observation,cancelled);root.update()
        assert result.ok,result
        expected='Return' if case=='press' else key
        assert any(event[0]==expected for event in events),events
        if case in {'type','shift'}:assert entry.get()==value,entry.get()
        report['normal_events']=list(events)
        events.clear();entry.delete(0,'end')
        changed=[list(original[0])]
        changed[0][0]=0xff1b if case=='press' else ord('b')
        changed[0][1]=0xff1b if case=='press' else ord('B')
        connection.change_keyboard_mapping(code,changed);connection.sync();root.update()
        try:
            result=adapter.execute(action,observation,cancelled)
        except RuntimeError as error:
            report['refusal']=str(error)
        else:
            assert not result.ok,('remapped input accepted',result)
        root.update()
        assert events==[] and entry.get()=='',(events,entry.get())
        report['remapped_events']=list(events)
    elif case=='release':
        def remap_after_ack(display,event_type,detail=0,*args,**kwargs):
            result=original_fake(display,event_type,detail,*args,**kwargs)
            if event_type==X.KeyPress and detail==code:
                display.sync()
                # Recovery must not reconstruct its release from either map.
                pyautogui.platformModule.keyboardMapping[key]=pyautogui.platformModule.keyboardMapping['b']
                changed=[list(original[0])];changed[0][0]=ord('b')
                connection.change_keyboard_mapping(code,changed);connection.sync()
            return result
        xtest.fake_input=remap_after_ack
        result=adapter.execute(action,observation,cancelled);root.update()
        assert result.ok,result
    else:
        original_fake(connection,X.KeyPress,held_code);connection.sync();root.update();events.clear()
        try:
            result=adapter.execute(action,observation,cancelled)
        except RuntimeError as error:
            report['refusal']=str(error)
        else:
            root.update()
            assert not result.ok,('external hold accepted',result,entry.get(),events)
        bitmap=connection.query_keymap()
        assert bitmap[held_code//8]&(1<<(held_code%8)),'Human key was released'
        root.update();assert events==[],events
        original_fake(connection,X.KeyRelease,held_code);connection.sync()
    assert not any(connection.query_keymap()),'Acknowledged physical key remains held'
    assert not adapter.keys,adapter.keys
    report['physical_keys_released']=True
finally:
    xtest.fake_input=original_fake
    adapter.release()
    original_fake(connection,X.KeyRelease,code)
    original_fake(connection,X.KeyRelease,held_code)
    connection.change_keyboard_mapping(code,original);connection.sync()
    pyautogui.platformModule.keyboardMapping[key]=original_cached
    connection.close();root.destroy()
print(json.dumps(report))
"""


@pytest.mark.skipif(
    sys.platform != "linux" or not shutil.which("Xvfb") or not shutil.which("xauth"),
    reason="Authenticated disposable X11 server required",
)
@pytest.mark.parametrize(
    "case", ["type", "press", "hotkey", "shift", "release", "human", "human_shift", "human_ctrl"]
)
def test_legacy_keyboard_native_binding_and_ownership(tmp_path, monkeypatch, case):
    monkeypatch.setattr(native_fixture, "PROGRAM", PROGRAM)
    native_fixture.test_native_logical_buttons_and_owned_release(tmp_path, case)
