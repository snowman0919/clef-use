import os
from types import SimpleNamespace

import pytest


@pytest.mark.skipif(os.name != "posix", reason="private capture is POSIX-only")
def test_head_capture_enforces_chunk_budget_and_removes_partial_files(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")
    import clef_use.head_trace as module

    monkeypatch.setattr(module, "CHUNK_BYTES", 8)
    hidden = torch.ones(1, 2, 5, dtype=torch.float16)
    ids = torch.ones(1, 2, dtype=torch.long)
    record = SimpleNamespace(
        input_ids=(1, 1),
        questions=[
            SimpleNamespace(
                question_id="x",
                question_type=0,
                question_span=(0, 1),
                option_spans=((0, 1), (1, 2)),
                option_ids=("true", "false"),
            )
        ],
    )

    class Head(torch.nn.Module):
        def forward(self, values, *args):
            return [[torch.tensor([1.0, -1.0])]]

    model = SimpleNamespace(head=Head())
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="chunk budget"):
        module.capture_head_inputs(
            model, lambda: {"answers": model.head(hidden, ids, ids, [record], None)}, root, {}
        )
    assert not list(root.iterdir())
    assert len(model.head._forward_pre_hooks) == len(model.head._forward_hooks) == 0
