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
from .deployment_profiles import resolve_profile, resolve_rocm_arch
from .harness import atomic_write
from .models import OMNI_SOURCE_REVISION, download, inventory
from .preparation_progress import PreparationProgress


def select_profile(config, requested):
    if requested != "auto":
        return resolve_profile(requested).name
    return resolve_profile(config.ml_profile, config.device).name


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
    result = subprocess.run(command, env=env, capture_output=True)
    if result.returncode:
        raise RuntimeError(
            f"Pinned ML installation failed ({lock.name}); "
            "unsupported wheel/platform or dependency boundary"
        )


def common_ml_requirements(text):
    lines, skip = [], False
    for line in text.splitlines(keepends=True):
        if line.strip() and not line[0].isspace() and not line.startswith("#"):
            skip = line.startswith(
                ("torch==", "torchvision==", "triton==", "cuda-", "nvidia-", "intel-")
            )
        if not skip:
            lines.append(line)
    return "".join(lines)


def prepare(config, python=None, profile="auto", quantization=None, rocm_arch=None, progress=None):
    report = PreparationProgress(progress)
    with report.stage("Selecting profiles, Python and existing source"):
        profile = select_profile(config, profile)
        selected = resolve_profile(profile)
        parser_selected = resolve_profile(
            "auto", "cpu" if config.parser_device == "auto" else config.parser_device
        )
        executable = select_python(
            python, "windows-rocm" if parser_selected.name == "windows-rocm" else profile
        )
        rocm_arch = (
            resolve_rocm_arch(config, rocm_arch)
            if "windows-rocm" in {profile, parser_selected.name}
            else None
        )
        quantization = quantization or (
            "4bit" if profile == "windows-rocm" else config.quantization
        )
        if quantization == "4bit" and selected.backend == "mps":
            raise ValueError(
                "MPS profile currently supports quantization none; MLX remains separate"
            )
        source = config.omni_source or config.model_dir.parent / "upstream/OmniParser"
        if source.exists():
            from .doctor import omni_source_probe

            if not omni_source_probe(source)["ready"]:
                raise ValueError(
                    "existing OmniParser checkout is modified or has the wrong revision"
                )
    parent = config.model_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    report.message(
        f"CLEF: {profile}; OmniParser: {parser_selected.name}; model cache: {config.model_dir}"
    )
    from .installer import environment_binary

    try:
        previous_profile = resolve_profile(config.ml_profile, config.device).name
    except (ValueError, RuntimeError):
        previous_profile = None
    paths = {
        "clef": (config.clef_python if previous_profile == profile else None)
        or environment_binary(parent / f"clef-env-{profile}", "python"),
        "omni": config.omni_python
        or environment_binary(parent / f"omni-env-{parser_selected.name}", "python"),
    }
    child_env = dict(os.environ, PIP_CACHE_DIR=str(parent / "pip-cache"))
    for kind, path in paths.items():
        with report.stage(f"Preparing {kind} inference environment"):
            environment = path.parent.parent
            if environment.exists() and not (environment / "pyvenv.cfg").exists():
                raise ValueError("refusing to modify a directory that is not a venv")
            report.message(f"Creating/checking {kind} Python environment")
            if not environment.exists():
                subprocess.run([executable, "-m", "venv", str(environment)], check=True)
            pip_check = subprocess.run([str(path), "-m", "pip", "--version"], capture_output=True)
            if pip_check.returncode:
                subprocess.run([str(path), "-m", "ensurepip"], check=True, capture_output=True)
            assets = Path(__file__).parent / "assets"
            lock = assets / f"ml-{kind}.txt"
            from .native_dependencies import install_native

            with tempfile.TemporaryDirectory(dir=environment) as temporary:
                common = Path(temporary) / lock.name
                common.write_text(common_ml_requirements(lock.read_text()))
                report.message(f"Installing pinned {kind} common dependencies")
                install_lock(path, common, child_env, no_deps=True)
                report.message(
                    f"Installing {kind} native backend: "
                    f"{(selected if kind == 'clef' else parser_selected).name}"
                )
                install_native(
                    path,
                    selected if kind == "clef" else parser_selected,
                    child_env,
                    lock,
                    rocm_arch=rocm_arch,
                )
            if kind == "clef" and quantization == "4bit":
                report.message("Installing 4-bit quantization dependencies")
                install_native(path, selected, child_env, lock, quantizer_only=True)
    from .doctor import ml_environment_probe

    with report.stage("Checking installed inference dependencies"):
        for kind, path in paths.items():
            backend = selected.backend if kind == "clef" else parser_selected.backend
            precision = quantization if kind == "clef" else "none"
            if not ml_environment_probe(path, kind, backend, precision, rocm_arch)["ready"]:
                raise RuntimeError(f"{kind} backend/dependency probe failed before model download")
    with report.stage("Preparing pinned OmniParser source"):
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
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if observed != OMNI_SOURCE_REVISION:
            raise ValueError("existing OmniParser checkout differs from the required revision")
    with report.stage("Downloading required model snapshots"):
        models = inventory(config.model_dir, config.decision_model)
        for number, model in enumerate(models, 1):
            if model["available"]:
                report.message(
                    f"Model {number}/{len(models)}: {model['model']} already cached; skipping"
                )
            else:
                report.message(f"Model {number}/{len(models)}: downloading {model['model']}")
                download(config.model_dir, model["model"])
    updated = config.model_copy(
        update={
            "clef_python": paths["clef"],
            "omni_python": paths["omni"],
            "omni_source": source,
            "ml_profile": profile,
            "rocm_arch": rocm_arch,
            "quantization": quantization,
            "device": selected.backend,
            "parser_device": parser_selected.backend,
        }
    )
    initialized = {}
    for kind in ("clef", "omni"):
        with report.stage(f"Loading {kind} model and verifying worker initialization"):
            worker = JsonWorker(
                paths[kind], kind, updated.model_copy(update={"backend_timeout": 600})
            )
            try:
                initialized[kind] = worker._start()
            finally:
                worker.close()
    with report.stage("Saving verified model configuration"):
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
        if rocm_arch:
            data["rocm_arch"] = rocm_arch
        else:
            data.pop("rocm_arch", None)
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
        "parser_profile": parser_selected.name,
        "initialized": initialized,
    }
