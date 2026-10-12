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


class Rect(ctypes.Structure):
    _fields_ = [("left", I32), ("top", I32), ("right", I32), ("bottom", I32)]


class WindowsDesktopUnavailable(RuntimeError):
    pass


class WindowsForegroundChanged(RuntimeError):
    pass


class WindowsInput:
    FAILSAFE = True

    def __init__(self, user32=None, kernel32=None):
        self.unicode_units: set[int] = set()
        self.key_events: dict[str, Input] = {}
        self.ownership_changed = None
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
            "GetWindowRect": ([ctypes.c_void_p, ctypes.POINTER(Rect)], ctypes.c_int),
            "SetCursorPos": ([ctypes.c_int, ctypes.c_int], ctypes.c_int),
            "GetCursorPos": ([ctypes.POINTER(Point)], ctypes.c_int),
            "GetSystemMetrics": ([ctypes.c_int], ctypes.c_int),
            "MapVirtualKeyExW": ([U32, U32, ctypes.c_void_p], U32),
            "GetWindowThreadProcessId": ([ctypes.c_void_p, ctypes.POINTER(U32)], U32),
            "GetKeyboardLayout": ([U32], ctypes.c_void_p),
            "GetClipboardSequenceNumber": ([], U32),
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
            raise WindowsDesktopUnavailable(
                "Windows GUI unavailable in SSH/service session 0; use an interactive session"
            )
        desktop = self.user.OpenInputDesktop(0, False, 1)
        if not desktop:
            raise WindowsDesktopUnavailable("Windows input desktop unavailable or locked")
        try:
            name, required = ctypes.create_unicode_buffer(256), U32()
            if not self.user.GetUserObjectInformationW(
                desktop, 2, name, ctypes.sizeof(name), ctypes.byref(required)
            ):
                raise RuntimeError("Windows input desktop identification failed")
            if name.value.lower() != "default":
                raise WindowsDesktopUnavailable("Windows secure/non-default desktop input refused")
        finally:
            self.user.CloseDesktop(desktop)
        foreground = self.foreground()
        if not foreground:
            raise WindowsDesktopUnavailable("Windows has no foreground input target")
        return {"session_id": session.value, "desktop": name.value, "foreground_window": foreground}

    def foreground(self):
        return self.user.GetForegroundWindow()

    def window_rect(self, target):
        rect = Rect()
        if not self.user.GetWindowRect(target, ctypes.byref(rect)):
            raise WindowsDesktopUnavailable("Windows foreground geometry unavailable")
        return rect.left, rect.top, rect.right, rect.bottom

    def ensure_target(self, expected):
        actual = self.desktop_status()["foreground_window"]
        if expected is not None and actual != expected:
            raise WindowsForegroundChanged(
                "Windows foreground changed since capture; no input sent"
            )
        return actual

    def _failsafe(self):
        if self.FAILSAFE:
            import pyautogui

            pyautogui.failSafeCheck()

    def _send(self, event, target=None):
        self._failsafe()
        releasing = (event.type == 1 and event.keyboard.flags & 2) or (
            event.type == 0 and event.mouse.flags & (4 | 16 | 64)
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
            "delete": 0x2E,
            "space": 0x20,
            "left": 0x25,
            "up": 0x26,
            "right": 0x27,
            "down": 0x28,
            "home": 0x24,
            "end": 0x23,
            "pageup": 0x21,
            "pagedown": 0x22,
            "insert": 0x2D,
            "minus": 0xBD,
            "equal": 0xBB,
            "period": 0xBE,
            "comma": 0xBC,
            "slash": 0xBF,
            "backslash": 0xDC,
            "semicolon": 0xBA,
            "apostrophe": 0xDE,
            "bracketleft": 0xDB,
            "bracketright": 0xDD,
            "grave": 0xC0,
        }
        vk = named.get(key)
        if vk is None and len(key) == 1 and key.isascii() and key.isalnum():
            vk = ord(key.upper())
        if vk is None and key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
            vk = 0x6F + int(key[1:])
        if vk is None:
            raise ValueError("unsupported Windows shortcut key")
        thread = self.user.GetWindowThreadProcessId(self.foreground(), None)
        layout = self.user.GetKeyboardLayout(thread)
        if not thread or not layout:
            raise WindowsDesktopUnavailable("Windows foreground keyboard layout unavailable")
        scan = self.user.MapVirtualKeyExW(vk, 4, layout)
        flags = (8 if scan else 0) | (1 if scan & 0xFF00 else 0) | (2 if up else 0)
        return Input(type=1, keyboard=KeyboardInput(0 if scan else vk, scan & 0xFF, flags, 0, 0))

    def keyDown(self, key, target=None):
        event = self._key(key, False)
        self._send(event, target)
        self.key_events[key] = event
        if self.ownership_changed:
            self.ownership_changed()

    def keyUp(self, key):
        event = self.key_events.get(key)
        if event is None:
            return
        original = event.keyboard
        self._send(
            Input(
                type=1,
                keyboard=KeyboardInput(
                    original.vk, original.scan, original.flags | 2, original.time, original.extra
                ),
            )
        )
        self.key_events.pop(key, None)
        if self.ownership_changed:
            self.ownership_changed()

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
        flags = {"left": 2, "right": 8, "middle": 32}.get(button)
        if flags is None:
            raise ValueError("unsupported Windows mouse button")
        self._send(Input(type=0, mouse=MouseInput(0, 0, 0, flags, 0, 0)), target)

    def mouseUp(self, button):
        flags = {"left": 4, "right": 16, "middle": 64}.get(button)
        if flags is None:
            raise ValueError("unsupported Windows mouse button")
        self._send(Input(type=0, mouse=MouseInput(0, 0, 0, flags, 0, 0)))

    def scroll(self, clicks, target=None):
        self._send(Input(type=0, mouse=MouseInput(0, 0, clicks * 120, 0x800, 0, 0)), target)

    def hscroll(self, clicks, target=None):
        self._send(Input(type=0, mouse=MouseInput(0, 0, clicks * 120, 0x1000, 0, 0)), target)

    def unowned_input(self, keys, buttons):
        """Conservatively reject held inputs that this injector did not acquire."""
        query = getattr(self.user, "GetAsyncKeyState", None)
        if query is None:
            raise WindowsDesktopUnavailable("Windows held-input observation unavailable")
        owned_scans = {event.keyboard.scan for key, event in self.key_events.items() if key in keys}
        owned_vk = {event.keyboard.vk for key, event in self.key_events.items() if key in keys}
        mouse = {"left": 1, "right": 2, "middle": 4}
        for vk in range(1, 256):
            if not query(vk) & 0x8000:
                continue
            if vk in mouse.values():
                if any(mouse[button] == vk for button in buttons):
                    continue
                return True
            # General and left/right modifier virtual keys can report the same hold.
            logical = {0xA0: 0x10, 0xA1: 0x10, 0xA2: 0x11, 0xA3: 0x11, 0xA4: 0x12, 0xA5: 0x12}.get(
                vk, vk
            )
            thread = self.user.GetWindowThreadProcessId(self.foreground(), None)
            layout = self.user.GetKeyboardLayout(thread)
            scan = self.user.MapVirtualKeyExW(logical, 4, layout) & 0xFF
            if logical not in owned_vk and scan not in owned_scans:
                return True
        return False

    def type_text(self, text, cancelled, target=None, *, before_input=None):
        if any(ord(character) < 32 for character in text):
            raise ValueError("control characters refused")
        encoded = text.encode("utf-16-le")
        target = self.ensure_target(target)
        try:
            for index in range(0, len(encoded), 2):
                if cancelled.is_set():
                    return
                if before_input is not None:
                    before_input()
                unit = int.from_bytes(encoded[index : index + 2], "little")
                try:
                    self._send(Input(type=1, keyboard=KeyboardInput(0, unit, 4, 0, 0)), target)
                    self.unicode_units.add(unit)
                    if self.ownership_changed:
                        self.ownership_changed()
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
                    if self.ownership_changed:
                        self.ownership_changed()
                except Exception as exc:
                    errors.append(exc)
        finally:
            self.FAILSAFE = previous
        if errors:
            raise errors[0]
