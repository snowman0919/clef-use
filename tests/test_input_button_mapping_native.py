"""Native logical mouse buttons under a non-default X server pointer map."""

import json
import os
import secrets
import select
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROGRAM = r'''
import ctypes, json, os, select, subprocess, sys, threading, time, tkinter as tk
from Xlib import X, display
from clef_use.backends import DesktopAction, DesktopCapture
from clef_use.input_ir import GestureInput, InputInterrupted, PointerInput, WheelInput
from clef_use.schema import ActionCandidate, BoundingBox, Observation, UIObject

root=tk.Tk(); root.overrideredirect(True); root.geometry('800x600+0+0')
events=[]
releases=[]
wheel_events=[]
root.bind('<ButtonPress>',lambda e:events.append((e.num,e.state)))
root.bind('<ButtonRelease>',lambda e:releases.append((e.num,e.state,e.x_root,e.y_root)))
root.bind('<MouseWheel>',lambda e:wheel_events.append((e.delta,e.state)))
root.update()
connection=display.Display()
connection.set_input_focus(root.winfo_id(),X.RevertToParent,X.CurrentTime)
connection.sync(); root.update()
original=list(connection.get_pointer_mapping())
mapping=list(original)
mapping[:7]=[3,2,1,5,4,7,6]
assert connection.set_pointer_mapping(mapping)==X.MappingSuccess
connection.sync()
adapter=DesktopAction(); cancelled=threading.Event()
frame=DesktopCapture().capture()
assert frame.foreground_window is not None
case=sys.argv[1]
try:
    if case=='typed':
        for button,number in [('left',1),('middle',2),('right',3)]:
            before=len(events)
            result=adapter.execute_input(PointerInput(button=button,point=(.5,.5)),frame,cancelled)
            root.update()
            assert [e[0] for e in events[before:]]==[number], (button,result,events)
            assert result.ok, result
        assert connection.set_pointer_mapping(original)==X.MappingSuccess
        connection.sync()
        before=len(events)
        result=adapter.execute_input(PointerInput(button='left',point=(.5,.5)),frame,cancelled)
        root.update()
        assert result.ok and events[before:]==[(1,0)], (result,events)
    elif case=='legacy':
        target=UIObject(id='target',bbox=BoundingBox(x1=.4,y1=.4,x2=.6,y2=.6),actions={'click'})
        observation=Observation('owned',frame,(target,))
        action=ActionCandidate(id='click',operation='click',description='Owned click',
                               target='target',observation_id='owned')
        result=adapter.execute(action,observation,cancelled)
        root.update()
        assert [e[0] for e in events]==[1], (result,events)
        assert result.ok
    elif case=='legacy_scroll':
        target=UIObject(id='target',bbox=BoundingBox(x1=.4,y1=.4,x2=.6,y2=.6),actions={'scroll'})
        observation=Observation('owned',frame,(target,))
        action=ActionCandidate(id='scroll',operation='scroll',description='Owned scroll',
                               target='target',value='up',observation_id='owned')
        result=adapter.execute(action,observation,cancelled)
        root.update()
        assert wheel_events==[(120,0)]*3, (result,wheel_events)
        assert result.ok
    elif case=='gesture':
        result=adapter.execute_input(GestureInput(button='right',modifiers=('ctrl',),
            points=((.4,.5),(.6,.5)),surface=(.1,.1,.9,.9),duration=.04),frame,cancelled)
        root.update()
        assert result.ok and events==[(3,X.ControlMask)], (result,events)
        assert releases==[(3,X.ControlMask|X.Button3Mask,480,300)], releases
        assert not adapter.input_executor.owned
    elif case=='disabled':
        disabled=list(mapping);disabled[2]=0
        assert connection.set_pointer_mapping(disabled)==X.MappingSuccess
        connection.sync()
        try:
            adapter.execute_input(PointerInput(button='left',point=(.5,.5)),frame,cancelled)
        except RuntimeError as error:
            assert 'logical mouse button unavailable' in str(error), error
        else:
            raise AssertionError('disabled logical button must refuse')
        root.update()
        assert events==[] and releases==[] and not adapter.input_executor.owned
    elif case=='human':
        from Xlib.ext.xtest import fake_input
        # Physical 1 is now logical right. This input is outside the lease.
        fake_input(connection,X.ButtonPress,1);connection.sync();root.update()
        try:
            try:
                adapter.execute_input(PointerInput(button='left',point=(.5,.5)),frame,cancelled)
            except InputInterrupted as error:
                assert 'unowned input held' in str(error), error
            else:
                raise AssertionError('human-held mapped button must refuse')
            root.update()
            assert events==[(3,0)], events
            assert connection.screen().root.query_pointer().mask & X.Button3Mask
        finally:
            fake_input(connection,X.ButtonRelease,1);connection.sync();root.update()
    elif case=='wheel':
        # Tk 8.6 translates native X11 wheel buttons into MouseWheel events.
        # Horizontal events carry Shift; positive amounts mean up/right.
        for axis,amount,expected in [('vertical',1,(120,0)),('vertical',-1,(-120,0)),
                                      ('horizontal',1,(-120,1)),('horizontal',-1,(120,1))]:
            before=len(wheel_events)
            result=adapter.execute_input(WheelInput(axis=axis,amount=amount,point=(.5,.5)),frame,cancelled)
            root.update()
            assert wheel_events[before:]==[expected], (axis,result,wheel_events)
            assert result.ok
    elif case=='abort':
        result=adapter.execute_input(PointerInput(phase='down',button='left',point=(.5,.5)),frame,cancelled,deadline=time.monotonic()+2)
        root.update()
        assert result.ok and events[-1][0]==1, (result,events)
        assert connection.screen().root.query_pointer().mask & X.Button1Mask
        # Remapping an actually held physical button is natively refused.
        assert connection.set_pointer_mapping(original)==X.MappingBusy
        changed=list(mapping);changed[3],changed[4]=changed[4],changed[3]
        assert connection.set_pointer_mapping(changed)==X.MappingSuccess
        connection.sync()
        cancelled.set()
        end=time.monotonic()+1
        while connection.screen().root.query_pointer().mask & X.Button1Mask:
            assert time.monotonic()<end, 'independent abort did not release logical left'
            time.sleep(.005)
        assert not adapter.input_executor.owned
    elif case=='crash':
        # Adopt the actual executor's guardian after its parent dies so this
        # isolated fixture can prove recovery and reap every owned process.
        assert ctypes.CDLL(None).prctl(36,1,0,0,0)==0
        child_program="""
import json,sys,threading,time
from clef_use.backends import DesktopAction,DesktopCapture
from clef_use.input_ir import PointerInput
adapter=DesktopAction()
result=adapter.execute_input(PointerInput(phase='down',button='left',point=(.5,.5)),
                             DesktopCapture().capture(),threading.Event(),deadline=time.monotonic()+5)
print(json.dumps({'ok':result.ok,'guardian':adapter.input_executor.guardian.pid}),flush=True)
sys.stdin.read(1)
"""
        child=subprocess.Popen([sys.executable,'-c',child_program],stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,text=True)
        guardian_pid=None
        try:
            assert select.select([child.stdout],[],[],5)[0], 'executor ACK absent'
            receipt=json.loads(child.stdout.readline());guardian_pid=receipt['guardian']
            root.update()
            assert receipt['ok'] and events[-1][0]==1, (receipt,events)
            assert connection.screen().root.query_pointer().mask & X.Button1Mask
            child.kill();child.wait(timeout=3)
            end=time.monotonic()+2
            while connection.screen().root.query_pointer().mask & X.Button1Mask:
                assert time.monotonic()<end, 'guardian EOF did not release physical button'
                time.sleep(.005)
            while True:
                reaped,status=os.waitpid(guardian_pid,os.WNOHANG)
                if reaped:
                    assert os.waitstatus_to_exitcode(status)==0
                    guardian_pid=None
                    break
                assert time.monotonic()<end, 'guardian did not exit after EOF recovery'
                time.sleep(.005)
        finally:
            if child.poll() is None:
                child.kill();child.wait(timeout=3)
            if guardian_pid is not None:
                os.kill(guardian_pid,15);os.waitpid(guardian_pid,0)
    mask=connection.screen().root.query_pointer().mask
    assert mask==0, mask
    print(json.dumps({'case':case,'native_events':events,'wheel_events':wheel_events,
                      'native_releases':releases,'pointer_mask':mask}))
finally:
    adapter.release()
    if adapter.input_executor is not None and adapter.input_executor.guardian is not None:
        guardian=adapter.input_executor.guardian
        guardian.stdin.close();guardian.wait(timeout=3)
    assert connection.set_pointer_mapping(original)==X.MappingSuccess
    connection.sync();connection.close();root.destroy()
'''


@pytest.mark.skipif(
    sys.platform != "linux" or not shutil.which("Xvfb") or not shutil.which("xauth"),
    reason="Authenticated disposable X11 server required",
)
@pytest.mark.parametrize(
    "case",
    ["typed", "legacy", "legacy_scroll", "wheel", "gesture", "disabled", "human", "abort", "crash"],
)
def test_native_logical_buttons_and_owned_release(tmp_path, case):
    cookie = secrets.token_hex(16)
    authority = tmp_path / "Xauthority"
    subprocess.run(
        ["xauth", "-f", str(authority), "add", ":65535", "MIT-MAGIC-COOKIE-1", cookie],
        check=True,
        capture_output=True,
    )
    authority.chmod(0o600)
    read_fd, write_fd = os.pipe()
    server = subprocess.Popen(
        [
            "Xvfb",
            "-displayfd",
            str(write_fd),
            "-screen",
            "0",
            "800x600x24",
            "-nolisten",
            "tcp",
            "-auth",
            str(authority),
            "-noreset",
        ],
        pass_fds=(write_fd,),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    os.close(write_fd)
    number = None
    try:
        assert select.select([read_fd], [], [], 5)[0], "Xvfb startup absent"
        with os.fdopen(read_fd) as stream:
            number = stream.readline().strip()
        assert number.isdigit()
        subprocess.run(
            ["xauth", "-f", str(authority), "add", f":{number}", "MIT-MAGIC-COOKIE-1", cookie],
            check=True,
            capture_output=True,
        )
        environment = dict(os.environ, DISPLAY=f":{number}", XAUTHORITY=str(authority))
        result = subprocess.run(
            [sys.executable, "-c", PROGRAM, case],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=Path(__file__).resolve().parents[1],
        )
        assert result.returncode == 0, result.stdout + result.stderr
        evidence = json.loads(result.stdout)
        (tmp_path / "native-button-evidence.json").write_text(json.dumps(evidence))
    finally:
        server.terminate()
        server.wait(timeout=5)
        assert number is None or not Path(f"/tmp/.X11-unix/X{number}").exists()
