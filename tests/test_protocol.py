import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from types import SimpleNamespace

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from clef_use.benchmark import fixture_runtime
from clef_use.client import RuntimeClient
from clef_use.schema import Decision
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


async def test_real_stdio_mcp_reports_confidence_gate_and_matching_status(service, monkeypatch):
    class RecordedAssessment:
        def decide(self, observation, goal, candidates, history):
            assert candidates == ()
            # Recorded decision scores with synthetic fixture capture, not new inference.
            return Decision(
                mode="ACT",
                mode_confidence=0.4444,
                confidence=1.0,
                goal_probability=0.1578,
                condition_probabilities=(0.1647,),
            )

    service[1].runtime = fixture_runtime()
    service[1].runtime.decision = RecordedAssessment()
    parameters = StdioServerParameters(
        command=sys.executable, args=["-m", "clef_use.cli", "mcp"], env=dict(os.environ)
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            result = await client.call_tool(
                "computer_run",
                {
                    "goal": "Assess Settings",
                    "success_conditions": ["Settings open"],
                    "execution_mode": "ASSESS",
                    "max_steps": 3,
                },
            )
            assert not result.isError
            data = result.structuredContent
            assert data["status"] == "LOW_CONFIDENCE" and data["confidence"] == 1.0
            assert data["steps"] == 0 and data["rounds"] == 1 and data["last_action"] is None
            assert data["blocker"]["kind"] == "CONFIDENCE_BELOW_THRESHOLD"
            observed = data["blocker"]["observed"]
            assert observed["source"] == "execution_mode"
            assert observed["probability"] == observed["mode_confidence"] == 0.4444
            assert observed["probability"] < observed["required_probability"]
            assert observed["action_selection_confidence"] == 1.0
            assert observed["goal_probability"] == 0.1578
            assert observed["condition_probabilities"] == [0.1647]
            status = await client.call_tool("computer_status", {"session_id": data["session_id"]})
            assert not status.isError
            assert status.structuredContent["blocker"] == data["blocker"]
            assert status.structuredContent["status"] == "LOW_CONFIDENCE"

            class DeferredWorkerThread:
                def __init__(self, *, target, args, daemon):
                    pass

                def start(self):
                    pass

            # Pause only the worker scheduler, not HTTP, MCP, or session state transitions.
            monkeypatch.setattr(
                "clef_use.service.threading", SimpleNamespace(Thread=DeferredWorkerThread)
            )
            resumed = RuntimeClient(start=False).request(
                "continue",
                session_id=data["session_id"],
                instruction="Use the new visible evidence",
            )
            assert resumed["status"] == "RUNNING" and resumed["blocker"] is None
            status = await client.call_tool("computer_status", {"session_id": data["session_id"]})
            assert not status.isError
            assert status.structuredContent["status"] == "RUNNING"
            assert status.structuredContent["blocker"] is None
            assert status.structuredContent["rounds"] == 1
            assert data["blocker"]["observed"]["probability"] == 0.4444


@pytest.mark.parametrize("operation", ["status", "abort"])
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


def test_idle_observation_waits_for_parser_beyond_control_timeout(service):
    import time

    from clef_use.client import RuntimeClient
    from clef_use.runtime import Session
    from clef_use.schema import Contract, Status

    manager = service[1]
    task = Session(Contract(goal="observe without input"), status=Status.COMPLETED)
    manager.sessions[task.id] = task
    manager.active = task.id

    class SlowObservation:
        def observe(self, session, **kwargs):
            time.sleep(5.1)
            return {**session.snapshot(), "observation_fresh": True, "objects": []}

    manager.runtime = SlowObservation()
    result = RuntimeClient(start=False).request("observe", session_id=task.id)
    assert result["observation_fresh"] is True
    assert result["steps"] == 0 and not manager.busy


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
