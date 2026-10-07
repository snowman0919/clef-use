"""Train only a dense grounding head on independent annotated screenshots.

Manifest: {"samples": [{"image": "screen.png", "query": "Modeling",
                       "bbox": [337, 3, 398, 25], "split": "train"}, ...]}
Bboxes are original screenshot pixels; right/bottom bounds are exclusive.
A null bbox marks an absent query within its region, or the full image if omitted.
Both splits require positives and negatives.
Optional region is normalized x1/y1/x2/y2 serving geometry; positives must fit it.
Optional coarse_strategy is tiled (default) or overview; each declared strategy
requires positives and absences in both independent splits.
Identical decoded screenshots cannot cross splits, even when encoded differently.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path
from types import SimpleNamespace
from typing import NamedTuple

from PIL import Image

from clef_use.grounding import (
    DenseGroundingHead,
    SiglipGrounder,
    SpatialPrediction,
    image_region_bounds,
    save_grounding_head,
)


def read_manifest(path):
    path = Path(path)
    raw = path.read_bytes()
    document = json.loads(raw)
    if not isinstance(document, dict) or not isinstance(document.get("samples"), list):
        raise ValueError("manifest requires a samples array")
    rows, hashes = [], {"train": set(), "validation": set()}
    for sample in document["samples"]:
        if not isinstance(sample, dict) or sample.get("split") not in hashes:
            raise ValueError("every sample must name a train or validation split")
        query = sample.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("every sample requires a nonempty query")
        strategy = sample.get("coarse_strategy", "tiled")
        if not isinstance(strategy, str) or strategy not in {"tiled", "overview"}:
            raise ValueError("coarse_strategy must be tiled or overview")
        image_path = sample.get("image")
        if not isinstance(image_path, str) or not image_path:
            raise ValueError("every sample requires an image path")
        image_path = (path.parent / image_path).resolve()
        with Image.open(image_path) as source:
            image = source.convert("RGB")
        bbox = sample.get("bbox")
        if "bbox" not in sample:
            raise ValueError("every sample requires bbox, or null for an absent target")
        if bbox is not None:
            if (
                not isinstance(bbox, list)
                or len(bbox) != 4
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    for value in bbox
                )
            ):
                raise ValueError("bbox must contain four finite pixel coordinates")
            x1, y1, x2, y2 = (float(value) for value in bbox)
            if not (0 <= x1 < x2 <= image.width and 0 <= y1 < y2 <= image.height):
                raise ValueError("bbox must be a positive region inside its screenshot")
            bbox = (x1, y1, x2, y2)
        region = sample.get("region")
        if region is not None:
            if not isinstance(region, dict) or set(region) != {"x1", "y1", "x2", "y2"}:
                raise ValueError("region must contain normalized x1/y1/x2/y2 coordinates")
            region = SimpleNamespace(**region)
            image_region_bounds(image.size, region)
            if bbox is not None and not (
                region.x1 * image.width <= bbox[0] < bbox[2] <= region.x2 * image.width
                and region.y1 * image.height <= bbox[1] < bbox[3] <= region.y2 * image.height
            ):
                raise ValueError("positive bbox must be inside its serving region")
        digest = hashlib.sha256(
            str(image.size).encode("ascii") + b"RGB" + image.tobytes()
        ).hexdigest()
        hashes[sample["split"]].add(digest)
        rows.append(
            {
                "image": image_path,
                "query": query.strip(),
                "bbox": bbox,
                "region": region,
                "split": sample["split"],
                "sha256": digest,
                "coarse_strategy": strategy,
            }
        )
    if not hashes["train"] or not hashes["validation"]:
        raise ValueError("nonempty independent train and validation splits are required")
    if hashes["train"] & hashes["validation"]:
        raise ValueError("identical screenshots cannot occur across splits")
    counts = {
        split: {
            label: sum(
                row["split"] == split and (row["bbox"] is not None) == (label == "positive")
                for row in rows
            )
            for label in ("positive", "negative")
        }
        for split in hashes
    }
    if any(count <= 0 for values in counts.values() for count in values.values()):
        raise ValueError("both splits require positive and negative annotations")
    strategy_counts = {
        strategy: {
            split: {
                label: sum(
                    row["coarse_strategy"] == strategy
                    and row["split"] == split
                    and (row["bbox"] is not None) == (label == "positive")
                    for row in rows
                )
                for label in ("positive", "negative")
            }
            for split in hashes
        }
        for strategy in sorted({row["coarse_strategy"] for row in rows})
    }
    if any(
        count <= 0
        for strategy in strategy_counts.values()
        for split in strategy.values()
        for count in split.values()
    ):
        raise ValueError("each coarse strategy requires independent positive and negative splits")
    return rows, {
        "split_counts": counts,
        "coarse_strategy_counts": strategy_counts,
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "train_image_sha256": sorted(hashes["train"]),
        "validation_image_sha256": sorted(hashes["validation"]),
    }


class _FeatureIndexHead:
    """Training-only patch indices into frozen embeddings, never action scores."""

    def __init__(self, pretrained_head):
        self.pretrained_head = pretrained_head
        self.embeddings = None

    def predict(self, features, text):
        rows, columns, _ = features.shape
        self.embeddings = self.pretrained_head.embed_features(features)
        return SpatialPrediction(
            [[row * columns + column for column in range(columns)] for row in range(rows)]
        )


class TrainingContext(NamedTuple):
    tokens: object
    text: object
    target: object
    offsets: object
    samples: list
    stage: str


def sample_loss(head, contexts):
    """Balance serving stages, independent of fine-crop augmentation count."""
    import torch

    losses = {"coarse": [], "fine": []}
    for context in contexts:
        if context.stage not in losses:
            raise ValueError("unknown grounding training stage")
        losses[context.stage].append(
            head.loss(context.tokens, context.text, context.target, context.offsets)
        )
    means = [torch.stack(values).mean() for values in losses.values() if values]
    if not means:
        raise ValueError("training sample requires spatial contexts")
    return torch.stack(means).mean()


def _context(grounder, image, boxes, bbox, text, *, stage):
    import torch

    pretrained_head = grounder.head
    index_head = _FeatureIndexHead(pretrained_head)
    tokens, samples = [], []
    grounder.head = index_head
    try:
        for box in boxes:
            current = grounder._samples(image, box, text)
            indices = torch.tensor([int(sample.score) for sample in current], device=text.device)
            tokens.append(index_head.embeddings[indices].detach().clone())
            samples.extend(current)
    finally:
        grounder.head = pretrained_head
    target = torch.zeros(len(samples), device=text.device)
    offsets = None
    if bbox is not None:
        offsets = torch.zeros(len(samples), 2, device=text.device)
        center_x, center_y = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        annotation_sigma_x, annotation_sigma_y = (bbox[2] - bbox[0]) / 4, (bbox[3] - bbox[1]) / 4
        for index, sample in enumerate(samples):
            x1, y1 = max(bbox[0], sample.footprint[0]), max(bbox[1], sample.footprint[1])
            x2, y2 = min(bbox[2], sample.footprint[2]), min(bbox[3], sample.footprint[3])
            if x1 >= x2 or y1 >= y2:
                continue
            # Presence covers the entire annotation. Spatial density prefers
            # its interior, rather than teaching a plateau of equally good peaks.
            sigma_x = max(annotation_sigma_x, sample.pitch_x / 2)
            sigma_y = max(annotation_sigma_y, sample.pitch_y / 2)
            target[index] = math.exp(
                -0.5
                * (
                    (((x1 + x2) / 2 - center_x) / sigma_x) ** 2
                    + (((y1 + y2) / 2 - center_y) / sigma_y) ** 2
                )
            )
            offsets[index] = torch.tensor(
                (
                    ((x1 + x2) / 2 - sample.center_x) / sample.pitch_x,
                    ((y1 + y2) / 2 - sample.center_y) / sample.pitch_y,
                ),
                device=text.device,
            )
        if not target.any():
            raise ValueError("annotation has no intersecting valid spatial patch")
        if (offsets.abs() > 0.500001).any():
            raise ValueError("annotation intersection is outside its patch")
        offsets = offsets.clamp(-0.5, 0.5)
    return TrainingContext(
        torch.cat(tokens), text.detach().clone(), target, offsets, samples, stage
    )


def fit_head(head, rows, optimizer, *, epochs, seed):
    """Visit each training row once per epoch, avoiding manifest class blocks."""
    order = list(rows)
    rng = random.Random(seed)
    updates = 0
    for _ in range(epochs):
        rng.shuffle(order)
        for passes in order:
            optimizer.zero_grad()
            loss = sample_loss(head, passes)
            if not head.torch.isfinite(loss):
                raise ValueError("training loss is not finite")
            loss.backward()
            if not all(
                p.grad is not None and head.torch.isfinite(p.grad).all() for p in head.parameters()
            ):
                raise ValueError("head gradients are missing or not finite")
            optimizer.step()
            updates += 1
            for context in passes:
                head.record_training_sample(bool(context.target.any()))
    return updates


def prepare_sample(grounder, row):
    with Image.open(row["image"]) as source:
        image = source.convert("RGB")
    text = grounder.text_encoder.encode_query(row["query"])
    size = grounder.backbone.image_size
    strategy = row.get("coarse_strategy", "tiled")
    contexts, seen = [], {}
    regions = [row["region"]] if row.get("region") is not None and row["bbox"] is None else [None]
    if row.get("region") is not None and row["bbox"] is not None:
        regions.append(row["region"])

    def add(boxes, stage):
        key = (stage, tuple(boxes))
        if key in seen:
            return seen[key]
        context = _context(grounder, image, boxes, row["bbox"], text, stage=stage)
        seen[key] = context
        contexts.append(context)
        return context

    for region in regions:
        left, top, right, bottom = image_region_bounds(image.size, region)
        boxes = (
            [(left, top, right, bottom)]
            if strategy == "overview"
            else [
                (x, y, min(x + size, right), min(y + size, bottom))
                for y in grounder._starts(top, bottom, size)
                for x in grounder._starts(left, right, size)
            ]
        )
        add(boxes, "coarse")
        for refinement in range(3):
            if row["bbox"] is None:
                # These are real absent-query serving proposals, never invented targets.
                fine_box = grounder.ground(
                    image,
                    row["query"],
                    region=region,
                    refinement=refinement,
                    coarse_strategy=strategy,
                ).coarse_roi
                add([fine_box], "fine")
                continue
            x1, y1, x2, y2 = row["bbox"]
            x, y = (x1 + x2) / 2, (y1 + y2) / 2
            radius = max(2, size / (4 * 2**refinement))
            # A predicted coarse point does not have the annotation's fixed
            # patch phase. Train half-patch translations at each magnification.
            nominal_box = (
                max(left, math.floor(x - radius)),
                max(top, math.floor(y - radius)),
                min(right, math.ceil(x + radius)),
                min(bottom, math.ceil(y + radius)),
            )
            nominal = add([nominal_box], "fine")
            phase_x = max(1, min(s.pitch_x for s in nominal.samples) / 2)
            phase_y = max(1, min(s.pitch_y for s in nominal.samples) / 2)
            for dx, dy in ((-phase_x, 0), (phase_x, 0), (0, -phase_y), (0, phase_y)):
                fine_box = (
                    max(left, math.floor(x + dx - radius)),
                    max(top, math.floor(y + dy - radius)),
                    min(right, math.ceil(x + dx + radius)),
                    min(bottom, math.ceil(y + dy + radius)),
                )
                add([fine_box], "fine")
    return contexts


def train(
    manifest, output, *, epochs=20, hidden_size=64, learning_rate=0.001, seed=0, device="cpu"
):
    import torch
    import transformers

    if not isinstance(epochs, int) or epochs <= 0:
        raise ValueError("epochs must be a positive integer")
    if not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("learning rate must be finite and positive")
    rows, audit = read_manifest(manifest)
    grounder = SiglipGrounder(device=device)
    dimension = grounder.model.config.vision_config.hidden_size
    head = DenseGroundingHead(dimension, hidden_size=hidden_size, seed=seed, device=device)
    head.coarse_strategies = frozenset(audit["coarse_strategy_counts"])
    contexts = [(row, prepare_sample(grounder, row)) for row in rows]
    optimizer = torch.optim.Adam(head.parameters(), lr=learning_rate)

    def evaluate(split):
        losses, hits, negative_presence = [], [], []
        stages = {
            name: {"losses": [], "hits": [], "negative_presence": []} for name in ("coarse", "fine")
        }
        with torch.no_grad():
            for row, passes in contexts:
                if row["split"] != split:
                    continue
                row_losses = {name: [] for name in stages}
                for tokens, text, target, offsets, samples, stage in passes:
                    loss = float(head.loss(tokens, text, target, offsets))
                    row_losses[stage].append(loss)
                    stages[stage]["losses"].append(loss)
                    logits, predicted_offsets = head.forward(tokens, text)
                    chosen = int(logits.argmax())
                    if not target.any():
                        presence = float(logits.sigmoid().max())
                        negative_presence.append(presence)
                        stages[stage]["negative_presence"].append(presence)
                        continue
                    sample = samples[chosen]
                    dx, dy = predicted_offsets[chosen].tolist()
                    x, y = (
                        sample.center_x + dx * sample.pitch_x,
                        sample.center_y + dy * sample.pitch_y,
                    )
                    x1, y1, x2, y2 = row["bbox"]
                    hit = x1 <= x < x2 and y1 <= y < y2
                    hits.append(hit)
                    stages[stage]["hits"].append(hit)
                means = [sum(values) / len(values) for values in row_losses.values() if values]
                losses.append(sum(means) / len(means))
        return {
            "combined_loss": sum(losses) / len(losses),
            "target_hit_rate": sum(hits) / len(hits),
            "negative_max_binary_score": max(negative_presence),
            "contexts": sum(len(values["losses"]) for values in stages.values()),
            "stages": {
                name: {
                    "context_mean_loss": sum(values["losses"]) / len(values["losses"]),
                    "target_hits": sum(values["hits"]),
                    "positive_contexts": len(values["hits"]),
                    "negative_max_binary_score": max(values["negative_presence"], default=None),
                    "contexts": len(values["losses"]),
                }
                for name, values in stages.items()
                if values["losses"]
            },
        }

    baseline = {split: evaluate(split) for split in ("train", "validation")}
    optimizer_steps = fit_head(
        head,
        [passes for row, passes in contexts if row["split"] == "train"],
        optimizer,
        epochs=epochs,
        seed=seed,
    )
    final = {split: evaluate(split) for split in ("train", "validation")}
    grounder.head.dense_head = head
    grounder.temperature = 1.0
    validation = []
    for row in rows:
        if row["split"] != "validation":
            continue
        with Image.open(row["image"]) as source:
            image = source.convert("RGB")
        regions = (
            [row["region"]]
            if row.get("region") is not None and row["bbox"] is None
            else [None] + ([row["region"]] if row.get("region") is not None else [])
        )
        for region, refinement in ((r, n) for r in regions for n in range(3)):
            result = grounder.ground(
                image,
                row["query"],
                region=region,
                refinement=refinement,
                coarse_strategy=row["coarse_strategy"],
            )
            inside = None
            if row["bbox"] is not None:
                x1, y1, x2, y2 = row["bbox"]
                inside = x1 <= result.point[0] < x2 and y1 <= result.point[1] < y2
            validation.append(
                {
                    "image_sha256": row["sha256"],
                    "query": row["query"],
                    "coarse_strategy": row["coarse_strategy"],
                    "refinement": refinement,
                    "region": vars(region) if region is not None else None,
                    "positive": row["bbox"] is not None,
                    "point": result.point,
                    "confidence": result.confidence,
                    "entropy": result.entropy,
                    "target_region": result.target_region,
                    "inside_target": inside,
                    "accepted": result.confidence >= 0.55,
                    "false_accept": row["bbox"] is None and result.confidence >= 0.55,
                }
            )
    audit.update(
        seed=seed,
        epochs=epochs,
        hidden_size=hidden_size,
        learning_rate=learning_rate,
        torch_version=torch.__version__,
        transformers_version=transformers.__version__,
        device=device,
        dtype="float32",
        runs=1,
        optimizer_steps=optimizer_steps,
        row_order="seeded shuffle each epoch; every training row visited once",
        training_objective=(
            "mean loss within coarse and fine serving stages, equal stage weight per row; "
            "one optimizer update per training row"
        ),
        context_method=(
            "declared full/scoped coarse input plus three native fine scales; "
            "translations use half of the actual fine-crop patch pitch per axis"
        ),
        localization_method=(
            "annotation-centered Gaussian density; sigma per axis is the greater of "
            "one quarter annotation extent and one half patch pitch; "
            "binary presence covers every intersecting annotation patch"
        ),
        scoped_samples=sum(row.get("region") is not None for row in rows),
        confidence_method=(
            "coarse binary/component minimum; fine permits uniformly positive valid crops; "
            "uncalibrated"
        ),
        baseline=baseline,
        final=final,
        validation_grounding=validation,
    )
    save_grounding_head(head, Path(output), audit)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--cpu-threads", type=int, default=4)
    args = parser.parse_args()
    import torch

    torch.set_num_threads(args.cpu_threads)
    report = train(
        args.manifest,
        args.output,
        epochs=args.epochs,
        hidden_size=args.hidden_size,
        learning_rate=args.learning_rate,
        seed=args.seed,
        device=args.device,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
