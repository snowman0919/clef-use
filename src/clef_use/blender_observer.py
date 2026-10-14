"""Read-only Blender UI-thread snapshot server with native local peer identity.

Run this installed file with Blender's --python and pass --clef-state-dir
after --. The directory must be newly created by this process. No operations,
scene writes, arbitrary code, paths, or client-supplied facts are accepted.
"""

from __future__ import annotations

import argparse
import atexit
import importlib.util
import json
import os
import queue
import socket
import stat
import struct
import sys
import threading
from pathlib import Path

MAX_RESPONSE_BYTES = 2 * 1024 * 1024


def private_directory(path: Path):
    info = path.lstat()
    if sys.platform == "win32":
        from .windows_observer import private_path

        if not stat.S_ISDIR(info.st_mode) or info.st_file_attributes & 0x400:
            raise ValueError("observer directory must be owned, private, and not a symlink")
        private_path(path)
        return
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("observer directory must be owned, private, and not a symlink")


def peer_credentials(connection):
    if sys.platform == "win32":
        from .windows_observer import peer_credentials as native_peer_credentials

        return native_peer_credentials(connection)
    return struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))


def current_user():
    if sys.platform == "win32":
        from .windows_observer import process_user

        return process_user(os.getpid())
    return os.getuid()


def observer_address(path):
    private_directory(path.parent)
    info = path.lstat()
    if sys.platform == "win32":
        from .windows_observer import private_path

        if not stat.S_ISREG(info.st_mode) or info.st_file_attributes & 0x400:
            raise ValueError("observer endpoint must be a regular private file")
        private_path(path)
        with path.open("rb") as stream:
            data = stream.read(513)
        if len(data) > 512:
            raise ValueError("observer endpoint metadata exceeds limit")
        endpoint = json.loads(data)
        if (
            not isinstance(endpoint, dict)
            or set(endpoint) != {"port"}
            or type(endpoint["port"]) is not int
            or not 1 <= endpoint["port"] <= 65535
        ):
            raise ValueError("invalid observer endpoint metadata")
        return "127.0.0.1", endpoint["port"]
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("observer socket ownership or permissions mismatch")
    return str(path)


def read_message(connection, limit):
    data = bytearray()
    while len(data) <= limit:
        part = connection.recv(min(4096, limit + 1 - len(data)))
        if not part:
            raise ValueError("incomplete observer message")
        data.extend(part)
        if b"\n" in part:
            if not data.endswith(b"\n") or data.count(b"\n") != 1:
                raise ValueError("invalid observer framing")
            return json.loads(data)
    raise ValueError("observer message exceeds limit")


class SnapshotServer:
    """Network thread queues fixed requests; pump() runs only on the UI thread."""

    def __init__(self, directory: Path, collect):
        if sys.platform == "win32":
            from .windows_observer import create_private_directory

            create_private_directory(directory)
        elif sys.platform == "linux":
            directory.mkdir(mode=0o700, parents=False, exist_ok=False)
        else:
            raise RuntimeError("Blender observer requires Linux or Windows native peer identity")
        private_directory(directory)
        self.path = directory / "state.sock"
        self.collect = collect
        self.requests = queue.Queue(maxsize=1)
        self.stopped = threading.Event()
        self.listener = None
        self.identity = None
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def start(self):
        # In Blender this runs from the first UI timer, after startup can
        # actually service sampling requests. Socket existence is not asserted
        # before the main thread has reached its event loop.
        if self.listener is not None or self.stopped.is_set():
            raise RuntimeError("observer already started or closed")
        if sys.platform == "win32":
            from .windows_observer import write_private_metadata

            self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.listener.bind(("127.0.0.1", 0))
            write_private_metadata(
                self.path, json.dumps({"port": self.listener.getsockname()[1]}).encode()
            )
        else:
            self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.listener.bind(str(self.path))
            os.chmod(self.path, 0o600)
        self.identity = self.path.stat().st_ino
        self.listener.listen(1)
        self.listener.settimeout(0.1)
        self.thread.start()

    def pump(self):
        if self.stopped.is_set():
            return None
        try:
            nonce, event, result = self.requests.get_nowait()
        except queue.Empty:
            return 0.01
        try:
            result.update(nonce=nonce, snapshot=self.collect())
        except Exception as exc:
            # Do not expose scene names or raw Blender exception content.
            result.update(nonce=nonce, error="snapshot unavailable", error_type=type(exc).__name__)
            if type(exc).__name__ == "SnapshotUnavailable":
                result["failed_check"] = str(exc)
        event.set()
        return 0.01

    def _serve(self):
        while not self.stopped.is_set():
            try:
                connection, _ = self.listener.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            with connection:
                try:
                    connection.settimeout(0.5)
                    _, uid, _ = peer_credentials(connection)
                    if uid != current_user():
                        continue
                    request = read_message(connection, 1024)
                    if (
                        not isinstance(request, dict)
                        or set(request) != {"request", "nonce"}
                        or request["request"] != "snapshot"
                        or not isinstance(request["nonce"], str)
                        or len(request["nonce"]) != 32
                    ):
                        continue
                    event, result = threading.Event(), {}
                    self.requests.put_nowait((request["nonce"], event, result))
                    if not event.wait(0.4):
                        connection.sendall(
                            json.dumps(
                                {
                                    "nonce": request["nonce"],
                                    "error": "snapshot unavailable",
                                    "error_type": "TimeoutError",
                                    "failed_check": "UI thread did not sample within 400ms",
                                }
                            ).encode()
                            + b"\n"
                        )
                        continue
                    data = json.dumps(result, allow_nan=False, separators=(",", ":")).encode()
                    if len(data) > MAX_RESPONSE_BYTES:
                        continue
                    connection.sendall(data + b"\n")
                except (OSError, ValueError, queue.Full):
                    continue

    def close(self):
        self.stopped.set()
        if self.listener is not None:
            self.listener.close()
        if self.thread.is_alive():
            self.thread.join(timeout=1)
        try:
            if self.identity is not None and self.path.lstat().st_ino == self.identity:
                self.path.unlink()
        except FileNotFoundError:
            pass


def main():
    import bpy

    parser = argparse.ArgumentParser()
    parser.add_argument("--clef-state-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    # Load this package's standalone helpers without the runtime's ML dependencies.
    if __package__ in (None, ""):
        import types

        package = types.ModuleType("clef_blender_observer")
        package.__path__ = [str(Path(__file__).parent)]
        sys.modules[package.__name__] = package
        globals()["__package__"] = package.__name__
    path = Path(__file__).with_name("blender_snapshot.py")
    spec = importlib.util.spec_from_file_location("clef_blender_snapshot", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = SnapshotServer(args.clef_state_dir, module.collect_snapshot)
    bpy.app.timers.register(server.pump, first_interval=0.01, persistent=True)
    bpy.app.timers.register(server.start, first_interval=0.01)
    atexit.register(server.close)


if __name__ == "__main__":
    main()
