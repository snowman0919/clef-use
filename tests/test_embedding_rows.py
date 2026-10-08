"""Output rows must not require a full-vocabulary host dtype copy."""

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("precision", ["float16", "bfloat16", "float32"])
@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_meta_embedding_gather_avoids_full_table_cast(tmp_path, monkeypatch, precision, device):
    torch = pytest.importorskip("torch")
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")
    dtype = getattr(torch, precision)
    save_file = pytest.importorskip("safetensors.torch").save_file
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "src/clef_use"))
    worker = importlib.import_module("model_worker")
    rows = (torch.arange(4096 * 64).reshape(4096, 64) % 97 / 97).to(torch.bfloat16)
    save_file({"lm_head.weight": rows}, tmp_path / "model.safetensors")
    (tmp_path / "model.safetensors.index.json").write_text(
        json.dumps({"weight_map": {"lm_head.weight": "model.safetensors"}}), encoding="utf-8"
    )
    embedding = torch.nn.Embedding(4096, 64, device="meta")

    class Head(torch.nn.Module):
        def forward(self, hidden, indices, weight):
            return weight[indices].mean(dim=0)

    model = SimpleNamespace(
        language_model=SimpleNamespace(get_output_embeddings=lambda: embedding), head=Head()
    )
    indices = torch.tensor([0, 11, 4095, 11], device=device)
    hidden = torch.zeros(1, dtype=dtype, device=device)
    # Include the first query: delaying a full-table cast until first use
    # must not evade the same host-copy budget as eager initialization.
    with torch.profiler.profile(
        activities=[torch.profiler.ProfilerActivity.CPU], profile_memory=True, acc_events=True
    ) as profile:
        worker.offload_output_embeddings(model, path=tmp_path, dtype=dtype)
        actual = model.head(hidden, indices, embedding.weight)
    expected = rows.to(dtype)[indices.cpu()].to(device).mean(dim=0)
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    # Safetensors reports its file mapping as a [memory] event even though it
    # is not a host dtype copy. Measure allocated conversion bytes, not mapped
    # address space; a full table cast can double storage on load or first use.
    copy_bytes = sum(
        event.cpu_memory_usage for event in profile.events() if event.name == "aten::_to_copy"
    )
    assert copy_bytes < rows.numel() * rows.element_size() // 2
