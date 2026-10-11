import copy
import json
import os
import socket
import struct
import sys
import threading
import time

import pytest
from PIL import Image

from clef_use.blender_observer import SnapshotServer, peer_credentials, read_message
from clef_use.blender_state import compile_snapshot
from clef_use.schema import Frame, Observation
from clef_use.state import FactValidity, StateCompiler


def snapshot():
    now = time.time()
    return {
        "schema_version": 1,
        "source": "BLENDER_PUBLIC_RNA",
        "pid": 123,
        "sampled_at": now,
        "completed_at": now,
        "windows": [
            {
                "width": 100,
                "height": 80,
                "selection": ["Cube"],
                "active_object_mode": "OBJECT",
                "objects": {"Cube": {"properties": {"location_x": 2.5, "shading": "FLAT"}}},
                "positive_modal_operators": [],
                "areas": [],
            }
        ],
    }


def compile_document(document):
    frame = Frame(
        Image.new("RGB", (100, 80)), foreground_window=42, foreground_bounds=(0, 0, 100, 80)
    )
    facts = compile_snapshot(
        document,
        pid=123,
        frame=frame,
        version=1,
        started_at=document["sampled_at"] - 0.01,
        completed_at=document["sampled_at"] + 0.01,
    )
    return StateCompiler().compile(Observation("scene", frame, ()), facts)


def test_partial_scene_evidence_preserves_numbers_without_inventing_input_context():
    state = compile_document(snapshot())
    assert state.require("selection") == ["Cube"]
    assert state.require("properties")["Cube"]["location_x"] == 2.5
    assert state.require("mode") == "OBJECT"
    assert state.access_level == "APP_TELEMETRY_ASSISTED"
    for name in ("modal", "popup", "text_focus", "ime_composing", "keymap", "loading", "unit"):
        assert state.fact(name).validity == FactValidity.UNKNOWN


@pytest.mark.parametrize("change", ["pid", "stale", "future", "windows", "size", "source"])
def test_wrong_process_age_or_ambiguous_window_refuses_scene_evidence(change):
    document = snapshot()
    frame = Frame(
        Image.new("RGB", (100, 80)), foreground_window=42, foreground_bounds=(0, 0, 100, 80)
    )
    start, end = document["sampled_at"] - 0.01, document["sampled_at"] + 0.01
    if change == "pid":
        document["pid"] = 999
    elif change == "stale":
        end += 1
    elif change == "future":
        document["sampled_at"] = end + 1
    elif change == "windows":
        document["windows"].append(copy.deepcopy(document["windows"][0]))
    elif change == "size":
        document["windows"][0]["width"] = 101
    elif change == "source":
        document["source"] = "CALLER_FACTS"
    with pytest.raises(ValueError):
        compile_snapshot(
            document, pid=123, frame=frame, version=1, started_at=start, completed_at=end
        )


def test_positive_modal_never_becomes_absence():
    document = snapshot()
    operators = [{"id": "123:44", "rna": "TRANSFORM_OT_translate", "name": "Move"}]
    document["windows"][0]["positive_modal_operators"] = operators
    assert compile_document(document).require("modal") == {"positive_operators": operators}


def test_xres_pid_wire_byte_length_yields_one_real_pid():
    from clef_use.blender_state import _query_ids

    # XRes 1.2 LocalClientPid reply: one ID, four value bytes, one uint32 PID.
    wire = struct.pack("=BBHII20xIIII", 1, 0, 1, 4, 1, 42, 2, 4, 12345)
    reply, remaining = _query_ids()._reply.parse_binary(wire, None)
    assert reply.ids[0].value == [12345]
    assert remaining == b""


@pytest.mark.skipif(sys.platform != "linux", reason="Linux peer credentials required")
def test_real_socket_requires_fixed_request_and_samples_only_on_pump(tmp_path):
    calls = []
    server = SnapshotServer(
        tmp_path / "observer",
        lambda: calls.append(threading.get_ident()) or {"selection": ["Cube"]},
    )
    assert not server.path.exists()
    server.start()
    responses = []

    def client():
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(1)
            connection.connect(str(server.path))
            assert peer_credentials(connection)[:2] == (os.getpid(), os.getuid())
            connection.sendall(
                json.dumps({"request": "snapshot", "nonce": "a" * 32}).encode() + b"\n"
            )
            responses.append(read_message(connection, 4096))

    worker = threading.Thread(target=client)
    worker.start()
    try:
        deadline = time.monotonic() + 1
        while server.requests.empty() and time.monotonic() < deadline:
            time.sleep(0.001)
        assert calls == []
        server.pump()
        worker.join(timeout=2)
        assert responses == [{"nonce": "a" * 32, "snapshot": {"selection": ["Cube"]}}]
        assert calls == [threading.get_ident()]
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(1)
            connection.connect(str(server.path))
            connection.sendall(
                b'{"request":"execute","nonce":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}\n'
            )
            assert connection.recv(1) == b""
        server.pump()
        assert calls == [threading.get_ident()]
    finally:
        server.close()
        worker.join(timeout=2)
    assert not server.path.exists()


@pytest.mark.skipif(sys.platform != "linux", reason="Linux peer credentials required")
def test_observer_refuses_reuse_of_existing_directory(tmp_path):
    private = tmp_path / "existing"
    private.mkdir(mode=0o700)
    (private / "user.txt").write_text("preserve")
    with pytest.raises(FileExistsError):
        SnapshotServer(private, lambda: {})
    assert (private / "user.txt").read_text() == "preserve"


def test_slow_perception_cannot_publish_new_scene_state_as_matching_old_pixels(monkeypatch):
    import clef_use.state as state_module
    from clef_use.benchmark import FixtureDesktop
    from clef_use.config import Config
    from clef_use.runtime import SessionRuntime
    from clef_use.state import StateFact, StateSource

    clock = [100.0]
    mode = ["OBJECT"]

    class DelayedParser(FixtureDesktop):
        def parse(self, image):
            clock[0] += 2
            mode[0] = "EDIT"
            return super().parse(image)

    def provide(observation, version):
        return {
            "mode": StateFact(
                value=mode[0],
                source=StateSource.APP_TELEMETRY,
                observed_at=clock[0],
                state_version=version,
                validity=FactValidity.VALID,
                uncertainty=0,
            )
        }

    monkeypatch.setattr(state_module.time, "time", lambda: clock[0])
    desktop = DelayedParser()
    runtime = SessionRuntime(
        desktop, desktop, desktop, desktop, Config(activity_overlay=False), state_provider=provide
    )
    result = runtime.observe()
    state = result["compiled_state"]
    assert state["observation_id"] != result["observation_id"]
    assert state["facts"]["mode"]["value"] == "OBJECT"
    assert state["facts"]["mode"]["validity"] == "STALE"
    assert result["observation_fresh"] is True
    assert desktop.stage == 0
