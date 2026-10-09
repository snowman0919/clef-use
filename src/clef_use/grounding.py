"""Frozen SigLIP spatial readout with optional trained dense localization.

The default readout is zero-shot semantic patch localization. Optional dense
weights require an audited trained checkpoint, never a random served head.
Confidence combines connected spatial support with a class-balanced binary
target score. Neither is a calibrated probability of target correctness. The independent
screen verifier must establish actionability before any input is sent.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from PIL import Image

if TYPE_CHECKING:
    from .schema import BoundingBox


class GroundingQueryTooLong(ValueError):
    """The complete target query exceeds a backbone's text context."""


class GroundingStrategyUnsupported(ValueError):
    """The loaded head has no training provenance for the requested coarse input."""


class GroundingHeadProvenanceError(ValueError):
    """Configured dense weights do not belong to the required audited head format."""


SIGLIP_MODEL = "google/siglip2-base-patch16-512"
SIGLIP_REVISION = "a89f5c5093f902bf39d3cd4d81d2c09867f0724b"


def image_region_bounds(image_size, region=None):
    """Map a normalized region to original pixels without an application dependency."""
    width, height = image_size
    if region is None:
        return 0, 0, width, height
    values = tuple(getattr(region, name) for name in ("x1", "y1", "x2", "y2"))
    if any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        for v in values
    ):
        raise ValueError("region requires finite normalized coordinates")
    x1, y1, x2, y2 = values
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        raise ValueError("region must be a positive normalized rectangle")
    return (
        math.floor(x1 * width),
        math.floor(y1 * height),
        math.ceil(x2 * width),
        math.ceil(y2 * height),
    )


class VisionBackbone(Protocol):
    image_size: int

    def encode_image(self, image: Image.Image) -> Any:
        """Return a rows x columns x embedding spatial feature grid."""


class TextEncoder(Protocol):
    def encode_query(self, query: str) -> Any:
        """Return the shared-space text embedding."""


class GroundingHead(Protocol):
    def predict(self, features: Any, text: Any) -> SpatialPrediction:
        """Return spatial scores, optional subpatch offsets and target presence."""


@dataclass(frozen=True)
class SpatialPrediction:
    """Spatial logits, offsets in patch fractions, and uncalibrated binary scores."""

    scores: Any
    offsets: Any = None
    target_probabilities: Any = None


@dataclass(frozen=True)
class GroundingResult:
    """Pixel coordinates and sparse fine-grid (x, y, probability) mass."""

    point: tuple[float, float]
    confidence: float
    entropy: float
    coarse_roi: tuple[int, int, int, int]
    fine_target: tuple[float, float]
    heatmap: Any = None
    target_region: tuple[float, float, float, float] | None = None


def _normalize(vector):
    values = tuple(float(value) for value in vector)
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError("embeddings must be nonempty and finite")
    norm = math.sqrt(sum(value * value for value in values))
    if not math.isfinite(norm) or norm <= 0:
        raise ValueError("embedding norm must be finite and positive")
    return tuple(value / norm for value in values)


class NormalizedDotProductHead:
    """Dependency-free reference readout for injected shared-space encoders."""

    def predict(self, features, text):
        text = _normalize(text)
        result = []
        for row in features:
            scores = []
            for token in row:
                token = _normalize(token)
                if len(token) != len(text):
                    raise ValueError("vision and text embedding dimensions differ")
                scores.append(sum(a * b for a, b in zip(token, text, strict=True)))
            result.append(scores)
        return SpatialPrediction(result)


class DenseGroundingHead:
    """Trainable local presence and subpatch position on frozen shared features."""

    def __init__(self, dimension, *, hidden_size=64, seed=0, device="cpu"):
        import torch

        if not isinstance(dimension, int) or dimension < 1:
            raise ValueError("embedding dimension must be positive")
        if not isinstance(hidden_size, int) or not 1 <= hidden_size <= 64:
            raise ValueError("hidden size must be between 1 and 64")
        if not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        self.torch, self.dimension, self.hidden_size = torch, dimension, hidden_size
        self.seed = seed
        self.coarse_strategies = frozenset({"tiled"})
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            self.network = torch.nn.ModuleDict(
                {
                    "image": torch.nn.Linear(dimension, hidden_size),
                    "text": torch.nn.Linear(dimension, hidden_size),
                    "fusion": torch.nn.Sequential(
                        torch.nn.Linear(hidden_size, hidden_size),
                        torch.nn.SiLU(),
                        torch.nn.Linear(hidden_size, 3),
                    ),
                }
            ).to(device)
        self.training_steps = self.positive_steps = self.negative_steps = 0
        self._initial_digest = self._weight_digest()

    def parameters(self):
        return self.network.parameters()

    def state_dict(self):
        return {
            name: value.detach().cpu().contiguous().clone()
            for name, value in self.network.state_dict().items()
        }

    def _weight_digest(self):
        digest = hashlib.sha256()
        for name, value in self.state_dict().items():
            digest.update(name.encode("ascii"))
            digest.update(bytes(value.view(self.torch.uint8).flatten().tolist()))
        return digest.hexdigest()

    def forward(self, tokens, text):
        torch = self.torch
        tokens, text = tokens.detach().float(), text.detach().float()
        if (
            tokens.ndim != 2
            or tokens.shape[0] < 1
            or tokens.shape[-1] != self.dimension
            or text.shape != (self.dimension,)
            or not torch.isfinite(tokens).all()
            or not torch.isfinite(text).all()
        ):
            raise ValueError(
                "spatial and query embeddings must have expected dimensions and be finite"
            )
        image = self.network["image"](torch.nn.functional.normalize(tokens, dim=-1))
        query = self.network["text"](torch.nn.functional.normalize(text, dim=-1))
        output = self.network["fusion"](image * query)
        return output[:, 0], 0.5 * output[:, 1:].tanh()

    def predict(self, features, text):
        rows, columns, dimension = features.shape
        with self.torch.inference_mode():
            logits, offsets = self.forward(features.reshape(-1, dimension), text)
            return SpatialPrediction(
                logits.reshape(rows, columns).cpu().tolist(),
                offsets.reshape(rows, columns, 2).cpu().tolist(),
                logits.sigmoid().reshape(rows, columns).cpu().tolist(),
            )

    def loss(self, tokens, text, target_weights, target_offsets=None):
        torch = self.torch
        logits, offsets = self.forward(tokens, text)
        target = torch.as_tensor(target_weights, dtype=logits.dtype, device=logits.device).detach()
        if (
            target.shape != logits.shape
            or not torch.isfinite(target).all()
            or ((target < 0) | (target > 1)).any()
        ):
            raise ValueError("target weights must contain one finite zero-to-one value per patch")
        positives = target.bool()
        if not positives.any():
            if target_offsets is not None:
                raise ValueError("absent targets cannot have offsets")
            return torch.nn.functional.softplus(logits).mean() + offsets.sum() * 0
        if target_offsets is None:
            raise ValueError("positive targets require subpatch offsets")
        desired = torch.as_tensor(
            target_offsets, dtype=offsets.dtype, device=offsets.device
        ).detach()
        if (
            desired.shape != offsets.shape
            or not torch.isfinite(desired).all()
            or (desired.abs() > 0.5).any()
        ):
            raise ValueError("target offsets must be finite Nx2 fractions within half a patch")
        negatives = ~positives
        positive_loss = torch.nn.functional.softplus(-logits[positives]).mean()
        binary = positive_loss
        if negatives.any():
            binary = 0.5 * (positive_loss + torch.nn.functional.softplus(logits[negatives]).mean())
        density = target[positives] / target[positives].sum()
        location = -(density * torch.log_softmax(logits, dim=0)[positives]).sum()
        position = torch.nn.functional.smooth_l1_loss(offsets[positives], desired[positives])
        return location + binary + position

    def record_training_sample(self, present):
        self.training_steps += 1
        if present:
            self.positive_steps += 1
        else:
            self.negative_steps += 1


def _validate_training_audit(audit):
    def valid_hash(value):
        return (
            isinstance(value, str)
            and len(value) == 64
            and all(c in "0123456789abcdef" for c in value)
        )

    if not isinstance(audit, dict) or not valid_hash(audit.get("manifest_sha256")):
        raise ValueError("training manifest hash is missing or invalid")
    if not isinstance(audit.get("seed"), int):
        raise ValueError("training seed is missing")
    train, validation = audit.get("train_image_sha256"), audit.get("validation_image_sha256")
    if (
        not isinstance(train, list)
        or not train
        or not isinstance(validation, list)
        or not validation
        or not all(valid_hash(value) for value in train + validation)
    ):
        raise ValueError("training and validation split hashes are required")
    if set(train) & set(validation):
        raise ValueError("identical images cannot occur in both splits")
    counts = audit.get("split_counts", {})
    if any(
        not isinstance(counts.get(split), dict)
        or any(
            not isinstance(counts[split].get(label), int) or counts[split][label] <= 0
            for label in ("positive", "negative")
        )
        for split in ("train", "validation")
    ):
        raise ValueError("both splits require positive and negative annotations")
    strategies = audit.get("coarse_strategy_counts")
    if (
        not isinstance(strategies, dict)
        or not strategies
        or not set(strategies).issubset({"tiled", "overview"})
    ):
        raise ValueError("trained coarse strategies must be declared")
    for strategy_counts in strategies.values():
        if not isinstance(strategy_counts, dict) or any(
            not isinstance(strategy_counts.get(split), dict)
            or any(
                not isinstance(strategy_counts[split].get(label), int)
                or strategy_counts[split][label] <= 0
                for label in ("positive", "negative")
            )
            for split in ("train", "validation")
        ):
            raise ValueError(
                "each coarse strategy requires independent positive and negative splits"
            )
    if any(
        sum(values[split][label] for values in strategies.values()) != counts[split][label]
        for split in ("train", "validation")
        for label in ("positive", "negative")
    ):
        raise ValueError("coarse strategy counts do not match annotated split counts")


def save_grounding_head(head, path, audit):
    """Save trained dense weights only; never pickle or untrained served weights."""
    from safetensors.torch import save_file

    _validate_training_audit(audit)
    if (
        head.positive_steps <= 0
        or head.negative_steps <= 0
        or head.training_steps != head.positive_steps + head.negative_steps
        or head._weight_digest() == head._initial_digest
    ):
        raise ValueError("a trained head with positive and negative supervision is required")
    if audit["seed"] != head.seed:
        raise ValueError("training seed does not match head initialization")
    if head.coarse_strategies != frozenset(audit["coarse_strategy_counts"]):
        raise ValueError("head coarse strategies do not match training provenance")
    if not all(head.torch.isfinite(p).all() for p in head.parameters()):
        raise ValueError("head weights must be finite")
    metadata = {
        "format": "clef-use-grounding-head-v3",
        "backbone_model": SIGLIP_MODEL,
        "backbone_revision": SIGLIP_REVISION,
        "dimension": str(head.dimension),
        "hidden_size": str(head.hidden_size),
        "temperature": "1",
        "trained_steps": str(head.training_steps),
        "positive_steps": str(head.positive_steps),
        "negative_steps": str(head.negative_steps),
        "training_manifest": json.dumps(audit, sort_keys=True),
    }
    save_file(head.state_dict(), str(path), metadata=metadata)


def load_grounding_head(path, *, dimension, device="cpu"):
    """Fail closed on old formats, mismatched provenance, shape, or numerics."""
    from safetensors import safe_open

    with safe_open(str(path), framework="pt", device="cpu") as checkpoint:
        metadata = checkpoint.metadata() or {}
        if (
            metadata.get("format") != "clef-use-grounding-head-v3"
            or metadata.get("backbone_model") != SIGLIP_MODEL
            or metadata.get("backbone_revision") != SIGLIP_REVISION
            or metadata.get("temperature") != "1"
        ):
            raise GroundingHeadProvenanceError(
                "grounding head provenance does not match the pinned dense model"
            )
        try:
            stored_dimension = int(metadata["dimension"])
            hidden_size = int(metadata["hidden_size"])
            steps = int(metadata["trained_steps"])
            positive = int(metadata["positive_steps"])
            negative = int(metadata["negative_steps"])
            audit = json.loads(metadata["training_manifest"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("grounding head training metadata is invalid") from exc
        _validate_training_audit(audit)
        if (
            stored_dimension != dimension
            or positive <= 0
            or negative <= 0
            or steps != positive + negative
        ):
            raise ValueError("trained head dimension or training steps are invalid")
        head = DenseGroundingHead(
            dimension, hidden_size=hidden_size, seed=audit["seed"], device=device
        )
        expected = head.network.state_dict()
        if set(checkpoint.keys()) != set(expected):
            raise ValueError("grounding head checkpoint has unexpected tensor keys")
        values = {}
        for name, tensor in expected.items():
            if tuple(checkpoint.get_slice(name).get_shape()) != tuple(tensor.shape):
                raise ValueError("grounding head tensor shape does not match its metadata")
            value = checkpoint.get_tensor(name)
            if value.dtype != head.torch.float32 or not head.torch.isfinite(value).all():
                raise ValueError("grounding head weights must be finite float32 tensors")
            values[name] = value.to(device)
        head.network.load_state_dict(values)
        if head._weight_digest() == head._initial_digest:
            raise ValueError("grounding head contains untrained random weights")
        head.training_steps, head.positive_steps, head.negative_steps = steps, positive, negative
        head.coarse_strategies = frozenset(audit["coarse_strategy_counts"])
        head.network.eval().requires_grad_(False)
        return head


@dataclass(frozen=True)
class _Sample:
    x: float
    y: float
    score: float
    pitch: float
    pitch_x: float
    pitch_y: float
    center_x: float
    center_y: float
    footprint: tuple[float, float, float, float]
    presence: float | None = None


class Grounder:
    """Overlapping native tiles followed by a magnified, aspect-preserved ROI.

    Input regions are normalized screenshot bounds. Output points and ROI bounds
    always use original screenshot pixels; right/bottom ROI bounds are exclusive.
    Each tile is letterboxed before encoding, and pure padding is discarded.
    Refinement narrows the fine crop, never stretches the source image to a square.
    """

    def __init__(
        self,
        backbone: VisionBackbone,
        text_encoder: TextEncoder,
        head: GroundingHead,
        *,
        temperature: float = 0.05,
        presence_threshold: float = 0.9,
    ):
        if not math.isfinite(temperature) or temperature <= 0:
            raise ValueError("temperature must be finite and positive")
        if not isinstance(backbone.image_size, int) or backbone.image_size < 4:
            raise ValueError("backbone image_size must be an integer >= 4")
        if not math.isfinite(presence_threshold) or not 0.5 <= presence_threshold <= 1:
            raise ValueError("presence threshold must be finite within 0.5 and 1")
        self.backbone = backbone
        self.text_encoder = text_encoder
        self.head = head
        self.temperature = temperature
        self.presence_threshold = presence_threshold

    @staticmethod
    def _starts(start, end, size):
        if end - start <= size:
            return [start]
        stride = max(1, size * 3 // 4)
        starts = list(range(start, end - size + 1, stride))
        if starts[-1] != end - size:
            starts.append(end - size)
        return starts

    def _samples(self, image, box, text):
        left, top, right, bottom = box
        crop = image.crop(box).convert("RGB")
        size = self.backbone.image_size
        scale = min(size / crop.width, size / crop.height)
        width = max(1, min(size, round(crop.width * scale)))
        height = max(1, min(size, round(crop.height * scale)))
        pad_x, pad_y = (size - width) // 2, (size - height) // 2
        canvas = Image.new("RGB", (size, size), (127, 127, 127))
        canvas.paste(crop.resize((width, height), Image.Resampling.BILINEAR), (pad_x, pad_y))
        prediction = self.head.predict(self.backbone.encode_image(canvas), text)
        scores = prediction.scores
        rows = len(scores)
        columns = len(scores[0]) if rows else 0
        if not rows or not columns or any(len(row) != columns for row in scores):
            raise ValueError("heatmap must be a nonempty rectangular grid")
        samples = []
        pitch_x, pitch_y = size / columns * crop.width / width, size / rows * crop.height / height
        pitch = max(pitch_x, pitch_y)
        for grid in (prediction.offsets, prediction.target_probabilities):
            if grid is not None and (len(grid) != rows or any(len(row) != columns for row in grid)):
                raise ValueError("prediction grids must match the spatial score grid")
        for row_index, row in enumerate(scores):
            for col_index, raw_score in enumerate(row):
                score = float(raw_score)
                if not math.isfinite(score):
                    raise ValueError("heatmap scores must be finite")
                model_x = (col_index + 0.5) * size / columns
                model_y = (row_index + 0.5) * size / rows
                half_x, half_y = size / columns / 2, size / rows / 2
                if (
                    model_x + half_x <= pad_x
                    or model_x - half_x >= pad_x + width
                    or model_y + half_y <= pad_y
                    or model_y - half_y >= pad_y + height
                ):
                    continue
                center_x = left + (model_x - pad_x) * crop.width / width
                center_y = top + (model_y - pad_y) * crop.height / height
                footprint = (
                    max(left, center_x - pitch_x / 2),
                    max(top, center_y - pitch_y / 2),
                    min(right, center_x + pitch_x / 2),
                    min(bottom, center_y + pitch_y / 2),
                )
                if prediction.offsets is not None:
                    offset = prediction.offsets[row_index][col_index]
                    if len(offset) != 2 or any(
                        not math.isfinite(float(v)) or abs(float(v)) > 0.5 for v in offset
                    ):
                        raise ValueError("spatial offsets must be finite within half a patch")
                    model_x += float(offset[0]) * size / columns
                    model_y += float(offset[1]) * size / rows
                presence = (
                    None
                    if prediction.target_probabilities is None
                    else float(prediction.target_probabilities[row_index][col_index])
                )
                if presence is not None and (not math.isfinite(presence) or not 0 <= presence <= 1):
                    raise ValueError("target probabilities must be finite within zero and one")
                model_x = min(max(model_x, pad_x), math.nextafter(pad_x + width, -math.inf))
                model_y = min(max(model_y, pad_y), math.nextafter(pad_y + height, -math.inf))
                # Separate rounded resize axes preserve the exact inverse transform.
                x = min(
                    left + (model_x - pad_x) * crop.width / width,
                    math.nextafter(float(right), -math.inf),
                )
                y = min(
                    top + (model_y - pad_y) * crop.height / height,
                    math.nextafter(float(bottom), -math.inf),
                )
                samples.append(
                    _Sample(
                        x,
                        y,
                        score,
                        pitch,
                        pitch_x,
                        pitch_y,
                        center_x,
                        center_y,
                        footprint,
                        presence,
                    )
                )
        if not samples:
            raise ValueError("region contains no valid spatial patch centers")
        return samples

    def _probabilities(self, samples):
        peak = max(sample.score for sample in samples)
        weights = [math.exp((sample.score - peak) / self.temperature) for sample in samples]
        total = sum(weights)
        return [weight / total for weight in weights]

    def _support(self, samples, peak):
        for index, sample in enumerate(samples):
            if (
                sample.presence >= 0.5
                if peak.presence is not None
                else sample.score >= peak.score - self.temperature
            ):
                yield index

    def _line_confidence(self, samples, probabilities, peak):
        """Aggregate a declared horizontal target without merging parallel targets."""
        pitch_y = min(sample.pitch_y for sample in samples)
        active = list(self._support(samples, peak))
        # One physical edge can activate adjacent rows through patch coverage.
        selected = {index for index in active if abs(samples[index].y - peak.y) <= pitch_y}
        members = [samples[index] for index in selected]
        if not members:
            return 0.0, None
        if max(sample.x for sample in members) - min(sample.x for sample in members) < (
            2 * min(sample.pitch_x for sample in samples)
        ):
            return 0.0, None
        mass = sum(probabilities[index] for index in selected)
        remaining = sorted(
            (samples[index].y, probabilities[index]) for index in active if index not in selected
        )
        start, current, competitor = 0, 0.0, 0.0
        for y, probability in remaining:
            current += probability
            while y - remaining[start][0] > 2 * pitch_y:
                current -= remaining[start][1]
                start += 1
            competitor = max(competitor, current)
        region = (
            min(sample.x - sample.pitch_x / 2 for sample in members),
            min(sample.y - sample.pitch_y / 2 for sample in members),
            max(sample.x + sample.pitch_x / 2 for sample in members),
            max(sample.y + sample.pitch_y / 2 for sample in members),
        )
        denominator = mass + competitor if peak.presence is not None else 1
        return min(1.0, max(0.0, (mass - competitor) / denominator)), region

    def _component_confidence(self, samples, probabilities, peak, geometry="point"):
        # One temperature is one natural-log unit of relative spatial evidence.
        # If the entire observed domain lies inside this band, no distinct target
        # region has been established (including uniform and low-contrast maps).
        if peak.score - min(sample.score for sample in samples) <= self.temperature:
            return 0.0, None
        if geometry == "horizontal_line":
            return self._line_confidence(samples, probabilities, peak)
        pitch = min(sample.pitch for sample in samples)
        origin_x = min(sample.center_x for sample in samples)
        origin_y = min(sample.center_y for sample in samples)
        keys = [
            (
                round((sample.center_x - origin_x) / pitch),
                round((sample.center_y - origin_y) / pitch),
            )
            for sample in samples
        ]
        active = {}
        for index in self._support(samples, peak):
            active.setdefault(keys[index], []).append(index)
        peak_key = keys[samples.index(peak)]
        if peak_key not in active:
            return 0.0, None
        components = []
        while active:
            start = next(iter(active))
            stack, members, contains_peak = [start], [], False
            while stack:
                key = stack.pop()
                indices = active.pop(key, None)
                if indices is None:
                    continue
                members.extend(indices)
                contains_peak = contains_peak or key == peak_key
                x, y = key
                stack.extend(
                    (x + dx, y + dy)
                    for dx in (-1, 0, 1)
                    for dy in (-1, 0, 1)
                    if (dx or dy) and (x + dx, y + dy) in active
                )
            mass = sum(probabilities[index] for index in members)
            components.append((contains_peak, mass, members))
        primary = next(component for component in components if component[0])
        competitor = max((mass for contains, mass, _ in components if not contains), default=0.0)
        denominator = primary[1] + competitor if peak.presence is not None else 1
        confidence = min(1.0, max(0.0, (primary[1] - competitor) / denominator))
        members = [samples[index] for index in primary[2]]
        region = (
            min(sample.x - sample.pitch / 2 for sample in members),
            min(sample.y - sample.pitch / 2 for sample in members),
            max(sample.x + sample.pitch / 2 for sample in members),
            max(sample.y + sample.pitch / 2 for sample in members),
        )
        return confidence, region

    def _summarize(self, samples, probabilities=None, geometry="point"):
        peak = max(samples, key=lambda sample: sample.score)
        if probabilities is None:
            probabilities = self._probabilities(samples)
        entropy = (
            (-sum(p * math.log(p) for p in probabilities if p > 0) / math.log(len(samples)))
            if len(samples) > 1
            else 1.0
        )
        confidence, region = self._component_confidence(samples, probabilities, peak, geometry)
        if peak.presence is not None:
            confidence = (
                min(confidence, peak.presence) if peak.presence >= self.presence_threshold else 0.0
            )
        return peak, min(1.0, max(0.0, entropy)), confidence, region

    def ground(
        self,
        image: Image.Image,
        query: str,
        region: BoundingBox | None = None,
        refinement: int = 0,
        geometry: str = "point",
        coarse_strategy: str = "tiled",
    ) -> GroundingResult:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must contain nonempty text")
        if not isinstance(geometry, str) or geometry not in {"point", "horizontal_line"}:
            raise ValueError("unsupported visual target geometry")
        if not isinstance(coarse_strategy, str) or coarse_strategy not in {"tiled", "overview"}:
            raise ValueError("unsupported coarse grounding strategy")
        dense_head = getattr(self.head, "dense_head", None)
        if dense_head is not None and coarse_strategy not in dense_head.coarse_strategies:
            raise GroundingStrategyUnsupported("coarse strategy was not supervised by this head")
        if (
            isinstance(refinement, bool)
            or not isinstance(refinement, int)
            or not 0 <= refinement <= 4
        ):
            raise ValueError("refinement must be an integer between 0 and 4")
        if image.width <= 0 or image.height <= 0:
            raise ValueError("image must have positive dimensions")
        bounds = image_region_bounds(image.size, region)
        left, top, right, bottom = bounds
        size = self.backbone.image_size
        text = self.text_encoder.encode_query(query.strip())
        samples = []
        boxes = (
            [bounds]
            if coarse_strategy == "overview"
            else [
                (x, y, min(x + size, right), min(y + size, bottom))
                for y in self._starts(top, bottom, size)
                for x in self._starts(left, right, size)
            ]
        )
        for box in boxes:
            samples.extend(self._samples(image, box, text))
        # Fuse overlapping tile predictions onto a native patch lattice. Repeated
        # observations must not multiply entropy merely because a tile overlaps.
        if coarse_strategy == "tiled":
            pitch = min(sample.pitch for sample in samples)
            fused = {}
            for sample in samples:
                key = (int((sample.center_x - left) / pitch), int((sample.center_y - top) / pitch))
                previous = fused.get(key)
                if previous is None or sample.score > previous.score:
                    fused[key] = sample
            samples = list(fused.values())
        coarse, coarse_entropy, coarse_confidence, _ = self._summarize(samples, geometry=geometry)
        radius = max(2, size / (4 * 2**refinement))
        roi = (
            max(left, math.floor(coarse.x - radius)),
            max(top, math.floor(coarse.y - radius)),
            min(right, math.ceil(coarse.x + radius)),
            min(bottom, math.ceil(coarse.y + radius)),
        )
        fine_samples = self._samples(image, roi, text)
        fine_probabilities = self._probabilities(fine_samples)
        fine, fine_entropy, fine_confidence, target_region = self._summarize(
            fine_samples, fine_probabilities, geometry
        )
        if fine.presence is not None:
            # A supervised fine crop may lie wholly inside the target. Its
            # weakest valid binary score supports that case; negative gaps still
            # require the component margin. The coarse gate remains strict.
            minimum_presence = min(sample.presence for sample in fine_samples)
            if minimum_presence >= self.presence_threshold:
                fine_confidence = max(fine_confidence, minimum_presence)
        if target_region is not None:
            x1, y1, x2, y2 = target_region
            target_region = (max(roi[0], x1), max(roi[1], y1), min(roi[2], x2), min(roi[3], y2))
        point = (fine.x, fine.y)
        return GroundingResult(
            point,
            min(coarse_confidence, fine_confidence),
            max(coarse_entropy, fine_entropy),
            roi,
            point,
            [
                (s.x, s.y, probability)
                for s, probability in zip(fine_samples, fine_probabilities, strict=True)
            ],
            target_region,
        )


class _SiglipVisionBackbone:
    def __init__(self, model, processor, torch):
        self.model, self.processor, self.torch = model, processor, torch
        self.image_size = int(model.config.vision_config.image_size)
        # Repeated label queries/refinements reuse the same frozen native tiles.
        # Sixteen 512px SigLIP grids occupy about 48 MiB in float32.
        self._features = OrderedDict()

    def encode_image(self, image):
        key = (image.size, image.mode, hashlib.sha256(image.tobytes()).digest())
        cached = self._features.get(key)
        if cached is not None:
            self._features.move_to_end(key)
            return cached
        inputs = self.processor.image_processor(images=image, do_resize=False, return_tensors="pt")
        pixels = inputs["pixel_values"].to(self.model.device)
        with self.torch.inference_mode():
            output = self.model.vision_model(pixel_values=pixels)
        tokens = output.last_hidden_state[0]
        side = self.image_size // self.model.config.vision_config.patch_size
        if tokens.shape[0] != side * side:
            raise ValueError("SigLIP spatial token count does not match its patch grid")
        features = tokens.reshape(side, side, -1)
        self._features[key] = features
        if len(self._features) > 16:
            self._features.popitem(last=False)
        return features


class _SiglipTextEncoder:
    def __init__(self, model, processor, torch):
        self.model, self.processor, self.torch = model, processor, torch

    def encode_query(self, query):
        limit = self.model.config.text_config.max_position_embeddings
        inputs = self.processor(
            text=[query.lower()],
            padding="max_length",
            max_length=limit,
            truncation=False,
            return_tensors="pt",
        )
        if inputs["input_ids"].shape[-1] > limit:
            raise GroundingQueryTooLong(f"visual query exceeds the {limit}-token text context")
        inputs = inputs.to(self.model.device)
        with self.torch.inference_mode():
            # The pretrained text projection is part of text_model's pooler output.
            return self.model.text_model(**inputs).pooler_output[0]


class _SiglipGroundingHead:
    def __init__(self, model, torch, dense_head=None):
        self.pooler = model.vision_model.head
        self.torch = torch
        self.dense_head = dense_head

    def embed_features(self, features):
        """Frozen pretrained spatial projection used by both training and serving."""
        with self.torch.inference_mode():
            return self.pooler(features.reshape(-1, 1, features.shape[-1]))

    def predict(self, features, text):
        torch = self.torch
        with torch.inference_mode():
            rows, columns, _ = features.shape
            # Exact pretrained attention-pool output for each singleton spatial
            # token. The learned V/out projections and residual MLP are retained;
            # Q/K attention is identically one for a singleton, without new weights.
            tokens = self.embed_features(features)
            if (
                not torch.isfinite(tokens).all()
                or not torch.isfinite(text).all()
                or (tokens.norm(dim=-1) <= 0).any()
                or text.norm() <= 0
            ):
                raise ValueError("SigLIP embeddings must be finite with positive norm")
            tokens = torch.nn.functional.normalize(tokens.float(), dim=-1)
            if self.dense_head is not None:
                return self.dense_head.predict(tokens.reshape(rows, columns, -1), text)
            text = torch.nn.functional.normalize(text.float(), dim=-1)
            return SpatialPrediction((tokens @ text).reshape(rows, columns).cpu().tolist())


class SiglipGrounder(Grounder):
    """Load the real frozen pretrained FixRes checkpoint in the ML environment.

    Imports torch/transformers only on construction. Loading errors propagate;
    unavailable weights never produce a random model or a synthetic prediction.
    """

    def __init__(
        self,
        model: str = SIGLIP_MODEL,
        revision: str = SIGLIP_REVISION,
        device: str = "cpu",
        head_path: Path | None = None,
        presence_threshold: float = 0.9,
    ):
        import torch
        from transformers import AutoModel, AutoProcessor

        cache = Path.home() / ".cache/clef-use/models/huggingface/hub"
        processor = AutoProcessor.from_pretrained(
            model, revision=revision, cache_dir=cache, trust_remote_code=False
        )
        pretrained, loading = AutoModel.from_pretrained(
            model,
            revision=revision,
            cache_dir=cache,
            trust_remote_code=False,
            output_loading_info=True,
        )
        if loading.get("missing_keys") or loading.get("mismatched_keys"):
            raise ValueError("SigLIP checkpoint is missing pretrained weights")
        pretrained.eval().requires_grad_(False).to(device)
        if pretrained.config.model_type != "siglip":
            raise ValueError("grounding requires the fixed-resolution SigLIP architecture")
        self.model = pretrained
        dense_head = None
        if head_path is not None:
            if revision != SIGLIP_REVISION:
                raise ValueError("trained head requires the pinned backbone revision")
            dense_head = load_grounding_head(
                head_path, dimension=pretrained.config.vision_config.hidden_size, device=device
            )
        super().__init__(
            _SiglipVisionBackbone(pretrained, processor, torch),
            _SiglipTextEncoder(pretrained, processor, torch),
            _SiglipGroundingHead(pretrained, torch, dense_head),
            temperature=1.0 if dense_head else 0.05,
            presence_threshold=presence_threshold,
        )
