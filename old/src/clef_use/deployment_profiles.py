"""OS/backend deployment contracts shared by installation and isolated workers."""

from __future__ import annotations

import os
import platform
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

Backend = Literal["cuda", "rocm", "xpu", "mps", "cpu"]
ProfileName = Literal[
    "auto",
    "default",
    "macos-mps",
    "macos-cpu",
    "linux-cuda",
    "linux-rocm",
    "linux-xpu",
    "linux-cpu",
    "windows-cuda",
    "windows-rocm",
    "windows-xpu",
    "windows-cpu",
]


@dataclass(frozen=True)
class Profile:
    name: str
    system: str
    backend: str
    index: str | None
    python_versions: tuple[str, ...] = ("3.11", "3.12")


INDEX_SUFFIXES = {"cuda": "cu130", "rocm": "rocm7.2", "xpu": "xpu", "cpu": "cpu"}

PROFILES = {
    f"{system}-{backend}": Profile(
        f"{system}-{backend}",
        system,
        backend,
        None
        if system == "macos"
        else "https://repo.amd.com/rocm/whl-multi-arch/"
        if system == "windows" and backend == "rocm"
        else f"https://download.pytorch.org/whl/{INDEX_SUFFIXES[backend]}",
        ("3.12",) if system == "windows" and backend == "rocm" else ("3.11", "3.12"),
    )
    for system, backends in {
        "macos": ("mps", "cpu"),
        "linux": ("cuda", "rocm", "xpu", "cpu"),
        "windows": ("cuda", "rocm", "xpu", "cpu"),
    }.items()
    for backend in backends
}


def host_system():
    names = {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}
    try:
        return names[platform.system()]
    except KeyError as exc:
        raise RuntimeError("deployment requires macOS, Linux or Windows") from exc


def detect_backend():
    system = host_system()
    if system == "macos":
        return "mps" if platform.machine().lower() in {"arm64", "aarch64"} else "cpu"
    names = []
    if system == "windows":
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode:
            raise RuntimeError("GPU discovery failed; specify --profile explicitly")
        names = result.stdout.lower().splitlines()
        if any("nvidia" in name for name in names):
            return "cuda"
        if any("amd" in name or "radeon" in name for name in names):
            return "rocm"
        if any(
            "intel" in name and any(tag in name for tag in ("arc", "graphics", "gpu"))
            for name in names
        ):
            return "xpu"
    else:
        vendors = set()
        for path in Path("/sys/class/drm").glob("card[0-9]*/device/vendor"):
            try:
                vendors.add(path.read_text().strip().lower())
            except OSError:
                continue
        for vendor, backend in (("0x10de", "cuda"), ("0x1002", "rocm"), ("0x8086", "xpu")):
            if vendor in vendors:
                return backend
        try:
            result = subprocess.run(
                ["nvidia-smi", "-L"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and "GPU" in result.stdout:
                return "cuda"
        except (OSError, subprocess.TimeoutExpired):
            pass
    return "cpu"


def resolve_profile(requested="auto", device="auto"):
    system = host_system()
    if requested == "default":
        requested = "auto"
        if device == "auto":
            device = "mps" if system == "macos" and platform.machine() == "arm64" else "cpu"
    if requested == "auto":
        requested = f"{system}-{detect_backend() if device == 'auto' else device}"
    if requested not in PROFILES:
        raise ValueError(f"unsupported deployment profile {requested}")
    selected = PROFILES[requested]
    if selected.system != system:
        raise ValueError(f"{selected.name} requires {selected.system}; current OS is {system}")
    if selected.backend == "mps" and platform.machine().lower() not in {"arm64", "aarch64"}:
        raise ValueError("MPS requires Apple Silicon")
    if device != "auto" and device != selected.backend:
        # 0.1.8 persisted the HIP torch device name rather than its backend.
        if not (requested == "windows-rocm" and device == "cuda"):
            raise ValueError(f"device {device} conflicts with profile {selected.name}")
    return selected


def profile_catalog():
    return [
        dict(asdict(profile), status="TARGET; hardware and full model initialization required")
        for profile in PROFILES.values()
    ]


def select_backend(torch, requested="auto"):
    available = []
    if torch.cuda.is_available():
        available.append("rocm" if getattr(torch.version, "hip", None) else "cuda")
    xpu = getattr(torch, "xpu", None)
    if xpu is not None and xpu.is_available():
        available.append("xpu")
    mps = getattr(getattr(torch, "backends", None), "mps", None)
    if mps is not None and mps.is_available():
        available.append("mps")
    available.append("cpu")
    if requested == "auto":
        return available[0]
    if requested not in available:
        raise RuntimeError(f"requested {requested} backend unavailable; observed {available}")
    return requested


def torch_device(backend):
    return "cuda" if backend == "rocm" else backend


def resolve_rocm_arch(config, requested=None):
    arch = requested or config.rocm_arch or os.environ.get("ROCM_SDK_TARGET_FAMILY")
    if not arch:
        command = (
            [
                str(config.clef_python),
                "-c",
                "import torch;print(torch.cuda.get_device_properties(0).gcnArchName)"
                " if torch.version.hip and torch.cuda.is_available() else print('')",
            ]
            if config.clef_python
            else ["offload-arch"]
        )
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                arch = result.stdout.strip().splitlines()[0].split(":")[0]
        except (OSError, subprocess.TimeoutExpired):
            pass
    if not arch or not re.fullmatch(r"gfx[0-9a-f]+", arch):
        raise ValueError("Windows ROCm ISA unavailable; specify --rocm-arch for your supported GPU")
    return arch
