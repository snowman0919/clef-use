"""Score predeclared native reaction opportunities, including failures and omissions."""

from __future__ import annotations

import math
from collections import Counter


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
    sessions = set()
    for row in rows:
        sessions.add(row["session_id"])
        fast += bool(row.get("attempted") and row.get("fast_eligible"))
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
    accuracy, coverage = useful / count, fast / count
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
        "critical_errors": dict(critical),
        "release_gate_pass": bool(
            count >= 1000
            and len(observed) == count
            and baseline is not None
            and accuracy >= baseline
            and p95 is not None
            and p95 <= 100
            and coverage >= 0.8
            and not critical
        ),
        "limitations": "Zero observed critical errors is not proof of zero underlying risk.",
    }
