"""Pinned CUDA NF4 loader peak-memory regression (no GPU required)."""

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("free_bytes", [256 * 1024**2, 4 * 1024**3])
def test_low_memory_loader_frees_unused_rows_before_joint_head(tmp_path, monkeypatch, free_bytes):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "src/clef_use"))
    worker = importlib.import_module("model_worker")
    (tmp_path / "joint_head_config.json").write_text(json.dumps({"hidden_size": 4}))
    weight = SimpleNamespace(device="cuda", detach=lambda: SimpleNamespace(cpu=lambda: "cpu-rows"))
    embedding = SimpleNamespace(weight=weight)
    backbone = SimpleNamespace(
        config=SimpleNamespace(use_cache=True), get_output_embeddings=lambda: embedding
    )
    hooks = []

    class Head:
        def __init__(self, **kwargs):
            self.hidden_size = kwargs["hidden_size"]

        def load_state_dict(self, state, strict):
            assert strict and state == {"actual_fixture_weight": 7}

        def to(self, device, dtype):
            if free_bytes < 1024**3 and embedding.weight is weight:
                raise MemoryError("joint head does not fit until lexical rows leave CUDA")
            return self

        def register_forward_pre_hook(self, hook):
            hooks.append(hook)

    class Model:
        def __init__(self, language_model, head):
            self.language_model, self.head = language_model, head

        def eval(self):
            return self

    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(
            cuda=SimpleNamespace(
                mem_get_info=lambda: (free_bytes, 10 * 1024**3), empty_cache=lambda: None
            ),
            nn=SimpleNamespace(Parameter=lambda value, requires_grad: value),
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            Qwen3_5ForConditionalGeneration=SimpleNamespace(
                from_pretrained=lambda *a, **k: backbone
            ),
            AutoProcessor=SimpleNamespace(from_pretrained=lambda *a, **k: "processor"),
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "safetensors.torch",
        SimpleNamespace(load_file=lambda *a, **k: {"actual_fixture_weight": 7}),
    )
    monkeypatch.setitem(
        sys.modules, "joint_schema_model", SimpleNamespace(ClefModel=Model, JointSchemaHead=Head)
    )
    model, processor = worker.load_cuda_nf4_model(tmp_path, dtype="fp16", local_files_only=True)
    assert model.language_model is backbone and processor == "processor"
    assert not backbone.config.use_cache
    assert model.head.hidden_size == 4
    assert embedding.weight == "cpu-rows" if free_bytes < 1024**3 else embedding.weight is weight
    assert len(hooks) == (1 if free_bytes < 1024**3 else 0)
