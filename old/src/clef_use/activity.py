from __future__ import annotations

import contextlib
import json
import queue
import subprocess
import sys
import threading


class ActivityOverlay:
    """Owned display process, excluded from capture or hidden before capture."""

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.process = None
        self.responses = queue.Queue()
        self.lock = threading.RLock()
        self.sequence = 0
        self.windows = []
        self.requested = enabled
        self.capture_excluded = sys.platform == "darwin"
        self.state = {"phase": "Starting", "steps": 0, "rounds": 0}

    def _read(self, process):
        try:
            for line in process.stdout:
                self.responses.put(json.loads(line))
        finally:
            self.responses.put({"closed": True})

    def _start(self):
        if self.process is not None or not self.enabled:
            return
        self.process = subprocess.Popen(
            [sys.executable, "-m", "clef_use.activity_display"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
            bufsize=1,
        )
        threading.Thread(target=self._read, args=(self.process,), daemon=True).start()
        reply = self.responses.get(timeout=5)
        self.windows = reply.get("windows", [])
        if sys.platform == "win32":
            self.capture_excluded = reply.get("capture_excluded", False)
        if reply.get("ready") is not True:
            raise RuntimeError("activity display unavailable")

    def _stop(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
            for stream in (self.process.stdin, self.process.stdout):
                stream.close()
            self.process = None
        self.enabled = False

    def _send(self, operation):
        with self.lock:
            if not self.enabled:
                return
            try:
                self._start()
                self.sequence += 1
                self.process.stdin.write(
                    json.dumps({"seq": self.sequence, "op": operation, "state": self.state}) + "\n"
                )
                self.process.stdin.flush()
                reply = self.responses.get(timeout=2)
                if reply.get("seq") != self.sequence:
                    raise RuntimeError("activity display acknowledgement missing")
            except (OSError, ValueError, RuntimeError, queue.Empty):
                # Removing the owned process also removes its windows before capture resumes.
                self._stop()

    def update(self, phase, session, point=None, target=None):
        with self.lock:
            self.state = {
                "phase": phase,
                "steps": session.steps,
                "rounds": session.rounds,
                "point": point,
                "target": target,
            }
            self._send("show")

    @contextlib.contextmanager
    def capture(self, backend=None):
        with self.lock:
            if (
                self.enabled
                and self.windows
                and self.capture_excluded
                and getattr(backend, "native_overlay_exclusion", False)
            ):
                with backend.excluding_windows(self.windows):
                    yield
                return
            self._send("hide")
            try:
                yield
            finally:
                self._send("show")

    def finish(self, session):
        with self.lock:
            self.state = {
                "phase": session.status.value.replace("_", " ").title(),
                "steps": session.steps,
                "rounds": session.rounds,
                "terminal": True,
            }
            self._send("show")

    def close(self):
        with self.lock:
            self._stop()


class SilentActivity:
    def update(self, *args, **kwargs):
        pass

    def capture(self, backend=None):
        return contextlib.nullcontext()

    def finish(self, session):
        pass

    def close(self):
        pass
