"""Check lexical-row offloading against the pinned, loaded CLEF head."""

import argparse
import json
import sys
import time
import tomllib
from pathlib import Path
from types import SimpleNamespace

import torch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("evidence output already exists")
    sys.path.insert(0, str(args.package_root))
    from model_worker import model_path, offload_output_embeddings
    from models import MODEL_REVISIONS

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    repo = config.get("decision_model", "Cloudflare/clef-flash")
    path = model_path(config, repo, MODEL_REVISIONS[repo])
    sys.path.insert(0, str(path))
    from joint_schema_model import load_release_model
    from transformers import BitsAndBytesConfig

    started = time.perf_counter()
    model, _ = load_release_model(
        path,
        device="cuda",
        dtype=torch.float16,
        attn_implementation="sdpa",
        local_files_only=True,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16,
            llm_int8_skip_modules=["lm_head", "model.visual"],
        ),
    )
    torch.manual_seed(730)
    hidden = torch.randn(1, 8, 4096, device="cuda", dtype=torch.float16)
    ids = torch.tensor([[1, 37, 42, 311, 50, 90, 72, 4]], device="cuda")
    masks = torch.ones_like(ids)
    records = [
        SimpleNamespace(
            questions=[
                SimpleNamespace(
                    question_type=0, question_span=(0, 2), option_spans=[(2, 4), (4, 6)]
                )
            ]
        )
    ]
    embedding = model.language_model.get_output_embeddings()
    before = torch.cuda.memory_allocated()
    with torch.inference_mode():
        expected = model.head(hidden, ids, masks, records, embedding.weight)[0][0].cpu()
        offload_output_embeddings(model)
        actual = model.head(hidden, ids, masks, records, embedding.weight)[0][0].cpu()
        delta = (expected - actual).abs().max().item()
        original = embedding.weight[42].clone()
        embedding.weight[42].add_(0.1)
        changed = model.head(hidden, ids, masks, records, embedding.weight)[0][0].cpu()
        perturbation_delta = (changed - actual).abs().max().item()
        embedding.weight[42].copy_(original)
    report = {
        "scope": (
            "Loaded real CLEF head/embeddings with seeded fixture hidden states; "
            "separate from GUI acceptance"
        ),
        "revision": MODEL_REVISIONS[repo],
        "head_max_abs_delta": delta,
        "lexical_perturbation_delta": perturbation_delta,
        "allocated_bytes_before": before,
        "allocated_bytes_after": torch.cuda.memory_allocated(),
        "embedding_device": str(embedding.weight.device),
        "embedding_dtype": str(embedding.weight.dtype),
        "seed": 730,
        "wall_seconds": time.perf_counter() - started,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    assert delta == 0 and perturbation_delta > 0, report
    assert embedding.weight.device.type == "cpu" and embedding.weight.is_floating_point()
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
