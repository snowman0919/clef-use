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
