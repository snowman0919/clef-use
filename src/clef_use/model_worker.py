"""Resident ML worker; separate environments keep upstream dependency versions isolated."""

from __future__ import annotations

import base64
import contextlib
import gc
import hashlib
import io
import json
import os
import struct
import sys
import time
import traceback
from collections import OrderedDict
from pathlib import Path

from deployment_profiles import resolve_profile, select_backend, torch_device
from head_trace import capture_head_inputs
from models import MODEL_REVISIONS
from PIL import Image


def choose_device(torch, requested):
    return torch_device(select_backend(torch, requested))


def model_path(config, repo, revision):
    return (
        Path(config["model_dir"])
        / "huggingface/hub"
        / ("models--" + repo.replace("/", "--"))
        / "snapshots"
        / revision
    )


class VisualWorker:
    def __init__(self, config):
        from grounding import SiglipGrounder

        self.device = config["visual_device"]
        self.backend = self.device
        path = (
            Path(config["model_dir"])
            / "huggingface/hub"
            / ("models--" + config["visual_model"].replace("/", "--"))
            / "snapshots"
            / config["visual_revision"]
        )
        self.grounder = SiglipGrounder(
            str(path),
            revision=config["visual_revision"],
            device=self.device,
            head_path=config.get("visual_head"),
            presence_threshold=config.get("visual_presence_threshold", 0.9),
        )
        dense_head = self.grounder.head.dense_head
        self.coarse_strategies = sorted(
            dense_head.coarse_strategies if dense_head is not None else {"tiled", "overview"}
        )

    def request(self, payload):
        from dataclasses import asdict
        from types import SimpleNamespace

        image = Image.open(io.BytesIO(base64.b64decode(payload["image"]))).convert("RGB")
        region = SimpleNamespace(**payload["region"]) if payload.get("region") else None
        result = asdict(
            self.grounder.ground(
                image,
                payload["query"],
                region=region,
                refinement=payload.get("refinement", 0),
                geometry=payload.get("geometry", "point"),
                coarse_strategy=payload.get("coarse_strategy", "tiled"),
            )
        )
        result.pop("heatmap", None)
        return {"grounding": result}


class CpuEmbeddingRows:
    def __init__(self, weight, device, dtype=None):
        self.weight = weight
        self.device = device
        self.dtype = dtype

    def __getitem__(self, indices):
        return self.weight[indices.cpu()].to(self.device, dtype=self.dtype)


def offload_output_embeddings(model, *, path=None, dtype=None):
    """Pinned immutable CLEF joint-head rows; not HF generation or embedding mutation."""
    import torch

    embedding = model.language_model.get_output_embeddings()
    weight = embedding.weight
    if bool(getattr(weight, "is_meta", False)):
        # Quantizers skip this never-executed module. Keep its lexical rows as
        # a lazy checkpoint slice rather than materializing the whole table.
        from safetensors import safe_open

        if path is None:
            raise RuntimeError("meta lm_head requires the checkpoint path to materialize")
        index = json.loads((Path(path) / "model.safetensors.index.json").read_text())
        shard = Path(path) / index["weight_map"]["lm_head.weight"]
        with safe_open(str(shard), framework="pt") as handle:
            weight = handle.get_slice("lm_head.weight")
        # Meta placement alone retains the full CPU table in Accelerate's
        # offload hook. Replace this never-executed output projection through
        # the public setter, preserving its metadata and the real lazy rows.
        model.language_model.set_output_embeddings(
            torch.nn.Linear(
                embedding.weight.shape[1],
                embedding.weight.shape[0],
                bias=getattr(embedding, "bias", None) is not None,
                device="meta",
                dtype=embedding.weight.dtype,
            )
        )
    elif str(weight.device) != "cpu":
        embedding.weight = torch.nn.Parameter(weight.detach().cpu(), requires_grad=False)
        weight = embedding.weight

    def select_rows(_module, arguments):
        # The pinned joint head reads lexical rows directly; lm_head is never executed.
        return (
            *arguments[:-1],
            CpuEmbeddingRows(weight, arguments[0].device, dtype),
        )

    model.head.register_forward_pre_hook(select_rows)


def load_cuda_nf4_model(path, *, device="cuda", dtype, **kwargs):
    """Compose the pinned release before moving its joint head onto a tight GPU."""
    import torch
    from joint_schema_model import ClefModel, JointSchemaHead
    from safetensors.torch import load_file
    from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration

    # Scope CUDA to the model subtree: Accelerate's recursive root placement
    # would temporarily migrate the CPU lm_head before its offload hook exists.
    # lm_head is never executed; the lexical-row helper below serves the joint
    # head from its checkpoint without a full-vocabulary CUDA allocation.
    backbone = Qwen3_5ForConditionalGeneration.from_pretrained(
        path, dtype=dtype, device_map={"model": str(device), "lm_head": "cpu"}, **kwargs
    )
    backbone.config.use_cache = False
    head = JointSchemaHead(**json.loads((path / "joint_head_config.json").read_text()))
    head.load_state_dict(load_file(path / "joint_head.safetensors"), strict=True)
    model = ClefModel(backbone, head)
    offload_output_embeddings(model, path=path, dtype=dtype)
    # Forward wrappers form cycles; release their unused CPU table before
    # inference and before another resident worker needs transient host memory.
    gc.collect()
    torch.cuda.empty_cache()
    head.to(device=device, dtype=dtype)
    return model.eval(), AutoProcessor.from_pretrained(path, local_files_only=True)


class ClefWorker:
    def __init__(self, config):
        import torch

        requested = config["device"]
        if config.get("ml_profile", "auto") not in {"auto", "default"}:
            requested = resolve_profile(config["ml_profile"], requested).backend
        self.backend = select_backend(torch, requested)
        self.device = torch_device(self.backend)
        revision = MODEL_REVISIONS[config["decision_model"]]
        self.decision_model = config["decision_model"]
        self.model_revision = revision
        path = model_path(config, config["decision_model"], revision)
        sys.path.insert(0, str(path))
        from joint_schema_model import encode_record, load_release_model, systemone

        self.systemone = systemone
        self.encode_record = encode_record
        quantization = config.get("quantization", "none")
        if quantization == "4bit" and self.backend == "mps":
            raise RuntimeError("NF4 is not enabled for the MPS profile")
        dtype = (
            getattr(torch, config.get("cpu_compute_dtype", "float32"))
            if self.device == "cpu"
            else torch.float16
            if self.device == "mps" or torch.version.hip or quantization == "4bit"
            else torch.bfloat16
            if (torch.xpu if self.backend == "xpu" else torch.cuda).is_bf16_supported()
            else torch.float16
        )
        kwargs = {}
        if quantization == "4bit":
            from transformers import BitsAndBytesConfig

            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=dtype,
                # lm_head is never executed (joint head gathers rows), so it
                # must stay out of quantizers; a split device_map leaves the
                # skipped CPU module as a meta tensor. The row hook reads only
                # selected checkpoint rows and casts them to compute dtype.
                llm_int8_skip_modules=["lm_head", "model.visual"],
                # lm_head stays fp16 and lives on the CPU in the device map; the
                # quantizer only accepts a split map when the offloaded module
                # keeps its native dtype.
                llm_int8_enable_fp32_cpu_offload=True,
            )
        loader = (
            load_cuda_nf4_model
            if quantization == "4bit" and self.backend == "cuda"
            else load_release_model
        )
        self.model, self.processor = loader(
            path,
            device=self.device,
            dtype=dtype,
            attn_implementation="sdpa" if self.backend in {"cpu", "cuda", "rocm"} else "eager",
            local_files_only=True,
            **kwargs,
        )
        self.compute_dtype = str(dtype).removeprefix("torch.")
        backbone_config = getattr(getattr(self.model, "language_model", self.model), "config", None)
        text_config = getattr(backbone_config, "text_config", backbone_config)
        self.attention_implementation = getattr(text_config, "_attn_implementation", None)
        self.quantized_modules = 0
        # Only the local operator environment can opt in; model/request fields cannot.
        self.head_trace_root = os.environ.get("CLEF_USE_HEAD_TRACE_DIR")
        self._head_trace_attempted = False
        if quantization == "4bit":
            import bitsandbytes as bnb

            names = [
                name
                for name, module in self.model.named_modules()
                if isinstance(module, bnb.nn.Linear4bit)
            ]
            if not names or any(
                ".visual." in name or "lm_head" in name or name.startswith("head.")
                for name in names
            ):
                raise RuntimeError("CLEF NF4 exclusion invariant failed")
            if not all(parameter.is_floating_point() for parameter in self.model.head.parameters()):
                raise RuntimeError("CLEF typed head must remain floating point")
            self.quantized_modules = len(names)

    def request(self, record):
        record = {**record, "model": self.decision_model}
        # The pinned release backbone's vision tower supports exactly one image;
        # a second raster fails inside its linear projection (verified on the real
        # CUDA checkpoint, 2026-10-08). Effect evidence therefore travels as a
        # bounded, quantified text summary plus a change vector -- never a crop --
        # so no evidence path may ever reintroduce an images list here.
        image = record.pop("image", None)
        record.pop("evidence_images", None)
        trace_root = getattr(self, "head_trace_root", None)
        capture_requested = bool(trace_root and not getattr(self, "_head_trace_attempted", False))
        png_sha256 = None
        if image:
            decoded = base64.b64decode(image)
            if capture_requested:
                png_sha256 = hashlib.sha256(decoded).hexdigest()
            record["images"] = [Image.open(io.BytesIO(decoded)).convert("RGB")]
            del decoded
            record["media_kwargs"] = {"min_pixels": 56 * 56, "max_pixels": 512 * 512}
        try:
            # The pinned encoder clips state to its token budget. Encode with
            # a larger bound first: <=8192 proves no clipping at the real bound;
            # >=16384 is already a refusal, not a larger inference allowance.
            encoded = self.encode_record(
                self.processor.tokenizer, record, max_length=16384, processor=self.processor
            )
            if len(encoded.input_ids) > 8192:
                raise ValueError("decision would truncate observed evidence at the token budget")
            del encoded
            if capture_requested:
                # Consume the attempt before any real inference, including failing attempts.
                self._head_trace_attempted = True
                state = record.get("state")
                reference = state.get("frame_reference") if isinstance(state, dict) else None
                metadata = {
                    "worker_pid": os.getpid(),
                    "model_revision": self.model_revision,
                    "decision_model": self.decision_model,
                    "backend": self.backend,
                    "compute_dtype": self.compute_dtype,
                    "quantized_modules": self.quantized_modules,
                    "image_png_sha256": png_sha256,
                    "frame_image_sha256": reference.get("image_sha256")
                    if isinstance(reference, dict)
                    else None,
                }
                return capture_head_inputs(
                    self.model,
                    lambda: self.systemone(self.model, self.processor, record, max_length=8192),
                    trace_root,
                    metadata,
                )
            return self.systemone(self.model, self.processor, record, max_length=8192)
        finally:
            if self.device == "mps":
                import torch

                torch.mps.empty_cache()


def load_d1_model(path, *, device, dtype):
    import transformers

    if transformers.__version__ != "5.14.1":
        raise RuntimeError(
            "d1 worker requires pinned transformers 5.14.1; prepare its own environment"
        )
    return transformers.AutoModel.from_pretrained(
        str(path),
        trust_remote_code=True,
        local_files_only=True,
        code_revision=MODEL_REVISIONS["LiquidAI/d1-3B"],
        dtype=dtype,
        device_map={"": str(device)},
        attn_implementation="sdpa",
    )


@contextlib.contextmanager
def bounded_d1_decision(model):
    """Guard actual encoded inputs without re-rendering the pinned SDK's prompt."""
    engine = model.engine
    plan, answer = engine._plan, model.answer

    def check(count):
        if count > 8192:
            raise ValueError("d1 decision record exceeds the 8192 token budget")

    def checked_plan(lengths, token_budget=None):
        # Branch-only packing otherwise permits partial execution of an oversized record.
        check(sum(lengths))
        return plan(lengths, token_budget)

    def checked_answer(trunk, packed, lengths, **vision):
        check(trunk.numel() + packed.numel())
        return answer(trunk, packed, lengths, **vision)

    def checked_forward(_module, args, kwargs):
        input_ids = kwargs.get("input_ids")
        if input_ids is None and args:
            input_ids = args[0]
        if input_ids is None:
            raise ValueError("d1 decision record has no encoded input ids")
        check(input_ids.numel())

    with contextlib.ExitStack() as cleanup:
        hook = model.register_forward_pre_hook(checked_forward, with_kwargs=True)
        cleanup.callback(hook.remove)
        for owner, name, replacement in (
            (engine, "_plan", checked_plan),
            (model, "answer", checked_answer),
        ):
            owned, original = name in vars(owner), vars(owner).get(name)
            setattr(owner, name, replacement)
            if owned:
                cleanup.callback(setattr, owner, name, original)
            else:
                cleanup.callback(delattr, owner, name)
        yield


class D1Worker:
    def __init__(self, config):
        if config["decision_model"] != "LiquidAI/d1-3B":
            raise ValueError("d1 worker only accepts LiquidAI/d1-3B")
        if config.get("quantization", "none") != "none":
            raise ValueError(
                "d1 candidate currently requires quantization none; CLEF NF4 is separate"
            )
        import torch

        requested = config["device"]
        if config.get("ml_profile", "auto") not in {"auto", "default"}:
            requested = resolve_profile(config["ml_profile"], requested).backend
        self.backend = select_backend(torch, requested)
        self.device = torch_device(self.backend)
        dtype = (
            getattr(torch, config.get("cpu_compute_dtype", "float32"))
            if self.device == "cpu"
            else torch.float16
            if self.device == "mps"
            else torch.bfloat16
            if (torch.xpu if self.backend == "xpu" else torch.cuda).is_bf16_supported()
            else torch.float16
        )
        self.decision_model = config["decision_model"]
        self.model_revision = MODEL_REVISIONS[self.decision_model]
        path = model_path(config, self.decision_model, self.model_revision)
        self.model = load_d1_model(path, device=self.device, dtype=dtype).eval()
        self.model.engine.token_budget = 8192
        self.compute_dtype = str(dtype).removeprefix("torch.")
        # d1 executes its tied lm_head. CLEF's never-executed-head offload and
        # quantizer exclusions must not be transplanted into this worker.

    def request(self, record):
        images = None
        if record.get("image"):
            image = Image.open(io.BytesIO(base64.b64decode(record["image"]))).convert("RGB")
            max_pixels = 512 * 512
            if image.width * image.height > max_pixels:
                scale = (max_pixels / (image.width * image.height)) ** 0.5
                image = image.resize(
                    (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
                    Image.Resampling.BICUBIC,
                )
            images = [image]
        # Keep the common single-frame contract even though d1 can accept more.
        # Effect evidence remains the same quantified state, not a second raster.
        try:
            with bounded_d1_decision(self.model):
                return self.model.system_one(record["state"], record["questions"], images=images)
        finally:
            if self.device == "mps":
                import torch

                torch.mps.empty_cache()


def caption_crop_coordinates(box, size):
    """Match pinned OmniParser's float32 products and NumPy slicing exactly."""

    def float32(value):
        return struct.unpack("f", struct.pack("f", value))[0]

    width, height = size
    pixels = [
        int(float32(float32(value) * (width if i % 2 == 0 else height)))
        for i, value in enumerate(box)
    ]
    xmin, xmax, _ = slice(pixels[0], pixels[2]).indices(width)
    ymin, ymax, _ = slice(pixels[1], pixels[3]).indices(height)
    return xmin, ymin, xmax, ymax


def caption_regions(image, boxes, captioner, cache, limit=256, *, telemetry=None):
    """Reuse only byte-identical icon crops within this pinned worker instance."""
    started = time.perf_counter()
    keys = []
    missing = {}
    cache_hits = 0
    duplicate_misses = 0
    for box in boxes:
        crop = image.crop(caption_crop_coordinates(box, image.size))
        key = (crop.mode, crop.size, hashlib.sha256(crop.tobytes()).digest())
        keys.append(key)
        if key not in cache:
            duplicate_misses += key in missing
            missing.setdefault(key, box)
        else:
            cache_hits += 1
            cache.move_to_end(key)
    fresh = {}
    caption_ms = 0.0
    if missing:
        caption_started = time.perf_counter()
        captions = captioner(list(missing.values()))
        caption_ms = (time.perf_counter() - caption_started) * 1000
        for key, caption in zip(missing, captions, strict=True):
            fresh[key] = caption
            cache[key] = caption
    # A frame may itself have more distinct controls than the cache capacity.
    result = [fresh[key] if key in fresh else cache[key] for key in keys]
    while len(cache) > limit:
        cache.popitem(last=False)
    if telemetry is not None:
        telemetry.update(
            caption_ms=caption_ms,
            caption_cache_ms=(time.perf_counter() - started) * 1000 - caption_ms,
            caption_regions=len(keys),
            cache_hits=cache_hits,
            unique_misses=len(missing),
            duplicate_misses=duplicate_misses,
        )
    return result


class OmniWorker:
    def __init__(self, config):
        started = time.perf_counter()
        import torch

        self.backend = select_backend(torch, config["parser_device"])
        self.device = torch_device(self.backend)
        source = config.get("omni_source")
        if not source or not (Path(source) / "util/utils.py").is_file():
            raise RuntimeError("pinned OmniParser source unavailable")
        sys.path.insert(0, source)
        import_started = time.perf_counter()
        from transformers import AutoModelForCausalLM, AutoProcessor
        from util.utils import (
            check_ocr_box,
            get_parsed_content_icon,
            get_yolo_model,
            int_box_area,
            predict_yolo,
            remove_overlap_new,
        )

        self.load_metrics = {
            "upstream_import_ms": (time.perf_counter() - import_started) * 1000,
            "effective_torch_threads": torch.get_num_threads(),
        }
        path = model_path(
            config, "microsoft/OmniParser-v2.0", MODEL_REVISIONS["microsoft/OmniParser-v2.0"]
        )
        load_started = time.perf_counter()
        self.detector = get_yolo_model(path / "icon_detect_v3/model.pt", device=self.device)
        self.load_metrics["detector_load_ms"] = (time.perf_counter() - load_started) * 1000
        load_started = time.perf_counter()
        self.processor = AutoProcessor.from_pretrained(
            "microsoft/Florence-2-base",
            revision=MODEL_REVISIONS["microsoft/Florence-2-base"],
            trust_remote_code=True,
            local_files_only=True,
        )
        self.load_metrics["processor_load_ms"] = (time.perf_counter() - load_started) * 1000
        dtype = torch.float32 if self.device == "cpu" else torch.float16
        load_started = time.perf_counter()
        self.caption = AutoModelForCausalLM.from_pretrained(
            path / "icon_caption",
            trust_remote_code=True,
            local_files_only=True,
            torch_dtype=dtype,
            code_revision=MODEL_REVISIONS["microsoft/Florence-2-base-ft"],
        ).to(self.device)
        self.load_metrics["caption_load_ms"] = (time.perf_counter() - load_started) * 1000
        # Upstream selects the Florence prompt/generation contract using this metadata.
        # A local cache path otherwise selects its incompatible generic caption branch.
        self.caption.config.name_or_path = "microsoft/florence-2-base-ft"
        self.check_ocr_box = check_ocr_box
        self.predict = predict_yolo
        self.overlap = remove_overlap_new
        self.caption_icons = get_parsed_content_icon
        self.area = int_box_area
        self.icon_caption_cache = OrderedDict()
        self.load_metrics["total_load_ms"] = (time.perf_counter() - started) * 1000

    def request(self, record):
        started = time.perf_counter()
        image = Image.open(io.BytesIO(base64.b64decode(record["image"]))).convert("RGB")
        telemetry = {"decode_ms": (time.perf_counter() - started) * 1000}
        stage_started = time.perf_counter()
        (text, boxes), _ = self.check_ocr_box(
            image,
            display_img=False,
            output_bb_format="xyxy",
            easyocr_args={"text_threshold": 0.8},
            use_paddleocr=False,
        )
        telemetry["ocr_ms"] = (time.perf_counter() - stage_started) * 1000
        telemetry["ocr_count"] = len(boxes)
        import numpy as np
        import torch

        width, height = image.size
        stage_started = time.perf_counter()
        detected, _, _ = self.predict(self.detector, image, 0.05, (height, width), False)
        telemetry["detection_ms"] = (time.perf_counter() - stage_started) * 1000
        telemetry["detected_count"] = len(detected)
        stage_started = time.perf_counter()
        scale = torch.tensor([width, height, width, height], device=detected.device)
        icons = [
            {"type": "icon", "bbox": box, "interactivity": True, "content": None}
            for box in (detected / scale).tolist()
            if self.area(box, width, height) > 0
        ]
        ocr = [
            {
                "type": "text",
                "bbox": [box[0] / width, box[1] / height, box[2] / width, box[3] / height],
                "interactivity": False,
                "content": label,
                "source": "box_ocr_content_ocr",
            }
            for box, label in zip(boxes, text, strict=True)
        ]
        merged = self.overlap(icons, iou_threshold=0.7, ocr_bbox=ocr)
        if not ocr:
            # The pinned empty-OCR branch returns coordinates, unlike its dict branch.
            merged = [
                {"type": "icon", "bbox": box, "interactivity": True, "content": None}
                for box in merged
            ]
        objects = sorted(merged, key=lambda box: box["content"] is None)
        start = next((i for i, box in enumerate(objects) if box["content"] is None), None)
        telemetry.update(
            fusion_ms=(time.perf_counter() - stage_started) * 1000,
            object_count=len(objects),
            caption_ms=0.0,
            caption_cache_ms=0.0,
            caption_regions=0,
            cache_hits=0,
            unique_misses=0,
            duplicate_misses=0,
        )
        # Compose upstream primitives without its annotation helper's empty-OCR and
        # starting_idx=-1 bugs. Caption only regions that actually lack OCR content.
        if start is not None:
            captions = caption_regions(
                image,
                [box["bbox"] for box in objects[start:]],
                lambda boxes: self.caption_icons(
                    torch.tensor(boxes, dtype=torch.float32),
                    0,
                    np.asarray(image),
                    {"model": self.caption, "processor": self.processor},
                    batch_size=16,
                ),
                self.icon_caption_cache,
                telemetry=telemetry,
            )
            for box, caption in zip(objects[start:], captions, strict=True):
                box["content"] = caption
                box["source"] = "box_yolo_content_yolo"
        telemetry["total_ms"] = (time.perf_counter() - started) * 1000
        return {"objects": objects, "telemetry": telemetry}


def profiled_request(worker, payload):
    if not payload.pop("benchmark_metrics", False):
        return worker.request(payload)
    import torch

    seed = payload.pop("benchmark_seed", 0)
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("benchmark seed must be a uint32")
    torch.manual_seed(seed)
    gpu = worker.backend in {"cuda", "rocm"}
    if gpu:
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    result = worker.request(payload)
    if gpu:
        torch.cuda.synchronize()
    metrics = {"seed": seed}
    try:
        import resource

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        metrics["peak_rss_bytes"] = peak if sys.platform == "darwin" else peak * 1024
    except ImportError:
        pass
    if gpu:
        metrics["gpu_peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
        metrics["gpu_peak_reserved_bytes"] = torch.cuda.max_memory_reserved()
    result["benchmark_metrics"] = metrics
    return result


def main():
    protocol = sys.stdout

    def emit(payload):
        protocol.write(json.dumps(payload) + "\n")
        protocol.flush()

    def diagnostic(exc):
        message = str(exc)
        if getattr(exc, "head_capture_cleanup_incomplete", False) is True:
            message += "; private head capture cleanup incomplete"
        code = "OUT_OF_MEMORY" if "out of memory" in message.lower() else type(exc).__name__
        return {
            "error": code,
            # Operators saw only "ModelWorkerError in runtime backend" while the
            # real CUDA message named the cause; carry a bounded exception text.
            "message": message[-600:],
            "frames": [
                {"file": Path(frame.filename).name, "function": frame.name, "line": frame.lineno}
                for frame in traceback.extract_tb(exc.__traceback__)[-4:]
            ],
        }

    try:
        config = json.loads(sys.stdin.readline())
        if config.get("rocm_arch"):
            os.environ["ROCM_SDK_TARGET_FAMILY"] = config["rocm_arch"]
        with contextlib.redirect_stdout(sys.stderr):
            worker_type = {
                "clef": ClefWorker,
                "d1": D1Worker,
                "omni": OmniWorker,
                "visual": VisualWorker,
            }
            worker = worker_type[sys.argv[1]](config)
        ready = {
            "ready": True,
            "device": worker.device,
            "backend": worker.backend,
            "quantized_modules": getattr(worker, "quantized_modules", 0),
        }
        if hasattr(worker, "decision_model"):
            import importlib.metadata

            ready["worker_pid"] = os.getpid()
            ready["libraries"] = {
                name: importlib.metadata.version(name)
                for name in ("torch", "transformers", "tokenizers")
            }
            ready["decision_model"] = worker.decision_model
            ready["model_revision"] = worker.model_revision
        if hasattr(worker, "load_metrics"):
            ready["load_metrics"] = worker.load_metrics
        if hasattr(worker, "compute_dtype"):
            ready["compute_dtype"] = worker.compute_dtype
        if getattr(worker, "attention_implementation", None) is not None:
            ready["attention_implementation"] = worker.attention_implementation
        if hasattr(worker, "coarse_strategies"):
            ready["coarse_strategies"] = worker.coarse_strategies
        emit(ready)
        for line in sys.stdin:
            try:
                with contextlib.redirect_stdout(sys.stderr):
                    result = profiled_request(worker, json.loads(line))
                emit(result)
            except Exception as exc:
                emit(diagnostic(exc))
    except Exception as exc:
        emit(diagnostic(exc))


if __name__ == "__main__":
    main()
