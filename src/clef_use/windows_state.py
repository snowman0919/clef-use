"""Bound, partial Windows focus evidence; unknown app state stays unknown."""

from __future__ import annotations

import json
import math
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from .state import FactValidity, StateFact, StateSource


def focus_evidence(observation, version, sample):
    """Validate native focus provenance independently of the worker protocol."""
    frame = observation.frame
    now = time.time()
    if sample.get("status") not in {"VALID", "PARTIAL"} or sample.get("cleanup_errors"):
        return {}
    timestamp = sample.get("observed_at")
    duration = sample.get("acquisition_seconds")
    if (
        type(timestamp) not in (int, float)
        or not math.isfinite(timestamp)
        or not 0 <= now - timestamp <= 0.5
        or type(duration) not in (int, float)
        or not 0 <= duration <= 0.5
        or not 0 <= now - frame.captured_at <= 0.5
    ):
        return {}
    before, after = sample.get("native_before"), sample.get("native_after")
    if (
        not isinstance(before, dict)
        or before != after
        or type(before.get("hwnd")) is not int
        or before["hwnd"] != frame.foreground_window
        or type(before.get("pid")) is not int
        or before["pid"] <= 0
        or type(before.get("tid")) is not int
        or before["tid"] <= 0
        or frame.foreground_bounds is None
        or before.get("bounds") != list(frame.foreground_bounds)
        or sample.get("pattern_supported") is not True
        or sample.get("text_focus") is not True
    ):
        return {}
    facts = {
        "text_focus": StateFact(
            value=True,
            source=StateSource.ACCESSIBILITY,
            observed_at=timestamp,
            state_version=version,
            validity=FactValidity.VALID,
            uncertainty=0,
        )
    }
    composition = sample.get("composition")
    ime = sample.get("ime_composing")
    if (
        sample["status"] == "VALID"
        and type(ime) is bool
        and isinstance(composition, dict)
        and composition.get("hresult") == "0x00000000"
        and composition.get("range_present") is ime
    ):
        facts["ime_composing"] = facts["text_focus"].model_copy(update={"value": ime})
    return facts


class WindowsStateProvider:
    """One stdlib-only worker bounds a stuck native COM call by process exit.

    The base interpreter runs a file that needs no installed packages. Its
    ready PID must match Popen's PID, so killing a launcher cannot leave a
    hung interpreter behind. One failed observation is never retried.
    """

    def __init__(self, application_provider=None):
        self.application_provider = application_provider
        self.process = None
        self.reader = None
        self.replies = queue.Queue()
        self.lock = threading.RLock()
        self.status = {"status": "NOT_PROBED", "provider": "WINDOWS_UIA"}

    def _read(self, process, replies):
        while line := process.stdout.readline(65537):
            if len(line) > 65536:
                break
            try:
                reply = json.loads(line)
                if not isinstance(reply, dict):
                    break
                replies.put(reply)
            except ValueError:
                break
        replies.put({"error": "native observation worker disconnected"})

    def _receive(self, timeout):
        try:
            result = self.replies.get(timeout=timeout)
        except queue.Empty as exc:
            raise TimeoutError("native observation worker timed out") from exc
        if "error" in result:
            raise RuntimeError("native observation worker disconnected")
        return result

    def _start(self):
        self.replies = queue.Queue()
        self.process = subprocess.Popen(
            [sys._base_executable, str(Path(__file__).with_name("windows_uia.py")), "--worker"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        self.reader = threading.Thread(
            target=self._read, args=(self.process, self.replies), daemon=True
        )
        self.reader.start()
        ready = self._receive(1)
        if (
            ready.get("ready") is not True
            or ready.get("protocol") != 1
            or type(ready.get("pid")) is not int
            or ready["pid"] != self.process.pid
        ):
            raise RuntimeError("native observation worker identity unavailable")

    def _close_worker(self):
        process, reader = self.process, self.reader
        self.process = self.reader = None
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=3)
            if reader is not None:
                reader.join(timeout=1)
                if reader.is_alive():
                    raise RuntimeError("native observation reader did not exit")
            process.stdin.close()
            process.stdout.close()

    def close(self):
        with self.lock:
            self._close_worker()
            close = getattr(self.application_provider, "close", None)
            if close:
                close()

    def __call__(self, observation, version):
        with self.lock:
            evidence = (
                self.application_provider(observation, version)
                if self.application_provider is not None
                else {}
            )
            frame = observation.frame
            try:
                if sys.platform != "win32":
                    raise RuntimeError("Windows native observation unavailable")
                if frame.foreground_window is None or frame.foreground_bounds is None:
                    raise ValueError("captured native foreground identity unavailable")
                if not 0 <= time.time() - frame.captured_at <= 0.5:
                    raise ValueError("captured native foreground is stale")
                if self.process is None or self.process.poll() is not None:
                    self._close_worker()
                    self._start()
                request = {"window": frame.foreground_window, "bounds": frame.foreground_bounds}
                self.process.stdin.write(json.dumps(request) + "\n")
                self.process.stdin.flush()
                sample = self._receive(0.5)
                facts = focus_evidence(observation, version, sample)
                self.status = {
                    "status": "PARTIAL" if facts else "UNAVAILABLE",
                    "provider": "WINDOWS_UIA",
                    "verified_facts": sorted(facts),
                    "native_status": sample.get("status"),
                    "failed_check": sample.get("failed_stage"),
                    "ime_scope": "bound focused TextEdit control only; not global UI idle",
                }
                for name, fact in facts.items():
                    prior = evidence.get(name)
                    if (
                        prior is not None
                        and prior.validity == FactValidity.VALID
                        and prior.value != fact.value
                    ):
                        fact = fact.model_copy(
                            update={"validity": FactValidity.INVALIDATED, "uncertainty": 1}
                        )
                    evidence[name] = fact
            except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
                self._close_worker()
                self.status = {
                    "status": "UNAVAILABLE",
                    "provider": "WINDOWS_UIA",
                    "reason": "Native focus observation unavailable",
                    "error_type": type(exc).__name__,
                }
            if self.application_provider is not None:
                self.status["application_provider"] = self.application_provider.status
            return evidence
