"""Probe isolated ML environments without loading weights or importing OCR readers."""

from __future__ import annotations

import contextlib
import importlib
import json
import sys

MODULES = {
    "clef": (
        "torch",
        "torchvision",
        "transformers",
        "accelerate",
        "PIL",
        "numpy",
        "safetensors",
        "huggingface_hub",
    ),
    "omni": (
        "torch",
        "torchvision",
        "transformers",
        "accelerate",
        "PIL",
        "numpy",
        "easyocr",
        "paddle",
        "paddleocr",
        "cv2",
        "supervision",
        "timm",
        "einops",
        "huggingface_hub",
        "requests",
        "openai",
        "matplotlib",
    ),
}


def probe(kind, requested):
    modules = {}
    errors = {}
    versions = {}
    for name in MODULES[kind]:
        try:
            module = importlib.import_module(name)
            if name == "transformers":
                _ = module.AutoProcessor
                _ = getattr(
                    module,
                    "Qwen3_5ForConditionalGeneration" if kind == "clef" else "AutoModelForCausalLM",
                )
            modules[name] = module
            versions[name] = str(getattr(module, "__version__", "UNKNOWN"))
        except Exception as exc:
            errors[name] = type(exc).__name__
    report = {
        "status": "ERROR" if errors else "OBSERVED",
        "requested_device": requested,
        "imports": versions,
        "errors": errors,
        "ready": False,
    }
    if "torch" in modules and "PIL" in modules:
        try:
            from model_worker import choose_device

            torch = modules["torch"]
            device = choose_device(torch, requested)
            # is_available alone does not establish usable runtime/driver initialization.
            value = torch.tensor([1.0, 2.0], device=device).sum().item()
            if value != 3.0:
                raise RuntimeError("device arithmetic failed")
            report["device"] = device
            report["device_operation"] = "OBSERVED"
            report["hip"] = torch.version.hip
            report["ready"] = not errors
        except Exception as exc:
            report["status"] = "ERROR"
            report["device_operation"] = "ERROR"
            report["device_error"] = type(exc).__name__
    return report


def main():
    protocol = sys.stdout
    with contextlib.redirect_stdout(sys.stderr):
        result = probe(sys.argv[1], sys.argv[2])
    protocol.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    main()
