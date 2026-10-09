"""The real dispatch hooks must not migrate the unused lexical table to CUDA."""

import importlib
import json
import sys
import weakref
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("execution", ["guarded_cpu", "cuda"])
def test_nf4_loader_dispatch_excludes_cpu_lexical_table(tmp_path, monkeypatch, execution):
    torch = pytest.importorskip("torch")
    accelerate = pytest.importorskip("accelerate")
    hooks = importlib.import_module("accelerate.hooks")
    transformers = pytest.importorskip("transformers")
    save_file = pytest.importorskip("safetensors.torch").save_file
    if execution == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "src/clef_use"))
    worker = importlib.import_module("model_worker")
    rows = (torch.arange(8 * 4).reshape(8, 4) / 16).to(torch.bfloat16)
    save_file({"lm_head.weight": rows}, tmp_path / "model.safetensors")
    (tmp_path / "model.safetensors.index.json").write_text(
        json.dumps({"weight_map": {"lm_head.weight": "model.safetensors"}}), encoding="utf-8"
    )
    (tmp_path / "joint_head_config.json").write_text(
        json.dumps({"hidden_size": 4}), encoding="utf-8"
    )
    save_file({"scale": torch.tensor(2.0)}, tmp_path / "joint_head.safetensors")
    actual_device = "cuda" if execution == "cuda" else "cpu"

    class Backbone(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.model = torch.nn.Linear(4, 4, bias=False, dtype=torch.float16)
            self.lm_head = torch.nn.Linear(4, 8, bias=False, dtype=torch.float16)
            self.config = SimpleNamespace(use_cache=True)
            with torch.no_grad():
                self.model.weight.copy_(torch.eye(4))
                self.lm_head.weight.copy_(rows)

        def get_output_embeddings(self):
            return self.lm_head

        def set_output_embeddings(self, embedding):
            self.lm_head = embedding

    backbone = Backbone()
    transfer = hooks.set_module_tensor_to_device
    moved_body = set()
    lexical_cuda_moves = []
    cpu_owners = []

    def checked_transfer(module, tensor_name, device, **kwargs):
        prefix = next(name for name, child in backbone.named_modules() if child is module)
        full_name = f"{prefix}.{tensor_name}" if prefix else tensor_name
        requested = torch.device(device)
        if requested.type == "cuda":
            if full_name == "lm_head.weight":
                lexical_cuda_moves.append(full_name)
                raise MemoryError("unused lexical table must not be materialized on CUDA")
            moved_body.add(full_name)
            # Only the external CUDA-transfer boundary is simulated on CPU-only
            # hosts. Installed dispatch recursion, hooks, meta placement and
            # safetensors lexical gathering below all remain real.
            if execution == "guarded_cpu":
                device = "cpu"
        return transfer(module, tensor_name, device, **kwargs)

    monkeypatch.setattr(hooks, "set_module_tensor_to_device", checked_transfer)

    def from_pretrained(path, *, device_map, **kwargs):
        result = accelerate.dispatch_model(backbone, device_map=device_map)
        cpu_owners.append(weakref.ref(result.lm_head._hf_hook.weights_map["weight"]))
        return result

    monkeypatch.setattr(
        transformers.Qwen3_5ForConditionalGeneration, "from_pretrained", from_pretrained
    )
    monkeypatch.setattr(transformers.AutoProcessor, "from_pretrained", lambda *a, **k: None)

    class Head(torch.nn.Module):
        def __init__(self, hidden_size):
            super().__init__()
            self.scale = torch.nn.Parameter(torch.ones(()))

        def to(self, *, device, dtype):
            assert backbone.lm_head.weight.is_meta
            return super().to(device=actual_device, dtype=dtype)

        def forward(self, hidden, indices, weight):
            return weight[indices].mean(dim=0) * self.scale

    class Model(torch.nn.Module):
        def __init__(self, language_model, head):
            super().__init__()
            self.language_model = language_model
            self.head = head

    monkeypatch.setitem(
        sys.modules,
        "joint_schema_model",
        SimpleNamespace(ClefModel=Model, JointSchemaHead=Head),
    )
    model, _ = worker.load_cuda_nf4_model(tmp_path, dtype=torch.float16, local_files_only=True)
    assert not lexical_cuda_moves
    assert moved_body == {"model.weight"}
    assert backbone.lm_head.weight.is_meta
    assert not backbone.config.use_cache
    assert next(model.parameters()).device.type == actual_device
    # A meta parameter alone does not prove that the host allocation is gone.
    assert all(owner() is None for owner in cpu_owners), "unused CPU lexical table retained"
    indices = torch.tensor([0, 7, 2, 7], device=actual_device)
    hidden = torch.zeros(1, 4, dtype=torch.float16, device=actual_device)
    with torch.inference_mode():
        actual = model.head(hidden, indices, backbone.lm_head.weight)
    expected = rows.to(torch.float16)[indices.cpu()].to(actual_device).mean(dim=0) * 2
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)
