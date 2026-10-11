import copy

import pytest

from clef_use.reaction_metrics import summarize_reactions


def eligible_row(identity, **changes):
    value = dict(
        id=identity,
        session_id="session",
        attempted=True,
        fast_eligible=True,
        eligibility_observed_ns=2_000_000,
        policy_decision_ns=2_500_000,
        eligibility_source="native focused-window/key-state readback",
        input_dispatch_ns=3_000_000,
        state_change_ns=1_000_000,
        os_event_ns=51_000_000,
        correct_event=True,
        effect_verified=True,
        critical_error=None,
    )
    value.update(changes)
    return value


def test_missing_and_late_events_remain_in_denominator():
    scope = {"opportunity_ids": ["a", "b", "c", "d"]}
    rows = [eligible_row("a"), eligible_row("b")]
    rows[1]["os_event_ns"] = 151_000_000
    rows.append(eligible_row("c", os_event_ns=None, correct_event=False))
    report = summarize_reactions(scope, rows)
    assert report["opportunities"] == 4
    assert report["goodput_100"] == 0.25
    assert report["deadline_misses"] == 3
    assert report["fast_coverage"] is None
    assert report["fast_coverage_status"] == "NOT_MEASURED"
    assert report["missing_opportunities"] == ["d"]
    assert not report["release_gate_pass"]


def test_duplicate_ids_and_negative_time_cannot_manufacture_samples():
    with pytest.raises(ValueError, match="duplicate"):
        summarize_reactions({"opportunity_ids": ["a"]}, [eligible_row("a"), eligible_row("a")])
    with pytest.raises(ValueError, match="timestamp"):
        summarize_reactions({"opportunity_ids": ["a"]}, [eligible_row("a", os_event_ns=0)])


def test_zero_critical_errors_does_not_override_accuracy_regression():
    scope = {"opportunity_ids": [str(i) for i in range(1000)], "baseline_accuracy": 1.0}
    rows = [eligible_row(str(i)) for i in range(1000)]
    rows[0]["effect_verified"] = False
    report = summarize_reactions(scope, rows)
    assert report["p95_reaction_ms"] == 50
    assert report["accuracy"] == 0.999
    assert not report["release_gate_pass"]


def test_critical_input_leak_blocks_an_otherwise_fast_correct_run():
    scope = {"opportunity_ids": [str(i) for i in range(1000)], "baseline_accuracy": 1.0}
    rows = [eligible_row(str(i)) for i in range(1000)]
    rows[0]["critical_error"] = "input_leak"
    report = summarize_reactions(scope, rows)
    assert report["goodput_100"] == 1
    assert report["critical_errors"] == {"input_leak": 1}
    assert not report["release_gate_pass"]


def test_historical_unknown_eligibility_cannot_claim_zero_coverage_or_release():
    rows = [eligible_row(str(i), fast_eligible=None) for i in range(1000)]
    report = summarize_reactions(
        {"opportunity_ids": [str(i) for i in range(1000)], "baseline_accuracy": 1.0}, rows
    )
    assert report["fast_coverage"] is None
    assert report["fast_coverage_status"] == "NOT_MEASURED"
    assert not report["release_gate_pass"]
    assert report["accuracy"] == report["goodput_100"] == 1.0
    assert report["p95_reaction_ms"] == 50.0


@pytest.mark.parametrize(
    "changes",
    [
        {"fast_eligible": "true"},
        {"fast_eligible": 1},
        {"eligibility_source": None},
        {"eligibility_source": "  "},
        {"eligibility_observed_ns": None},
        {"eligibility_observed_ns": True},
        {"input_dispatch_ns": None},
        {"input_dispatch_ns": True},
        {"policy_decision_ns": None},
        {"policy_decision_ns": True},
        {"policy_decision_ns": 1_500_000},
        {"policy_decision_ns": 4_000_000},
        {"eligibility_observed_ns": 0},
        {"eligibility_observed_ns": 4_000_000},
        {"eligibility_observed_ns": 52_000_000, "input_dispatch_ns": 53_000_000},
        {"input_dispatch_ns": 52_000_000},
    ],
)
def test_unproven_or_post_dispatch_eligibility_is_unknown(changes):
    report = summarize_reactions({"opportunity_ids": ["a"]}, [eligible_row("a", **changes)])
    assert report["fast_coverage"] is None
    assert report["fast_coverage_status"] == "NOT_MEASURED"
    assert report["accuracy"] == report["goodput_100"] == 1.0
    assert report["p95_reaction_ms"] == 50.0
    assert not report["release_gate_pass"]


def test_missing_metadata_and_missing_opportunities_prevent_measured_coverage():
    row = eligible_row("a")
    del row["eligibility_source"]
    report = summarize_reactions({"opportunity_ids": ["a"]}, [row])
    assert report["fast_coverage"] is None
    report = summarize_reactions({"opportunity_ids": ["a", "b"]}, [eligible_row("a")])
    assert report["fast_coverage"] is None
    assert report["fast_coverage_status"] == "NOT_MEASURED"
    assert report["missing_opportunities"] == ["b"]
    assert report["accuracy"] == report["goodput_100"] == 0.5


def test_observed_eligibility_is_independent_of_attempt_success_and_deadline():
    rows = [
        eligible_row("a", os_event_ns=151_000_000),
        eligible_row("b", fast_eligible=False),
        eligible_row(
            "c", attempted=False, input_dispatch_ns=None, os_event_ns=None, correct_event=False
        ),
    ]
    original = copy.deepcopy(rows)
    report = summarize_reactions({"opportunity_ids": ["a", "b", "c"]}, rows)
    assert report["fast_coverage"] == 2 / 3
    assert report["fast_coverage_status"] == "MEASURED"
    assert report["accuracy"] == 2 / 3
    assert report["goodput_100"] == 1 / 3
    assert report["deadline_misses"] == 2
    assert report["p50_reaction_ms"] == 50
    assert report["p95_reaction_ms"] == report["p99_reaction_ms"] == 150
    assert report["max_reaction_ms"] == 150
    assert rows == original


def test_real_zero_eligibility_is_measured_and_cannot_pass_release():
    report = summarize_reactions(
        {"opportunity_ids": ["a"]}, [eligible_row("a", fast_eligible=False)]
    )
    assert report["fast_coverage"] == 0
    assert report["fast_coverage_status"] == "MEASURED"
    assert not report["release_gate_pass"]


def test_complete_prospectively_observed_eligible_population_can_pass_existing_gate():
    ids = [str(i) for i in range(1000)]
    report = summarize_reactions(
        {"opportunity_ids": ids, "baseline_accuracy": 1.0},
        [eligible_row(identity) for identity in ids],
    )
    assert report["fast_coverage"] == 1.0
    assert report["fast_coverage_status"] == "MEASURED"
    assert report["release_gate_pass"]


def test_bare_historical_true_flags_do_not_qualify_a_release():
    rows = [eligible_row(str(i)) for i in range(1000)]
    for row in rows:
        del row["eligibility_observed_ns"]
        del row["eligibility_source"]
        del row["policy_decision_ns"]
        del row["input_dispatch_ns"]
    report = summarize_reactions(
        {"opportunity_ids": [str(i) for i in range(1000)], "baseline_accuracy": 1.0}, rows
    )
    assert report["fast_coverage"] is None
    assert report["fast_coverage_status"] == "NOT_MEASURED"
    assert not report["release_gate_pass"]
    assert report["accuracy"] == report["goodput_100"] == 1.0
    assert report["p95_reaction_ms"] == 50.0


def test_unattempted_eligibility_needs_policy_boundary_without_dispatch_or_event():
    row = eligible_row(
        "a", attempted=False, input_dispatch_ns=None, os_event_ns=None, correct_event=False
    )
    report = summarize_reactions({"opportunity_ids": ["a"]}, [row])
    assert report["fast_coverage"] == 1
    assert report["fast_coverage_status"] == "MEASURED"
    assert report["attempted"] == 0
    assert report["accuracy"] == report["goodput_100"] == 0
    assert report["p95_reaction_ms"] is None
    del row["policy_decision_ns"]
    report = summarize_reactions({"opportunity_ids": ["a"]}, [row])
    assert report["fast_coverage"] is None
    assert report["fast_coverage_status"] == "NOT_MEASURED"


@pytest.mark.parametrize(
    "changes",
    [
        {"attempted": None},
        {"attempted": "false"},
        {"attempted": False},
        {"attempted": False, "input_dispatch_ns": None},
        {"attempted": False, "os_event_ns": None},
    ],
)
def test_missing_attempt_evidence_or_unattempted_dispatch_event_contradiction_is_unknown(changes):
    report = summarize_reactions({"opportunity_ids": ["a"]}, [eligible_row("a", **changes)])
    assert report["fast_coverage"] is None
    assert report["fast_coverage_status"] == "NOT_MEASURED"
    assert not report["release_gate_pass"]
