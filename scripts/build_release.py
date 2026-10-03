from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import zipfile
from pathlib import Path

from packaging.utils import parse_wheel_filename

ROOT = Path(__file__).resolve().parents[1]


def build_release(output, base_url, wheelhouse=None):
    version = __import__("tomllib").loads((ROOT / "pyproject.toml").read_text())["project"][
        "version"
    ]
    subprocess.run([sys.executable, str(ROOT / "scripts/build_installer.py")], check=True)
    if wheelhouse is None:
        wheelhouse = ROOT / "dist/wheelhouse"
        wheelhouse.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-build-isolation",
                "--require-hashes",
                "-r",
                str(ROOT / "requirements/runtime.txt"),
                "--wheel-dir",
                str(wheelhouse),
            ],
            check=True,
        )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            str(ROOT),
            "--outdir",
            str(wheelhouse),
        ],
        check=True,
    )
    wheels = sorted(wheelhouse.glob("*.whl"))
    requirements, seen = [], set()
    for wheel in wheels:
        name, package_version, _, _ = parse_wheel_filename(wheel.name)
        if name in seen:
            raise ValueError("wheelhouse must contain one wheel per distribution")
        seen.add(name)
        requirements.append(
            f"{name}=={package_version} --hash=sha256:"
            f"{hashlib.sha256(wheel.read_bytes()).hexdigest()}"
        )
    machine = {"aarch64": "arm64", "amd64": "x86_64"}.get(
        platform.machine().lower(), platform.machine().lower()
    )
    python = f"{sys.version_info.major}.{sys.version_info.minor}"
    filename = f"clef-use-{version}-{sys.platform}-{machine}-py{python.replace('.', '')}.zip"
    release = output / "releases" / version
    release.mkdir(parents=True, exist_ok=True)
    archive = release / filename
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as payload:
        payload.writestr("requirements.txt", "\n".join(requirements) + "\n")
        for wheel in wheels:
            payload.write(wheel, "wheels/" + wheel.name)
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            if (ROOT / name).exists():
                payload.write(ROOT / name, name)
    manifest = {
        "schema_version": 1,
        "version": version,
        "minimum_python": "3.11",
        "maximum_python_exclusive": "3.14",
        "artifacts": [
            {
                "filename": filename,
                "platform": sys.platform,
                "architecture": machine,
                "python": python,
                "url": f"{base_url.rstrip('/')}/releases/{version}/{filename}",
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            }
        ],
    }
    (release / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    sums = f"{manifest['artifacts'][0]['sha256']}  {filename}\n"
    (release / "SHA256SUMS").write_text(sums)
    latest = output / "latest"
    latest.mkdir(exist_ok=True)
    (latest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (latest / "SHA256SUMS").write_text(sums)
    for name in ("install.sh", "install.ps1"):
        for destination in (output / name, release / name):
            destination.write_bytes((ROOT / name).read_bytes())
            destination.chmod(0o755)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "release-site")
    parser.add_argument("--base-url", default="https://ftp.kotori9.dev/clef-use")
    parser.add_argument("--wheelhouse", type=Path)
    args = parser.parse_args()
    print(json.dumps(build_release(args.output, args.base_url, args.wheelhouse), indent=2))
