import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image

from clef_use.grounding import DenseGroundingHead, load_grounding_head, save_grounding_head

torch = pytest.importorskip("torch")


def test_siglip_rejects_query_whose_target_would_be_truncated():
    from types import SimpleNamespace

    from transformers import AutoProcessor

    from clef_use.grounding import GroundingQueryTooLong, _SiglipTextEncoder

    path = (
        Path.home()
        / ".cache/clef-use/models/huggingface/hub"
        / "models--google--siglip2-base-patch16-512/snapshots"
        / "a89f5c5093f902bf39d3cd4d81d2c09867f0724b"
    )
    if not path.is_dir():
        pytest.skip("pinned tokenizer is not installed")
    processor = AutoProcessor.from_pretrained(path, local_files_only=True)
    model = SimpleNamespace(
        device="cpu",
        config=SimpleNamespace(text_config=SimpleNamespace(max_position_embeddings=64)),
    )
    encoder = _SiglipTextEncoder(model, processor, torch)
    with pytest.raises(GroundingQueryTooLong):
        encoder.encode_query("face " * 70 + "different target after the context limit")


def trained_head():
    head = DenseGroundingHead(3, hidden_size=8, seed=7)
    tokens = torch.tensor([[1.0, 0, 0], [0, 1.0, 0]], requires_grad=True)
    text = torch.tensor([0, 1.0, 0], requires_grad=True)
    absent = torch.tensor([0, 0, 1.0])
    optimizer = torch.optim.Adam(head.parameters(), lr=0.025)
    before = float(head.loss(tokens, text, [0, 1], [[0, 0], [0.3, -0.2]]).detach())
    for _ in range(100):
        for features, query, index, offset in [
            (tokens, text, [0, 1], [[0, 0], [0.3, -0.2]]),
            (tokens, absent, [0, 0], None),
            (torch.zeros_like(tokens), text, [0, 0], None),
        ]:
            optimizer.zero_grad()
            head.loss(features, query, index, offset).backward()
            optimizer.step()
            head.record_training_sample(any(index))
    return head, tokens, text, absent, before


def metadata():
    return {
        "manifest_sha256": "a" * 64,
        "seed": 7,
        "train_image_sha256": ["b" * 64],
        "validation_image_sha256": ["c" * 64],
        "split_counts": {
            "train": {"positive": 1, "negative": 1},
            "validation": {"positive": 1, "negative": 1},
        },
        "coarse_strategy_counts": {
            "tiled": {
                "train": {"positive": 1, "negative": 1},
                "validation": {"positive": 1, "negative": 1},
            },
        },
    }


def test_dense_head_learns_presence_offsets_and_keeps_encoders_frozen():
    head, tokens, text, absent, before = trained_head()
    logits, offsets = head.forward(tokens, text)
    assert before - float(head.loss(tokens, text, [0, 1], [[0, 0], [0.3, -0.2]]).detach()) > 1
    assert logits.argmax().item() == 1
    assert logits[1].sigmoid().item() > 0.9
    assert head.forward(tokens, absent)[0].sigmoid().max().item() < 0.1
    assert head.forward(torch.zeros_like(tokens), text)[0].sigmoid().max().item() < 0.1
    assert offsets[1].detach().tolist() == pytest.approx([0.3, -0.2], abs=0.04)
    assert tokens.grad is None and text.grad is None
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in head.parameters())
    assert any(p.grad.norm().item() > 1e-8 for p in head.parameters())
    with torch.no_grad():
        head.network["text"].weight.zero_()
        head.network["text"].bias.zero_()
    assert torch.allclose(head.forward(tokens, text)[0], head.forward(tokens, absent)[0])


def test_absence_loss_has_no_location_or_offset_supervision():
    head = DenseGroundingHead(3, hidden_size=8)
    tokens, text = torch.eye(3), torch.ones(3)
    loss = head.loss(tokens, text, [0, 0, 0])
    logits, _ = head.forward(tokens, text)
    assert loss.item() == pytest.approx(torch.nn.functional.softplus(logits).mean().item())
    loss.backward()
    output_weight = head.network["fusion"][2].weight
    assert output_weight.grad[1:].abs().sum().item() == 0
    assert output_weight.grad[0].abs().sum().item() > 0


def test_dense_location_weights_prefer_one_interior_point_without_losing_presence():
    torch.manual_seed(0)
    head = DenseGroundingHead(3, hidden_size=8)
    tokens, text = torch.eye(3), torch.ones(3)
    optimizer = torch.optim.Adam(head.parameters(), lr=0.02)
    for _ in range(180):
        optimizer.zero_grad()
        head.loss(tokens, text, [0.05, 1, 0.05], torch.zeros(3, 2)).backward()
        optimizer.step()
    logits, _ = head.forward(tokens, text)
    # Every point is inside the target; the location density still prefers a
    # stable interior point instead of requiring a flat spatial distribution.
    assert logits.argmax().item() == 1
    assert logits.softmax(0)[1].item() > 0.8
    assert logits.sigmoid().min().item() > 0.8


def test_safe_checkpoint_roundtrip_preserves_prediction_and_freezes_head(tmp_path):
    head, tokens, text, _, _ = trained_head()
    path = tmp_path / "head.safetensors"
    save_grounding_head(head, path, metadata())
    restored = load_grounding_head(path, dimension=3)
    for actual, expected in zip(
        restored.forward(tokens, text), head.forward(tokens, text), strict=True
    ):
        assert torch.allclose(actual, expected, atol=1e-6)
    assert all(not p.requires_grad for p in restored.parameters())


def test_checkpoint_refuses_undeclared_overview_and_inconsistent_strategy_counts(tmp_path):
    from clef_use.grounding import GroundingStrategyUnsupported

    head, _, _, _, _ = trained_head()
    path = tmp_path / "tiled.safetensors"
    save_grounding_head(head, path, metadata())
    restored = load_grounding_head(path, dimension=3)
    grounder = spatial_fixture()
    grounder.head.dense_head = restored
    with pytest.raises(GroundingStrategyUnsupported):
        grounder.ground(Image.new("RGB", (64, 64)), "target", coarse_strategy="overview")
    inconsistent = metadata()
    inconsistent["coarse_strategy_counts"]["tiled"]["train"]["positive"] = 2
    with pytest.raises(ValueError, match="counts"):
        save_grounding_head(head, tmp_path / "invalid.safetensors", inconsistent)


def test_random_head_and_missing_absence_training_cannot_be_served(tmp_path):
    head = DenseGroundingHead(3, hidden_size=8, seed=7)
    head.record_training_sample(True)
    head.record_training_sample(False)
    with pytest.raises(ValueError, match="trained"):
        save_grounding_head(head, tmp_path / "random.safetensors", metadata())
    head, *_ = trained_head()
    audit = metadata()
    audit["split_counts"]["validation"]["negative"] = 0
    with pytest.raises(ValueError, match="positive and negative"):
        save_grounding_head(head, tmp_path / "positive-only.safetensors", audit)


def test_checkpoint_rejects_old_format_wrong_backbone_shape_and_nonfinite_weights(tmp_path):
    from safetensors import safe_open
    from safetensors.torch import save_file

    head, *_ = trained_head()
    good = tmp_path / "good.safetensors"
    save_grounding_head(head, good, metadata())
    with safe_open(good, framework="pt") as checkpoint:
        data = checkpoint.metadata()
    for key, value in [
        ("format", "clef-use-grounding-head-v1"),
        ("format", "clef-use-grounding-head-v2"),
        ("backbone_revision", "wrong"),
    ]:
        bad = dict(data)
        bad[key] = value
        path = tmp_path / "bad.safetensors"
        save_file(head.state_dict(), path, metadata=bad)
        with pytest.raises(ValueError, match="provenance"):
            load_grounding_head(path, dimension=3)
    weights = head.state_dict()
    weights["image.weight"] = weights["image.weight"][:1]
    save_file(weights, path, metadata=data)
    with pytest.raises(ValueError, match="shape"):
        load_grounding_head(path, dimension=3)
    weights = head.state_dict()
    weights["image.weight"][0, 0] = float("nan")
    save_file(weights, path, metadata=data)
    with pytest.raises(ValueError, match="finite"):
        load_grounding_head(path, dimension=3)


def training_script():
    path = Path(__file__).parents[1] / "scripts/train_grounding_head.py"
    spec = importlib.util.spec_from_file_location("train_grounding_head", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fine_augmentation_count_does_not_change_coarse_training_influence():
    script = training_script()
    text = torch.ones(3)
    coarse = script.TrainingContext(
        torch.eye(3),
        text,
        torch.tensor([0.0, 1.0, 0.0]),
        torch.zeros(3, 2),
        [],
        "coarse",
    )
    fine = script.TrainingContext(
        torch.tensor([[1.0, 1.0, 0.0], [1.0, 0.0, 1.0]]),
        text,
        torch.tensor([0.0, 1.0]),
        torch.zeros(2, 2),
        [],
        "fine",
    )
    heads = [DenseGroundingHead(3, hidden_size=8, seed=3) for _ in range(2)]
    for head, count in zip(heads, [1, 12], strict=True):
        optimizer = torch.optim.SGD(head.parameters(), lr=0.1)
        for _ in range(30):
            optimizer.zero_grad()
            script.sample_loss(head, [coarse] + [fine] * count).backward()
            optimizer.step()
    for context in [coarse, fine]:
        for first, repeated in zip(
            heads[0].forward(context.tokens, text),
            heads[1].forward(context.tokens, text),
            strict=True,
        ):
            torch.testing.assert_close(first, repeated, atol=1e-6, rtol=1e-6)
    expected = 0.5 * sum(
        heads[0].loss(c.tokens, c.text, c.target, c.offsets) for c in [coarse, fine]
    )
    torch.testing.assert_close(script.sample_loss(heads[0], [coarse] + [fine] * 12), expected)


def test_class_grouped_training_learns_present_and_absent_targets_reproducibly():
    script = training_script()
    tokens = torch.eye(3)
    present, absent = torch.tensor([1.0, 0.0, 0.0]), torch.tensor([0.0, 1.0, 0.0])
    positive = script.TrainingContext(
        tokens,
        present,
        torch.tensor([0.0, 1.0, 0.0]),
        torch.zeros(3, 2),
        [],
        "coarse",
    )
    negative = script.TrainingContext(
        tokens,
        absent,
        torch.zeros(3),
        None,
        [],
        "coarse",
    )
    # Explicit frozen features isolate the head's optimizer from image encoding.
    rows = [[positive]] * 20 + [[negative]] * 35
    heads = [DenseGroundingHead(3, hidden_size=8, seed=3) for _ in range(2)]
    for head in heads:
        optimizer = torch.optim.Adam(head.parameters(), lr=0.01)
        script.fit_head(head, rows, optimizer, epochs=30, seed=7)
        scores = head.forward(tokens, present)[0]
        assert scores.argmax().item() == 1
        assert scores[1].sigmoid().item() > 0.55
        assert head.forward(tokens, absent)[0].sigmoid().max().item() < 0.55
    for query in (present, absent):
        torch.testing.assert_close(
            heads[0].forward(tokens, query)[0], heads[1].forward(tokens, query)[0], atol=0, rtol=0
        )


def test_manifest_rejects_reencoded_same_image_across_training_and_validation(tmp_path):
    image = Image.new("RGB", (16, 16), "red")
    image.save(tmp_path / "one.png")
    image.save(tmp_path / "two.bmp")
    samples = [
        {"image": name, "query": "red", "bbox": [0, 0, 16, 16], "split": split}
        for name, split in [("one.png", "train"), ("two.bmp", "validation")]
    ]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"samples": samples}))
    with pytest.raises(ValueError, match="splits"):
        training_script().read_manifest(manifest)


def test_manifest_keeps_independent_split_hashes_and_checks_annotation_bounds(tmp_path):
    for name, color in [("one.png", "red"), ("two.png", "blue")]:
        Image.new("RGB", (16, 16), color).save(tmp_path / name)
    samples = [
        {"image": name, "query": "red", "bbox": [0, 0, 16, 16], "split": split}
        for name, split in [("one.png", "train"), ("two.png", "validation")]
    ]
    samples += [
        {"image": name, "query": "absent", "bbox": None, "split": split}
        for name, split in [("one.png", "train"), ("two.png", "validation")]
    ]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"samples": samples}))
    rows, audit = training_script().read_manifest(manifest)
    assert audit["train_image_sha256"] != audit["validation_image_sha256"]
    assert rows[0]["bbox"] == (0.0, 0.0, 16.0, 16.0)
    samples[0]["bbox"] = [0, 0, 17, 16]
    manifest.write_text(json.dumps({"samples": samples}))
    with pytest.raises(ValueError, match="bbox"):
        training_script().read_manifest(manifest)


def test_each_manifest_split_requires_present_and_absent_queries(tmp_path):
    for name, color in [("one.png", "red"), ("two.png", "blue")]:
        Image.new("RGB", (16, 16), color).save(tmp_path / name)
    samples = [
        {"image": name, "query": "red", "bbox": [0, 0, 16, 16], "split": split}
        for name, split in [("one.png", "train"), ("two.png", "validation")]
    ]
    samples.append({"image": "one.png", "query": "absent", "bbox": None, "split": "train"})
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"samples": samples}))
    with pytest.raises(ValueError, match="positive and negative"):
        training_script().read_manifest(manifest)


def test_manifest_rejects_target_outside_serving_region(tmp_path):
    for name, color in [("one.png", "red"), ("two.png", "blue")]:
        Image.new("RGB", (16, 16), color).save(tmp_path / name)
    samples = [
        {"image": name, "query": "red", "bbox": bbox, "split": split}
        for name, split in [("one.png", "train"), ("two.png", "validation")]
        for bbox in [[0, 0, 8, 8], None]
    ]
    samples[0]["region"] = dict(x1=0.5, y1=0, x2=1, y2=1)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"samples": samples}))
    with pytest.raises(ValueError, match="region"):
        training_script().read_manifest(manifest)


def spatial_fixture():
    from clef_use.grounding import Grounder, NormalizedDotProductHead

    class Backbone:
        image_size = 64

        def encode_image(self, image):
            return torch.ones(4, 4, 3)

    class Text:
        def encode_query(self, query):
            return torch.ones(3)

    class Head(NormalizedDotProductHead):
        def embed_features(self, features):
            return features.reshape(-1, 3)

    return Grounder(Backbone(), Text(), Head())


def test_every_intersecting_thin_divider_patch_gets_reachable_interior_offset():
    script = training_script()
    context = script._context(
        spatial_fixture(),
        Image.new("RGB", (64, 64)),
        [(0, 0, 64, 64)],
        (0, 31, 64, 34),
        torch.ones(3),
        stage="coarse",
    )
    target, offsets, samples = context.target, context.offsets, context.samples
    assert target.bool().tolist() == [False] * 4 + [True] * 8 + [False] * 4
    for index in target.nonzero().flatten().tolist():
        sample = samples[index]
        x = sample.center_x + float(offsets[index, 0]) * sample.pitch_x
        y = sample.center_y + float(offsets[index, 1]) * sample.pitch_y
        assert 0 <= x < 64 and 31 <= y < 34
        assert offsets[index].abs().max().item() <= 0.5


def test_absent_manifest_sample_supervises_all_serving_crop_scales_without_fake_box(tmp_path):
    image = tmp_path / "blank.png"
    Image.new("RGB", (64, 64)).save(image)
    contexts = training_script().prepare_sample(
        spatial_fixture(),
        {"image": image, "query": "absent", "bbox": None},
    )
    assert all(not c.target.any() and c.offsets is None for c in contexts)
    assert [c.samples[0].pitch_x for c in contexts] == [16, 6, 4, 2]


def test_region_training_preserves_scoped_original_coordinates(tmp_path):
    from clef_use.schema import BoundingBox

    image = tmp_path / "screen.png"
    Image.new("RGB", (64, 64)).save(image)
    contexts = training_script().prepare_sample(
        spatial_fixture(),
        {
            "image": image,
            "query": "target",
            "bbox": (40, 16, 48, 32),
            "region": BoundingBox(x1=0.5, y1=0, x2=1, y2=1),
        },
    )
    scoped = [
        context
        for context in contexts
        if len(context.samples) == 8 and all(s.center_x >= 32 for s in context.samples)
    ]
    target, offsets, samples = scoped[0].target, scoped[0].offsets, scoped[0].samples
    for index in target.nonzero().flatten().tolist():
        sample = samples[index]
        x = sample.center_x + float(offsets[index, 0]) * sample.pitch_x
        y = sample.center_y + float(offsets[index, 1]) * sample.pitch_y
        assert 40 <= x < 48 and 16 <= y < 32


def test_scoped_absence_never_supervises_pixels_outside_that_region(tmp_path):
    from clef_use.schema import BoundingBox

    image = tmp_path / "screen.png"
    Image.new("RGB", (64, 64)).save(image)
    contexts = training_script().prepare_sample(
        spatial_fixture(),
        {
            "image": image,
            "query": "absent in right region",
            "bbox": None,
            "region": BoundingBox(x1=0.5, y1=0, x2=1, y2=1),
        },
    )
    for context in contexts:
        assert context.offsets is None and not context.target.any()
        assert all(s.footprint[0] >= 32 and s.footprint[2] <= 64 for s in context.samples)


def test_cached_spatial_features_preserve_queries_and_changed_pixel_targets():
    from types import SimpleNamespace

    from clef_use.grounding import Grounder, NormalizedDotProductHead, _SiglipVisionBackbone

    class PixelEncoder:
        def __call__(self, *, pixel_values):
            colors = torch.nn.functional.max_pool2d(pixel_values[:, :2], 4)
            features = torch.cat((colors, torch.ones_like(colors[:, :1])), dim=1)
            return SimpleNamespace(last_hidden_state=features.permute(0, 2, 3, 1).reshape(1, -1, 3))

    class PixelProcessor:
        def image_processor(self, *, images, **kwargs):
            pixels = torch.frombuffer(bytearray(images.tobytes()), dtype=torch.uint8)
            return {"pixel_values": pixels.reshape(64, 64, 3).permute(2, 0, 1)[None].float()}

    class ColorQuery:
        def encode_query(self, query):
            return {"red": [1, 0, 0], "green": [0, 1, 0]}[query]

    model = SimpleNamespace(
        config=SimpleNamespace(vision_config=SimpleNamespace(image_size=64, patch_size=4)),
        device="cpu",
        vision_model=PixelEncoder(),
    )
    backbone = _SiglipVisionBackbone(model, PixelProcessor(), torch)
    grounder = Grounder(backbone, ColorQuery(), NormalizedDotProductHead())
    image = Image.new("RGB", (64, 64))
    image.putpixel((17, 31), (255, 0, 0))
    image.putpixel((45, 31), (0, 255, 0))
    assert grounder.ground(image, "red").point == pytest.approx((17, 31), abs=3)
    assert grounder.ground(image, "green").point == pytest.approx((45, 31), abs=3)
    image.putpixel((17, 31), (0, 0, 0))
    image.putpixel((51, 31), (255, 0, 0))
    assert grounder.ground(image, "red").point == pytest.approx((51, 31), abs=3)
