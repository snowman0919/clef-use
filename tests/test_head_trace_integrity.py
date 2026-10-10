"""Regressions for the independently reviewed capture failure boundaries."""

import json
import os
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.skipif(os.name != "posix", reason="private capture is POSIX-only")


def _case(tmp_path, *, logits=None):
    torch = pytest.importorskip("torch")
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    hidden = torch.arange(16, dtype=torch.float32).reshape(1, 4, 4).to(torch.float16)
    ids = torch.tensor([[1, 2, 3, 4]])
    actual = torch.tensor([1.0, -1.0]) if logits is None else logits
    record = SimpleNamespace(
        input_ids=tuple(ids[0].tolist()),
        questions=[
            SimpleNamespace(
                question_id="private prose",
                question_type=0 if actual.numel() == 2 else 1,
                question_span=(0, 1),
                option_spans=tuple((1, 2) for _ in range(actual.numel())),
                option_ids=tuple("private option prose" for _ in range(actual.numel())),
            )
        ],
    )

    class Head(torch.nn.Module):
        def forward(self, *args):
            return [[actual]]

    model = SimpleNamespace(head=Head())

    def infer():
        model.head(hidden, ids, torch.ones_like(ids), [record], None)
        return {"answers": {}}

    return root, model, infer, hidden, actual


def test_capture_saves_no_arbitrary_record_identifiers(tmp_path):
    from clef_use.head_trace import capture_head_inputs

    root, model, infer, _, _ = _case(tmp_path)
    capture_head_inputs(model, infer, root, {})
    text = (root / "manifest.json").read_text()
    assert "private prose" not in text and "private option" not in text
    assert json.loads(text)["questions"] == [
        {"question_type": 0, "question_span": [0, 1], "option_spans": [[1, 2], [1, 2]]}
    ]


def test_capture_refuses_non_allowlisted_metadata_before_inference(tmp_path):
    from clef_use.head_trace import capture_head_inputs

    root, model, _, _, _ = _case(tmp_path)
    with pytest.raises(ValueError, match="metadata"):
        capture_head_inputs(
            model,
            lambda: pytest.fail("prose must be refused before inference"),
            root,
            {"frame_reference": {"private_prose": "do not save"}},
        )


def test_capture_preserves_signed_zero_and_nonfinite_logit_bits(tmp_path):
    torch = pytest.importorskip("torch")
    from clef_use.head_trace import capture_head_inputs

    bits = torch.tensor([0x0000, 0x8000, 0x7C00, 0xFC00, 0x7E01], dtype=torch.uint16)
    logits = bits.view(torch.float16)
    root, model, infer, _, _ = _case(tmp_path, logits=logits)
    # This head fixture's option count follows its actual vector.
    original = model.head

    class Head(torch.nn.Module):
        def forward(self, *args):
            return original(*args)

    model.head = Head()
    capture_head_inputs(model, infer, root, {})
    assert (root / "logits.bin").exists(), "raw nonfinite logits were discarded"
    assert (root / "logits.bin").read_bytes() == bits.view(torch.uint8).numpy().tobytes()
    meta = json.loads((root / "manifest.json").read_text())["logits"][0]
    assert meta["dtype"] == "float16" and meta["shape"] == [5] and not meta["finite"]


def test_capture_manifest_is_streamed_with_incremental_budget(tmp_path, monkeypatch):
    import clef_use.head_trace as module

    root, model, infer, _, _ = _case(tmp_path)
    monkeypatch.setattr(
        module.json,
        "dumps",
        lambda *a, **kw: pytest.fail("full manifest serialization is not bounded"),
    )
    monkeypatch.setattr(module, "MAX_MANIFEST_BYTES", 64)
    with pytest.raises(ValueError, match="manifest byte budget"):
        module.capture_head_inputs(model, infer, root, {})
    assert not list(root.iterdir())
    assert len(model.head._forward_pre_hooks) == len(model.head._forward_hooks) == 0


def test_capture_closes_failed_fdopen_and_continues_cleanup(tmp_path, monkeypatch):
    import clef_use.head_trace as module

    root, model, infer, _, _ = _case(tmp_path)
    real_fdopen, real_unlink = os.fdopen, os.unlink
    failed_descriptors = []
    attempted = []

    def fdopen(descriptor, *args, **kwargs):
        if os.readlink(f"/proc/self/fd/{descriptor}").endswith("manifest.json"):
            failed_descriptors.append(descriptor)
            raise RuntimeError("manifest open failure")
        return real_fdopen(descriptor, *args, **kwargs)

    def unlink(name, *args, **kwargs):
        attempted.append(name)
        if name == "hidden.bin":
            raise PermissionError("injected cleanup failure")
        return real_unlink(name, *args, **kwargs)

    monkeypatch.setattr(module.os, "fdopen", fdopen)
    monkeypatch.setattr(module.os, "unlink", unlink)
    with pytest.raises(RuntimeError, match="manifest open failure") as caught:
        module.capture_head_inputs(model, infer, root, {})
    assert "manifest.json" in attempted and "logits.bin" in attempted
    assert sorted(path.name for path in root.iterdir()) == ["hidden.bin"]
    assert any("cleanup" in note for note in caught.value.__notes__)
    for descriptor in failed_descriptors:
        with pytest.raises(OSError):
            os.fstat(descriptor)
    assert len(model.head._forward_pre_hooks) == len(model.head._forward_hooks) == 0


def test_capture_rejects_ancestor_symlink_swap_at_open_boundary(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")
    import clef_use.head_trace as module

    parent = tmp_path / "swap-parent"
    parent.mkdir(mode=0o700)
    root = parent / "private"
    root.mkdir(mode=0o700)
    replacement = tmp_path / "original-parent"
    real_open = os.open
    swapped = []

    def opened(path, *args, **kwargs):
        if not swapped and (os.fspath(path) == "swap-parent" or os.fspath(path) == str(root)):
            parent.rename(replacement)
            parent.symlink_to(replacement, target_is_directory=True)
            swapped.append(True)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(module.os, "open", opened)
    with pytest.raises(ValueError, match="symlink|private"):
        module.capture_head_inputs(
            SimpleNamespace(head=torch.nn.Linear(1, 1)),
            lambda: pytest.fail("ancestor race must reject before inference"),
            root,
            {},
        )
    assert swapped and not list((replacement / "private").iterdir())


def test_capture_multichunk_hidden_preserves_nonfinite_bits_without_full_copy(
    tmp_path, monkeypatch
):
    torch = pytest.importorskip("torch")
    import clef_use.head_trace as module

    root, model, infer, hidden, _ = _case(tmp_path)
    hidden.view(torch.uint16).flatten()[:2] = torch.tensor([0x8000, 0x7E03], dtype=torch.uint16)
    monkeypatch.setattr(module, "CHUNK_BYTES", 8)
    real_cpu = torch.Tensor.cpu
    sizes = []

    def cpu(tensor, *args, **kwargs):
        if tensor.is_floating_point():
            amount = tensor.numel() * tensor.element_size()
            sizes.append(amount)
            assert amount <= 8, "a full hidden/logit copy bypassed the slice bound"
        return real_cpu(tensor, *args, **kwargs)

    monkeypatch.setattr(torch.Tensor, "cpu", cpu)
    module.capture_head_inputs(model, infer, root, {})
    assert (root / "hidden.bin").read_bytes() == hidden.view(torch.uint8).numpy().tobytes()
    assert not json.loads((root / "manifest.json").read_text())["hidden"]["finite"]
    assert len(sizes) >= 4


def test_capture_checks_empty_directory_without_materializing_all_names(tmp_path, monkeypatch):
    import clef_use.head_trace as module

    root, model, infer, _, _ = _case(tmp_path)
    monkeypatch.setattr(
        module.os,
        "listdir",
        lambda *a: pytest.fail("directory emptiness must use a bounded iterator"),
    )
    module.capture_head_inputs(model, infer, root, {})
    assert (root / "manifest.json").exists()
