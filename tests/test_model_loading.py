"""Pinned CUDA NF4 loader peak-memory regression (no GPU required)."""

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from clef_use.config import Config


def test_cpu_compute_dtype_rejects_unsupported_precision():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Config(cpu_compute_dtype="float16")


@pytest.mark.parametrize(
    ("device", "precision", "expected_dtype"),
    [("cpu", None, "float32"), ("cpu", "bfloat16", "bfloat16"), ("mps", "bfloat16", "float16")],
)
def test_worker_precision_runs_real_torch_forward(
    tmp_path, monkeypatch, device, precision, expected_dtype
):
    torch = pytest.importorskip("torch")
    torch.set_num_threads(4)
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "src/clef_use"))
    worker_module = importlib.import_module("model_worker")
    monkeypatch.setattr(worker_module, "select_backend", lambda torch, requested: requested)
    monkeypatch.setattr(worker_module, "torch_device", lambda backend: backend)
    if device == "mps":
        monkeypatch.setattr(torch.mps, "empty_cache", lambda: None)
    # Replace only the heavyweight release boundary with an actual tiny Torch model.
    # The worker's dtype controls resident bytes and the executed numerical forward.
    weight = torch.tensor([[0.4, -0.7, 0.2], [-0.3, 0.5, 0.9]])
    inputs = torch.tensor([[0.25, -0.5, 0.75], [-0.2, 0.6, 0.1]])

    def load_release_model(path, *, dtype, **kwargs):
        model = torch.nn.Linear(3, 2, bias=False, dtype=dtype)
        with torch.no_grad():
            model.weight.copy_(weight)
        return model.eval(), None

    def systemone(model, processor, record, **kwargs):
        return model(record["inputs"].to(model.weight.dtype)).tanh()

    monkeypatch.setitem(
        sys.modules,
        "joint_schema_model",
        SimpleNamespace(load_release_model=load_release_model, systemone=systemone),
    )
    values = {"device": device, "model_dir": tmp_path}
    if precision is not None:
        values["cpu_compute_dtype"] = precision
    config = Config(**values).model_dump(mode="json")
    worker = worker_module.ClefWorker(config)
    actual = worker.request({"inputs": inputs})
    assert actual.dtype == getattr(torch, expected_dtype)
    assert torch.isfinite(actual).all()
    torch.testing.assert_close(actual.float(), (inputs @ weight.T).tanh(), rtol=0.02, atol=0.003)
    expected_bytes = 4 if expected_dtype == "float32" else 2
    assert worker.model.weight.numel() * worker.model.weight.element_size() == 6 * expected_bytes


@pytest.mark.parametrize("precision", ["float32", "bfloat16"])
def test_cpu_worker_preserves_causal_attention_without_quadratic_score_storage(
    tmp_path, monkeypatch, precision
):
    torch = pytest.importorskip("torch")
    pytest.importorskip("transformers")
    from transformers import Qwen3_5TextConfig
    from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5TextModel

    torch.set_num_threads(4)
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "src/clef_use"))
    worker_module = importlib.import_module("model_worker")

    def make_model(dtype, attention):
        config = Qwen3_5TextConfig(
            vocab_size=64,
            hidden_size=64,
            intermediate_size=128,
            num_hidden_layers=1,
            num_attention_heads=4,
            num_key_value_heads=2,
            head_dim=16,
            layer_types=["full_attention"],
            rope_parameters={
                "rope_type": "default",
                "rope_theta": 10000,
                "partial_rotary_factor": 1.0,
                "mrope_section": [2, 2, 4],
            },
        )
        config._attn_implementation = attention
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(11)
            return Qwen3_5TextModel(config).to(dtype=dtype).eval()

    def load_release_model(path, *, dtype, attn_implementation, **kwargs):
        return make_model(dtype, attn_implementation), None

    def systemone(model, processor, record, **kwargs):
        return model(**record, use_cache=False).last_hidden_state

    monkeypatch.setitem(
        sys.modules,
        "joint_schema_model",
        SimpleNamespace(
            load_release_model=load_release_model,
            systemone=systemone,
        ),
    )
    config = Config(device="cpu", model_dir=tmp_path, cpu_compute_dtype=precision)
    worker = worker_module.ClefWorker(config.model_dump(mode="json"))
    length = 512
    ids = torch.arange(length).remainder(64).unsqueeze(0)
    with torch.inference_mode():
        reference = make_model(torch.float32, "eager")(ids, use_cache=False).last_hidden_state
        with torch.profiler.profile(
            activities=[torch.profiler.ProfilerActivity.CPU], profile_memory=True
        ) as profile:
            actual = worker.request({"input_ids": ids})
        tolerance = 0.03 if precision == "bfloat16" else 2e-5
        torch.testing.assert_close(actual.float(), reference, rtol=tolerance, atol=tolerance)
        changed = ids.clone()
        changed[:, 128:] = (changed[:, 128:] + 17).remainder(64)
        changed_output = worker.request({"input_ids": changed})
        torch.testing.assert_close(actual[:, :128], changed_output[:, :128], rtol=0, atol=0)
    # The real provider's eager path allocates a heads x T x T float32 softmax.
    # CPU execution must avoid that storage while preserving causal behavior.
    largest = max(event.cpu_memory_usage for event in profile.events())
    assert largest < 4 * length * length


@pytest.mark.parametrize("free_bytes", [256 * 1024**2, 4 * 1024**3])
# lm_head placement is now unconditional (CPU) so both free-memory branches must offload.
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
    calls = {}

    class Head:
        def __init__(self, **kwargs):
            self.hidden_size = kwargs["hidden_size"]

        def load_state_dict(self, state, strict):
            assert strict and state == {"actual_fixture_weight": 7}

        def to(self, device, dtype):
            if embedding.weight is weight:
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
                from_pretrained=lambda *a, **k: calls.update(map=k["device_map"]) or backbone
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
    assert embedding.weight == "cpu-rows"
    assert len(hooks) == 1
    assert calls.get("map") == {"": "cuda", "lm_head": "cpu"}
