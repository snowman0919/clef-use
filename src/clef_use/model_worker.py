"""Resident ML worker; separate environments keep upstream dependency versions isolated."""

from __future__ import annotations

import base64
import contextlib
import io
import json
import sys
import traceback
from pathlib import Path

from models import MODEL_REVISIONS
from PIL import Image


def choose_device(torch, requested):
    if requested != "auto":
        if requested == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA unavailable")
        if requested == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("MPS unavailable")
        return requested
    return (
        "cuda"
        if torch.cuda.is_available()
        else "mps"
        if torch.backends.mps.is_available()
        else "cpu"
    )


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

        self.device = choose_device(torch, config["device"])
        revision = MODEL_REVISIONS[config["decision_model"]]
        path = model_path(config, config["decision_model"], revision)
        sys.path.insert(0, str(path))
        from joint_schema_model import load_release_model, systemone

        self.systemone = systemone
        dtype = (
            torch.float32
            if self.device == "cpu"
            else torch.float16
            if self.device == "mps"
            else torch.bfloat16
        )
        self.model, self.processor = load_release_model(
            path,
            device=self.device,
            dtype=dtype,
            attn_implementation="eager",
            local_files_only=True,
        )

    def request(self, record):
        image = record.pop("image", None)
        if image:
            record["images"] = [Image.open(io.BytesIO(base64.b64decode(image))).convert("RGB")]
            record["media_kwargs"] = {"max_pixels": 512 * 512}
        try:
            return self.systemone(self.model, self.processor, record, max_length=8192)
        finally:
            if self.device == "mps":
                import torch

                torch.mps.empty_cache()


class OmniWorker:
    def __init__(self, config):
        import torch

        self.device = choose_device(torch, config["parser_device"])
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
        with contextlib.redirect_stdout(sys.stderr):
            worker = ClefWorker(config) if sys.argv[1] == "clef" else OmniWorker(config)
        emit({"ready": True, "device": worker.device})
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
