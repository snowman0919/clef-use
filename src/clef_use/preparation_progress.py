from __future__ import annotations

import threading
import time
from contextlib import contextmanager


class PreparationProgress:
    def __init__(self, callback=None, total=9, interval=10):
        self.callback = callback
        self.total = total
        self.interval = interval
        self.step = 0
        self.label = ""
        self.started = 0.0
        self.lock = threading.RLock()

    def message(self, label):
        with self.lock:
            self.label = label
            if self.callback:
                self.callback(f"[{self.step}/{self.total}] {label}")

    @contextmanager
    def stage(self, label):
        self.step += 1
        self.started = time.monotonic()
        self.message(label)
        stop = threading.Event()

        def heartbeat():
            while not stop.wait(self.interval):
                with self.lock:
                    elapsed = time.monotonic() - self.started
                    self.callback(
                        f"[{self.step}/{self.total}] Still working: {self.label} "
                        f"(elapsed {elapsed:.0f}s)"
                    )

        thread = threading.Thread(target=heartbeat, daemon=True) if self.callback else None
        if thread:
            thread.start()
        failed = False
        try:
            yield
        except BaseException:
            failed = True
            raise
        finally:
            stop.set()
            if thread:
                thread.join()
            self.message(
                f"Failed or interrupted: {self.label}"
                if failed
                else f"Done ({time.monotonic() - self.started:.1f}s): {label}"
            )
