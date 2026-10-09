import base64
import io
import json
import os
import sys
import threading

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image

from clef_use.benchmark import fixture_runtime
from clef_use.runtime import Session
from clef_use.schema import Contract, Observation, Status
from clef_use.service import SessionManager, make_server


def previous_observation(executor, session):
    session.observation = Observation(
        "old", executor.capture.capture(), executor.perception.parse(None)
    )
    executor.capture.stage = 1


def test_observe_preview_has_its_own_pixel_identity_and_native_parent():
    import hashlib

    from clef_use.schema import Frame

    executor = fixture_runtime()
    executor.capture.capture = lambda: Frame(Image.new("RGB", (1920, 1080), "white"))
    result = executor.observe(include_image=True)
    image = Image.open(io.BytesIO(base64.b64decode(result["image_png"])))
    assert image.size == (1280, 720)
    assert result["preview_reference"] == {
        "image_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
        "image_size": [1280, 720],
        "image_mode": "RGB",
        "derived_from_frame_sha256": result["frame_reference"]["image_sha256"],
    }
    assert result["preview_reference"]["image_sha256"] != result["image_sha256"]


def test_idle_observe_refreshes_without_actions_or_decisions():
    executor = fixture_runtime()
    session = Session(Contract(goal="test"), status=Status.NEEDS_REPLAN)
    previous_observation(executor, session)
    result = executor.observe(session, include_image=True)
    assert result["observation_fresh"] and result["observation_id"] != "old"
    assert result["objects"][0]["label"] == "Apply"
    image = Image.open(io.BytesIO(base64.b64decode(result["image_png"])))
    assert image.getpixel((0, 0)) == (173, 216, 230)
    assert session.steps == session.rounds == 0
    assert executor.action.released == 0 and session.status == Status.NEEDS_REPLAN


def test_observe_before_first_run_binds_fresh_pixels_without_creating_a_session():
    executor = fixture_runtime()
    executor.capture.stage = 1
    manager = SessionManager(lambda: executor)
    result = manager.dispatch("observe", {"include_image": True})
    assert result["session_id"] is None
    assert result["observation_fresh"] and result["objects"][0]["label"] == "Apply"
    image = Image.open(io.BytesIO(base64.b64decode(result["image_png"])))
    assert image.getpixel((0, 0)) == (173, 216, 230)
    assert result["frame_reference"] == executor.capture.capture().reference().model_dump(
        mode="json"
    )
    assert manager.active is None and not manager.sessions and not manager.busy
    assert executor.action.released == 0


def test_first_observation_reserves_input_during_runtime_initialization():
    executor = fixture_runtime()
    entered, unblock = threading.Event(), threading.Event()

    def factory():
        entered.set()
        assert unblock.wait(5)
        return executor

    manager = SessionManager(factory)
    results = []
    worker = threading.Thread(target=lambda: results.append(manager.dispatch("observe", {})))
    worker.start()
    try:
        assert entered.wait(5)
        cached = manager.dispatch("observe", {})
        assert not cached["observation_fresh"] and cached["objects"] == []
        assert cached["frame_reference"] is None and cached["observation_id"] is None
        assert manager.run({"goal": "concurrent input"})["status"] == "SAFETY_BLOCK"
    finally:
        unblock.set()
        worker.join(5)
    assert not worker.is_alive() and not manager.busy
    assert results[0]["observation_fresh"] and executor.action.released == 0


def test_observation_reserves_desktop_and_cached_reads_do_not_parse():
    executor = fixture_runtime()
    session = Session(Contract(goal="test"), status=Status.NEEDS_REPLAN)
    previous_observation(executor, session)
    manager = SessionManager(lambda: executor)
    manager.runtime, manager.active = executor, session.id
    manager.sessions[session.id] = session
    entered, unblock = threading.Event(), threading.Event()
    original = executor.perception.parse

    class BlockingParser:
        def parse(self, image):
            entered.set()
            assert unblock.wait(5)
            return original(image)

    executor.perception = BlockingParser()
    result = []
    worker = threading.Thread(target=lambda: result.append(manager.dispatch("observe", {})))
    worker.start()
    try:
        assert entered.wait(5)
        assert manager.run({"goal": "concurrent"})["status"] == "SAFETY_BLOCK"
        cached = manager.dispatch("observe", {"session_id": session.id})
        assert not cached["observation_fresh"]
        assert cached["observation_id"] == "old"
    finally:
        unblock.set()
        worker.join(5)
    assert not worker.is_alive() and not manager.busy
    assert result[0]["observation_fresh"] and session.steps == session.rounds == 0
    assert executor.action.released == 0


async def test_stdio_observe_returns_matching_fresh_objects_and_pixels(tmp_path, monkeypatch):
    executor = fixture_runtime()
    session = Session(Contract(goal="test"), status=Status.NEEDS_REPLAN)
    previous_observation(executor, session)
    manager = SessionManager(lambda: executor)
    manager.runtime, manager.active = executor, session.id
    manager.sessions[session.id] = session
    server = make_server(manager, "observation-test-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    (tmp_path / "endpoint.json").write_text(
        json.dumps(
            {"port": server.server_port, "token": "observation-test-token", "pid": os.getpid()}
        )
    )
    monkeypatch.setenv("CLEF_USE_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("CLEF_USE_CONFIG", str(tmp_path / "absent.toml"))
    parameters = StdioServerParameters(
        command=sys.executable, args=["-m", "clef_use.cli", "mcp"], env=dict(os.environ)
    )
    try:
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                result = await client.call_tool(
                    "computer_observe", {"session_id": session.id, "include_image": True}
                )
                assert not result.isError
                data = json.loads(result.content[0].text)
                assert data["observation_fresh"] and data["objects"][0]["label"] == "Apply"
                image = Image.open(io.BytesIO(base64.b64decode(result.content[1].data)))
                assert image.getpixel((0, 0)) == (173, 216, 230)
                assert data["steps"] == data["rounds"] == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)
