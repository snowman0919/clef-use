"""Resolve official backend wheels, then install the exact SHA-256-pinned result."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ALLOWED_HOSTS = {
    "download.pytorch.org",
    "download-r2.pytorch.org",
    "files.pythonhosted.org",
    "repo.amd.com",
}


def report_lock(report):
    lines = []
    for item in report["install"]:
        info = item["download_info"]
        url = info["url"]
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in ALLOWED_HOSTS
            or parsed.username
            or parsed.password
        ):
            raise ValueError("native wheel report contains an unapproved download origin")
        digest = info["archive_info"].get("hashes", {}).get("sha256")
        if not digest or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("native dependency lacks a SHA-256 digest")
        name = item["metadata"]["name"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise ValueError("invalid native package name")
        lines.append(f"{name} @ {url.split('#')[0]} --hash=sha256:{digest}")
    if not lines:
        raise ValueError("native resolution produced no packages")
    return "\n".join(lines) + "\n"


def install_native(python, profile, env, common_lock, quantizer_only=False, rocm_arch=None):
    with tempfile.TemporaryDirectory(prefix="native-lock-", dir=python.parent.parent) as temporary:
        root = Path(temporary)
        constraints = root / "constraints.txt"
        specs = []
        for line in common_lock.read_text().splitlines():
            if re.match(r"^[a-zA-Z0-9_-]+==", line) and not line.startswith(
                ("torch==", "torchvision==", "triton==", "cuda-", "nvidia-", "intel-")
            ):
                specs.append(line.rstrip(" \\"))
        constraints.write_text("\n".join(specs) + "\n")
        report = root / "report.json"
        index = (
            "https://pypi.org/simple"
            if quantizer_only
            else (profile.index or "https://pypi.org/simple")
        )
        suffix = {"cuda": "cu130", "rocm": "rocm7.2", "xpu": "xpu", "cpu": "cpu"}
        build = "" if profile.system == "macos" else "+" + suffix[profile.backend]
        if profile.name == "windows-rocm":
            build = "+rocm7.14.1"
        if profile.name == "windows-rocm" and not quantizer_only:
            if not rocm_arch or not re.fullmatch(r"gfx[0-9a-f]+", rocm_arch):
                raise ValueError("Windows ROCm requires a detected or explicit --rocm-arch")
            env = dict(env, ROCM_SDK_TARGET_FAMILY=rocm_arch)
        packages = (
            ["bitsandbytes==0.50.2"]
            if quantizer_only
            else [f"torch==2.11.0{build}", f"torchvision==0.26.0{build}"]
        )
        if profile.name == "windows-rocm" and not quantizer_only:
            packages = [
                f"torch[device-{rocm_arch}]==2.11.0{build}",
                f"torchvision[device-{rocm_arch}]==0.26.0{build}",
                f"rocm[device-{rocm_arch}]==7.14.1",
            ]
        command = [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--dry-run",
            "--ignore-installed",
            "--only-binary=:all:",
            "--index-url",
            index,
            "--report",
            str(report),
            "-c",
            str(constraints),
            *packages,
        ]
        if index != "https://pypi.org/simple":
            command.extend(["--extra-index-url", "https://pypi.org/simple"])
        if quantizer_only:
            command.append("--no-deps")
        if profile.name == "windows-rocm" and not quantizer_only:
            command.extend(["--no-binary=rocm", "--no-build-isolation"])
        resolved = subprocess.run(command, env=env, capture_output=True, text=True)
        if resolved.returncode:
            raise RuntimeError(
                f"{profile.name} wheel resolution failed; "
                "Python/architecture/driver support is required"
            )
        data = json.loads(report.read_text())
        lock = root / "native.txt"
        lock.write_text(report_lock(data))
        command = [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--require-hashes",
            "--no-deps",
            "--only-binary=:all:",
            "-r",
            str(lock),
        ]
        if profile.name == "windows-rocm" and not quantizer_only:
            command.extend(["--no-binary=rocm", "--no-build-isolation"])
        installed = subprocess.run(command, env=env, capture_output=True, text=True)
        if installed.returncode:
            raise RuntimeError(f"{profile.name} hashed native installation failed")
        stem = "quantizer" if quantizer_only else "native"
        (python.parent.parent / f"clef-use-{stem}-lock.txt").write_text(lock.read_text())
        (python.parent.parent / f"clef-use-{stem}-report.json").write_text(
            json.dumps(data, indent=2) + "\n"
        )
