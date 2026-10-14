"""Native Windows boundaries for the read-only Blender observation transport."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path


@unittest.skipUnless(sys.platform == "win32", "Windows native peer identity and NTFS ACLs required")
class WindowsObserverTests(unittest.TestCase):
    def setUp(self):
        from clef_use.windows_observer import create_private_directory

        self.temporary = tempfile.TemporaryDirectory(prefix="clef-observer-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.private = self.root / "private"
        create_private_directory(self.private)

    def test_metadata_is_private_and_existing_user_bytes_are_preserved(self):
        from clef_use.blender_observer import observer_address
        from clef_use.windows_observer import private_path, write_private_metadata

        path = self.private / "endpoint"
        data = b'{"port":23456}'
        write_private_metadata(path, data)
        private_path(path)
        self.assertEqual(observer_address(path), ("127.0.0.1", 23456))
        with self.assertRaises(FileExistsError):
            write_private_metadata(path, b'{"port":34567}')
        self.assertEqual(path.read_bytes(), data)

    def test_endpoint_cannot_redirect_connection_or_coerce_port(self):
        from clef_use.blender_observer import observer_address
        from clef_use.windows_observer import write_private_metadata

        cases = [
            {"port": 0},
            {"port": 65536},
            {"port": True},
            {"port": "12345"},
            {"port": 12345, "host": "192.0.2.1"},
            [],
            None,
        ]
        for index, value in enumerate(cases):
            with self.subTest(value=value):
                path = self.private / str(index)
                write_private_metadata(path, json.dumps(value).encode())
                with self.assertRaises(ValueError):
                    observer_address(path)

    def test_oversize_metadata_is_refused_without_creating_endpoint(self):
        from clef_use.windows_observer import write_private_metadata

        path = self.private / "oversize"
        with self.assertRaises(ValueError):
            write_private_metadata(path, b"x" * 513)
        self.assertFalse(path.exists())

    def test_failed_or_short_native_write_removes_only_new_endpoint(self):
        import ctypes
        from unittest.mock import patch

        from clef_use.windows_observer import api, write_private_metadata

        kernel, _, _ = api()
        for name, result in (("failed", 0), ("short", 1)):
            with self.subTest(name=name):
                path = self.private / name

                def incomplete_write(*_, write_result=result):
                    ctypes.set_last_error(112)
                    return write_result

                # Creation/ACL/handle lifetime use the real OS. Inject the I/O
                # fault and assert the resulting filesystem, not mock calls.
                with patch.object(kernel, "WriteFile", side_effect=incomplete_write):
                    with self.assertRaises(OSError):
                        write_private_metadata(path, b'{"port":23456}')
                self.assertFalse(path.exists())

    def test_foreign_acl_grant_refuses_endpoint(self):
        from clef_use.blender_observer import observer_address
        from clef_use.windows_observer import write_private_metadata

        path = self.private / "endpoint"
        write_private_metadata(path, b'{"port":23456}')
        subprocess.run(
            ["icacls.exe", str(path), "/grant", "*S-1-1-0:R"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with self.assertRaises(ValueError):
            observer_address(path)

    def test_directory_reuse_preserves_existing_files(self):
        from clef_use.blender_observer import SnapshotServer

        path = self.private / "user.txt"
        path.write_bytes(b"preserve user bytes")
        with self.assertRaises(FileExistsError):
            SnapshotServer(self.private, lambda: {})
        self.assertEqual(path.read_bytes(), b"preserve user bytes")

    def test_native_peer_pid_identifies_distinct_connected_process(self):
        from clef_use.windows_observer import peer_credentials, process_user

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            listener.settimeout(5)
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    "import os,socket,sys; "
                    "s=socket.create_connection(('127.0.0.1',int(sys.argv[1])));"
                    "s.sendall(str(os.getpid()).encode()+b'\\n'); s.recv(1); s.close()",
                    str(listener.getsockname()[1]),
                ]
            )
            try:
                with listener.accept()[0] as connection:
                    # Windows venv launchers can delegate to a second process.
                    # Compare with the actual Python receiver, not its launcher.
                    receiver_pid = int(connection.makefile("rb").readline(32))
                    pid, user, _ = peer_credentials(connection)
                    self.assertEqual(pid, receiver_pid)
                    self.assertNotEqual(pid, os.getpid())
                    self.assertEqual(user, process_user(os.getpid()))
                    connection.sendall(b"y")
                self.assertEqual(child.wait(timeout=5), 0)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)

    def test_server_samples_only_on_ui_thread_and_rejects_commands(self):
        from clef_use.blender_observer import SnapshotServer, observer_address, read_message

        calls = []
        server = SnapshotServer(
            self.root / "server",
            lambda: calls.append(threading.get_ident()) or {"selection": ["Cube"]},
        )
        self.addCleanup(server.close)
        server.start()
        responses, errors = [], []

        def request():
            try:
                with socket.create_connection(
                    observer_address(server.path), timeout=2
                ) as connection:
                    connection.sendall(
                        b'{"request":"snapshot","nonce":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}\n'
                    )
                    responses.append(read_message(connection, 4096))
            except BaseException as exc:
                errors.append(exc)

        worker = threading.Thread(target=request)
        worker.start()
        deadline = time.monotonic() + 2
        while server.requests.empty() and time.monotonic() < deadline:
            time.sleep(0.001)
        self.assertEqual(calls, [])
        server.pump()
        worker.join(timeout=3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(responses, [{"nonce": "a" * 32, "snapshot": {"selection": ["Cube"]}}])
        self.assertEqual(calls, [threading.get_ident()])
        with socket.create_connection(observer_address(server.path), timeout=2) as connection:
            connection.sendall(
                b'{"request":"execute","nonce":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}\n'
            )
            self.assertEqual(connection.recv(1), b"")
        server.pump()
        self.assertEqual(calls, [threading.get_ident()])
        server.close()
        self.assertFalse(server.path.exists())


if __name__ == "__main__":
    unittest.main()
