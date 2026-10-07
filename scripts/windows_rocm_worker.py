"""Experimental Windows ROCm/NF4 loader using the canonical resident JSON protocol."""

import json
import os
import subprocess
import sys
import threading
from pathlib import Path


def start_worker(worker, script, log_path):
    if worker.process is not None:
        raise RuntimeError("diagnostic loader must start before the first model request")
    import clef_use

    child_env = dict(
        os.environ,
        HF_HOME=str(worker.config.model_dir / "huggingface"),
        HF_HUB_OFFLINE="1",
        TOKENIZERS_PARALLELISM="false",
        CLEF_USE_DIAGNOSTIC_PACKAGE_ROOT=str(Path(clef_use.__file__).parent),
    )
    with Path(log_path).open("xb") as log:
        worker.process = subprocess.Popen(
            [str(worker.python), str(script), "clef"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=log,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=child_env,
        )
    worker.process.stdin.write(worker.config.model_dump_json() + "\n")
    worker.process.stdin.flush()
    threading.Thread(
        target=worker._reader, args=(worker.process, worker.replies), daemon=True
    ).start()
    ready = worker._receive()
    if ready.get("device") != "cuda":
        worker.close()
        raise RuntimeError("Windows ROCm diagnostic did not initialize its GPU")


def main():
    package_root = os.environ.get("CLEF_USE_DIAGNOSTIC_PACKAGE_ROOT")
    if package_root is None:
        import clef_use

        package_root = str(Path(clef_use.__file__).parent)
    sys.path.insert(0, package_root)
    import model_worker

    class RocmQuantizedWorker(model_worker.ClefWorker):
        def __init__(self, config):
            import bitsandbytes as bnb
            import torch
            from transformers import BitsAndBytesConfig

            if not torch.version.hip or not torch.cuda.is_available():
                raise RuntimeError("ROCm-enabled PyTorch and an available AMD GPU are required")
            self.device = "cuda"
            path = model_worker.model_path(
                config,
                config["decision_model"],
                model_worker.MODEL_REVISIONS[config["decision_model"]],
            )
            sys.path.insert(0, str(path))
            from joint_schema_model import load_release_model, systemone

            self.systemone = systemone
            quantization = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.float16,
                llm_int8_skip_modules=["lm_head", "model.visual"],
            )
            self.model, self.processor = load_release_model(
                path,
                device=self.device,
                dtype=torch.float16,
                quantization_config=quantization,
                attn_implementation="eager",
                local_files_only=True,
            )
            quantized = [
                name
                for name, module in self.model.named_modules()
                if isinstance(module, bnb.nn.Linear4bit)
            ]
            if not quantized or any(
                ".visual." in name or "lm_head" in name or name.startswith("head.")
                for name in quantized
            ):
                raise RuntimeError("CLEF quantization exclusion invariant failed")
            if not all(parameter.is_floating_point() for parameter in self.model.head.parameters()):
                raise RuntimeError("CLEF typed head must remain floating point")
            print(
                json.dumps(
                    {
                        "backend": "rocm",
                        "torch": torch.__version__,
                        "hip": torch.version.hip,
                        "quantized_modules": len(quantized),
                        "quantized_visual": False,
                        "quantized_output_head": False,
                        "quantized_joint_head": False,
                    }
                ),
                file=sys.stderr,
                flush=True,
            )

    model_worker.ClefWorker = RocmQuantizedWorker
    model_worker.main()


if __name__ == "__main__":
    main()
