import importlib.util
from pathlib import Path

import pytest

from clef_use.backends import JsonWorker
from clef_use.config import Config


def test_cpu_readiness_cannot_be_accepted_as_rocm_and_child_is_reaped(tmp_path, monkeypatch):
    path = Path(__file__).parents[1] / "scripts/windows_rocm_worker.py"
    spec = importlib.util.spec_from_file_location("windows_rocm_worker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    script = tmp_path / "cpu_worker.py"
    script.write_text(
        "import json,sys\n"
        "sys.stdin.readline()\n"
        "print(json.dumps({'ready':True,'device':'cpu'}),flush=True)\n"
        "sys.stdin.read()\n"
    )
    processes = []
    popen = module.subprocess.Popen

    def launch(*args, **kwargs):
        process = popen(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(module.subprocess, "Popen", launch)
    worker = JsonWorker(None, "clef", Config(model_dir=tmp_path, backend_timeout=5))
    with pytest.raises(RuntimeError, match="did not initialize its GPU"):
        module.start_worker(worker, script, tmp_path / "worker.log")
    assert len(processes) == 1 and processes[0].poll() is not None
    assert worker.process is None


def test_worker_uses_installed_package_without_adding_its_dependencies_to_ml_path(tmp_path):
    import json
    import os
    import subprocess
    import sys

    worker_module = tmp_path / "model_worker.py"
    worker_module.write_text(
        "import json\nclass ClefWorker: pass\n"
        "def main(): print(json.dumps({'selected_worker': __file__}))\n"
    )
    script = Path(__file__).parents[1] / "scripts/windows_rocm_worker.py"
    child_env = dict(os.environ, CLEF_USE_DIAGNOSTIC_PACKAGE_ROOT=str(tmp_path))
    child_env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, str(script), "clef"],
        env=child_env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    assert Path(json.loads(result.stdout)["selected_worker"]) == worker_module
