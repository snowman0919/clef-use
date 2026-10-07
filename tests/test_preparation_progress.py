import json
import threading

import pytest

from clef_use import cli, provision
from clef_use.preparation_progress import PreparationProgress


def test_heartbeat_is_visible_during_blocking_work_and_stops_on_failure():
    messages = []
    pulse = threading.Event()

    def emit(message):
        messages.append(message)
        if "Still working:" in message:
            pulse.set()

    report = PreparationProgress(emit, interval=0.01)
    with pytest.raises(RuntimeError, match="failed dependency"):
        with report.stage("Installing dependencies"):
            report.message("Installing torch backend")
            assert pulse.wait(2), "no live progress while work was blocked"
            raise RuntimeError("failed dependency")
    assert messages[-1].startswith("[1/9] Failed or interrupted:")
    assert "Installing torch backend" in messages[-1]
    assert any("elapsed" in m for m in messages)


@pytest.mark.parametrize("json_mode", [False, True])
def test_cli_prepare_reports_stages_without_corrupting_json(json_mode, monkeypatch, capsys):
    def prepare(*args, progress=None):
        if json_mode:
            assert progress is None
        else:
            assert progress is not None
            progress("[1/9] Selecting profiles")
        return {"status": "PREPARED"}

    monkeypatch.setattr(provision, "prepare", prepare)
    monkeypatch.setattr(cli, "load_config", lambda: None)
    assert cli.main(["models", "prepare", *(["--json"] if json_mode else [])]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"status": "PREPARED"}
    assert bool(captured.err) != json_mode


def test_canonical_prepare_reports_all_stages_and_saves_after_both_workers(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from clef_use.config import Config

    config_file = tmp_path / "config.toml"
    config_file.write_text("# keep existing settings\nmax_steps = 12\n")
    monkeypatch.setenv("CLEF_USE_CONFIG", str(config_file))
    monkeypatch.setattr("clef_use.deployment_profiles.host_system", lambda: "linux")
    config = Config(model_dir=tmp_path / "models", ml_profile="linux-cpu", device="cpu")
    monkeypatch.setattr(provision, "select_python", lambda *_: "python")
    monkeypatch.setattr("clef_use.installer.windows_user_access", lambda _path: None)
    monkeypatch.setattr(provision, "install_lock", lambda *_a, **_kw: None)
    monkeypatch.setattr("clef_use.native_dependencies.install_native", lambda *_a, **_kw: None)
    monkeypatch.setattr("clef_use.doctor.ml_environment_probe", lambda *_: {"ready": True})

    def run(command, **kwargs):
        if command[1:3] == ["-m", "venv"]:
            folder = tmp_path / command[-1]
            folder.mkdir()
            (folder / "pyvenv.cfg").touch()
        return SimpleNamespace(returncode=0, stdout=provision.OMNI_SOURCE_REVISION)

    monkeypatch.setattr(provision.subprocess, "run", run)
    cache = set()
    monkeypatch.setattr(
        provision,
        "inventory",
        lambda *_: [
            {"model": "cached-model", "available": True},
            {"model": "missing-model", "available": "missing-model" in cache},
        ],
    )
    monkeypatch.setattr(provision, "download", lambda _root, model: cache.add(model))
    messages = []
    initialized = []

    class Worker:
        def __init__(self, _python, kind, _config):
            self.kind = kind

        def _start(self):
            assert f"Loading {self.kind} model" in messages[-1]
            assert config_file.read_text() == "# keep existing settings\nmax_steps = 12\n"
            initialized.append(self.kind)
            return {"ready": True}

        def close(self):
            pass

    monkeypatch.setattr(provision, "JsonWorker", Worker)
    result = provision.prepare(config, progress=messages.append)
    assert result["status"] == "PREPARED"
    assert initialized == ["clef", "omni"]
    assert cache == {"missing-model"}
    assert messages[-1].startswith("[9/9] Done")
    assert "max_steps = 12" in config_file.read_text()
    assert any("already cached; skipping" in m for m in messages)
    assert any("Model 2/2: downloading missing-model" in m for m in messages)
