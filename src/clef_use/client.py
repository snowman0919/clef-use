from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from filelock import FileLock

from . import __version__
from .config import desktop_scope, load_config, state_dir


class RuntimeClient:
    def __init__(self, start: bool = True):
        self.start = start

    def _endpoint(self):
        data = json.loads((state_dir() / "endpoint.json").read_text())
        if not isinstance(data["port"], int) or not 1 <= data["port"] <= 65535:
            raise ValueError("invalid local service port")
        return data

    def _send(self, operation, data):
        endpoint = self._endpoint()
        request = urllib.request.Request(
            f"http://127.0.0.1:{endpoint['port']}/{operation}",
            data=json.dumps(data).encode(),
            headers={
                "Authorization": "Bearer " + endpoint["token"],
                "Content-Type": "application/json",
                "X-Clef-Desktop-Scope": desktop_scope() or "",
            },
            method="POST",
        )
        timeout = 5
        if operation == "observe":
            config = load_config()
            # Idle observation may cold-start its parser and then parse a fresh frame.
            timeout += 2 * config.backend_timeout + config.screen_timeout
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)

    def _check_desktop(self, health):
        expected = desktop_scope()
        if "desktop_scope" not in health and expected is not None:
            raise RuntimeError(
                "runtime desktop ownership is unknown; stop the legacy service explicitly"
            )
        if health.get("desktop_scope") != expected:
            raise RuntimeError("runtime belongs to another desktop; match the desktop environment")

    def _ensure(self):
        try:
            health = self._send("health", {})
            self._check_desktop(health)
            if not self.start or health.get("version") == __version__:
                return
            if health.get("busy"):
                raise RuntimeError("previous runtime version is active; finish or abort it first")
        except (OSError, ValueError):
            if not self.start:
                raise RuntimeError("runtime service is not running") from None
        root = state_dir()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with FileLock(root / "start.lock", timeout=15):
            try:
                health = self._send("health", {})
                self._check_desktop(health)
                if health.get("version") == __version__:
                    return
                if health.get("busy"):
                    raise RuntimeError(
                        "previous runtime version is active; finish or abort it first"
                    )
                self._send("shutdown_idle", {})
                deadline = time.monotonic() + 10
                while (root / "endpoint.json").exists() and time.monotonic() < deadline:
                    time.sleep(0.1)
                if (root / "endpoint.json").exists():
                    raise RuntimeError("previous runtime did not stop")
            except (OSError, ValueError):
                pass
            subprocess.Popen(
                [sys.executable, "-m", "clef_use.service"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=os.environ.copy(),
            )
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                try:
                    health = self._send("health", {})
                    self._check_desktop(health)
                    return
                except (OSError, ValueError):
                    time.sleep(0.1)
            raise RuntimeError("runtime service did not start")

    def request(self, operation, **data):
        self._ensure()
        try:
            return self._send(operation, data)
        except urllib.error.HTTPError as exc:
            try:
                reply = json.loads(exc.read(4096))
                code = reply.get("error") if isinstance(reply, dict) else None
            except (OSError, ValueError):
                code = None
            messages = {
                "NO_ACTIVE_SESSION": "no active session; start computer_run first",
                "SESSION_NOT_FOUND": "session not found; it may have expired or restarted",
            }
            if exc.code == 404 and code in messages:
                raise RuntimeError(messages[code]) from None
            raise RuntimeError(f"runtime refused {operation}; inspect session status") from None

    def wait(self, result):
        session_id = result["session_id"]
        try:
            while result["status"] == "RUNNING":
                time.sleep(0.1)
                result = self._send("status", {"session_id": session_id})
            return result
        except KeyboardInterrupt:
            return self.request("abort", session_id=session_id)

    def run(self, contract):
        self._ensure()
        result = self._send("run", contract.model_dump(mode="json"))
        return self.wait(result)

    def continue_session(self, session_id, instruction):
        return self.wait(self.request("continue", session_id=session_id, instruction=instruction))
