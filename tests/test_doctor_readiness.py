import json
import subprocess
import venv
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from clef_use import doctor as diagnostics
from clef_use import ml_probe
from clef_use.config import Config


@pytest.mark.parametrize("missing", ["clef", "omni", "source"])
def test_doctor_refuses_ready_with_cached_models_but_missing_ml_prerequisite(monkeypatch, missing):
    monkeypatch.setattr(diagnostics, "load_config", Config)
    monkeypatch.setattr(diagnostics.sys, "platform", "linux")
    monkeypatch.setattr(
        diagnostics,
        "mac_permissions",
        lambda: {
            "screen_capture": True,
            "input_injection": True,
        },
    )
    monkeypatch.setattr(diagnostics, "inventory", lambda *_: [{"available": True}])
    monkeypatch.setattr(
        diagnostics.subprocess,
        "run",
        lambda *_a, **_k: SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"cpu": True}),
        ),
    )
    frame = Image.new("RGB", (2, 2), "white")
    frame.putpixel((0, 0), (0, 0, 0))
    monkeypatch.setattr(
        "clef_use.backends.DesktopCapture",
        lambda: SimpleNamespace(
            capture=lambda: SimpleNamespace(image=frame, logical_size=(2, 2)),
        ),
    )

    async def tools():
        return [
            "computer_run",
            "computer_continue",
            "computer_observe",
            "computer_status",
            "computer_abort",
        ]

    monkeypatch.setattr(diagnostics, "mcp_probe", tools)
    monkeypatch.setattr(
        diagnostics,
        "ml_environment_probe",
        lambda _p, kind, _d: {
            "status": "ERROR" if kind == missing else "OBSERVED",
            "ready": kind != missing,
        },
    )
    monkeypatch.setattr(
        diagnostics,
        "omni_source_probe",
        lambda _: {
            "status": "MISSING" if missing == "source" else "OBSERVED",
            "ready": missing != "source",
        },
    )
    report = diagnostics.doctor()
    assert report["capture"]["status"] == "OBSERVED"
    assert report["ready"] is False
    monkeypatch.setattr(diagnostics, "ml_environment_probe", lambda *_: {"ready": True})
    monkeypatch.setattr(diagnostics, "omni_source_probe", lambda _: {"ready": True})
    assert diagnostics.doctor()["ready"] is True


def test_explicit_cuda_does_not_become_cpu_ready(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(diagnostics.__file__).parent))
    module = SimpleNamespace(
        __version__="probe-fixture",
        AutoProcessor=object,
        Qwen3_5ForConditionalGeneration=object,
        cuda=SimpleNamespace(is_available=lambda: False),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False)),
    )
    monkeypatch.setattr(ml_probe.importlib, "import_module", lambda _: module)
    result = ml_probe.probe("clef", "cuda")
    assert result["errors"] == {}
    assert result["ready"] is False
    assert result["device_operation"] == "ERROR"
    assert "device" not in result


def test_isolated_probe_rejects_missing_runtime_dependency(tmp_path):
    from clef_use.installer import environment_binary

    environment = tmp_path / "empty-ml-env"
    venv.EnvBuilder(with_pip=False).create(environment)
    report = diagnostics.ml_environment_probe(
        environment_binary(environment, "python"), "clef", "cpu"
    )
    assert report["status"] == "ERROR"
    assert report["ready"] is False
    assert report["errors"]["torch"] == "ModuleNotFoundError"


def test_source_pin_and_tracked_changes_are_checked_with_git(tmp_path, monkeypatch):
    source = tmp_path / "omni"
    (source / "util").mkdir(parents=True)
    util = source / "util/utils.py"
    util.write_text("original = True\n")

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(source), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init")
    git("add", "util/utils.py")
    git("-c", "user.name=Probe", "-c", "user.email=probe@example.invalid", "commit", "-m", "pin")
    assert diagnostics.omni_source_probe(source)["status"] == "REVISION_MISMATCH"
    monkeypatch.setattr(diagnostics, "OMNI_SOURCE_REVISION", git("rev-parse", "HEAD"))
    assert diagnostics.omni_source_probe(source)["ready"] is True
    util.write_text("original = False\n")
    assert diagnostics.omni_source_probe(source)["status"] == "MODIFIED"
    assert diagnostics.omni_source_probe(source)["ready"] is False


def test_cached_weights_do_not_hide_missing_caption_code_or_joint_head_config(tmp_path):
    from clef_use.models import inventory

    missing = inventory(tmp_path, "Cloudflare/clef-flash")
    for model in missing:
        for name in model["missing"]:
            path = Path(model["path"]) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"weight_map": {}}' if name.endswith("index.json") else "fixture")
    assert all(model["available"] for model in inventory(tmp_path, "Cloudflare/clef-flash"))
    for model in missing:
        name = (
            "joint_head_config.json"
            if model["model"] == "Cloudflare/clef-flash"
            else (
                "modeling_florence2.py"
                if model["model"] == "microsoft/Florence-2-base-ft"
                else None
            )
        )
        if name:
            (Path(model["path"]) / name).unlink()
    observed = {m["model"]: m for m in inventory(tmp_path, "Cloudflare/clef-flash")}
    assert observed["Cloudflare/clef-flash"]["missing"] == ["joint_head_config.json"]
    assert observed["microsoft/Florence-2-base-ft"]["missing"] == ["modeling_florence2.py"]
