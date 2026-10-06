import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from clef_use.benchmark import fixture_runtime
from clef_use.service import SessionManager, make_server


@pytest.fixture
def service(tmp_path, monkeypatch):
    manager = SessionManager(fixture_runtime)
    server = make_server(manager, "test-scoped-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    (tmp_path / "endpoint.json").write_text(
        json.dumps({"port": server.server_port, "token": "test-scoped-token", "pid": os.getpid()})
    )
    monkeypatch.setenv("CLEF_USE_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("CLEF_USE_CONFIG", str(tmp_path / "absent.toml"))
    yield server, manager, tmp_path
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_cli_reaches_shared_runtime_core(service):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "clef_use.cli",
            "run",
            "Open Settings and apply size 16",
            "--max-steps",
            "8",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["status"] == "COMPLETED" and data["steps"] == 2
    assert service[1].get(data["session_id"]).steps == 2


async def test_real_stdio_mcp_runs_same_service_and_lists_only_high_level_tools(service):
    parameters = StdioServerParameters(
        command=sys.executable, args=["-m", "clef_use.cli", "mcp"], env=dict(os.environ)
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            assert {t.name for t in listed.tools} == {
                "computer_run",
                "computer_continue",
                "computer_observe",
                "computer_status",
                "computer_abort",
            }
            result = await session.call_tool(
                "computer_run", {"goal": "Open Settings and apply size 16", "max_steps": 8}
            )
            assert not result.isError
            data = result.structuredContent
            assert data["status"] == "COMPLETED" and data["steps"] == 2
            assert service[1].get(data["session_id"]).rounds == 4
            status = await session.call_tool("computer_status", {"session_id": data["session_id"]})
            assert status.structuredContent["status"] == "COMPLETED"


@pytest.mark.parametrize("operation", ["status", "observe", "abort"])
def test_idle_session_requests_explain_how_to_start(service, operation):
    from clef_use.client import RuntimeClient

    with pytest.raises(RuntimeError, match="no active session; start computer_run first"):
        RuntimeClient(start=False).request(operation, session_id=None)
    assert service[1].runtime is None
    assert not service[1].busy
    assert not service[1].sessions


def test_unknown_session_is_distinguished_from_idle(service):
    from clef_use.client import RuntimeClient

    with pytest.raises(RuntimeError, match="session not found; it may have expired or restarted"):
        RuntimeClient(start=False).request("status", session_id="unknown")


def test_loopback_api_rejects_unauthenticated_and_browser_origin_requests(service):
    server = service[0]
    url = f"http://127.0.0.1:{server.server_port}/health"
    for headers in (
        {},
        {"Authorization": "Bearer test-scoped-token", "Origin": "https://evil.example"},
    ):
        request = urllib.request.Request(
            url, data=b"{}", headers={"Content-Type": "application/json", **headers}
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(request)
        assert exc.value.code == 403
