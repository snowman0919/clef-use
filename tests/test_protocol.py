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


@pytest.mark.parametrize("value", [None, 0, 1, "false", [], {}])
def test_invalid_observe_policy_is_rejected_before_client_startup(service, monkeypatch, value):
    endpoint = service[2] / "endpoint.json"
    endpoint.unlink()

    def refuse_start(*args, **kwargs):
        pytest.fail("invalid observe policy reached service startup")

    monkeypatch.setattr(
        "clef_use.client.subprocess",
        SimpleNamespace(Popen=refuse_start, DEVNULL=subprocess.DEVNULL),
    )
    with pytest.raises(ValueError, match="refresh must be a boolean"):
        RuntimeClient().request("observe", refresh=value)
    assert not (service[2] / "start.lock").exists()
    assert service[1].runtime is None


def test_cache_only_client_does_not_create_missing_service(service, monkeypatch):
    endpoint = service[2] / "endpoint.json"
    endpoint.unlink()

    def refuse_start(*args, **kwargs):
        pytest.fail("a missing-service cached request attempted process startup")

    monkeypatch.setattr(
        "clef_use.client.subprocess",
        SimpleNamespace(Popen=refuse_start, DEVNULL=subprocess.DEVNULL),
    )
    with pytest.raises(RuntimeError, match="cached reads cannot start it"):
        RuntimeClient().request("observe", refresh=False)
    assert not endpoint.exists() and not (service[2] / "start.lock").exists()
    assert service[1].runtime is None and not service[1].sessions


def test_cli_cache_only_does_not_initialize_cold_runtime(service):
    def refuse_runtime():
        pytest.fail("cache-only CLI must not initialize capture/parser")

    manager = service[1]
    manager.factory = refuse_runtime
    result = subprocess.run(
        [sys.executable, "-m", "clef_use.cli", "observe", "--cached"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["observation_fresh"] is False and data["observation_id"] is None
    assert data["frame_reference"] is None and data["objects"] == []
    assert manager.runtime is None and not manager.busy and not manager.sessions


def test_cache_only_client_binds_capability_and_read_to_same_service(service, monkeypatch):
    from clef_use.runtime import Session
    from clef_use.schema import Contract, Observation, Status

    first = service[1]
    first.runtime = fixture_runtime()
    recorded = Observation("selected-service-record", first.runtime.capture.capture(), ())
    task = Session(Contract(goal="Inspect recorded menu"), status=Status.LOW_CONFIDENCE)
    task.observation = recorded
    first.sessions[task.id] = task
    first.active = task.id
    other = SessionManager(fixture_runtime)
    other.runtime = fixture_runtime()
    second_operations = []
    original_second = other.dispatch

    def legacy_second(operation, data):
        second_operations.append(operation)
        if operation == "observe":
            data = {**data, "refresh": True}
        return original_second(operation, data)

    monkeypatch.setattr(other, "dispatch", legacy_second)
    server = make_server(other, "test-second-endpoint-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    original = first.dispatch

    def changed_endpoint_after_health(operation, data):
        result = original(operation, data)
        if operation == "health":
            (service[2] / "endpoint.json").write_text(
                json.dumps(
                    {
                        "port": server.server_port,
                        "token": "test-second-endpoint-token",
                        "pid": os.getpid(),
                    }
                )
            )
        return result

    monkeypatch.setattr(first, "dispatch", changed_endpoint_after_health)
    try:
        result = RuntimeClient().request("observe", refresh=False)
        assert result["observation_fresh"] is False
        assert result["observation_id"] == recorded.id and result["session_id"] == task.id
        assert not second_operations
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("older_version", [False, True])
def test_cache_only_client_refuses_legacy_before_observe_or_restart(
    service, monkeypatch, older_version
):
    manager = service[1]
    manager.runtime = fixture_runtime()
    operations = []
    dispatch = manager.dispatch

    def legacy_dispatch(operation, data):
        operations.append(operation)
        if operation == "health":
            result = dispatch(operation, data)
            result.pop("capabilities", None)
            if older_version:
                result["version"] = "0.0.0"
            return result
        if operation == "shutdown_idle":
            raise RuntimeError("legacy fixture refuses service mutation")
        if operation == "observe":
            return dispatch(operation, {**data, "refresh": True})
        return dispatch(operation, data)

    def refuse_start(*args, **kwargs):
        pytest.fail("a cache-only request tried to start a service")

    monkeypatch.setattr(manager, "dispatch", legacy_dispatch)
    monkeypatch.setattr(
        "clef_use.client.subprocess",
        SimpleNamespace(Popen=refuse_start, DEVNULL=subprocess.DEVNULL),
    )
    with pytest.raises(RuntimeError, match="does not support cached observations"):
        RuntimeClient().request("observe", refresh=False)
    assert operations == ["health"]
    assert manager.runtime.capture.stage == 0 and not manager.busy


async def test_real_stdio_mcp_cache_only_keeps_recorded_pixels_and_refusal(service):
    import base64
    import io

    from PIL import Image

    from clef_use.benchmark import FixtureDesktop
    from clef_use.runtime import Session, SessionRuntime
    from clef_use.schema import Contract, Observation, Status

    class CountingDesktop(FixtureDesktop):
        captures = 0
        parses = 0

        def capture(self):
            self.captures += 1
            return super().capture()

        def parse(self, image):
            self.parses += 1
            return super().parse(image)

    desktop = CountingDesktop()
    recorded = Observation("recorded-file-menu", desktop.capture(), desktop.parse(None))
    desktop.captures = desktop.parses = 0
    manager = service[1]
    manager.runtime = SessionRuntime(desktop, desktop, desktop, desktop)
    task = Session(
        Contract(goal="Inspect the recorded File dropdown", max_steps=3),
        status=Status.LOW_CONFIDENCE,
        rounds=1,
    )
    task.observation = recorded
    task.blocker = {"kind": "CONFIDENCE_BELOW_THRESHOLD", "observed": {"probability": 0.4444}}
    manager.sessions[task.id] = task
    manager.active = task.id
    before = task.snapshot()
    parameters = StdioServerParameters(
        command=sys.executable, args=["-m", "clef_use.cli", "mcp"], env=dict(os.environ)
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            result = await client.call_tool(
                "computer_observe",
                {"session_id": task.id, "refresh": False, "include_image": True},
            )
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["observation_fresh"] is False
            assert data["observation_id"] == recorded.id
            assert data["frame_reference"] == recorded.frame.reference().model_dump(mode="json")
            assert data["blocker"] == before["blocker"] and data["rounds"] == 1
            image = Image.open(io.BytesIO(base64.b64decode(result.content[1].data)))
            assert image.tobytes() == recorded.frame.image.tobytes()
            assert image.size == recorded.frame.image.size
    assert task.snapshot() == before and task.observation is recorded
    assert desktop.captures == desktop.parses == desktop.stage == 0


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
