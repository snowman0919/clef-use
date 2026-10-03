"""Checked Win32 input for the current interactive desktop."""

from __future__ import annotations

import ctypes
import os
import sys
from contextlib import contextmanager

U16 = ctypes.c_uint16
U32 = ctypes.c_uint32
I32 = ctypes.c_int32
PTR = ctypes.c_size_t


class KeyboardInput(ctypes.Structure):
    _fields_ = [("vk", U16), ("scan", U16), ("flags", U32), ("time", U32), ("extra", PTR)]


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("x", I32),
        ("y", I32),
        ("data", U32),
        ("flags", U32),
        ("time", U32),
        ("extra", PTR),
    ]


class HardwareInput(ctypes.Structure):
    _fields_ = [("message", U32), ("low", U16), ("high", U16)]


class InputData(ctypes.Union):
    _fields_ = [("keyboard", KeyboardInput), ("mouse", MouseInput), ("hardware", HardwareInput)]


class Input(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = [("type", U32), ("data", InputData)]


class Point(ctypes.Structure):
    _fields_ = [("x", I32), ("y", I32)]


class WindowsInput:
    FAILSAFE = True

    def __init__(self, user32=None, kernel32=None):
        self.unicode_units: set[int] = set()
        if user32 is not None:
            self.user, self.kernel = user32, kernel32
            return
        if sys.platform != "win32":
            raise RuntimeError("Win32 input requires Windows")
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "SendInput": ([U32, ctypes.POINTER(Input), ctypes.c_int], U32),
            "GetForegroundWindow": ([], ctypes.c_void_p),
            "SetCursorPos": ([ctypes.c_int, ctypes.c_int], ctypes.c_int),
            "GetCursorPos": ([ctypes.POINTER(Point)], ctypes.c_int),
            "GetSystemMetrics": ([ctypes.c_int], ctypes.c_int),
            "MapVirtualKeyW": ([U32, U32], U32),
            "OpenInputDesktop": ([U32, ctypes.c_int, U32], ctypes.c_void_p),
            "CloseDesktop": ([ctypes.c_void_p], ctypes.c_int),
            "GetUserObjectInformationW": (
                [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, U32, ctypes.POINTER(U32)],
                ctypes.c_int,
            ),
            "SetThreadDpiAwarenessContext": ([ctypes.c_void_p], ctypes.c_void_p),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.user, name)
            function.argtypes, function.restype = arguments, result
        self.kernel.ProcessIdToSessionId.argtypes = [U32, ctypes.POINTER(U32)]
        self.kernel.ProcessIdToSessionId.restype = ctypes.c_int

    @contextmanager
    def physical_coordinates(self):
        previous = self.user.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
        if not previous:
            raise RuntimeError("Windows refused per-monitor DPI coordinate context")
        try:
            yield
        finally:
            if not self.user.SetThreadDpiAwarenessContext(previous):
                raise RuntimeError("Windows failed to restore DPI coordinate context")

    def desktop_status(self):
        session = U32()
        if not self.kernel.ProcessIdToSessionId(os.getpid(), ctypes.byref(session)):
            raise RuntimeError("Windows session identification failed")
        if session.value == 0:
            raise RuntimeError(
                "Windows GUI unavailable in SSH/service session 0; use an interactive session"
            )
        desktop = self.user.OpenInputDesktop(0, False, 1)
        if not desktop:
            raise RuntimeError("Windows input desktop unavailable or locked")
        try:
            name, required = ctypes.create_unicode_buffer(256), U32()
            if not self.user.GetUserObjectInformationW(
                desktop, 2, name, ctypes.sizeof(name), ctypes.byref(required)
            ):
                raise RuntimeError("Windows input desktop identification failed")
            if name.value.lower() != "default":
                raise RuntimeError("Windows secure/non-default desktop input refused")
        finally:
            self.user.CloseDesktop(desktop)
        foreground = self.foreground()
        if not foreground:
            raise RuntimeError("Windows has no foreground input target")
        return {"session_id": session.value, "desktop": name.value, "foreground_window": foreground}

    def foreground(self):
        return self.user.GetForegroundWindow()

    def ensure_target(self, expected):
        actual = self.desktop_status()["foreground_window"]
        if expected is not None and actual != expected:
            raise RuntimeError("Windows foreground changed since capture; no input sent")
        return actual

    def _failsafe(self):
        if self.FAILSAFE:
            import pyautogui

            pyautogui.failSafeCheck()

    def _send(self, event, target=None):
        self._failsafe()
        releasing = (event.type == 1 and event.keyboard.flags & 2) or (
            event.type == 0 and event.mouse.flags & 4
        )
        if not releasing:
            self.ensure_target(target)
        events = (Input * 1)(event)
        inserted = self.user.SendInput(1, events, ctypes.sizeof(Input))
        if inserted != 1:
            raise RuntimeError(
                "Windows SendInput inserted no event; desktop/UIPI may block delivery"
            )

    def _key(self, key, up):
        named = {
            "enter": 0x0D,
            "escape": 0x1B,
            "tab": 9,
            "backspace": 8,
            "ctrl": 0x11,
            "shift": 0x10,
            "alt": 0x12,
            "command": 0x5B,
        }
        vk = named.get(key)
        if vk is None and key in {"a", "l"}:
            vk = ord(key.upper())
        if vk is None:
            raise ValueError("unsupported Windows shortcut key")
        scan = self.user.MapVirtualKeyW(vk, 4)
        flags = (8 if scan else 0) | (1 if scan & 0xFF00 else 0) | (2 if up else 0)
        return Input(type=1, keyboard=KeyboardInput(0 if scan else vk, scan & 0xFF, flags, 0, 0))

    def keyDown(self, key, target=None):
        self._send(self._key(key, False), target)

    def keyUp(self, key):
        self._send(self._key(key, True))

    def moveTo(self, x, y):
        self._failsafe()
        left, top, width, height = [self.user.GetSystemMetrics(i) for i in (76, 77, 78, 79)]
        if not left <= x < left + width or not top <= y < top + height:
            raise ValueError("Windows pointer coordinate outside virtual desktop")
        if not self.user.SetCursorPos(x, y):
            raise RuntimeError("Windows pointer move refused")
        actual = Point()
        if not self.user.GetCursorPos(ctypes.byref(actual)) or (actual.x, actual.y) != (x, y):
            raise RuntimeError("Windows pointer movement was not confirmed")

    def mouseDown(self, button, target=None):
        if button != "left":
            raise ValueError("unsupported Windows mouse button")
        self._send(Input(type=0, mouse=MouseInput(0, 0, 0, 2, 0, 0)), target)

    def mouseUp(self, button):
        if button != "left":
            raise ValueError("unsupported Windows mouse button")
        self._send(Input(type=0, mouse=MouseInput(0, 0, 0, 4, 0, 0)))

    def scroll(self, clicks, target=None):
        self._send(Input(type=0, mouse=MouseInput(0, 0, clicks * 120, 0x800, 0, 0)), target)

    def type_text(self, text, cancelled, target=None):
        if any(ord(character) < 32 for character in text):
            raise ValueError("control characters refused")
        target = self.ensure_target(target)
        try:
            for character in text:
                if cancelled.is_set():
                    return
                self.ensure_target(target)
                encoded = character.encode("utf-16-le")
                for index in range(0, len(encoded), 2):
                    if cancelled.is_set():
                        return
                    self.ensure_target(target)
                    unit = int.from_bytes(encoded[index : index + 2], "little")
                    self.unicode_units.add(unit)
                    try:
                        self._send(Input(type=1, keyboard=KeyboardInput(0, unit, 4, 0, 0)), target)
                    finally:
                        self.release_text()
        finally:
            self.release_text()

    def release_text(self):
        previous, self.FAILSAFE = self.FAILSAFE, False
        errors = []
        try:
            for unit in tuple(self.unicode_units):
                try:
                    self._send(Input(type=1, keyboard=KeyboardInput(0, unit, 6, 0, 0)))
                    self.unicode_units.discard(unit)
                except Exception as exc:
                    errors.append(exc)
        finally:
            self.FAILSAFE = previous
        if errors:
            raise errors[0]
