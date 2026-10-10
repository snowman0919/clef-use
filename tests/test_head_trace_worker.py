"""Host diagnostic opt-in must stay outside the model's request authority."""

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_clef_worker_capture_is_one_shot_and_preserves_packet(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "src" / "clef_use"))
    import model_worker as module

    worker = module.ClefWorker.__new__(module.ClefWorker)
    worker.device = "cpu"
    worker.decision_model = "Cloudflare/clef-flash"
    worker.model_revision = "pinned"
    worker.compute_dtype = "float16"
    worker.quantized_modules = 1
    worker.backend = "cpu"
    worker.head_trace_root = str(tmp_path)
    worker.model = object()
    worker.processor = SimpleNamespace(tokenizer=object())
    worker.encode_record = lambda *a, **kw: SimpleNamespace(input_ids=range(5))
    seen = []
    traced = []

    def infer(model, processor, record, *, max_length):
        seen.append(copy.deepcopy(record))
        assert max_length == 8192
        return {"answers": {}}

    def capture(model, infer, root, metadata):
        traced.append((root, metadata))
        return infer()

    worker.systemone = infer
    monkeypatch.setattr(module, "capture_head_inputs", capture, raising=False)
    packet = {"state": {"observation_id": "owned"}, "questions": {"complete": {"type": "noul"}}}
    worker.request(packet)
    worker.request(packet)
    assert len(traced) == 1
    assert seen[0] == seen[1] == {**packet, "model": worker.decision_model}
    assert traced[0][0] == str(tmp_path)
    assert traced[0][1]["model_revision"] == "pinned"
    assert "state" not in traced[0][1] and "questions" not in traced[0][1]


def test_clef_worker_capture_is_not_enabled_by_request(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "src" / "clef_use"))
    import model_worker as module

    worker = module.ClefWorker.__new__(module.ClefWorker)
    worker.device = "cpu"
    worker.decision_model = "Cloudflare/clef-flash"
    worker.model = object()
    worker.processor = SimpleNamespace(tokenizer=object())
    worker.encode_record = lambda *a, **kw: SimpleNamespace(input_ids=range(5))
    worker.systemone = lambda *a, **kw: {"answers": {}}
    monkeypatch.setattr(
        module,
        "capture_head_inputs",
        lambda *a: pytest.fail("request must not opt in"),
        raising=False,
    )
    worker.request({"state": {}, "questions": {}, "head_trace_root": str(tmp_path)})


def test_clef_worker_consumes_capture_attempt_after_genuine_inference_failure(
    tmp_path, monkeypatch
):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "src" / "clef_use"))
    import model_worker as module

    worker = module.ClefWorker.__new__(module.ClefWorker)
    for name, value in {
        "device": "cpu",
        "decision_model": "Cloudflare/clef-flash",
        "model_revision": "f" * 40,
        "compute_dtype": "float16",
        "backend": "cpu",
        "quantized_modules": 1,
        "head_trace_root": str(tmp_path),
    }.items():
        setattr(worker, name, value)
    worker.model = object()
    worker.processor = SimpleNamespace(tokenizer=object())
    worker.encode_record = lambda *a, **kw: SimpleNamespace(input_ids=range(5))
    inferences, captures = [], []

    def infer(*a, **kw):
        inferences.append(True)
        return {"answers": {}}

    def capture(model, infer, root, metadata):
        captures.append(True)
        infer()
        raise RuntimeError("post-inference capture failure")

    worker.systemone = infer
    monkeypatch.setattr(module, "capture_head_inputs", capture)
    packet = {"state": {}, "questions": {"complete": {"type": "noul"}}}
    with pytest.raises(RuntimeError, match="post-inference"):
        worker.request(packet)
    worker.request(packet)
    assert len(inferences) == 2 and len(captures) == 1


def test_clef_worker_diagnostic_avoids_full_record_copy_and_repeated_decode(tmp_path, monkeypatch):
    import base64
    import io

    from PIL import Image

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "src" / "clef_use"))
    import model_worker as module

    worker = module.ClefWorker.__new__(module.ClefWorker)
    for name, value in {
        "device": "cpu",
        "decision_model": "Cloudflare/clef-flash",
        "model_revision": "f" * 40,
        "compute_dtype": "float16",
        "backend": "cpu",
        "quantized_modules": 1,
        "head_trace_root": str(tmp_path),
    }.items():
        setattr(worker, name, value)
    worker.model = object()
    worker.processor = SimpleNamespace(tokenizer=object())
    worker.encode_record = lambda *a, **kw: SimpleNamespace(input_ids=range(5))
    worker.systemone = lambda *a, **kw: {"answers": {}}
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    calls, metadata = [], []
    decode = base64.b64decode

    def once(value):
        calls.append(True)
        return decode(value)

    def capture(model, infer, root, source):
        metadata.append(source)
        return infer()

    monkeypatch.setattr(module.base64, "b64decode", once)
    monkeypatch.setattr(
        module.json,
        "dumps",
        lambda *a, **kw: pytest.fail("diagnostics must not serialize state/questions"),
    )
    monkeypatch.setattr(module, "capture_head_inputs", capture)
    worker.request(
        {
            "state": {
                "frame_reference": {"image_sha256": "f" * 64, "private_prose": "do not save"}
            },
            "questions": {"complete": {"type": "noul", "sdk_ignored": "x" * 100000}},
            "image": encoded,
        }
    )
    assert len(calls) == 1
    assert metadata[0]["frame_image_sha256"] == "f" * 64
    assert "frame_reference" not in metadata[0] and "record_sha256" not in metadata[0]
