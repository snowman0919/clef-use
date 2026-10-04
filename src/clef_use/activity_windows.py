from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W

from .windows_input import WindowsInput


class Point(C.Structure):
    _fields_ = [("x", W.LONG), ("y", W.LONG)]


class Size(C.Structure):
    _fields_ = [("cx", W.LONG), ("cy", W.LONG)]


class BitmapInfo(C.Structure):
    _fields_ = [
        ("size", W.DWORD),
        ("width", W.LONG),
        ("height", W.LONG),
        ("planes", W.WORD),
        ("bits", W.WORD),
        ("compression", W.DWORD),
        ("image_size", W.DWORD),
        ("xppm", W.LONG),
        ("yppm", W.LONG),
        ("used", W.DWORD),
        ("important", W.DWORD),
    ]


class Blend(C.Structure):
    _fields_ = [
        ("operation", C.c_byte),
        ("flags", C.c_byte),
        ("alpha", C.c_ubyte),
        ("format", C.c_byte),
    ]


class Display:
    def __init__(self):
        WindowsInput().ensure_target(None)
        self.user = C.WinDLL("user32", use_last_error=True)
        self.gdi = C.WinDLL("gdi32", use_last_error=True)
        self.user.SetThreadDpiAwarenessContext.argtypes = [C.c_void_p]
        self.user.SetThreadDpiAwarenessContext.restype = C.c_void_p
        self.user.SetThreadDpiAwarenessContext(C.c_void_p(-4))
        self.user.CreateWindowExW.argtypes = [
            W.DWORD,
            W.LPCWSTR,
            W.LPCWSTR,
            W.DWORD,
            C.c_int,
            C.c_int,
            C.c_int,
            C.c_int,
            C.c_void_p,
            C.c_void_p,
            C.c_void_p,
            C.c_void_p,
        ]
        self.user.CreateWindowExW.restype = C.c_void_p
        self.user.GetDC.argtypes = [C.c_void_p]
        self.user.GetDC.restype = C.c_void_p
        self.user.ReleaseDC.argtypes = [C.c_void_p, C.c_void_p]
        self.user.UpdateLayeredWindow.argtypes = [
            C.c_void_p,
            C.c_void_p,
            C.POINTER(Point),
            C.POINTER(Size),
            C.c_void_p,
            C.POINTER(Point),
            W.DWORD,
            C.POINTER(Blend),
            W.DWORD,
        ]
        self.user.UpdateLayeredWindow.restype = W.BOOL
        self.user.SetWindowPos.argtypes = [
            C.c_void_p,
            C.c_void_p,
            C.c_int,
            C.c_int,
            C.c_int,
            C.c_int,
            W.UINT,
        ]
        self.user.ShowWindow.argtypes = [C.c_void_p, C.c_int]
        self.user.DestroyWindow.argtypes = [C.c_void_p]
        self.user.SetWindowDisplayAffinity.argtypes = [C.c_void_p, W.DWORD]
        self.gdi.CreateCompatibleDC.argtypes = [C.c_void_p]
        self.gdi.CreateCompatibleDC.restype = C.c_void_p
        self.gdi.CreateDIBSection.argtypes = [
            C.c_void_p,
            C.POINTER(BitmapInfo),
            W.UINT,
            C.POINTER(C.c_void_p),
            C.c_void_p,
            W.DWORD,
        ]
        self.gdi.CreateDIBSection.restype = C.c_void_p
        self.gdi.SelectObject.argtypes = [C.c_void_p, C.c_void_p]
        self.gdi.SelectObject.restype = C.c_void_p
        self.gdi.DeleteObject.argtypes = [C.c_void_p]
        self.gdi.DeleteDC.argtypes = [C.c_void_p]
        self.windows = []
        self.capture_excluded = True
        for width, height in ((340, 84), (48, 48)):
            hwnd = self.user.CreateWindowExW(
                0x080800A0,
                "STATIC",
                "clef-use activity",
                0x80000000,
                18,
                18,
                width,
                height,
                None,
                None,
                None,
                None,
            )
            if not hwnd:
                raise C.WinError(C.get_last_error())
            self.windows.append(hwnd)
            self.capture_excluded = (
                bool(self.user.SetWindowDisplayAffinity(hwnd, 0x11)) and self.capture_excluded
            )

    def _show(self, index, image, x, y):
        width, height = image.size
        header = BitmapInfo(C.sizeof(BitmapInfo), width, -height, 1, 32)
        bits = C.c_void_p()
        screen = self.user.GetDC(None)
        dc = self.gdi.CreateCompatibleDC(screen)
        bitmap = self.gdi.CreateDIBSection(screen, C.byref(header), 0, C.byref(bits), None, 0)
        if not bitmap or not dc:
            raise RuntimeError("cannot allocate activity surface")
        old = self.gdi.SelectObject(dc, bitmap)
        try:
            data = image.convert("RGBa").tobytes("raw", "BGRa")
            C.memmove(bits, data, len(data))
            if not self.user.UpdateLayeredWindow(
                self.windows[index],
                screen,
                C.byref(Point(x, y)),
                C.byref(Size(width, height)),
                dc,
                C.byref(Point()),
                0,
                C.byref(Blend(0, 0, 255, 1)),
                2,
            ):
                raise C.WinError(C.get_last_error())
            self.user.SetWindowPos(self.windows[index], C.c_void_p(-1), 0, 0, 0, 0, 0x53)
        finally:
            self.gdi.SelectObject(dc, old)
            self.gdi.DeleteObject(bitmap)
            self.gdi.DeleteDC(dc)
            self.user.ReleaseDC(None, screen)

    def show(self, panel, cursor, point):
        self._show(0, panel, 18, 18)
        if point is None:
            self.user.ShowWindow(self.windows[1], 0)
        else:
            self._show(1, cursor, point[0] - 24, point[1] - 24)

    def hide(self):
        for hwnd in self.windows:
            self.user.ShowWindow(hwnd, 0)

    def pump(self):
        message = W.MSG()
        while self.user.PeekMessageW(C.byref(message), None, 0, 0, 1):
            self.user.TranslateMessage(C.byref(message))
            self.user.DispatchMessageW(C.byref(message))

    def window_ids(self):
        return list(self.windows)

    def close(self):
        for hwnd in self.windows:
            self.user.DestroyWindow(hwnd)
