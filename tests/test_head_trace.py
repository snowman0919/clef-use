"""Private diagnostic capture must not alter inference or lose tensor bits."""

import hashlib
import json
import os
from types import SimpleNamespace

import pytest


@pytest.mark.skipif(os.name != "posix", reason="private descriptor-relative capture is POSIX-only")
@pytest.mark.parametrize("precision", ["float16", "bfloat16", "float32"])
def test_private_head_capture_preserves_tensors_and_decision(tmp_path, precision):
    torch = pytest.importorskip("torch")
    from clef_use.head_trace import capture_head_inputs

    dtype = getattr(torch, precision)
    hidden = torch.arange(32, dtype=torch.float32).reshape(1, 8, 4).div(7).to(dtype)
    ids = torch.tensor([[1, 4, 5, 3, 4, 5, 7, 8]])
    mask = torch.ones_like(ids)
    records = [
        SimpleNamespace(
            input_ids=tuple(ids[0].tolist()),
            questions=[
                SimpleNamespace(
                    question_id="complete",
                    question_type=0,
                    question_span=(0, 2),
                    option_spans=((2, 4), (4, 6)),
                    option_ids=("true", "false"),
                )
            ],
        )
    ]

    class Head(torch.nn.Module):
        def forward(self, values, *args):
            return [[torch.stack((values.sum(), -values.sum()))]]

    head = Head().eval()
    model = SimpleNamespace(head=head)
    expected = head(hidden, ids, mask, records, None)[0][0].clone()
    root = tmp_path / "private"
    root.mkdir(mode=0o700)

    def infer():
        logits = head(hidden, ids, mask, records, None)[0][0]
        return {"answers": {"complete": logits.tolist()}}

    metadata = {"frame_image_sha256": "f" * 64, "model_revision": "f" * 40}
    result = capture_head_inputs(model, infer, root, metadata)
    torch.testing.assert_close(
        torch.tensor(result["answers"]["complete"], dtype=dtype), expected, rtol=0, atol=0
    )
    manifest = json.loads((root / "manifest.json").read_text())
    raw = (root / "hidden.bin").read_bytes()
    restored = torch.frombuffer(bytearray(raw), dtype=dtype).reshape(hidden.shape)
    assert torch.equal(restored, hidden)
    assert manifest["hidden"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert manifest["input_ids"] == ids.tolist()
    assert manifest["attention_mask"] == mask.tolist()
    assert manifest["questions"][0]["option_spans"] == [[2, 4], [4, 6]]
    logit_meta = manifest["logits"][0]
    logit_raw = (root / "logits.bin").read_bytes()
    assert logit_meta["dtype"] == precision and logit_meta["shape"] == [2]
    assert logit_raw == expected.view(torch.uint8).numpy().tobytes()
    assert logit_meta["sha256"] == hashlib.sha256(logit_raw).hexdigest()
    assert manifest["source"] == metadata
    assert manifest["hidden"]["finite"] is True
    assert len(head._forward_pre_hooks) == len(head._forward_hooks) == 0
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in root.iterdir())
    assert root.stat().st_mode & 0o777 == 0o700


@pytest.mark.skipif(os.name != "posix", reason="private capture is POSIX-only")
@pytest.mark.parametrize("unsafe", ["symlink", "public", "nonempty"])
def test_private_head_capture_refuses_unsafe_destination_before_inference(tmp_path, unsafe):
    torch = pytest.importorskip("torch")
    from clef_use.head_trace import capture_head_inputs

    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    root = real
    if unsafe == "symlink":
        root = tmp_path / "link"
        root.symlink_to(real, target_is_directory=True)
    elif unsafe == "public":
        real.chmod(0o755)
    else:
        (real / "keep").write_text("unchanged")

    model = SimpleNamespace(head=torch.nn.Linear(2, 2))

    def infer():
        pytest.fail("unsafe diagnostic destination must be refused before inference")

    with pytest.raises(ValueError, match="private|empty|symlink"):
        capture_head_inputs(model, infer, root, {})
    if unsafe == "nonempty":
        assert (real / "keep").read_text() == "unchanged"
    assert len(model.head._forward_pre_hooks) == len(model.head._forward_hooks) == 0


@pytest.mark.skipif(os.name != "posix", reason="private capture is POSIX-only")
def test_private_head_capture_removes_hooks_on_failure(tmp_path):
    torch = pytest.importorskip("torch")
    from clef_use.head_trace import capture_head_inputs

    model = SimpleNamespace(head=torch.nn.Linear(2, 2))
    root = tmp_path / "private"
    root.mkdir(mode=0o700)

    def fail():
        raise RuntimeError("original inference failure")

    with pytest.raises(RuntimeError, match="original inference failure"):
        capture_head_inputs(model, fail, root, {})
    assert len(model.head._forward_pre_hooks) == len(model.head._forward_hooks) == 0
    assert not list(root.iterdir())
