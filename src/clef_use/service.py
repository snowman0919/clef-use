from __future__ import annotations

import base64
import json
import os
import secrets
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from filelock import FileLock

from . import __version__
from .backends import runtime
from .config import load_config, state_dir
from .runtime import Session
from .schema import Contract, Status


class SessionManager:
    def __init__(self, factory=None):
        self.factory = factory or (lambda: runtime(load_config(), state_dir() / "steps.jsonl"))
        self.runtime = None
        self.sessions = {}
        self.active = None
        self.lock = threading.RLock()
        self.busy = False
        self.stopping = False

    def _execute(self, session):
        try:
            if self.runtime is None:
                self.runtime = self.factory()
            self.runtime.execute(session)
        except Exception as exc:
            with session.lock:
                session.status, session.reason = (
                    Status.ERROR,
                    f"{type(exc).__name__}: runtime initialization failed; run doctor",
                )
        finally:
            with self.lock:
                self.busy = False

    def _launch(self, session):
        if self.busy:
            raise RuntimeError("another session owns the desktop")
        self.active = session.id
        self.busy = True
        threading.Thread(target=self._execute, args=(session,), daemon=True).start()
        return session.snapshot()

    def run(self, data):
        session = Session(Contract.model_validate(data))
        with self.lock:
            if self.stopping:
                raise RuntimeError("service is stopping")
            if self.busy:
                session.status = Status.SAFETY_BLOCK
                session.reason = "another session owns the desktop or is finishing cancellation"
                self.sessions[session.id] = session
                return session.snapshot()
            if len(self.sessions) >= 64:
                removable = next(
                    (s for s in self.sessions if self.sessions[s].status != Status.RUNNING), None
                )
                if removable:
                    del self.sessions[removable]
            self.sessions[session.id] = session
            return self._launch(session)

    def get(self, session_id=None):
        with self.lock:
            return self.sessions[session_id or self.active]

    def continue_session(self, session_id, instruction):
        if not isinstance(instruction, str) or not instruction.strip() or len(instruction) > 1000:
            raise ValueError("instruction must be 1 to 1000 characters")
        with self.lock:
            if self.busy or self.stopping:
                raise RuntimeError("previous execution is still finishing")
            session = self.get(session_id)
            if session.status not in {
                Status.NEEDS_REPLAN,
                Status.LOW_CONFIDENCE,
                Status.NO_PROGRESS,
                Status.BLOCKED,
            }:
                raise ValueError("session status cannot be resumed")
            if session.rounds >= session.contract.max_steps:
                raise ValueError("create a new contract after budget exhaustion")
            session.guidance.append(instruction)
            session.status, session.reason = Status.RUNNING, "resumed with planner guidance"
            return self._launch(session)

    def dispatch(self, operation, data):
        if operation == "run":
            return self.run(data)
        if operation == "continue":
            return self.continue_session(data["session_id"], data["instruction"])
        if operation == "health":
            return {"ok": True, "pid": os.getpid(), "version": __version__, "busy": self.busy}
        if operation == "shutdown_idle":
            with self.lock:
                if self.busy:
                    raise RuntimeError("cannot restart a service that owns the desktop")
                self.stopping = True
            return {"ok": True}
        session = self.get(data.get("session_id"))
        if operation == "status":
            return session.snapshot()
        if operation == "abort":
            session.cancelled.set()
            if self.runtime:
                return self.runtime.abort(session)
            session.status, session.reason = Status.ABORTED, "abort requested"
            return session.snapshot()
        if operation == "observe":
            with self.lock:
                if not self.runtime:
                    return session.snapshot()
                refresh = not self.busy and not self.stopping
                if refresh:
                    self.busy = True
            try:
                return self.runtime.observe(
                    session, refresh=refresh, include_image=bool(data.get("include_image"))
                )
            finally:
                if refresh:
                    with self.lock:
                        self.busy = False
        raise ValueError("unknown operation")


def make_server(manager, token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            if (
                self.headers.get("Origin") is not None
                or self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}"
                or not secrets.compare_digest(
                    self.headers.get("Authorization", ""), "Bearer " + token
                )
            ):
                self.send_error(403)
                return
            if self.headers.get("Content-Type") != "application/json":
                self.send_error(415)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    raise ValueError("request size")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("request must be an object")
                result = manager.dispatch(self.path.removeprefix("/"), data)
                if self.path == "/shutdown_idle":
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                status = 200
            except (ValueError, KeyError, RuntimeError) as exc:
                result, status = {"error": type(exc).__name__}, 400
            raw = json.dumps(result).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)


def main():
    root = state_dir()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    with FileLock(root / "service.lock", timeout=0):
        token = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        manager = SessionManager()
        server = make_server(manager, token)
        endpoint = root / "endpoint.json"
        temporary = root / "endpoint.tmp"
        fd = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump({"port": server.server_port, "token": token, "pid": os.getpid()}, stream)
        temporary.replace(endpoint)

        def shutdown(*_):
            with manager.lock:
                for session in manager.sessions.values():
                    if session.status == Status.RUNNING:
                        manager.dispatch("abort", {"session_id": session.id})
            threading.Thread(target=server.shutdown, daemon=True).start()

        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)
        try:
            server.serve_forever(poll_interval=0.2)
        finally:
            server.server_close()
            if manager.runtime:
                manager.runtime.activity.close()
                for backend in (manager.runtime.perception, manager.runtime.decision):
                    worker = getattr(backend, "worker", None)
                    if worker:
                        worker.close()
            endpoint.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
