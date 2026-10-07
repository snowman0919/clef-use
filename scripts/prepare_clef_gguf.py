"""Build a pinned, text-only CLEF GGUF without changing the installed runtime."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MODEL_REVISION = "17f0b0ad64efb65d273590632833508766b2aae6"
LLAMA_REVISION = "0504396140d1c882f5f6ee34466a42db7ae90114"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--llama-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    source, llama, output = args.source.resolve(), args.llama_dir.resolve(), args.output.resolve()
    if source.name != MODEL_REVISION or output.exists():
        raise ValueError("require the pinned snapshot and a new output directory")
    observed = subprocess.check_output(
        ["git", "-C", str(llama), "rev-parse", "HEAD"], text=True
    ).strip()
    if observed != LLAMA_REVISION:
        raise ValueError("llama.cpp revision differs from the reviewed converter")
    sys.path.insert(0, str(llama / "gguf-py"))
    import gguf

    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=".clef-gguf-", dir=output.parent) as temporary:
        stage = Path(temporary)
        bundle = stage / "bundle"
        bundle.mkdir()
        intermediate = stage / "clef-flash-bf16.gguf"
        model = bundle / "clef-flash-Q4_K_M.gguf"
        subprocess.run(
            [
                sys.executable,
                str(llama / "convert_hf_to_gguf.py"),
                str(source),
                "--outfile",
                str(intermediate),
                "--outtype",
                "bf16",
            ],
            check=True,
        )
        subprocess.run(
            [
                str(llama / "build/bin/llama-quantize"),
                "--tensor-type",
                r"^(decision\.|dec\.)=f16",
                str(intermediate),
                str(model),
                "Q4_K_M",
                str(args.threads),
            ],
            check=True,
        )
        reader = gguf.GGUFReader(model)
        architecture = reader.get_field("general.architecture").contents()
        heads = [
            tensor for tensor in reader.tensors if tensor.name.startswith(("decision.", "dec."))
        ]
        floating = {
            gguf.GGMLQuantizationType.F32,
            gguf.GGMLQuantizationType.F16,
            gguf.GGMLQuantizationType.BF16,
        }
        types = collections.Counter(tensor.tensor_type.name for tensor in reader.tensors)
        if (
            architecture != "clef"
            or not heads
            or any(tensor.tensor_type not in floating for tensor in heads)
        ):
            raise RuntimeError("CLEF architecture or floating decision-head invariant failed")
        if not types["Q4_K"]:
            raise RuntimeError("backbone was not quantized to Q4_K")
        del reader
        for name in (
            "joint_head_config.json",
            "joint_head.safetensors",
            "joint_schema_model.py",
            "README.md",
        ):
            shutil.copyfile(source / name, bundle / name)
        manifest = {
            "model": "Cloudflare/clef-flash",
            "model_revision": MODEL_REVISION,
            "llama_cpp_revision": LLAMA_REVISION,
            "quantization": "Q4_K_M",
            "decision_head": "embedded floating point; original sidecar preserved",
            "image_input": "UNSUPPORTED by pinned upstream CLEF implementation",
            "runtime_integration": "NOT_IMPLEMENTED; standalone artifact",
            "tensor_types": dict(types),
            "decision_head_tensors": len(heads),
            "build_seconds": time.monotonic() - started,
            "files": {
                path.name: {"bytes": path.stat().st_size, "sha256": digest(path)}
                for path in sorted(bundle.iterdir())
            },
        }
        (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        bundle.rename(output)
    print(json.dumps({"output": str(output), "status": "QUANTIZED", **manifest}, indent=2))


if __name__ == "__main__":
    main()
