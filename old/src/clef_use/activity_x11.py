from __future__ import annotations

import ctypes as C


class Display:
    def __init__(self):
        self.x = C.CDLL("libX11.so.6")
        self.shape = C.CDLL("libXext.so.6")
        signatures = {
            "XOpenDisplay": ([C.c_char_p], C.c_void_p),
            "XDefaultScreen": ([C.c_void_p], C.c_int),
            "XRootWindow": ([C.c_void_p, C.c_int], C.c_ulong),
            "XDefaultVisual": ([C.c_void_p, C.c_int], C.c_void_p),
            "XDefaultDepth": ([C.c_void_p, C.c_int], C.c_int),
            "XCreateSimpleWindow": (
                [
                    C.c_void_p,
                    C.c_ulong,
                    C.c_int,
                    C.c_int,
                    C.c_uint,
                    C.c_uint,
                    C.c_uint,
                    C.c_ulong,
                    C.c_ulong,
                ],
                C.c_ulong,
            ),
            "XCreateGC": ([C.c_void_p, C.c_ulong, C.c_ulong, C.c_void_p], C.c_void_p),
            "XCreateImage": (
                [
                    C.c_void_p,
                    C.c_void_p,
                    C.c_uint,
                    C.c_int,
                    C.c_int,
                    C.c_void_p,
                    C.c_uint,
                    C.c_uint,
                    C.c_int,
                    C.c_int,
                ],
                C.c_void_p,
            ),
            "XPutImage": (
                [
                    C.c_void_p,
                    C.c_ulong,
                    C.c_void_p,
                    C.c_void_p,
                    C.c_int,
                    C.c_int,
                    C.c_int,
                    C.c_int,
                    C.c_uint,
                    C.c_uint,
                ],
                C.c_int,
            ),
            "XMoveWindow": ([C.c_void_p, C.c_ulong, C.c_int, C.c_int], C.c_int),
            "XMapRaised": ([C.c_void_p, C.c_ulong], C.c_int),
            "XUnmapWindow": ([C.c_void_p, C.c_ulong], C.c_int),
            "XDestroyWindow": ([C.c_void_p, C.c_ulong], C.c_int),
            "XFreeGC": ([C.c_void_p, C.c_void_p], C.c_int),
            "XCloseDisplay": ([C.c_void_p], C.c_int),
            "XSync": ([C.c_void_p, C.c_int], C.c_int),
            "XFree": ([C.c_void_p], C.c_int),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.x, name)
            function.argtypes, function.restype = args, result
        self.shape.XShapeCombineRectangles.argtypes = [
            C.c_void_p,
            C.c_ulong,
            C.c_int,
            C.c_int,
            C.c_int,
            C.c_void_p,
            C.c_int,
            C.c_int,
            C.c_int,
        ]
        self.display = self.x.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("an X11 desktop is required for activity display")
        screen = self.x.XDefaultScreen(self.display)
        self.visual = self.x.XDefaultVisual(self.display, screen)
        self.depth = self.x.XDefaultDepth(self.display, screen)
        if self.depth != 24:
            raise RuntimeError("activity display requires a 24-bit X11 visual")
        self.windows = []
        # Override-redirect skips WM decoration and activation; the input shape is empty.
        self.x.XChangeWindowAttributes.argtypes = [C.c_void_p, C.c_ulong, C.c_ulong, C.c_void_p]

        class Attributes(C.Structure):
            _fields_ = [
                ("background_pixmap", C.c_ulong),
                ("background_pixel", C.c_ulong),
                ("border_pixmap", C.c_ulong),
                ("border_pixel", C.c_ulong),
                ("bit_gravity", C.c_int),
                ("win_gravity", C.c_int),
                ("backing_store", C.c_int),
                ("backing_planes", C.c_ulong),
                ("backing_pixel", C.c_ulong),
                ("save_under", C.c_int),
                ("event_mask", C.c_long),
                ("do_not_propagate_mask", C.c_long),
                ("override_redirect", C.c_int),
                ("colormap", C.c_ulong),
                ("cursor", C.c_ulong),
            ]

        for width, height in ((340, 84), (48, 48)):
            window = self.x.XCreateSimpleWindow(
                self.display,
                self.x.XRootWindow(self.display, screen),
                18,
                18,
                width,
                height,
                0,
                0,
                0x101B2E,
            )
            attrs = Attributes(override_redirect=1)
            self.x.XChangeWindowAttributes(self.display, window, 1 << 9, C.byref(attrs))
            self.shape.XShapeCombineRectangles(self.display, window, 2, 0, 0, None, 0, 0, 0)
            self.windows.append((window, self.x.XCreateGC(self.display, window, 0, None)))

    def _show(self, index, image, x, y):
        background = image.convert("RGB")
        data = C.create_string_buffer(background.tobytes("raw", "BGRX"))
        native = self.x.XCreateImage(
            self.display,
            self.visual,
            self.depth,
            2,
            0,
            C.cast(data, C.c_void_p),
            *image.size,
            32,
            0,
        )
        if not native:
            raise RuntimeError("cannot create activity image")
        window, gc = self.windows[index]
        try:
            self.x.XMoveWindow(self.display, window, x, y)
            self.x.XMapRaised(self.display, window)
            self.x.XPutImage(self.display, window, gc, native, 0, 0, 0, 0, *image.size)
            self.x.XSync(self.display, False)
        finally:
            # XDestroyImage would free the Python-owned pixel buffer as well.
            self.x.XFree(native)

    def show(self, panel, cursor, point):
        self._show(0, panel, 18, 18)
        if point is None:
            self.x.XUnmapWindow(self.display, self.windows[1][0])
        else:
            self._show(1, cursor, point[0] - 24, point[1] - 24)
        self.x.XSync(self.display, False)

    def hide(self):
        for window, _ in self.windows:
            self.x.XUnmapWindow(self.display, window)
        self.x.XSync(self.display, False)

    def pump(self):
        pass

    def window_ids(self):
        return [window for window, _ in self.windows]

    def close(self):
        for window, gc in self.windows:
            self.x.XFreeGC(self.display, gc)
            self.x.XDestroyWindow(self.display, window)
        self.x.XCloseDisplay(self.display)
