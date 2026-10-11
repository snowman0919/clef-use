"""Private read-only X11 query connection; native state is never cached."""

import os
import threading
import weakref
from contextlib import contextmanager
from itertools import zip_longest


class X11InputState:
    def __init__(self, display_name):
        self.process = os.getpid()
        self.environment_display = os.environ.get("DISPLAY")
        self.display_name = display_name
        self.lock = threading.RLock()
        self.connection = None
        self.failed = False
        self.finalizer = None

    def _binding(self):
        if os.getpid() != self.process or os.environ.get("DISPLAY") != self.environment_display:
            # Never acquire a possibly inherited locked mutex or flush an
            # inherited X protocol stream in the child.
            if self.finalizer:
                self.finalizer()
            self.failed = True
            raise RuntimeError("X11 input query process or display changed")

    @contextmanager
    def query(self):
        from Xlib import error

        self._binding()
        with self.lock:
            self._binding()
            if self.failed:
                raise RuntimeError("X11 input query connection unavailable")
            try:
                if self.connection is None:
                    from Xlib import display

                    self.connection = display.Display(self.display_name)
                    # Read-only queries have no server resources to free. Closing
                    # the socket avoids a blocking protocol flush at collection.
                    self.finalizer = weakref.finalize(self, self.connection.display.socket.close)
                if self.connection.display.socket.fileno() < 0:
                    self.failed = True
                    raise RuntimeError("X11 input query connection unavailable")
                yield self.connection
            except (error.ConnectionClosedError, error.DisplayConnectionError, OSError):
                self.failed = True
                if self.finalizer:
                    self.finalizer()
                raise

    def foreground(self):
        with self.query() as connection:
            window = connection.get_input_focus().focus
            root = connection.screen().root
            if not hasattr(window, "id") or window.id == root.id:
                return None, None
            while True:
                parent = window.query_tree().parent
                if parent.id == root.id:
                    break
                window = parent
            geometry = window.get_geometry()
            position = root.translate_coords(window, 0, 0)
            return window.id, (
                position.x,
                position.y,
                position.x + geometry.width,
                position.y + geometry.height,
            )

    def binding_matches(self, code, expected):
        with self.query() as connection:
            actual = tuple(connection.get_keyboard_mapping(code, 1)[0])
        # X11 pads keymap rows with NoSymbol to the longest server row.
        return all(left == right for left, right in zip_longest(expected, actual, fillvalue=0))
