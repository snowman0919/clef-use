"""Foreground restoration shared by owned Windows validation fixtures."""

import ctypes
import time


def widget_point(gui, widget, frame, x, y, owned_target):
    """Map owned widget coordinates to captured physical desktop pixels."""
    from clef_use.windows_input import Point

    width, height = widget.winfo_width(), widget.winfo_height()
    if width <= 0 or height <= 0 or not (0 <= x < width and 0 <= y < height):
        raise ValueError("input point is outside the owned widget")
    gui.user.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    gui.user.GetAncestor.restype = ctypes.c_void_p
    gui.user.WindowFromPoint.argtypes = [Point]
    gui.user.WindowFromPoint.restype = ctypes.c_void_p
    with gui.physical_coordinates():
        left, top, right, bottom = gui.window_rect(widget.winfo_id())
        pixel = Point(
            round(left + x * (right - left) / width), round(top + y * (bottom - top) / height)
        )
        actual = gui.user.WindowFromPoint(pixel)
        if not actual or gui.user.GetAncestor(actual, 2) != owned_target:
            raise RuntimeError("physical input point is outside the owned receiver")
    return (
        (pixel.x - frame.origin[0]) / frame.image.width,
        (pixel.y - frame.origin[1]) / frame.image.height,
    )


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
