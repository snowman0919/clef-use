import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def test_help_can_select_checkout_with_an_older_incompatible_runtime(tmp_path):
    package = tmp_path / "clef_use"
    package.mkdir()
    (package / "__init__.py").write_text("raise ImportError('older runtime has no scorer')\n")
    runner = Path(__file__).resolve().parents[1] / "scripts/native_reaction_benchmark.py"
    result = subprocess.run(
        [sys.executable, str(runner), "--checkout", str(tmp_path), "--help"],
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "--checkout" in result.stdout


def test_summary_keeps_failures_and_critical_errors_in_goodput_denominator():
    path = Path(__file__).resolve().parents[1] / "scripts/native_reaction_benchmark.py"
    spec = importlib.util.spec_from_file_location("native_reaction_benchmark", path)
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    rows = [
        {"verified": True, "event_latency_ms": value, "critical_errors": []}
        for value in (10, 40, 100, 100.1, 300)
    ] + [
        {"verified": False, "event_latency_ms": None, "critical_errors": []},
        {"verified": False, "event_latency_ms": None, "critical_errors": []},
        {"verified": False, "event_latency_ms": 20, "critical_errors": ["wrong_widget_state"]},
    ]
    summary = benchmark.summarize(rows, elapsed_seconds=2, target_ms=100)
    assert summary["opportunities"] == 8
    assert summary["correct"] == 5 and summary["accuracy"] == 0.625
    assert summary["fast_correct"] == 3 and summary["goodput_100"] == 0.375
    assert summary["fast_coverage"] is None
    assert summary["misses"] == 5 and summary["critical_errors"] == 1
    assert summary["goodput_per_second"] == 2.5
    assert summary["correct_event_latency_ms"] == {"p50": 100, "p95": 300, "p99": 300}


def test_summary_does_not_present_only_failed_opportunities_as_zero_latency_success():
    path = Path(__file__).resolve().parents[1] / "scripts/native_reaction_benchmark.py"
    spec = importlib.util.spec_from_file_location("native_reaction_benchmark", path)
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    result = benchmark.summarize(
        [{"verified": False, "event_latency_ms": None, "critical_errors": ["worker_exit"]}],
        elapsed_seconds=3,
        target_ms=100,
    )
    assert result["correct_event_latency_ms"] == {"p50": None, "p95": None, "p99": None}
    assert result["accuracy"] == 0 and result["goodput_100"] == 0
    assert result["fast_coverage"] is None
    assert result["misses"] == 1 and result["goodput_per_second"] == 0


def test_fast_path_eligibility_is_distinct_from_correct_actions_within_deadline():
    path = Path(__file__).resolve().parents[1] / "scripts/native_reaction_benchmark.py"
    spec = importlib.util.spec_from_file_location("native_reaction_benchmark", path)
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    result = benchmark.summarize(
        [
            {
                "verified": True,
                "event_latency_ms": 150,
                "critical_errors": [],
                "state_changed_ns": 1_000_000,
                "eligibility_observed_ns": 2_000_000,
                "policy_decision_ns": 2_500_000,
                "attempted": True,
                "input_dispatch_ns": 3_000_000,
                "eligibility_source": "native focused-window/key-state readback",
                "received_ns": 151_000_000,
                "fast_eligible": True,
            },
            {
                "verified": True,
                "event_latency_ms": 20,
                "critical_errors": [],
                "state_changed_ns": 1_000_000,
                "eligibility_observed_ns": 2_000_000,
                "policy_decision_ns": 2_500_000,
                "attempted": True,
                "input_dispatch_ns": 3_000_000,
                "eligibility_source": "native focused-window/key-state readback",
                "received_ns": 21_000_000,
                "fast_eligible": False,
            },
            {
                "verified": False,
                "event_latency_ms": None,
                "critical_errors": [],
                "state_changed_ns": 1_000_000,
                "eligibility_observed_ns": 2_000_000,
                "policy_decision_ns": 2_500_000,
                "attempted": True,
                "input_dispatch_ns": 3_000_000,
                "eligibility_source": "native focused-window/key-state readback",
                "received_ns": None,
                "fast_eligible": True,
            },
        ],
        elapsed_seconds=1,
        target_ms=100,
    )
    assert result["goodput_100"] == 1 / 3
    assert result["fast_coverage"] == 2 / 3


def test_benchmark_refuses_bare_and_post_dispatch_eligibility_without_changing_numeric_results():
    path = Path(__file__).resolve().parents[1] / "scripts/native_reaction_benchmark.py"
    spec = importlib.util.spec_from_file_location("native_reaction_benchmark", path)
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    for evidence in (
        {},
        {
            "state_changed_ns": 1_000_000,
            "eligibility_observed_ns": 4_000_000,
            "policy_decision_ns": 2_500_000,
            "attempted": True,
            "input_dispatch_ns": 3_000_000,
            "eligibility_source": "native focused-window/key-state readback",
            "received_ns": 51_000_000,
        },
    ):
        row = {
            "verified": True,
            "event_latency_ms": 50,
            "critical_errors": [],
            "fast_eligible": True,
            **evidence,
        }
        summary = benchmark.summarize([row], elapsed_seconds=2, target_ms=100)
        assert summary["fast_coverage"] is None
        assert summary["fast_coverage_status"] == "NOT_MEASURED"
        assert summary["accuracy"] == summary["goodput_100"] == 1
        assert summary["goodput_per_second"] == 0.5
        assert summary["misses"] == 0
        assert summary["correct_event_latency_ms"] == {"p50": 50, "p95": 50, "p99": 50}


def test_benchmark_counts_eligible_unattempted_policy_decision_without_fake_dispatch():
    path = Path(__file__).resolve().parents[1] / "scripts/native_reaction_benchmark.py"
    spec = importlib.util.spec_from_file_location("native_reaction_benchmark", path)
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    row = {
        "verified": False,
        "event_latency_ms": None,
        "critical_errors": [],
        "fast_eligible": True,
        "attempted": False,
        "state_changed_ns": 1_000_000,
        "eligibility_observed_ns": 2_000_000,
        "policy_decision_ns": 3_000_000,
        "eligibility_source": "native focused-window/key-state readback",
    }
    summary = benchmark.summarize([row], elapsed_seconds=2, target_ms=100)
    assert summary["fast_coverage"] == 1
    assert summary["fast_coverage_status"] == "MEASURED"
    assert summary["accuracy"] == summary["goodput_100"] == 0
    row["input_dispatch_ns"] = 4_000_000
    summary = benchmark.summarize([row], elapsed_seconds=2, target_ms=100)
    assert summary["fast_coverage"] is None
    assert summary["fast_coverage_status"] == "NOT_MEASURED"
