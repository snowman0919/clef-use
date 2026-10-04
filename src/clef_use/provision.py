from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import tomlkit

from .backends import JsonWorker
from .config import config_path
from .harness import atomic_write
from .models import OMNI_SOURCE_REVISION, download, inventory


def select_profile(config, requested):
    if requested != "auto":
        if requested == "windows-rocm" and sys.platform != "win32":
            raise RuntimeError("Windows ROCm profile requires native Windows")
        return requested
    if config.ml_profile != "auto":
        return select_profile(config, config.ml_profile)
    if sys.platform == "win32" and config.device in {"auto", "cuda"}:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "ConvertTo-Json -Compress -InputObject @(Get-CimInstance Win32_VideoController | "
                "Select-Object -ExpandProperty Name)",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode:
            raise RuntimeError("Windows GPU discovery failed; choose --profile explicitly")
        names = json.loads(result.stdout)
        if any("890m" in name.lower() for name in names):
            return "windows-rocm"
    return "default"


def select_python(python, profile):
    required = (3, 12) if profile == "windows-rocm" else None
    executable = shutil.which(python) if python else None
    if python is None:
        if sys.version_info[:2] in ((3, 11), (3, 12)) and (
            required is None or sys.version_info[:2] == required
        ):
            executable = sys.executable
        else:
            executable = shutil.which("python3.12" if required else "python3.11")
        if not executable and sys.platform == "win32" and shutil.which("py"):
            result = subprocess.run(
                ["py", "-3.12", "-c", "import sys;print(sys.executable)"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            executable = result.stdout.strip() if result.returncode == 0 else None
    if not executable:
        raise RuntimeError(
            "Install Python 3.12 for Windows ROCm or 3.11/3.12 for default ML; "
            "pass --python /path/to/python"
        )
    check = subprocess.run(
        [executable, "-c", "import sys,json; print(json.dumps(list(sys.version_info[:2])))"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    version = tuple(json.loads(check.stdout)) if check.returncode == 0 else ()
    if (required and version != required) or (not required and version not in ((3, 11), (3, 12))):
        raise RuntimeError("Pinned Windows ROCm requires Python 3.12; default ML uses 3.11/3.12")
    return executable


def install_lock(path, lock, env, index=None, rocm=False, no_deps=False):
    command = [
        str(path),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--require-hashes",
        "--only-binary=:all:",
        "-r",
        str(lock),
    ]
    if index:
        command.extend(["--index-url", index])
    if index or no_deps:
        command.append("--no-deps")
    if rocm:
        command.extend(["--no-binary=rocm", "--no-build-isolation"])
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(
            f"Pinned ML installation failed ({lock.name}); "
            "unsupported wheel/platform or dependency boundary"
        )


def common_windows_requirements(text):
    lines, skip = [], False
    for line in text.splitlines(keepends=True):
        if line.strip() and not line[0].isspace() and not line.startswith("#"):
            skip = line.startswith(("torch==", "torchvision=="))
        if not skip:
            lines.append(line)
    return "".join(lines)


def prepare(config, python=None, profile="auto", quantization=None):
    profile = select_profile(config, profile)
    executable = select_python(python, profile)
    if profile == "windows-rocm" and config.device not in {"auto", "cuda"}:
        raise ValueError("Windows ROCm requires device auto/cuda")
    quantization = quantization or ("4bit" if profile == "windows-rocm" else config.quantization)
    if quantization == "4bit" and profile != "windows-rocm":
        raise ValueError("automatic NF4 dependency installation is currently Windows ROCm only")
    source = config.omni_source or config.model_dir.parent / "upstream/OmniParser"
    if source.exists():
        from .doctor import omni_source_probe

        if not omni_source_probe(source)["ready"]:
            raise ValueError("existing OmniParser checkout is modified or has the wrong revision")
    parent = config.model_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    from .installer import environment_binary

    paths = {
        "clef": config.clef_python or environment_binary(parent / "clef-env", "python"),
        "omni": config.omni_python or environment_binary(parent / "omni-env", "python"),
    }
    child_env = dict(os.environ, PIP_CACHE_DIR=str(parent / "pip-cache"))
    for kind, path in paths.items():
        environment = path.parent.parent
        if environment.exists() and not (environment / "pyvenv.cfg").exists():
            raise ValueError("refusing to modify a directory that is not a venv")
        if not environment.exists():
            subprocess.run([executable, "-m", "venv", str(environment)], check=True)
        pip_check = subprocess.run([str(path), "-m", "pip", "--version"], capture_output=True)
        if pip_check.returncode:
            subprocess.run([str(path), "-m", "ensurepip"], check=True, capture_output=True)
        assets = Path(__file__).parent / "assets"
        lock = assets / f"ml-{kind}.txt"
        if profile == "windows-rocm":
            with tempfile.TemporaryDirectory(dir=environment) as temporary:
                common = Path(temporary) / lock.name
                common.write_text(common_windows_requirements(lock.read_text()))
                install_lock(path, common, child_env, no_deps=True)
        else:
            install_lock(path, lock, child_env)
        if profile == "windows-rocm":
            install_lock(
                path,
                assets / ("ml-windows-rocm.txt" if kind == "clef" else "ml-windows-torch-cpu.txt"),
                child_env,
                "https://repo.amd.com/rocm/whl-multi-arch/"
                if kind == "clef"
                else "https://download.pytorch.org/whl/cpu",
                rocm=kind == "clef",
            )
        if kind == "clef" and quantization == "4bit":
            install_lock(path, assets / "ml-windows-nf4.txt", child_env, no_deps=True)
    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--sparse",
                "https://github.com/microsoft/OmniParser.git",
                str(source),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(source), "checkout", "--detach", OMNI_SOURCE_REVISION],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(source), "sparse-checkout", "set", "util"],
            check=True,
            capture_output=True,
        )
    observed = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    if observed != OMNI_SOURCE_REVISION:
        raise ValueError("existing OmniParser checkout differs from the required revision")
    for model in inventory(config.model_dir, config.decision_model):
        if not model["available"]:
            download(config.model_dir, model["model"])
    updated = config.model_copy(
        update={
            "clef_python": paths["clef"],
            "omni_python": paths["omni"],
            "omni_source": source,
            "ml_profile": profile,
            "quantization": quantization,
            "device": "cuda" if profile == "windows-rocm" else config.device,
            "parser_device": "cpu"
            if profile == "windows-rocm" and config.parser_device == "auto"
            else config.parser_device,
        }
    )
    initialized = {}
    for kind in ("clef", "omni"):
        worker = JsonWorker(paths[kind], kind, updated.model_copy(update={"backend_timeout": 600}))
        try:
            initialized[kind] = worker._start()
        finally:
            worker.close()
    path = config_path()
    data = tomlkit.parse(path.read_text() if path.exists() else "")
    for field in (
        "model_dir",
        "clef_python",
        "omni_python",
        "omni_source",
        "ml_profile",
        "quantization",
        "device",
        "parser_device",
    ):
        data[field] = str(getattr(updated, field))
    atomic_write(path, tomlkit.dumps(data))
    if sys.platform == "win32":
        from .installer import windows_user_access

        windows_user_access(path)
    return {
        "status": "PREPARED",
        "models": inventory(config.model_dir, config.decision_model),
        "omni_source_revision": observed,
        "config": str(path),
        "profile": profile,
        "initialized": initialized,
    }
