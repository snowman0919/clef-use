from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def merge(inputs, output):
    manifests = [
        json.loads(path.read_text()) for path in inputs.glob("**/releases/*/manifest.json")
    ]
    versions = {manifest["version"] for manifest in manifests}
    if len(versions) != 1:
        raise ValueError("release merge requires one version")
    version = versions.pop()
    artifacts, keys = [], set()
    release = output / "releases" / version
    release.mkdir(parents=True, exist_ok=True)
    for path in inputs.glob("**/releases/*/manifest.json"):
        manifest = json.loads(path.read_text())
        for artifact in manifest["artifacts"]:
            key = (artifact["platform"], artifact["architecture"], artifact["python"])
            if key in keys:
                raise ValueError("duplicate platform/python release")
            keys.add(key)
            source = path.parent / artifact["filename"]
            if hashlib.sha256(source.read_bytes()).hexdigest() != artifact["sha256"]:
                raise ValueError("release artifact checksum mismatch")
            shutil.copy2(source, release / source.name)
            artifacts.append(artifact)
    combined = {**manifests[0], "artifacts": sorted(artifacts, key=lambda item: item["filename"])}
    latest = output / "latest"
    latest.mkdir(exist_ok=True)
    sums = "".join(f"{a['sha256']}  {a['filename']}\n" for a in combined["artifacts"])
    for destination in (latest, release):
        (destination / "manifest.json").write_text(json.dumps(combined, indent=2) + "\n")
        (destination / "SHA256SUMS").write_text(sums)
    for name in ("install.sh", "install.ps1"):
        sources = list(inputs.glob(f"**/releases/{version}/{name}"))
        contents = {path.read_bytes() for path in sources}
        if len(contents) != 1:
            raise ValueError("bootstrap contents differ between platform builds")
        content = next(iter(contents))
        for destination in (output / name, release / name):
            destination.write_bytes(content)
            destination.chmod(0o755)
    return combined


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(merge(args.inputs, args.output), indent=2))
