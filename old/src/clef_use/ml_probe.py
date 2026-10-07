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


def probe(kind, requested, quantization="none"):
    modules = {}
    errors = {}
    versions = {}
    required = MODULES[kind] + (
        ("bitsandbytes",) if kind == "clef" and quantization == "4bit" else ()
    )
    for name in required:
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
            from deployment_profiles import select_backend

            report["backend"] = select_backend(torch, requested)
            report["device"] = device
            report["device_operation"] = "OBSERVED"
            report["hip"] = torch.version.hip
            if kind == "clef" and quantization == "4bit" and "bitsandbytes" in modules:
                if device == "mps":
                    raise RuntimeError("NF4 is not enabled for MPS")
                source = torch.linspace(-1, 1, 256, device=device, dtype=torch.float16)
                functional = modules["bitsandbytes"].functional
                packed, state = functional.quantize_4bit(
                    source, quant_type="nf4", compress_statistics=True
                )
                restored = functional.dequantize_4bit(packed, state)
                error = (restored.reshape(-1) - source).abs().max().item()
                if not torch.isfinite(restored).all().item() or error > 0.3:
                    raise RuntimeError("NF4 arithmetic validation failed")
                report["nf4"] = {"status": "OBSERVED", "max_abs_error": error, "tolerance": 0.3}
            report["ready"] = not errors
        except Exception as exc:
            report["status"] = "ERROR"
            report["device_operation"] = "ERROR"
            report["device_error"] = type(exc).__name__
    return report


def main():
    protocol = sys.stdout
    with contextlib.redirect_stdout(sys.stderr):
        result = probe(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "none")
    protocol.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    main()
