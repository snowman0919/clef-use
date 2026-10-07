from __future__ import annotations

from pathlib import Path

MODEL_REVISIONS = {
    "Cloudflare/clef-flash": "17f0b0ad64efb65d273590632833508766b2aae6",
    "Cloudflare/clef": "2f3de3dd85f379784083b0814d997ab627200f0c",
    "microsoft/OmniParser-v2.0": "f55d0750e5b94db2125ef0b45b0fa4a85ddc59b4",
    "microsoft/Florence-2-base": "5ca5edf5bd017b9919c05d08aebef5e4c7ac3bac",
    "microsoft/Florence-2-base-ft": "f6c1a25888ffc1d945ee8a1a77ac833c7303d46e",
    "google/siglip2-base-patch16-512": "a89f5c5093f902bf39d3cd4d81d2c09867f0724b",
}
OMNI_SOURCE_REVISION = "354021201345a96178360b28733573e27269f2de"


def snapshot_path(root: Path, repo: str) -> Path:
    return (
        root
        / "huggingface/hub"
        / ("models--" + repo.replace("/", "--"))
        / "snapshots"
        / MODEL_REVISIONS[repo]
    )


def download(root: Path, repo: str) -> Path:
    from huggingface_hub import snapshot_download

    patterns = None
    if repo == "microsoft/OmniParser-v2.0":
        patterns = ["icon_detect_v3/*", "icon_caption/*"]
    elif "Florence" in repo:
        patterns = ["*.json", "*.py", "*.txt"]
    return Path(
        snapshot_download(
            repo,
            revision=MODEL_REVISIONS[repo],
            cache_dir=str(root / "huggingface/hub"),
            allow_patterns=patterns,
        )
    )


def inventory(root: Path, decision_model: str, *, visual=False) -> list[dict]:
    required = {
        decision_model: [
            "config.json",
            "joint_schema_model.py",
            "joint_head.safetensors",
            "joint_head_config.json",
            "model.safetensors.index.json",
            "processor_config.json",
            "tokenizer.json",
            "tokenizer_config.json",
        ],
        "microsoft/OmniParser-v2.0": [
            "icon_detect_v3/model.pt",
            "icon_caption/model.safetensors",
            "icon_caption/config.json",
        ],
        "microsoft/Florence-2-base": [
            "config.json",
            "preprocessor_config.json",
            "processing_florence2.py",
            "configuration_florence2.py",
            "tokenizer.json",
            "tokenizer_config.json",
            "vocab.json",
        ],
        "microsoft/Florence-2-base-ft": [
            "config.json",
            "configuration_florence2.py",
            "modeling_florence2.py",
        ],
    }
    if visual:
        required["google/siglip2-base-patch16-512"] = [
            "config.json",
            "model.safetensors",
            "preprocessor_config.json",
            "tokenizer.json",
            "tokenizer_config.json",
        ]
    result = []
    for repo, filenames in required.items():
        path = snapshot_path(root, repo)
        missing = [name for name in filenames if not (path / name).is_file()]
        index = path / "model.safetensors.index.json"
        if index.exists():
            import json

            for name in set(json.loads(index.read_text())["weight_map"].values()):
                if not (path / name).is_file():
                    missing.append(name)
        result.append(
            {
                "model": repo,
                "revision": MODEL_REVISIONS[repo],
                "path": str(path),
                "available": not missing,
                "missing": missing,
            }
        )
    return result
