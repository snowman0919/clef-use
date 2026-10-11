import importlib.util
from pathlib import Path


def test_summary_keeps_failures_and_critical_errors_in_fast_coverage_denominator():
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
    assert summary["fast_correct"] == 3 and summary["fast_coverage"] == 0.375
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
    assert result["accuracy"] == 0 and result["fast_coverage"] == 0
    assert result["misses"] == 1 and result["goodput_per_second"] == 0
