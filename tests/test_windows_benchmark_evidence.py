import importlib.util
import json
from pathlib import Path

import pytest


def benchmark_module():
    path = Path(__file__).parents[1] / "scripts/windows_visual_benchmark.py"
    spec = importlib.util.spec_from_file_location("windows_visual_benchmark", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def successful_report():
    row = {"success": True, "wrong_input": 0, "early_advance": 0, "false_completion": 0}
    return {
        "repeats_per_variant": 1,
        "cold": dict(row),
        "runs": [
            {**row, "variant": variant, "actual_cold_workers": False}
            for variant in ("fixed_delay_no_cache", "visual_wait_no_cache", "visual_wait_cache")
        ],
        "no_effect": {
            "status": "NO_PROGRESS",
            "act": 1,
            "wrong_input": 0,
            "early_advance": 0,
            "false_completion": 0,
            "readback": {"stage": 0, "render_pending": False, "input_attempts": [{}]},
        },
    }


def test_acceptance_requires_cold_accuracy_complete_samples_and_negative_trial():
    module = benchmark_module()
    assert module.accepted_report(successful_report())
    for mutate in (
        lambda report: report["cold"].update(success=False),
        lambda report: report["runs"].pop(),
        lambda report: report["runs"][0].update(early_advance=1),
        lambda report: report["runs"][0].update(variant="visual_wait_cache"),
        lambda report: report["runs"][0].update(actual_cold_workers=True),
        lambda report: report.pop("no_effect"),
        lambda report: report["no_effect"].update(status="ERROR"),
        lambda report: report["no_effect"].update(act=2),
        lambda report: report["no_effect"]["readback"].update(stage=2),
        lambda report: report["no_effect"]["readback"]["input_attempts"].append({}),
    ):
        report = successful_report()
        mutate(report)
        assert not module.accepted_report(report)


def test_checkpoint_preserves_last_complete_report_when_replace_fails(tmp_path, monkeypatch):
    module = benchmark_module()
    path = tmp_path / "report.json"
    module.save_report(path, {"status": "RUNNING", "runs": [1]})

    def fail_replace(*args):
        raise OSError("disk unavailable")

    monkeypatch.setattr(module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="disk unavailable"):
        module.save_report(path, {"status": "RUNNING", "runs": [1, 2]})
    assert json.loads(path.read_text()) == {"status": "RUNNING", "runs": [1]}
    assert list(tmp_path.iterdir()) == [path]
