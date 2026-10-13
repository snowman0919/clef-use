"""Native GDI lifetime regressions; no windows, input or screenshot files."""

import ctypes as C
import sys
import unittest
from unittest.mock import patch


class NativeGdiProxy:
    def __init__(self, native):
        self.native = native

    def __getattr__(self, name):
        return getattr(self.native, name)


@unittest.skipUnless(sys.platform == "win32", "Windows native GDI resources required")
class WindowsCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from clef_use import windows_capture
        from clef_use.windows_input import WindowsDesktopUnavailable, WindowsInput

        cls.capture = windows_capture
        cls.user, cls.gdi = windows_capture.api()
        cls.kernel = C.WinDLL("kernel32", use_last_error=True)
        cls.kernel.GetCurrentProcess.argtypes = []
        cls.kernel.GetCurrentProcess.restype = C.c_void_p
        cls.user.GetGuiResources.argtypes = [C.c_void_p, C.c_uint32]
        cls.user.GetGuiResources.restype = C.c_uint32
        cls.gdi.GetObjectType.argtypes = [C.c_void_p]
        cls.gdi.GetObjectType.restype = C.c_uint32
        cls.process = cls.kernel.GetCurrentProcess()
        cls.coordinates = WindowsInput()
        try:
            cls.coordinates.desktop_status()
        except WindowsDesktopUnavailable as exc:
            raise unittest.SkipTest(str(exc)) from None
        # Establish native screen availability independently of the code under
        # test. An unavailable Session 0 display is a skip, not a fake capture.
        with cls.coordinates.physical_coordinates():
            if cls.user.GetSystemMetrics(0) <= 0 or cls.user.GetSystemMetrics(1) <= 0:
                raise unittest.SkipTest("native GDI primary-screen geometry unavailable")
            screen = cls.user.GetDC(None)
            if not screen:
                raise unittest.SkipTest(
                    f"native GDI GetDC(NULL) unavailable; winerror={C.get_last_error()}"
                )
            if not cls.user.ReleaseDC(None, screen):
                raise C.WinError(C.get_last_error())
            # Warm lazy DLL/Pillow initialization before comparing process GDI
            # counts. Once the OS admits a screen DC, product failures must fail.
            windows_capture.capture_primary().close()

    def setUp(self):
        self.before = self.resource_count()

    def resource_count(self):
        C.set_last_error(0)
        count = self.user.GetGuiResources(self.process, 0)  # GR_GDIOBJECTS
        if count == 0 and C.get_last_error():
            raise C.WinError(C.get_last_error())
        return count

    def capture_with(self, gdi):
        with patch.object(self.capture, "api", return_value=(self.user, gdi)):
            with self.coordinates.physical_coordinates():
                return self.capture.capture_primary()

    def test_invalid_native_memory_dc_preserves_error_without_gdi_growth(self):
        proxy = NativeGdiProxy(self.gdi)
        native_error = {}

        def invalid_dc(_screen):
            result = self.gdi.CreateCompatibleDC(C.c_void_p(-1))
            native_error["code"] = C.get_last_error()
            return result

        proxy.CreateCompatibleDC = invalid_dc
        with self.assertRaises(OSError) as error:
            self.capture_with(proxy).close()
        self.assertEqual(error.exception.winerror, native_error["code"])
        self.assertEqual(self.resource_count(), self.before)

    def test_failed_native_blit_retires_real_memory_dc_and_selected_bitmap(self):
        proxy = NativeGdiProxy(self.gdi)
        native_error = {}
        acquired = []

        def invalid_destination(_dc, *arguments):
            acquired.append(self.resource_count())
            result = self.gdi.BitBlt(None, *arguments)
            native_error["code"] = C.get_last_error()
            return result

        proxy.BitBlt = invalid_destination
        with self.assertRaises(OSError) as error:
            self.capture_with(proxy).close()
        self.assertEqual(error.exception.winerror, native_error["code"])
        self.assertGreater(acquired[0], self.before)
        self.assertEqual(self.resource_count(), self.before)

    def test_pixel_conversion_failure_preserves_error_and_retires_native_resources(self):
        failure = RuntimeError("pixel conversion fault")
        acquired = []

        def fail_conversion(*_args, **_kwargs):
            acquired.append(self.resource_count())
            raise failure

        with patch.object(self.capture.Image, "frombytes", side_effect=fail_conversion):
            with self.assertRaises(RuntimeError) as error:
                self.capture_with(self.gdi).close()
        self.assertIs(error.exception, failure)
        self.assertGreater(acquired[0], self.before)
        self.assertEqual(self.resource_count(), self.before)

    def test_borrowed_bitmap_restoration_failure_cannot_leak_owned_bitmap(self):
        proxy = NativeGdiProxy(self.gdi)
        borrowed = None
        owned_bitmap = None
        native_error = {}

        def select_bitmap(dc, bitmap):
            nonlocal borrowed, owned_bitmap
            if borrowed is not None and bitmap == borrowed:
                # Fail a legacy stock-bitmap restoration using the real API.
                # The owned-DC destruction path does not need this operation.
                result = self.gdi.SelectObject(dc, C.c_void_p(-1))
                native_error["code"] = C.get_last_error()
                return result
            result = self.gdi.SelectObject(dc, bitmap)
            if result:
                borrowed, owned_bitmap = result, bitmap
            return result

        proxy.SelectObject = select_bitmap
        try:
            try:
                self.capture_with(proxy).close()
            except OSError as error:
                # A correct restoration-based implementation may report the
                # native failure, but must still retire its owned bitmap/DC.
                self.assertEqual(error.winerror, native_error["code"])
            finally:
                self.assertEqual(self.resource_count(), self.before)
        finally:
            # Keep a failing legacy-source run isolated from subsequent tests.
            # This runs after the observable resource-count assertion.
            if owned_bitmap and self.gdi.GetObjectType(owned_bitmap) == 7:  # OBJ_BITMAP
                self.gdi.DeleteObject(owned_bitmap)


if __name__ == "__main__":
    unittest.main()
