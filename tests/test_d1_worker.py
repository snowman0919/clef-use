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
        "next": {
            "type": "choice",
            "instructions": "Choose the next allowed action",
            "criteria": {"wait": "Wait", "stop": "Stop"},
        },
        "progress": {
            "type": "score",
            "instructions": "Evaluate visible progress",
            "criteria": ["None", "Done"],
        },
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

    worker.model = DecisionBoundary(20, [9])
    worker.model.system_one = system_one
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


class EncodedSize:
    def __init__(self, tokens):
        self.tokens = tokens

    def numel(self):
        return self.tokens


class BranchPlanner:
    token_budget = 8192

    def _plan(self, lengths, token_budget=None):
        chunks, used = [[]], 0
        for index, count in enumerate(lengths):
            if chunks[-1] and used + count > self.token_budget:
                chunks.append([])
                used = 0
            chunks[-1].append(index)
            used += count
        return chunks


class DecisionBoundary:
    """Lightweight external SDK boundary; no tensor library or model inference."""

    def __init__(self, trunk, branches):
        self.engine = BranchPlanner()
        self.trunk, self.branches = trunk, branches
        self.executed = []
        self.hooks = []

    def register_forward_pre_hook(self, hook, *, with_kwargs):
        assert with_kwargs
        self.hooks.append(hook)
        return SimpleNamespace(remove=lambda: self.hooks.remove(hook))

    def answer(self, trunk, packed, lengths, **vision):
        self.executed.append(trunk.numel() + packed.numel())
        return {"answers": {}, "usage": {"input_tokens": self.executed[-1], "output_tokens": 0}}

    def system_one(self, state, submitted, images=None):
        reply = None
        for chunk in self.engine._plan(self.branches):
            reply = self.answer(
                EncodedSize(self.trunk),
                EncodedSize(sum(self.branches[index] for index in chunk)),
                None,
            )
        return reply


def test_d1_rejects_total_trunk_plus_branches_before_execution(worker_module):
    worker = worker_module.D1Worker.__new__(worker_module.D1Worker)
    worker.device = "cpu"
    worker.model = DecisionBoundary(8190, [2, 1])
    record = {
        "state": {"constraints": ["No input"]},
        "questions": {"visible": {"type": "noul", "instructions": "Is the result visible?"}},
    }
    with pytest.raises(ValueError, match="token budget"):
        worker.request(record)
    assert worker.model.executed == []
    assert worker.model.hooks == []
    assert "answer" not in vars(worker.model) and "_plan" not in vars(worker.model.engine)


@pytest.mark.parametrize("trunk, branches", [(8190, [2]), (0, [8192])])
def test_d1_exact_total_budget_is_allowed_and_temporary_guards_are_removed(
    worker_module, trunk, branches
):
    worker = worker_module.D1Worker.__new__(worker_module.D1Worker)
    worker.device = "cpu"
    worker.model = DecisionBoundary(trunk, branches)
    result = worker.request({"state": {}, "questions": {}})
    assert result["usage"]["input_tokens"] == 8192
    assert worker.model.executed == [8192]
    assert worker.model.hooks == []
    assert "answer" not in vars(worker.model) and "_plan" not in vars(worker.model.engine)


def test_d1_entire_branch_overflow_cannot_execute_a_first_under_budget_chunk(worker_module):
    worker = worker_module.D1Worker.__new__(worker_module.D1Worker)
    worker.device = "cpu"
    worker.model = DecisionBoundary(16, [5000, 5000])
    with pytest.raises(ValueError, match="token budget"):
        worker.request({"state": {}, "questions": {}})
    assert worker.model.executed == []
    assert worker.model.hooks == []
    assert "answer" not in vars(worker.model) and "_plan" not in vars(worker.model.engine)


def test_d1_restores_preexisting_instance_methods_after_model_exception(worker_module):
    worker = worker_module.D1Worker.__new__(worker_module.D1Worker)
    worker.device = "cpu"
    worker.model = DecisionBoundary(10, [2, 1])
    original_plan = worker.model.engine._plan

    def answer(*args, **kwargs):
        raise RuntimeError("test model exception")

    worker.model.answer = answer
    worker.model.engine._plan = original_plan
    with pytest.raises(RuntimeError, match="test model exception"):
        worker.request({"state": {}, "questions": {}})
    assert worker.model.answer is answer and worker.model.engine._plan is original_plan
    assert worker.model.hooks == []


@pytest.mark.parametrize("positional", [False, True])
@pytest.mark.parametrize("count", [8192, 8193])
def test_d1_plain_forward_is_guarded_before_execution(worker_module, count, positional):
    class PlainBoundary(DecisionBoundary):
        def system_one(self, state, submitted, images=None):
            args, kwargs = (
                ((EncodedSize(count),), {})
                if positional
                else ((), {"input_ids": EncodedSize(count)})
            )
            for hook in self.hooks:
                hook(self, args, kwargs)
            self.executed.append(count)
            return {"usage": {"input_tokens": count}}

    worker = worker_module.D1Worker.__new__(worker_module.D1Worker)
    worker.device = "cpu"
    worker.model = PlainBoundary(0, [])
    if count == 8193:
        with pytest.raises(ValueError, match="token budget"):
            worker.request({"state": {}, "questions": {}})
        assert worker.model.executed == []
    else:
        assert worker.request({"state": {}, "questions": {}})["usage"]["input_tokens"] == count
        assert worker.model.executed == [count]
    assert worker.model.hooks == []
    assert "answer" not in vars(worker.model) and "_plan" not in vars(worker.model.engine)


def test_d1_failed_guard_installation_restores_prior_state(worker_module):
    class ReadOnlyAnswer(DecisionBoundary):
        def __setattr__(self, name, value):
            if name == "answer":
                raise RuntimeError("cannot replace answer")
            super().__setattr__(name, value)

    worker = worker_module.D1Worker.__new__(worker_module.D1Worker)
    worker.device = "cpu"
    worker.model = ReadOnlyAnswer(10, [2])
    prior_hook = object()
    worker.model.hooks.append(prior_hook)
    with pytest.raises(RuntimeError, match="cannot replace answer"):
        worker.request({"state": {}, "questions": {}})
    assert worker.model.executed == [] and worker.model.hooks == [prior_hook]
    assert "_plan" not in vars(worker.model.engine)


def test_d1_plain_forward_without_encoded_ids_is_refused(worker_module):
    class MissingIds(DecisionBoundary):
        def system_one(self, state, submitted, images=None):
            for hook in self.hooks:
                hook(self, (), {"input_ids": None})
            self.executed.append(1)

    worker = worker_module.D1Worker.__new__(worker_module.D1Worker)
    worker.device = "cpu"
    worker.model = MissingIds(0, [])
    with pytest.raises(ValueError, match="no encoded input ids"):
        worker.request({"state": {}, "questions": {}})
    assert worker.model.executed == [] and worker.model.hooks == []
    assert "answer" not in vars(worker.model) and "_plan" not in vars(worker.model.engine)


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
    worker.processor = SimpleNamespace(tokenizer=object())
    worker.encode_record = lambda *_args, **_kwargs: SimpleNamespace(input_ids=range(10))
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
