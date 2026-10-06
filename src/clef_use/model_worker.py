"""Resident ML worker; separate environments keep upstream dependency versions isolated."""

from __future__ import annotations

import base64
import contextlib
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


class CpuEmbeddingRows:
    def __init__(self, weight, device):
        self.weight = weight
        self.device = device

    def __getitem__(self, indices):
        return self.weight[indices.cpu()].to(self.device)


def offload_output_embeddings(model):
    import torch

    embedding = model.language_model.get_output_embeddings()
    if str(embedding.weight.device) == "cpu":
        return
    embedding.weight = torch.nn.Parameter(embedding.weight.detach().cpu(), requires_grad=False)

    def select_rows(_module, arguments):
        # The pinned joint head reads lexical rows directly; lm_head is never executed.
        return (*arguments[:-1], CpuEmbeddingRows(arguments[-1], arguments[0].device))

    model.head.register_forward_pre_hook(select_rows)


def load_cuda_nf4_model(path, *, device="cuda", dtype, **kwargs):
    """Compose the pinned release before moving its joint head onto a tight GPU."""
    import torch
    from joint_schema_model import ClefModel, JointSchemaHead
    from safetensors.torch import load_file
    from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration

    backbone = Qwen3_5ForConditionalGeneration.from_pretrained(
        path, dtype=dtype, device_map={"": str(device)}, **kwargs
    )
    backbone.config.use_cache = False
    head = JointSchemaHead(**json.loads((path / "joint_head_config.json").read_text()))
    head.load_state_dict(load_file(path / "joint_head.safetensors"), strict=True)
    model = ClefModel(backbone, head)
    if torch.cuda.mem_get_info()[0] < 1024**3:
        # The upstream loader moves the head first, before the old offload guard can run.
        offload_output_embeddings(model)
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
        path = model_path(config, config["decision_model"], revision)
        sys.path.insert(0, str(path))
        from joint_schema_model import load_release_model, systemone

        self.systemone = systemone
        quantization = config.get("quantization", "none")
        if quantization == "4bit" and self.backend == "mps":
            raise RuntimeError("NF4 is not enabled for the MPS profile")
        dtype = (
            torch.float32
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
                llm_int8_skip_modules=["lm_head", "model.visual"],
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
            attn_implementation="sdpa" if self.backend in {"cuda", "rocm"} else "eager",
            local_files_only=True,
            **kwargs,
        )
        self.quantized_modules = 0
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
            if self.backend == "cuda" and torch.cuda.mem_get_info()[0] < 1024**3:
                offload_output_embeddings(self.model)

    def request(self, record):
        image = record.pop("image", None)
        if image:
            record["images"] = [Image.open(io.BytesIO(base64.b64decode(image))).convert("RGB")]
            record["media_kwargs"] = {"min_pixels": 56 * 56, "max_pixels": 512 * 512}
        try:
            return self.systemone(self.model, self.processor, record, max_length=8192)
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


def main():
    protocol = sys.stdout

    def emit(payload):
        protocol.write(json.dumps(payload) + "\n")
        protocol.flush()

    def diagnostic(exc):
        code = "OUT_OF_MEMORY" if "out of memory" in str(exc).lower() else type(exc).__name__
        return {
            "error": code,
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
            worker = ClefWorker(config) if sys.argv[1] == "clef" else OmniWorker(config)
        ready = {
            "ready": True,
            "device": worker.device,
            "backend": worker.backend,
            "quantized_modules": getattr(worker, "quantized_modules", 0),
        }
        if hasattr(worker, "load_metrics"):
            ready["load_metrics"] = worker.load_metrics
        emit(ready)
        for line in sys.stdin:
            try:
                with contextlib.redirect_stdout(sys.stderr):
                    result = worker.request(json.loads(line))
                emit(result)
            except Exception as exc:
                emit(diagnostic(exc))
    except Exception as exc:
        emit(diagnostic(exc))


if __name__ == "__main__":
    main()
