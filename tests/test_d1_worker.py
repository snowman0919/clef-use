from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from clef_use.backends import encode_image


@pytest.fixture
def worker_module(monkeypatch):
    source = Path(__file__).parents[1] / "src/clef_use/model_worker.py"
    monkeypatch.syspath_prepend(str(source.parent))
    spec = importlib.util.spec_from_file_location("decision_worker_under_test", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_d1_calls_public_system_one_once_without_changing_state_or_question_meanings(worker_module):
    worker = worker_module.D1Worker.__new__(worker_module.D1Worker)
    worker.device = "cpu"
    calls = []
    questions = {
        "next": {"type": "choice", "criteria": {"wait": "Wait", "stop": "Stop"}},
        "progress": {"type": "score", "criteria": ["None", "Done"]},
        "unsafe": {"type": "noul", "instructions": "Would this violate a constraint?"},
    }
    expected = {
        "answers": {
            "next": {
                "choice": "wait",
                "confidence": 0.8,
                "probabilities": {"wait": 0.8, "stop": 0.2},
            },
            "progress": {"score": 0.25},
            "unsafe": {"noul": 0.1},
        },
        "usage": {"input_tokens": 29, "output_tokens": 0},
    }

    def system_one(state, submitted, images=None):
        calls.append((state, submitted, images))
        return expected

    worker.model = SimpleNamespace(system_one=system_one)
    record = {
        "state": {"goal": "Wait", "constraints": ["No input"]},
        "questions": questions,
        "image": encode_image(Image.new("RGB", (1920, 1080), "white")),
        "evidence_images": ["must never be passed as a second raster"],
    }
    result = worker.request(record)
    assert result == expected and len(calls) == 1
    assert calls[0][0] is record["state"] and calls[0][1] is questions
    assert len(calls[0][2]) == 1 and calls[0][2][0].mode == "RGB"
    width, height = calls[0][2][0].size
    assert width * height <= 512 * 512
    assert record["image"] and record["evidence_images"]  # no mutation of replay payloads


def test_d1_does_not_inherit_clef_only_nf4_loader_or_silently_fall_back(worker_module):
    with pytest.raises(ValueError, match="quantization none"):
        worker_module.D1Worker({"decision_model": "LiquidAI/d1-3B", "quantization": "4bit"})
    with pytest.raises(ValueError, match="LiquidAI/d1-3B"):
        worker_module.D1Worker({"decision_model": "Cloudflare/clef-flash", "quantization": "none"})


def test_d1_loader_uses_only_the_pinned_local_snapshot_and_public_auto_model(
    worker_module, monkeypatch, tmp_path
):
    calls = []
    loaded = SimpleNamespace()

    def from_pretrained(path, **kwargs):
        calls.append((path, kwargs))
        return loaded

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            AutoModel=SimpleNamespace(from_pretrained=from_pretrained), __version__="5.14.1"
        ),
    )
    result = worker_module.load_d1_model(tmp_path, device="cuda", dtype="bf16")
    assert result is loaded and len(calls) == 1
    assert calls[0][0] == str(tmp_path)
    assert calls[0][1] == {
        "trust_remote_code": True,
        "local_files_only": True,
        "code_revision": "051bcc464b01b9f92942b364d9586b0ef5912432",
        "dtype": "bf16",
        "device_map": {"": "cuda"},
        "attn_implementation": "sdpa",
    }


def test_d1_rejects_unpinned_transformers_before_loading_model_code(
    worker_module, monkeypatch, tmp_path
):
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(__version__="5.10.2"))
    with pytest.raises(RuntimeError, match="5.14.1"):
        worker_module.load_d1_model(tmp_path, device="cpu", dtype="fp32")


def test_clef_adapter_supplies_its_required_model_tag_without_leaking_it_to_common_contract(
    worker_module,
):
    worker = worker_module.ClefWorker.__new__(worker_module.ClefWorker)
    worker.device = "cpu"
    worker.decision_model = "Cloudflare/clef-flash"
    worker.model = object()
    worker.processor = object()
    seen = []

    def systemone(model, processor, record, max_length):
        assert model is worker.model and processor is worker.processor
        assert max_length == 8192
        seen.append(record)
        assert record["model"] == worker.decision_model
        return {"answers": {}, "usage": {"output_tokens": 0}}

    worker.systemone = systemone
    packet = {"state": {"goal": "Wait"}, "questions": {"unsafe": {"type": "noul"}}}
    worker.request(packet)
    assert len(seen) == 1 and "model" not in packet
