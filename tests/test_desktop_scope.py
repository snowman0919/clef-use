import json
import os
import sys
import threading
import urllib.error
import urllib.request

import pytest

from clef_use.client import RuntimeClient
from clef_use.config import state_dir
from clef_use.service import SessionManager, make_server

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux desktop scoping")


def test_different_x11_desktops_do_not_share_runtime_endpoint(monkeypatch, tmp_path):
    monkeypatch.delenv("CLEF_USE_STATE_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DISPLAY", ":122")
    task_endpoint = state_dir() / "endpoint.json"
    monkeypatch.setenv("DISPLAY", ":0")
    other_endpoint = state_dir() / "endpoint.json"
    assert other_endpoint != task_endpoint
    monkeypatch.setenv("DISPLAY", ":122")
    assert state_dir() / "endpoint.json" == task_endpoint


@pytest.mark.parametrize("start", [False, True])
@pytest.mark.parametrize("version_mismatch", [False, True])
@pytest.mark.parametrize("reports_ownership", [False, True])
def test_shared_override_refuses_foreign_desktop_without_stopping_it(
    monkeypatch, tmp_path, start, version_mismatch, reports_ownership
):
    monkeypatch.setenv("CLEF_USE_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("DISPLAY", ":122")
    if version_mismatch:
        monkeypatch.setattr("clef_use.service.__version__", "previous-test-version")

    def forbid_runtime():
        raise AssertionError("protocol test must not initialize a GUI or model backend")

    def forbid_spawn(*args, **kwargs):
        raise AssertionError("protocol test must not spawn a runtime process")

    monkeypatch.setattr("clef_use.client.subprocess.Popen", forbid_spawn)
    manager = SessionManager(forbid_runtime)
    if not reports_ownership:
        dispatch = manager.dispatch

        def legacy_dispatch(operation, data):
            result = dispatch(operation, data)
            if operation == "health":
                result.pop("desktop_scope")
            return result

        monkeypatch.setattr(manager, "dispatch", legacy_dispatch)
    server = make_server(manager, "test-only-scope-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = tmp_path / "endpoint.json"
    endpoint.write_text(
        json.dumps(
            {"port": server.server_port, "token": "test-only-scope-token", "pid": os.getpid()}
        )
    )
    monkeypatch.setenv("DISPLAY", ":0")
    try:
        reason = "another desktop" if reports_ownership else "ownership is unknown"
        with pytest.raises(RuntimeError, match=reason):
            RuntimeClient(start=start).request("health")
        assert not manager.stopping
        assert manager.runtime is None
        assert endpoint.exists()
        assert thread.is_alive()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_x11_default_screen_alias_reuses_runtime(monkeypatch, tmp_path):
    monkeypatch.delenv("CLEF_USE_STATE_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DISPLAY", ":122")
    root = state_dir()
    monkeypatch.setenv("DISPLAY", ":122.0")
    assert state_dir() == root


def test_legacy_client_cannot_shutdown_a_scoped_service(monkeypatch):
    monkeypatch.setenv("DISPLAY", ":122")
    manager = SessionManager()
    server = make_server(manager, "test-only-scope-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.server_port}/shutdown_idle",
        data=b"{}",
        headers={
            "Authorization": "Bearer test-only-scope-token",
            "Content-Type": "application/json",
        },
    )
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=5)
        assert caught.value.code == 403
        assert json.loads(caught.value.read())["error"] == "DESKTOP_MISMATCH"
        assert not manager.stopping and manager.runtime is None
        assert thread.is_alive()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
