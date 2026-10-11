from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from filelock import FileLock
from packaging.version import InvalidVersion, Version

from . import __version__
from .capabilities import RUNTIME_PROTOCOL_VERSION, schema_sha256
from .config import desktop_scope, load_config, state_dir


class RuntimeClient:
    def __init__(self, start: bool = True):
        self.start = start

    def _endpoint(self):
        data = json.loads((state_dir() / "endpoint.json").read_text())
        if not isinstance(data["port"], int) or not 1 <= data["port"] <= 65535:
            raise ValueError("invalid local service port")
        return data

    def _send(self, operation, data, *, endpoint=None):
        endpoint = endpoint if endpoint is not None else self._endpoint()
        request = urllib.request.Request(
            f"http://127.0.0.1:{endpoint['port']}/{operation}",
            data=json.dumps(data).encode(),
            headers={
                "Authorization": "Bearer " + endpoint["token"],
                "Content-Type": "application/json",
                "X-Clef-Desktop-Scope": desktop_scope() or "",
                "X-Clef-Client-Version": __version__,
                "X-Clef-Api-Schema": schema_sha256(),
                "X-Clef-Runtime-Protocol": str(RUNTIME_PROTOCOL_VERSION),
            },
            method="POST",
        )
        timeout = 5
        if operation == "observe" and data.get("refresh", True) is not False:
            config = load_config()
            # Idle observation may cold-start its parser and then parse a fresh frame.
            timeout += 2 * config.backend_timeout + config.screen_timeout
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 409:
                exc.close()
                raise RuntimeError(
                    "runtime contract changed; reload the current clef-use executable and MCP "
                    "session before retrying; the existing service was not replaced"
                ) from None
            if exc.code == 400:
                try:
                    reply = json.loads(exc.read(4096))
                except (OSError, ValueError):
                    reply = None
                finally:
                    exc.close()
                if isinstance(reply, dict) and reply.get("error") == "INVALID_REQUEST":
                    raise RuntimeError(
                        "unsupported or invalid request; inspect current computer_capabilities "
                        "or clef-use capabilities --detail --json before submitting a new request"
                    ) from None
            raise

    def _check_desktop(self, health):
        expected = desktop_scope()
        if "desktop_scope" not in health and expected is not None:
            raise RuntimeError(
                "runtime desktop ownership is unknown; stop the legacy service explicitly"
            )
        if health.get("desktop_scope") != expected:
            raise RuntimeError("runtime belongs to another desktop; match the desktop environment")

    def _matching_runtime(self, health):
        self._check_desktop(health)
        if health.get("version") != __version__:
            try:
                remote = Version(health.get("version", ""))
            except (InvalidVersion, TypeError):
                raise RuntimeError(
                    "runtime version is unknown; reload the current executable"
                ) from None
            if remote > Version(__version__):
                raise RuntimeError(
                    "a newer runtime is already running; reload the current clef-use executable "
                    "and MCP session; the service was not replaced"
                )
            return False
        if (
            health.get("runtime_protocol_version") != RUNTIME_PROTOCOL_VERSION
            or health.get("schema_sha256") != schema_sha256()
        ):
            raise RuntimeError(
                "runtime contract differs; finish or abort its active session, explicitly stop "
                "the idle service, then reload the current clef-use executable and MCP session"
            )
        return True

    def _ensure(self):
        try:
            health = self._send("health", {})
            if self._matching_runtime(health):
                return
            if health.get("busy"):
                raise RuntimeError(
                    "previous runtime version is active; finish or abort it first using its "
                    "retained matching executable, then reload the current MCP session"
                )
            if not self.start:
                raise RuntimeError("runtime version differs; reload the matching executable")
        except (OSError, ValueError):
            if not self.start:
                raise RuntimeError("runtime service is not running") from None
        root = state_dir()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with FileLock(root / "start.lock", timeout=15):
            try:
                health = self._send("health", {})
                if self._matching_runtime(health):
                    return
                if health.get("busy"):
                    raise RuntimeError(
                        "previous runtime version is active; finish or abort it first using its "
                        "retained matching executable, then reload the current MCP session"
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
                    if self._matching_runtime(health):
                        return
                    raise RuntimeError(
                        "runtime version differs after startup; reload the executable"
                    )
                except (OSError, ValueError):
                    time.sleep(0.1)
            raise RuntimeError("runtime service did not start")

    def request(self, route, **data):
        if route == "observe" and not isinstance(data.get("refresh", True), bool):
            raise ValueError("refresh must be a boolean")
        endpoint = None
        if route == "observe" and data.get("refresh", True) is False:
            try:
                endpoint = self._endpoint()
                health = self._send("health", {}, endpoint=endpoint)
            except (OSError, ValueError):
                raise RuntimeError(
                    "runtime service is not running; cached reads cannot start it"
                ) from None
            self._check_desktop(health)
            capabilities = health.get("capabilities")
            if not isinstance(capabilities, dict) or capabilities.get("cached_observe") is not True:
                raise RuntimeError(
                    "runtime does not support cached observations; update it explicitly while idle"
                )
            if not self._matching_runtime(health):
                raise RuntimeError("runtime version differs; reload the matching executable")
        else:
            self._ensure()
        try:
            return (
                self._send(route, data, endpoint=endpoint)
                if endpoint is not None
                else self._send(route, data)
            )
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
            raise RuntimeError(f"runtime refused {route}; inspect session status") from None

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

    def continue_session(self, session_id, instruction, operation=None):
        return self.wait(
            self.request(
                "continue",
                session_id=session_id,
                instruction=instruction,
                **({"operation": operation} if operation is not None else {}),
            )
        )
