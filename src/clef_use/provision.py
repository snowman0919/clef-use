from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import tomlkit

from .backends import JsonWorker
from .config import config_path
from .harness import atomic_write
from .models import OMNI_SOURCE_REVISION, download, inventory


def prepare(config, python="python3.11"):
    executable = shutil.which(python)
    if not executable:
        raise RuntimeError(
            "ML preparation requires an installed Python 3.11; pass --python /path/to/python"
        )
    check = subprocess.run(
        [executable, "-c", "import sys;raise SystemExit(sys.version_info[:2] != (3,11))"],
        capture_output=True,
    )
    if check.returncode:
        raise RuntimeError("pinned V0 ML dependency environments require Python 3.11")
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
        lock = Path(__file__).parent / "assets" / f"ml-{kind}.txt"
        result = subprocess.run(
            [
                str(path),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--only-binary=:all:",
                "--require-hashes",
                "-r",
                str(lock),
            ],
            env=child_env,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise RuntimeError(
                f"{kind} pinned ML installation failed; "
                "unsupported wheel/platform or dependency boundary"
            )
    source = config.omni_source or parent / "upstream/OmniParser"
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
    for repo in [
        config.decision_model,
        "microsoft/OmniParser-v2.0",
        "microsoft/Florence-2-base",
        "microsoft/Florence-2-base-ft",
    ]:
        download(config.model_dir, repo)
    updated = config.model_copy(
        update={"clef_python": paths["clef"], "omni_python": paths["omni"], "omni_source": source}
    )
    path = config_path()
    data = tomlkit.parse(path.read_text() if path.exists() else "")
    for field in ("model_dir", "clef_python", "omni_python", "omni_source"):
        data[field] = str(getattr(updated, field))
    atomic_write(path, tomlkit.dumps(data))
    # The pinned OmniParser utility initializes OCR readers at import time.
    worker = JsonWorker(
        updated.omni_python, "omni", updated.model_copy(update={"backend_timeout": 600})
    )
    try:
        worker._start()
    finally:
        worker.close()
    return {
        "status": "PREPARED",
        "models": inventory(config.model_dir, config.decision_model),
        "omni_source_revision": observed,
        "config": str(path),
    }
