"""Resident ML worker; separate environments keep upstream dependency versions isolated."""

from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import sys
import traceback
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
        self.model, self.processor = load_release_model(
            path,
            device=self.device,
            dtype=dtype,
            attn_implementation="sdpa" if torch.version.hip else "eager",
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


class OmniWorker:
    def __init__(self, config):
        import torch

        self.backend = select_backend(torch, config["parser_device"])
        self.device = torch_device(self.backend)
        source = config.get("omni_source")
        if not source or not (Path(source) / "util/utils.py").is_file():
            raise RuntimeError("pinned OmniParser source unavailable")
        sys.path.insert(0, source)
        from transformers import AutoModelForCausalLM, AutoProcessor
        from util.utils import (
            check_ocr_box,
            get_parsed_content_icon,
            get_yolo_model,
            int_box_area,
            predict_yolo,
            remove_overlap_new,
        )

        path = model_path(
            config, "microsoft/OmniParser-v2.0", MODEL_REVISIONS["microsoft/OmniParser-v2.0"]
        )
        self.detector = get_yolo_model(path / "icon_detect_v3/model.pt", device=self.device)
        self.processor = AutoProcessor.from_pretrained(
            "microsoft/Florence-2-base",
            revision=MODEL_REVISIONS["microsoft/Florence-2-base"],
            trust_remote_code=True,
            local_files_only=True,
        )
        dtype = torch.float32 if self.device == "cpu" else torch.float16
        self.caption = AutoModelForCausalLM.from_pretrained(
            path / "icon_caption",
            trust_remote_code=True,
            local_files_only=True,
            torch_dtype=dtype,
            code_revision=MODEL_REVISIONS["microsoft/Florence-2-base-ft"],
        ).to(self.device)
        # Upstream selects the Florence prompt/generation contract using this metadata.
        # A local cache path otherwise selects its incompatible generic caption branch.
        self.caption.config.name_or_path = "microsoft/florence-2-base-ft"
        self.check_ocr_box = check_ocr_box
        self.predict = predict_yolo
        self.overlap = remove_overlap_new
        self.caption_icons = get_parsed_content_icon
        self.area = int_box_area

    def request(self, record):
        image = Image.open(io.BytesIO(base64.b64decode(record["image"]))).convert("RGB")
        (text, boxes), _ = self.check_ocr_box(
            image,
            display_img=False,
            output_bb_format="xyxy",
            easyocr_args={"text_threshold": 0.8},
            use_paddleocr=False,
        )
        import numpy as np
        import torch

        width, height = image.size
        detected, _, _ = self.predict(self.detector, image, 0.05, (height, width), False)
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
        objects = sorted(
            self.overlap(icons, iou_threshold=0.7, ocr_bbox=ocr),
            key=lambda box: box["content"] is None,
        )
        start = next((i for i, box in enumerate(objects) if box["content"] is None), None)
        # Compose upstream primitives without its annotation helper's empty-OCR and
        # starting_idx=-1 bugs. Caption only regions that actually lack OCR content.
        if start is not None:
            captions = self.caption_icons(
                torch.tensor([box["bbox"] for box in objects]),
                start,
                np.asarray(image),
                {"model": self.caption, "processor": self.processor},
                batch_size=16,
            )
            for box, caption in zip(objects[start:], captions, strict=True):
                box["content"] = caption
                box["source"] = "box_yolo_content_yolo"
        return {"objects": objects}


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
        emit(
            {
                "ready": True,
                "device": worker.device,
                "backend": worker.backend,
                "quantized_modules": getattr(worker, "quantized_modules", 0),
            }
        )
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
