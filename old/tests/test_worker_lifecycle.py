"""Exercise actual child-process lifetime through the canonical JSON protocol."""

import base64
import importlib.util
import io
import json
from pathlib import Path

import pytest
from PIL import Image

import clef_use.backends as backends
from clef_use.config import Config

spec = importlib.util.spec_from_file_location(
    "benchmark", Path(__file__).parents[1] / "scripts/blender_hybrid_benchmark.py"
)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def worker(tmp_path, monkeypatch):
    script = tmp_path / "model_worker.py"
    script.write_text(
        "import base64,io,json,os,sys\n"
        "from PIL import Image\n"
        "json.loads(sys.stdin.readline())\n"
        "print(json.dumps({'ready':True,'pid':os.getpid()}),flush=True)\n"
        "for line in sys.stdin:\n"
        " data=json.loads(line)\n"
        " journal=os.environ.get('CLEF_TEST_STARTUP_JOURNAL')\n"
        " if journal:\n"
        "  trace=json.load(open(journal))\n"
        "  assert any(x['ready']['pid']==os.getpid() for x in trace['model_startups'])\n"
        " pixel=0\n"
        " if data.get('image'):\n"
        "  pixel=Image.open(io.BytesIO(base64.b64decode(data['image']))).getpixel((0,0))[0]\n"
        " reply={'error':'INVALID_INPUT'} if data.get('fail') "
        "else {'square':data['value']**2+pixel}\n"
        " print(json.dumps(reply),flush=True)\n"
    )
    monkeypatch.setattr(backends, "__file__", str(tmp_path / "backends.py"))
    return backends.JsonWorker(
        None, "clef", Config(backend_timeout=5)
    )


def assert_reaped(process):
    assert process.poll() is not None


def test_exclusive_benchmark_keeps_active_worker_warm_and_reaps_previous_worker(
    tmp_path, monkeypatch
):
    first_client = worker(tmp_path, monkeypatch)
    second_client = worker(tmp_path, monkeypatch)
    benchmark.configure_exclusive_workers((first_client, second_client))
    try:
        assert first_client.request({"value": 3}) == {"square": 9}
        first = first_client.ready["pid"]
        first_process = first_client.process
        assert first_client.request({"value": -4}) == {"square": 16}
        assert first_client.ready["pid"] == first
        assert first_process.poll() is None
        assert second_client.request({"value": 5}) == {"square": 25}
        assert_reaped(first_process)
        second = second_client.ready["pid"]
        second_process = second_client.process
        assert first_client.request({"value": 6}) == {"square": 36}
        assert_reaped(second_process)
        replacement = first_client.ready["pid"]
        replacement_process = first_client.process
        assert replacement != first
        assert second != first
        with pytest.raises(backends.ModelWorkerError, match="INVALID_INPUT"):
            first_client.request({"fail": True})
        assert_reaped(replacement_process)
    finally:
        first_client.close()
        second_client.close()


def test_resident_default_keeps_child_until_explicit_close(tmp_path, monkeypatch):
    client = worker(tmp_path, monkeypatch)
    try:
        assert client.request({"value": 3}) == {"square": 9}
        pid = client.ready["pid"]
        process = client.process
        assert client.request({"value": 4}) == {"square": 16}
        assert client.ready["pid"] == pid
        assert process.poll() is None
    finally:
        client.close()
    assert_reaped(process)


def test_model_startup_is_durable_before_request_and_archived_image_replays(
    tmp_path, monkeypatch
):
    journal = tmp_path / "report.json"
    monkeypatch.setenv("CLEF_TEST_STARTUP_JOURNAL", str(journal))
    client = worker(tmp_path, monkeypatch)
    trial = {"case": "properties_tiny_icon", "variant": "baseline", "repetition": 0}
    report = {"in_flight": trial}

    def persist():
        journal.write_text(json.dumps(report))

    benchmark.instrument_worker_trace((("clef", client),), report, persist, tmp_path)
    image = io.BytesIO()
    Image.new("RGB", (2, 2), (17, 3, 5)).save(image, format="PNG")
    payload = {"value": 2, "image": base64.b64encode(image.getvalue()).decode(),
               "state": {"objects": [{"label": "Face"}],
                         "allowed_candidates": [{"id": "target"}]}}
    try:
        assert client.request(payload) == {"square": 21}
        archived = json.loads((tmp_path / report["clef_requests"][0]["request_file"]).read_text())
        client.close()
        replay = archived["request"]
        replay_image = (tmp_path / archived["image_file"]).read_bytes()
        replay["image"] = base64.b64encode(replay_image).decode()
        assert client.request(replay) == {"square": 21}
        persisted = json.loads(journal.read_text())
        assert persisted["model_startups"][0]["trial"] == trial
        assert persisted["clef_requests"][0]["trial"] == trial
        assert persisted["clef_requests"][0]["objects"] == 1
        assert persisted["clef_requests"][0]["candidates"] == 1
    finally:
        client.close()
