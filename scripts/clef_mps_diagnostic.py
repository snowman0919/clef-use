"""Run a public-safe structured request through one pinned resident CLEF MPS model."""

import argparse
import base64
import io
import json
import sys
import time
import traceback
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--request-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 10:
        raise ValueError("repeats must be 1..10")
    if args.model_path.name != "17f0b0ad64efb65d273590632833508766b2aae6":
        raise ValueError("the pinned CLEF-Flash snapshot is required")
    import torch
    from PIL import Image

    sys.path.insert(0, str(args.model_path))
    from joint_schema_model import load_release_model, systemone

    model, processor = load_release_model(
        args.model_path,
        device="mps",
        dtype=torch.float16,
        attn_implementation="eager",
        local_files_only=True,
    )
    record_source = json.loads(args.request_file.read_text())
    policies, rows = ("CLEAR", "SYNC_CLEAR", "KEEP"), []
    for repetition in range(args.repeats):
        for offset in range(len(policies)):
            policy = policies[(repetition + offset) % len(policies)]
            record = json.loads(json.dumps(record_source))
            image = Image.open(io.BytesIO(base64.b64decode(record.pop("image")))).convert("RGB")
            record.update(images=[image], media_kwargs={"max_pixels": 512 * 512})
            row = {"policy": policy, "repetition": repetition}
            started = time.perf_counter()
            try:
                if policy == "SYNC_CLEAR":
                    torch.mps.synchronize()
                row["answers"] = systemone(model, processor, record, max_length=8192)["answers"]
            except Exception as exc:
                row["error"] = type(exc).__name__
                row["frames"] = [
                    {"file": Path(f.filename).name, "function": f.name, "line": f.lineno}
                    for f in traceback.extract_tb(exc.__traceback__)[-6:]
                ]
            finally:
                if policy == "SYNC_CLEAR":
                    torch.mps.synchronize()
                if policy != "KEEP":
                    torch.mps.empty_cache()
            row.update(
                seconds=time.perf_counter() - started,
                mps_allocated=torch.mps.current_allocated_memory(),
                mps_driver=torch.mps.driver_allocated_memory(),
            )
            rows.append(row)
            args.output.write_text(
                json.dumps(
                    {
                        "torch": torch.__version__,
                        "rows": rows,
                        "method": "Rotated resident-model pilot; allocator carryover retained",
                        "limitation": "Not an independent policy benchmark or correctness proof",
                    },
                    indent=2,
                )
            )
            print(
                json.dumps({key: value for key, value in row.items() if key != "answers"}),
                flush=True,
            )


if __name__ == "__main__":
    main()
