import pytest

from clef_use.reaction_metrics import summarize_reactions


def row(identity, **changes):
    return dict(
        id=identity,
        session_id="session",
        attempted=True,
        fast_eligible=True,
        state_change_ns=1_000_000,
        os_event_ns=51_000_000,
        correct_event=True,
        effect_verified=True,
        critical_error=None,
        **changes,
    )


def test_missing_and_late_events_remain_in_denominator():
    scope = {"opportunity_ids": ["a", "b", "c", "d"]}
    rows = [row("a"), row("b", **{})]
    rows[1]["os_event_ns"] = 151_000_000
    rows.append({**row("c"), "os_event_ns": None, "correct_event": False})
    report = summarize_reactions(scope, rows)
    assert report["opportunities"] == 4
    assert report["goodput_100"] == 0.25
    assert report["deadline_misses"] == 3
    assert report["fast_coverage"] == 0.75
    assert report["missing_opportunities"] == ["d"]
    assert not report["release_gate_pass"]


def test_duplicate_ids_and_negative_time_cannot_manufacture_samples():
    with pytest.raises(ValueError, match="duplicate"):
        summarize_reactions({"opportunity_ids": ["a"]}, [row("a"), row("a")])
    with pytest.raises(ValueError, match="timestamp"):
        summarize_reactions({"opportunity_ids": ["a"]}, [{**row("a"), "os_event_ns": 0}])


def test_zero_critical_errors_does_not_override_accuracy_regression():
    scope = {"opportunity_ids": [str(i) for i in range(1000)], "baseline_accuracy": 1.0}
    rows = [row(str(i)) for i in range(1000)]
    rows[0]["effect_verified"] = False
    report = summarize_reactions(scope, rows)
    assert report["p95_reaction_ms"] == 50
    assert report["accuracy"] == 0.999
    assert not report["release_gate_pass"]


def test_critical_input_leak_blocks_an_otherwise_fast_correct_run():
    scope = {"opportunity_ids": [str(i) for i in range(1000)], "baseline_accuracy": 1.0}
    rows = [row(str(i)) for i in range(1000)]
    rows[0]["critical_error"] = "input_leak"
    report = summarize_reactions(scope, rows)
    assert report["goodput_100"] == 1
    assert report["critical_errors"] == {"input_leak": 1}
    assert not report["release_gate_pass"]
