import json
import os
import threading
import urllib.error
import urllib.request

import pytest

from clef_use import __version__
from clef_use.capabilities import API_SCHEMA_VERSION, capabilities
from clef_use.client import RuntimeClient
from clef_use.config import desktop_scope
from clef_use.service import SessionManager, make_server


@pytest.fixture
def idle_runtime(tmp_path, monkeypatch):
    manager = SessionManager()
    server = make_server(manager, "compatibility-test-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = tmp_path / "endpoint.json"
    endpoint.write_text(
        json.dumps(
            {"port": server.server_port, "token": "compatibility-test-token", "pid": os.getpid()}
        )
    )
    monkeypatch.setenv("CLEF_USE_STATE_DIR", str(tmp_path))
    yield server, manager, endpoint
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def request(server, route, identity, data=None):
    return urllib.request.urlopen(
        urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/{route}",
            data=json.dumps(data or {}).encode(),
            method="POST",
            headers={
                "Authorization": "Bearer compatibility-test-token",
                "Content-Type": "application/json",
                "X-Clef-Desktop-Scope": desktop_scope() or "",
                **identity,
            },
        ),
        timeout=5,
    )


@pytest.mark.parametrize("mismatch", ["missing", "version", "schema", "protocol"])
def test_incompatible_client_cannot_stop_idle_runtime(idle_runtime, mismatch):
    server, manager, endpoint = idle_runtime
    original = endpoint.read_bytes()
    identity = {
        "X-Clef-Client-Version": __version__,
        "X-Clef-Api-Schema": capabilities()["schema_sha256"],
        "X-Clef-Runtime-Protocol": "1",
    }
    if mismatch == "missing":
        identity.clear()
    else:
        identity[
            {
                "version": "X-Clef-Client-Version",
                "schema": "X-Clef-Api-Schema",
                "protocol": "X-Clef-Runtime-Protocol",
            }[mismatch]
        ] = "incompatible"
    with pytest.raises(urllib.error.HTTPError) as refused:
        request(server, "shutdown_idle", identity)
    assert refused.value.code == 409
    response = json.load(refused.value)
    assert response["error"] == "RUNTIME_CONTRACT_MISMATCH"
    assert response["runtime_version"] == __version__
    assert response["api_schema_version"] == API_SCHEMA_VERSION
    assert "reload" in response["guidance"].lower()
    assert not manager.stopping and manager.runtime is None and not manager.sessions
    assert endpoint.read_bytes() == original
    assert RuntimeClient(start=False).request("health")["busy"] is False


def test_incompatible_client_can_discover_but_cannot_read_unrelated_session(idle_runtime):
    server, manager, _ = idle_runtime
    with request(server, "health", {}) as response:
        assert json.load(response)["version"] == __version__
    with request(server, "capabilities", {}) as response:
        assert json.load(response)["schema_sha256"] == capabilities()["schema_sha256"]
    with pytest.raises(urllib.error.HTTPError) as refused:
        request(server, "status", {})
    assert refused.value.code == 409
    assert not manager.stopping and manager.runtime is None


@pytest.mark.parametrize("start", [False, True])
def test_client_refuses_newer_service_without_replacing_it(idle_runtime, monkeypatch, start):
    server, manager, endpoint = idle_runtime
    original = endpoint.read_bytes()
    monkeypatch.setattr("clef_use.service.__version__", "99.0.0")
    with pytest.raises(RuntimeError, match="newer runtime.*reload"):
        RuntimeClient(start=start).request("status")
    assert not manager.stopping and manager.runtime is None and not manager.sessions
    assert endpoint.read_bytes() == original
    with request(server, "health", {}) as response:
        assert json.load(response)["version"] == "99.0.0"


def test_client_rejects_same_version_schema_mismatch_without_dispatch(idle_runtime, monkeypatch):
    _, manager, endpoint = idle_runtime
    original = endpoint.read_bytes()
    dispatch = manager.dispatch

    def changed_contract(operation, data):
        result = dispatch(operation, data)
        if operation == "health":
            result["schema_sha256"] = "0" * 64
        return result

    monkeypatch.setattr(manager, "dispatch", changed_contract)
    with pytest.raises(RuntimeError, match="runtime contract.*reload"):
        RuntimeClient().request("status")
    assert not manager.stopping and manager.runtime is None and not manager.sessions
    assert endpoint.read_bytes() == original


def test_unsupported_operation_reports_current_discovery_without_initializing_runtime(idle_runtime):
    _, manager, _ = idle_runtime
    with pytest.raises(RuntimeError, match="unsupported or invalid request.*capabilities"):
        RuntimeClient(start=False).request(
            "run", goal="Unsupported operation must send no input", operation={"family": "shell"}
        )
    assert manager.runtime is None and not manager.sessions and not manager.busy
