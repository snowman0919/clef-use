"""Foreground restoration shared by owned Windows validation fixtures."""

import ctypes
import time


def restore_foreground(root, gui, previous_target, owned_target):
    if gui.foreground() != owned_target:
        raise RuntimeError("owned foreground changed; restoration refused")
    gui.user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    admitted = gui.user.SetForegroundWindow(previous_target)
    result = {"foreground_immediate": gui.foreground() == previous_target}
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
    result["foreground_queue_synchronized"] = bool(acknowledged)
    result["foreground_before_own_ui_pump"] = gui.foreground() == previous_target
    # The target's WM_NULL does not consume our own queued deactivation events.
    # Observe asynchronous activation while consuming our queued deactivation.
    # Never repeat the foreground request or overwrite intervening ownership.
    deadline = time.monotonic() + 1.0
    observations = []
    while True:
        root.update()
        current = gui.foreground()
        observations.append(
            "previous"
            if current == previous_target
            else "owned"
            if current == owned_target
            else "none"
            if not current
            else "other"
        )
        if current == previous_target or current not in (None, 0, owned_target):
            break
        if time.monotonic() >= deadline:
            break
        time.sleep(0.01)
    result["foreground_completion_observations"] = observations
    result["foreground_restored"] = bool(acknowledged and gui.foreground() == previous_target)
    return result
