"""Primary-monitor GDI capture without changing process DPI awareness.

The caller supplies the existing per-thread physical coordinate context. No
process-wide DPI setter is called, including indirectly through MSS.
"""

from __future__ import annotations

import ctypes as C
import sys
from functools import lru_cache

from PIL import Image

from .activity_windows import BitmapInfo

HANDLE, INT, DWORD = C.c_void_p, C.c_int, C.c_uint32


@lru_cache(maxsize=1)
def api():
    user = C.WinDLL("user32", use_last_error=True)
    gdi = C.WinDLL("gdi32", use_last_error=True)
    signatures = (
        (user, "GetSystemMetrics", [INT], INT),
        (user, "GetDC", [HANDLE], HANDLE),
        (user, "ReleaseDC", [HANDLE, HANDLE], INT),
        (gdi, "CreateCompatibleDC", [HANDLE], HANDLE),
        (
            gdi,
            "CreateDIBSection",
            [HANDLE, C.POINTER(BitmapInfo), DWORD, C.POINTER(HANDLE), HANDLE, DWORD],
            HANDLE,
        ),
        (gdi, "SelectObject", [HANDLE, HANDLE], HANDLE),
        (gdi, "BitBlt", [HANDLE, INT, INT, INT, INT, HANDLE, INT, INT, DWORD], INT),
        (gdi, "GdiFlush", [], INT),
        (gdi, "DeleteObject", [HANDLE], INT),
        (gdi, "DeleteDC", [HANDLE], INT),
    )
    for library, name, arguments, result in signatures:
        function = getattr(library, name)
        function.argtypes, function.restype = arguments, result
    return user, gdi


def capture_primary():
    """Return independent RGB pixels; release every owned GDI handle on failure."""
    user, gdi = api()
    width, height = user.GetSystemMetrics(0), user.GetSystemMetrics(1)
    if width <= 0 or height <= 0:
        raise RuntimeError("Windows primary monitor geometry unavailable")
    screen = user.GetDC(None)
    if not screen:
        raise C.WinError(C.get_last_error())
    dc = bitmap = None
    try:
        dc = gdi.CreateCompatibleDC(screen)
        if not dc:
            raise C.WinError(C.get_last_error())
        header = BitmapInfo(C.sizeof(BitmapInfo), width, -height, 1, 32)
        pixels = HANDLE()
        bitmap = gdi.CreateDIBSection(screen, C.byref(header), 0, C.byref(pixels), None, 0)
        if not bitmap or not pixels.value:
            raise C.WinError(C.get_last_error())
        previous = gdi.SelectObject(dc, bitmap)
        if previous in (None, 0, C.c_void_p(-1).value):
            raise C.WinError(C.get_last_error())
        # SRCCOPY | CAPTUREBLT retains the existing layered-window contract.
        if not gdi.BitBlt(dc, 0, 0, width, height, screen, 0, 0, 0x40CC0020):
            raise C.WinError(C.get_last_error())
        if not gdi.GdiFlush():
            raise C.WinError(C.get_last_error())
        raw = C.string_at(pixels, width * height * 4)
        return Image.frombytes("RGB", (width, height), raw, "raw", "BGRX")
    finally:
        failed = sys.exc_info()[0] is not None
        cleanup_error = None
        # The memory DC is wholly owned. Destroy it before deleting its bitmap:
        # DeleteObject refuses a bitmap that is still selected into a live DC.
        for operation, arguments in (
            (gdi.DeleteDC, (dc,)) if dc else (None, ()),
            (gdi.DeleteObject, (bitmap,)) if bitmap else (None, ()),
            (user.ReleaseDC, (None, screen)),
        ):
            if operation is not None and not operation(*arguments) and cleanup_error is None:
                cleanup_error = C.WinError(C.get_last_error())
        if cleanup_error is not None and not failed:
            raise cleanup_error
