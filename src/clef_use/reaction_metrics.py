"""Score predeclared native reaction opportunities, including failures and omissions."""

from __future__ import annotations

import math
from collections import Counter


def fast_path_eligibility(
    row: dict, *, state_change_ns: object, os_event_ns: object
) -> bool | None:
    """Return prospective eligibility, or None when its evidence is unavailable.

    The caller supplies actual observation provenance and timestamps from the
    same monotonic clock; this validator cannot establish their truth itself.
    Every opportunity needs an actual local policy decision boundary. Unattempted
    opportunities have no dispatch or native event; attempted ones need an actual
    dispatch timestamp, with an optional event when no native input was delivered.
    """
    eligibility_time = row.get("eligibility_observed_ns")
    decision = row.get("policy_decision_ns")
    dispatch = row.get("input_dispatch_ns")
    source = row.get("eligibility_source")
    if not (
        type(row.get("fast_eligible")) is bool
        and isinstance(source, str)
        and source.strip()
        and type(state_change_ns) is int
        and type(eligibility_time) is int
        and type(decision) is int
        and state_change_ns <= eligibility_time <= decision
    ):
        return None
    if row.get("attempted") is False:
        if dispatch is not None or os_event_ns is not None:
            return None
    elif row.get("attempted") is True:
        if not (
            type(dispatch) is int
            and decision <= dispatch
            and (os_event_ns is None or (type(os_event_ns) is int and dispatch <= os_event_ns))
        ):
            return None
    else:
        return None
    return row["fast_eligible"]


def summarize_reactions(scope: dict, rows: list[dict]) -> dict:
    ids = scope["opportunity_ids"]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("scope requires unique predeclared opportunities")
    declared = set(ids)
    observed = {}
    for row in rows:
        identity = row["id"]
        if identity not in declared or identity in observed:
            raise ValueError("undeclared or duplicate reaction opportunity")
        start, event = row.get("state_change_ns"), row.get("os_event_ns")
        if event is not None and (
            type(start) is not int or type(event) is not int or event < start
        ):
            raise ValueError("invalid native event timestamp")
        observed[identity] = row
    times, useful, fast, within, critical = [], 0, 0, 0, Counter()
    eligibility_known = 0
    sessions = set()
    for row in rows:
        sessions.add(row["session_id"])
        eligible = fast_path_eligibility(
            row,
            state_change_ns=row.get("state_change_ns"),
            os_event_ns=row.get("os_event_ns"),
        )
        if eligible is not None:
            eligibility_known += 1
            fast += eligible
        if row.get("critical_error"):
            critical[row["critical_error"]] += 1
        correct = (
            row.get("attempted")
            and row.get("correct_event")
            and row.get("effect_verified")
            and row.get("os_event_ns") is not None
        )
        if correct:
            elapsed = (row["os_event_ns"] - row["state_change_ns"]) / 1_000_000
            times.append(elapsed)
            useful += 1
            within += elapsed <= 100
    times.sort()

    def percentile(p):
        return times[max(0, math.ceil(p * len(times)) - 1)] if times else None

    count = len(ids)
    baseline = scope.get("baseline_accuracy")
    accuracy = useful / count
    coverage = fast / count if eligibility_known == count else None
    p95 = percentile(0.95)
    return {
        "opportunities": count,
        "attempted": sum(bool(row.get("attempted")) for row in rows),
        "sessions": len(sessions),
        "sampling_unit": "session/task; events within a session are correlated",
        "missing_opportunities": [identity for identity in ids if identity not in observed],
        "correct_useful_actions": useful,
        "accuracy": accuracy,
        "baseline_accuracy": baseline,
        "p50_reaction_ms": percentile(0.5),
        "p95_reaction_ms": p95,
        "p99_reaction_ms": percentile(0.99),
        "max_reaction_ms": max(times) if times else None,
        "latency_population": "independently verified correct native events only",
        "deadline_misses": count - within,
        "goodput_100": within / count,
        "fast_coverage": coverage,
        "fast_coverage_status": "MEASURED" if coverage is not None else "NOT_MEASURED",
        "critical_errors": dict(critical),
        "release_gate_pass": bool(
            count >= 1000
            and len(observed) == count
            and baseline is not None
            and accuracy >= baseline
            and p95 is not None
            and p95 <= 100
            and coverage is not None
            and coverage >= 0.8
            and not critical
        ),
        "limitations": "Zero observed critical errors is not proof of zero underlying risk.",
    }
