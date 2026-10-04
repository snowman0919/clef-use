"""Publish the assembled site on dev; keep version artifacts immutable."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from clef_use.installer import DEFAULT_BASE, fetch, parse_manifest, release_version  # noqa: E402

TARGETS = {
    (platform, architecture, python)
    for platform, architecture in (
        ("darwin", "arm64"),
        ("darwin", "x86_64"),
        ("linux", "arm64"),
        ("linux", "x86_64"),
        ("win32", "x86_64"),
    )
    for python in ("3.11", "3.12", "3.13")
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_copy(source, destination):
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
        path = Path(temporary.name)
    try:
        shutil.copyfile(source, path)
        path.chmod(0o644)
        os.replace(path, destination)
    finally:
        path.unlink(missing_ok=True)


def publish(site, root, base_url=DEFAULT_BASE):
    manifest = parse_manifest((site / "latest/manifest.json").read_bytes(), base_url)
    version = manifest["version"]
    artifacts = manifest["artifacts"]
    targets = {(a["platform"], a["architecture"], a["python"]) for a in artifacts}
    if targets != TARGETS or len(artifacts) != len(TARGETS):
        raise ValueError("deployment requires all 15 unique platform/Python targets")
    source = site / "releases" / version
    names = {"manifest.json", "SHA256SUMS", "install.sh", "install.ps1"}
    for artifact in artifacts:
        name = artifact["filename"]
        if artifact["url"] != f"{base_url}/releases/{version}/{name}":
            raise ValueError("artifact URL does not match its version directory")
        if digest(source / name) != artifact["sha256"]:
            raise ValueError("local archive checksum mismatch")
        names.add(name)
    for name in ("manifest.json", "SHA256SUMS"):
        if (source / name).read_bytes() != (site / "latest" / name).read_bytes():
            raise ValueError("release and latest metadata differ")
    sums = "".join(f"{a['sha256']}  {a['filename']}\n" for a in artifacts)
    if (source / "SHA256SUMS").read_text() != sums:
        raise ValueError("checksum list differs from manifest")
    for name in ("install.sh", "install.ps1"):
        if (source / name).read_bytes() != (site / name).read_bytes():
            raise ValueError("release and root bootstrap differ")
    if {p.name for p in source.iterdir()} != names:
        raise ValueError("unexpected release files")
    if root.is_symlink() or (root / "releases").is_symlink() or (root / "latest").is_symlink():
        raise ValueError("deployment directories must not be symlinks")
    current = root / "latest/manifest.json"
    if current.exists():
        old_version = json.loads(current.read_bytes())["version"]
        if release_version(version) < release_version(old_version):
            raise ValueError("deployment would downgrade latest")
    root.mkdir(parents=True, exist_ok=True)
    releases = root / "releases"
    releases.mkdir(exist_ok=True)
    destination = releases / version
    if destination.exists():
        if destination.is_symlink() or {p.name for p in destination.iterdir()} != names:
            raise ValueError("published version directory differs")
        if any(
            (destination / n).is_symlink() or digest(destination / n) != digest(source / n)
            for n in names
        ):
            raise ValueError("refusing to replace immutable published version")
    else:
        with tempfile.TemporaryDirectory(prefix=".clef-use-deploy-", dir=root.parent) as staging:
            prepared = Path(staging) / version
            prepared.mkdir(mode=0o755)
            for name in names:
                shutil.copyfile(source / name, prepared / name)
                (prepared / name).chmod(0o644)
            os.replace(prepared, destination)
    # HTTPS must serve every complete archive before the atomic manifest switch.
    for artifact in artifacts:
        if hashlib.sha256(fetch(artifact["url"])).hexdigest() != artifact["sha256"]:
            raise ValueError("public archive checksum mismatch; latest preserved")
    latest = root / "latest"
    latest.mkdir(exist_ok=True)
    for name in ("install.sh", "install.ps1"):
        atomic_copy(site / name, root / name)
    atomic_copy(site / "latest/SHA256SUMS", latest / "SHA256SUMS")
    atomic_copy(site / "latest/manifest.json", current)
    return {"status": "DEPLOYED", "version": version, "targets": len(artifacts)}


def main():
    import fcntl

    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    parser.add_argument("--root", type=Path, default=Path.home() / "share/clef-use")
    args = parser.parse_args()
    with (args.root.parent / ".clef-use-deploy.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        print(json.dumps(publish(args.site, args.root)))


if __name__ == "__main__":
    main()
